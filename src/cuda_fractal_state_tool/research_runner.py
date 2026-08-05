from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .agent_bundle import AgentBundle
from .research_context import (
    build_planner_context,
    build_review_context,
    build_synthesis_context,
    seal_communication_context,
)
from .research_cost import ResearchProviderStage
from .research_protocol import ResearchAction, canonical_json_sha256
from .research_provider import ResearchProviderDispatcher
from .research_results import (
    ResearchResultDisposition,
    ResearchResultService,
    SealedResearchResult,
)
from .research_session import ResearchSessionController, ResearchSessionState
from .scientific_record import (
    ArtifactRoot,
    ArtifactRootRegistry,
    EvidenceReference,
    make_evidence_reference,
)


@dataclass(frozen=True)
class ResearchSessionRunResult:
    result: SealedResearchResult
    disposition: ResearchResultDisposition
    current_bundle: AgentBundle
    attempts_consumed: int
    alternate_report_available: bool


class ResearchSessionRunner:
    """Bounded blocking route intended to run inside the shared async job owner."""

    def __init__(
        self,
        *,
        controller: ResearchSessionController,
        provider: ResearchProviderDispatcher,
        results: ResearchResultService,
    ) -> None:
        if provider.run_store.run_dir != controller.run_store.run_dir:
            raise ValueError("Research runner services disagree on run ownership")
        self.controller = controller
        self.provider = provider
        self.results = results

    def run(self) -> ResearchSessionRunResult:
        alternate_required = (
            self.controller.brief.communication_profile
            == "adult_beginner_carl_sagan"
        )
        try:
            while self.controller.state is ResearchSessionState.PLANNING:
                planner = build_planner_context(
                    self.controller.brief, self.controller.current_bundle
                )
                response = self.provider.dispatch(
                    stage=ResearchProviderStage.PLANNER,
                    turn_id=f"planner-{self.controller.attempts_consumed + 1:02d}",
                    prompt=planner.prompt,
                    packet_dir=self.controller.current_bundle.packet_dir,
                    planner_may_execute=(
                        self.controller.attempts_consumed
                        < self.controller.brief.maximum_experiment_rounds
                    ),
                    correction_available=not self.controller.correction_used,
                    alternate_communication_required=alternate_required,
                )
                try:
                    decision = self.controller.prepare_planner_response(
                        response.output_text
                    )
                except Exception as first_error:
                    if not self.controller.correction_available:
                        raise
                    correction_prompt = (
                        planner.prompt
                        + "\n\nThe prior response failed local protocol or payload validation. "
                        + "Return one corrected complete response. No further correction is available.\n\n"
                        + f"Local error: {first_error}\n\nPrior response:\n{response.output_text}"
                    )
                    corrected = self.provider.dispatch(
                        stage=ResearchProviderStage.CORRECTION,
                        turn_id=f"correction-{self.controller.attempts_consumed + 1:02d}",
                        prompt=correction_prompt,
                        packet_dir=self.controller.current_bundle.packet_dir,
                        planner_may_execute=True,
                        correction_available=False,
                        alternate_communication_required=alternate_required,
                    )
                    decision = self.controller.prepare_planner_response(
                        corrected.output_text,
                        correction=True,
                    )
                if decision.action in {
                    ResearchAction.ANSWER_READY,
                    ResearchAction.UNRESOLVED_REPORT,
                }:
                    break
                evidence = self.controller.execute_prepared()
                review_context = build_review_context(
                    run_store=self.controller.run_store,
                    brief=self.controller.brief,
                    bundle=self.controller.current_bundle,
                    evidence=evidence,
                )
                review = self.provider.dispatch(
                    stage=ResearchProviderStage.REVIEW,
                    turn_id=f"review-{evidence.attempt_number:02d}",
                    prompt=review_context.prompt,
                    packet_dir=self.controller.current_bundle.packet_dir,
                    additional_resources=review_context.resources,
                    alternate_communication_required=alternate_required,
                )
                self.controller.apply_review(review.output_text)

            if self.controller.state is not ResearchSessionState.READY_FOR_SYNTHESIS:
                raise RuntimeError("Research controller did not reach the synthesis boundary")
            roots, references = self._evidence_authority()
            terminal = None
            if self.controller.terminal_planner_decision is not None:
                terminal = {
                    "action": self.controller.terminal_planner_decision.action.value,
                    "fields": self.controller.terminal_planner_decision.fields,
                    "source_response_sha256": (
                        self.controller.terminal_planner_decision.source_response_sha256
                    ),
                    "authority_note": "Provisional planner output; not scientific evidence.",
                }
            synthesis = build_synthesis_context(
                run_store=self.controller.run_store,
                brief=self.controller.brief,
                current_bundle=self.controller.current_bundle,
                packet_lineage=self.controller.current_packet_lineage,
                evidence_references=references,
                roots=roots,
                terminal_planner_decision=terminal,
            )
            brief_sha = canonical_json_sha256(self.controller.brief.to_dict())
            try:
                synthesis_response = self.provider.dispatch(
                    stage=ResearchProviderStage.SYNTHESIS,
                    turn_id="synthesis-01",
                    prompt=synthesis.prompt,
                    packet_dir=None,
                    additional_resources=synthesis.resources,
                    alternate_communication_required=alternate_required,
                )
            except Exception as exc:
                sealed = self.results.seal_synthesis_failure(
                    str(exc),
                    research_brief_sha256=brief_sha,
                    current_bundle=self.controller.current_bundle,
                )
            else:
                sealed = self.results.seal_synthesis(
                    synthesis_response.output_text,
                    roots=roots,
                    research_brief_sha256=brief_sha,
                    current_bundle=self.controller.current_bundle,
                )
            disposition = sealed.disposition
            alternate_available = False
            if alternate_required and sealed.scientific_record.conclusion.value != "NO_SCIENTIFIC_CONCLUSION":
                communication = seal_communication_context(
                    run_store=self.controller.run_store,
                    record=sealed.scientific_record,
                )
                try:
                    rendered = self.provider.dispatch(
                        stage=ResearchProviderStage.COMMUNICATION,
                        turn_id="communication-01",
                        prompt=communication.prompt,
                        packet_dir=None,
                        additional_resources=communication.resources,
                    )
                except Exception as exc:
                    disposition = self.results.seal_communication_failure(
                        str(exc),
                        result=sealed,
                        required_deliverable=True,
                    )
                else:
                    report, disposition = self.results.seal_alternate_communication(
                        rendered.output_text,
                        result=sealed,
                        required_deliverable=True,
                    )
                    alternate_available = report is not None
            return ResearchSessionRunResult(
                sealed,
                disposition,
                self.controller.current_bundle,
                self.controller.attempts_consumed,
                alternate_available,
            )
        finally:
            self.provider.transport.close_owned_files(
                run_store=self.controller.run_store,
                reason="question_research_session_closed",
            )

    def _evidence_authority(
        self,
    ) -> tuple[ArtifactRootRegistry, tuple[EvidenceReference, ...]]:
        roots: list[ArtifactRoot] = []
        references: list[EvidenceReference] = []
        run_manifest = self.controller.run_store.manifest_path
        run_root = ArtifactRoot(
            "question_run",
            self.controller.run_store.run_dir,
            hashlib.sha256(run_manifest.read_bytes()).hexdigest(),
        )
        roots.append(run_root)
        for attempt in range(1, self.controller.attempts_consumed + 1):
            attempt_dir = self.controller.run_store.run_dir / "attempts" / f"{attempt:03d}"
            for filename, role in (
                ("round-plan.json", "locked_round_plan"),
                ("execution-ref.json", "experiment_execution_reference"),
                ("review-decision.json", "research_review_decision"),
            ):
                path = attempt_dir / filename
                if path.is_file():
                    references.append(
                        make_evidence_reference(
                            root=run_root,
                            path=path,
                            artifact_role=role,
                        )
                    )
        for evidence in self.controller.execution_history:
            if evidence.proof is not None:
                proof = evidence.proof
                proof_root = ArtifactRoot("proof", proof.proof_dir, proof.binding_sha256)
                roots.append(proof_root)
                references.append(
                    make_evidence_reference(
                        root=proof_root,
                        path=proof.receipt_path,
                        artifact_role="proof_receipt",
                        proof_id=proof.proof_id,
                    )
                )
                if proof.candidate_display_path is not None:
                    references.append(
                        make_evidence_reference(
                            root=proof_root,
                            path=proof.candidate_display_path,
                            artifact_role="proof_candidate_display",
                            proof_id=proof.proof_id,
                        )
                    )
            if evidence.sweep is not None:
                sweep = evidence.sweep
                sweep_root = ArtifactRoot(
                    "sweep",
                    sweep.sweep_dir,
                    hashlib.sha256(sweep.receipt_path.read_bytes()).hexdigest(),
                )
                roots.append(sweep_root)
                references.append(
                    make_evidence_reference(
                        root=sweep_root,
                        path=sweep.receipt_path,
                        artifact_role="scalar_sweep_receipt",
                        sweep_id=sweep.sweep_id,
                    )
                )
                if sweep.web_review_dir is not None:
                    for filename, role in (
                        ("sweep-evidence.json", "scalar_sweep_evidence"),
                        ("contact-sheet.png", "scalar_sweep_contact_sheet"),
                    ):
                        references.append(
                            make_evidence_reference(
                                root=sweep_root,
                                path=sweep.web_review_dir / filename,
                                artifact_role=role,
                                sweep_id=sweep.sweep_id,
                            )
                        )
        packet = self.controller.current_bundle
        packet_root = ArtifactRoot("packet", packet.packet_dir, packet.manifest_sha256)
        roots.append(packet_root)
        for filename, role in (
            ("manifest.json", "packet_manifest"),
            ("packet.md", "packet_index"),
            ("state.json", "engine_state_authority"),
        ):
            path = packet.packet_dir / filename
            if path.is_file():
                references.append(
                    make_evidence_reference(
                        root=packet_root,
                        path=path,
                        artifact_role=role,
                    )
                )
        return ArtifactRootRegistry(tuple(roots)), tuple(references)
