from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .agent_bundle import AgentBundle
from .json_utils import loads_strict_no_duplicates
from .research_context import (
    build_planner_context,
    build_review_context,
    build_synthesis_context,
    seal_prior_round_ledger,
    seal_communication_context,
)
from .research_cost import ResearchProviderStage
from .research_protocol import ResearchAction, canonical_json_sha256
from .research_provider import ResearchProviderDispatcher
from .openai_transport import DispatchAuthorizationRejected
from .runtime_surface import sha256_file
from .research_results import (
    ResearchResultDisposition,
    ResearchResultService,
    SealedResearchResult,
)
from .research_session import (
    ResearchExecutionEvidence,
    ResearchSessionController,
    ResearchSessionState,
)
from .scientific_record import (
    ArtifactRoot,
    ArtifactRootRegistry,
    EvidenceReference,
    make_evidence_reference,
)
from .sweep_presentation import compose_research_visual_summary


@dataclass(frozen=True)
class ResearchSessionRunResult:
    result: SealedResearchResult
    disposition: ResearchResultDisposition
    current_bundle: AgentBundle
    attempts_consumed: int
    alternate_report_available: bool
    visual_paths: tuple[Path, ...]
    controller_disposition: str


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
        self._provider_cleanup_attempted = False

    @staticmethod
    def _execution_blocker(evidence: ResearchExecutionEvidence) -> str | None:
        if evidence.sweep is not None and evidence.sweep.disposition == "AUTHORITY_DRIFT":
            return (
                "Published runtime or packet authority changed during the scalar sweep; "
                "no review, continuation, promotion, or synthesis is authorized."
            )
        return None

    def _close_execution_blocker(
        self,
        *,
        reason: str,
        controller_disposition: str,
    ) -> ResearchSessionRunResult:
        sealed = self.results.seal_synthesis_failure(
            reason,
            research_brief_sha256=canonical_json_sha256(
                self.controller.brief.to_dict()
            ),
            current_bundle=self.controller.current_bundle,
        )
        return self._finalize_run(
            sealed=sealed,
            disposition=ResearchResultDisposition.MANUAL_REVIEW_REQUIRED,
            alternate_available=False,
            controller_disposition=controller_disposition,
            reason=reason,
        )

    def run(self) -> ResearchSessionRunResult:
        alternate_required = (
            self.controller.brief.communication_profile
            == "adult_beginner_carl_sagan"
        )
        try:
            while self.controller.state is ResearchSessionState.PLANNING:
                ledger_path = seal_prior_round_ledger(
                    run_store=self.controller.run_store,
                    bundle=self.controller.current_bundle,
                    packet_lineage=list(
                        getattr(self.controller, "current_packet_lineage", [])
                    ),
                    attempts_consumed=self.controller.attempts_consumed,
                    maximum_experiment_rounds=(
                        self.controller.brief.maximum_experiment_rounds
                    ),
                    spent_cost_usd=str(
                        getattr(getattr(self.provider, "cost", None), "spent_cost_usd", "0")
                    ),
                    hard_budget_usd=str(
                        getattr(
                            getattr(self.provider, "cost", None),
                            "hard_budget_usd",
                            self.controller.brief.hard_dollar_budget,
                        )
                    ),
                )
                planner = build_planner_context(
                    self.controller.brief,
                    self.controller.current_bundle,
                    prior_round_ledger_path=ledger_path,
                )
                response = self.provider.dispatch(
                    stage=ResearchProviderStage.PLANNER,
                    turn_id=f"planner-{self.controller.attempts_consumed + 1:02d}",
                    prompt=planner.prompt,
                    packet_dir=self.controller.current_bundle.packet_dir,
                    additional_resources=planner.resources,
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
                        additional_resources=planner.resources,
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
                blocker = self._execution_blocker(evidence)
                if blocker is not None:
                    return self._close_execution_blocker(
                        reason=blocker,
                        controller_disposition="AUTHORITY_DRIFT",
                    )
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
            except DispatchAuthorizationRejected:
                raise
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
                except DispatchAuthorizationRejected:
                    raise
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
            result = self._finalize_run(
                sealed=sealed,
                disposition=disposition,
                alternate_available=alternate_available,
                controller_disposition=disposition.value,
            )
            return result
        except DispatchAuthorizationRejected as exc:
            brief_sha = canonical_json_sha256(self.controller.brief.to_dict())
            sealed = self.results.seal_synthesis_failure(
                f"BUDGET_EXHAUSTED: {exc}",
                research_brief_sha256=brief_sha,
                current_bundle=self.controller.current_bundle,
            )
            result = self._finalize_run(
                sealed=sealed,
                disposition=ResearchResultDisposition.MANUAL_REVIEW_REQUIRED,
                alternate_available=False,
                controller_disposition="BUDGET_EXHAUSTED",
                reason=str(exc),
            )
            return result
        finally:
            if not self._provider_cleanup_attempted:
                self.provider.transport.close_owned_files(
                    run_store=self.controller.run_store,
                    reason="question_research_session_aborted",
                )

    def _event_projection(self) -> dict[str, Any]:
        active_path = self.controller.run_store.active_turn_path
        if active_path.is_file():
            return dict(self.controller.run_store.load_active_turn()["projection"])
        return {
            "state": getattr(self.controller.state, "value", str(self.controller.state)),
            "disposition": "RUNNING",
            "attempts_consumed": self.controller.attempts_consumed,
            "maximum_experiment_rounds": (
                self.controller.brief.maximum_experiment_rounds
            ),
            "current_research_base": {
                "packet_id": self.controller.current_bundle.packet_id,
                "manifest_sha256": self.controller.current_bundle.manifest_sha256,
                "finding_id": self.controller.current_bundle.finding_id,
            },
            "current_packet_lineage": list(
                getattr(self.controller, "current_packet_lineage", [])
            ),
            "pending_round_plan_contract_sha256": None,
        }

    def _append_result_event(
        self,
        event_type: str,
        payload: dict[str, Any],
        **projection_updates: Any,
    ) -> None:
        projection = self._event_projection()
        projection.update(projection_updates)
        self.controller.run_store.record_transition(event_type, payload, projection)

    def _seal_navigation_workspace(
        self,
        *,
        sealed: SealedResearchResult,
        disposition: ResearchResultDisposition,
        controller_disposition: str,
        cleanup_complete: bool,
        reason: str | None,
    ) -> tuple[Path | None, Path, Path]:
        visual_sources = self._visual_paths()
        visual_summary: Path | None = None
        if visual_sources:
            summary_bytes, summary_receipt = compose_research_visual_summary(
                tuple(
                    (f"Experiment attempt {index}", path)
                    for index, path in enumerate(visual_sources, start=1)
                )
            )
            visual_summary = self.controller.run_store.write_evidence_once_bytes(
                "result/visual-summary.png", summary_bytes
            )
            self.controller.run_store.write_evidence_once_json(
                "result/visual-summary-receipt.json", summary_receipt
            )

        entries: list[dict[str, Any]] = []

        def add(role: str, path: Path, *, identity: dict[str, Any] | None = None) -> None:
            if not path.is_file():
                return
            entries.append(
                {
                    "artifact_role": role,
                    "local_path": str(path.resolve()),
                    "sha256": sha256_file(path),
                    "identity": identity or {},
                }
            )

        run_dir = self.controller.run_store.run_dir
        for relative, role in (
            ("manifest.json", "question_run_manifest"),
            ("result/scientific-record.json", "scientific_record"),
            ("result/working-session.md", "working_session_report"),
            ("result/disposition.json", "result_disposition"),
            ("result/visual-summary.png", "visual_summary"),
            ("result/visual-summary-receipt.json", "visual_summary_receipt"),
            ("transport/provider-file-cleanup.json", "provider_cleanup_receipt"),
        ):
            add(role, run_dir / relative)
        packet = self.controller.current_bundle
        for filename, role in (
            ("packet.md", "current_packet_index"),
            ("manifest.json", "current_packet_manifest"),
            ("state.json", "current_packet_state"),
        ):
            add(
                role,
                packet.packet_dir / filename,
                identity={"packet_id": packet.packet_id},
            )
        for evidence in self.controller.execution_history:
            attempt_identity = {"attempt_number": evidence.attempt_number}
            attempt_dir = run_dir / "attempts" / f"{evidence.attempt_number:03d}"
            for filename, role in (
                ("round-plan.json", "locked_round_plan"),
                ("execution-ref.json", "experiment_execution_reference"),
                ("review-decision.json", "research_review_decision"),
            ):
                add(role, attempt_dir / filename, identity=attempt_identity)
            proofs: list[tuple[Any, dict[str, Any]]] = []
            if evidence.proof is not None:
                proofs.append(
                    (evidence.proof, {**attempt_identity, "proof_id": evidence.proof.proof_id})
                )
            if evidence.sweep is not None:
                sweep = evidence.sweep
                sweep_identity = {**attempt_identity, "sweep_id": sweep.sweep_id}
                receipt_path = getattr(sweep, "receipt_path", None)
                if isinstance(receipt_path, Path):
                    add("scalar_sweep_receipt", receipt_path, identity=sweep_identity)
                if sweep.web_review_dir is not None:
                    add(
                        "scalar_sweep_contact_sheet",
                        sweep.web_review_dir / "contact-sheet.png",
                        identity=sweep_identity,
                    )
                    add(
                        "scalar_sweep_evidence",
                        sweep.web_review_dir / "sweep-evidence.json",
                        identity=sweep_identity,
                    )
                for member in sweep.members:
                    if member.proof_result is not None:
                        proofs.append(
                            (
                                member.proof_result,
                                {
                                    **sweep_identity,
                                    "member_index": member.index,
                                    "proof_id": member.proof_result.proof_id,
                                },
                            )
                        )
            for proof, identity in proofs:
                add("proof_receipt", proof.receipt_path, identity=identity)
                if proof.candidate_display_path is not None:
                    add(
                        "proof_candidate_display",
                        proof.candidate_display_path,
                        identity=identity,
                    )
        entries.sort(key=lambda item: (item["artifact_role"], item["local_path"]))
        index_path = self.controller.run_store.write_evidence_once_json(
            "result/artifact-index.json",
            {
                "research_artifact_index_version": 1,
                "question_run_id": run_dir.name,
                "navigation_only": True,
                "scientific_authority": "referenced artifacts and receipts",
                "artifacts": entries,
            },
        )
        closeout = {
            "research_closeout_version": 1,
            "controller_disposition": controller_disposition,
            "scientific_conclusion": sealed.scientific_record.conclusion.value,
            "scientific_record_sha256": sealed.scientific_record.sha256,
            "attempts_consumed": self.controller.attempts_consumed,
            "current_research_base": {
                "packet_id": packet.packet_id,
                "manifest_sha256": packet.manifest_sha256,
                "finding_id": packet.finding_id,
                "human_acceptance": False,
                "launched": False,
            },
            "packet_lineage": list(
                getattr(self.controller, "current_packet_lineage", [])
            ),
            "provider_cleanup_complete": cleanup_complete,
            "spent_cost_usd": str(
                getattr(getattr(self.provider, "cost", None), "spent_cost_usd", "0")
            ),
            "artifact_index_sha256": sha256_file(index_path),
            "visual_summary_sha256": (
                sha256_file(visual_summary) if visual_summary is not None else None
            ),
            "reason": reason,
            "provider_retry_authorized": False,
            "human_acceptance": False,
        }
        closeout_path = self.controller.run_store.write_evidence_once_json(
            "result/closeout.json", closeout
        )
        self.controller.run_store.write_evidence_once_json(
            "result/controller-closeout.json", closeout
        )
        return visual_summary, index_path, closeout_path

    def _finalize_run(
        self,
        *,
        sealed: SealedResearchResult,
        disposition: ResearchResultDisposition,
        alternate_available: bool,
        controller_disposition: str,
        reason: str | None = None,
    ) -> ResearchSessionRunResult:
        self._append_result_event(
            "scientific_record_sealed",
            {
                "scientific_conclusion": sealed.scientific_record.conclusion.value,
                "scientific_record_sha256": sealed.scientific_record.sha256,
                "validation_error": sealed.synthesis_validation_error,
            },
            final_record_sha256=sealed.scientific_record.sha256,
            scientific_conclusion=sealed.scientific_record.conclusion.value,
        )
        self._append_result_event(
            "working_report_rendered",
            {
                "path": str(sealed.working_report_path.resolve()),
                "sha256": sha256_file(sealed.working_report_path),
            },
            final_record_sha256=sealed.scientific_record.sha256,
            scientific_conclusion=sealed.scientific_record.conclusion.value,
        )
        cleanup_complete = True
        cleanup_error: str | None = None
        self._provider_cleanup_attempted = True
        try:
            self.provider.transport.close_owned_files(
                run_store=self.controller.run_store,
                reason="question_research_session_closed",
            )
        except Exception as exc:
            cleanup_complete = False
            cleanup_error = str(exc)
            disposition = ResearchResultDisposition.MANUAL_REVIEW_REQUIRED
            controller_disposition = "PROVIDER_CLEANUP_FAILED"
            reason = cleanup_error if reason is None else f"{reason}; {cleanup_error}"
        cleanup_path = (
            self.controller.run_store.run_dir / "transport/provider-file-cleanup.json"
        )
        if not cleanup_path.is_file():
            self.controller.run_store.write_evidence_once_json(
                "transport/provider-file-cleanup.json",
                {
                    "reason": "question_research_session_closed",
                    "cleanup_complete": cleanup_complete,
                    "remaining_provider_file_ids": [],
                    "failures": [] if cleanup_error is None else [cleanup_error],
                },
            )
        self._append_result_event(
            "provider_cleanup_completed",
            {
                "cleanup_complete": cleanup_complete,
                "receipt_sha256": sha256_file(cleanup_path),
                "error": cleanup_error,
            },
            cleanup_complete=cleanup_complete,
        )
        disposition_path = self.controller.run_store.run_dir / "result/disposition.json"
        current_disposition = json.loads(disposition_path.read_text(encoding="utf-8"))
        if current_disposition.get("controller_disposition") != controller_disposition:
            current_disposition["controller_disposition"] = controller_disposition
            current_disposition["error"] = reason
            self.controller.run_store.write_evidence_json(
                "result/disposition.json", current_disposition
            )
        visual_summary, index_path, closeout_path = self._seal_navigation_workspace(
            sealed=sealed,
            disposition=disposition,
            controller_disposition=controller_disposition,
            cleanup_complete=cleanup_complete,
            reason=reason,
        )
        terminal_state = (
            "COMPLETED"
            if disposition is ResearchResultDisposition.COMPLETED
            else "MANUAL_REVIEW_REQUIRED"
        )
        self._append_result_event(
            "research_session_closed",
            {
                "controller_disposition": controller_disposition,
                "scientific_conclusion": sealed.scientific_record.conclusion.value,
                "scientific_record_sha256": sealed.scientific_record.sha256,
                "artifact_index_sha256": sha256_file(index_path),
                "closeout_sha256": sha256_file(closeout_path),
                "cleanup_complete": cleanup_complete,
                "provider_retry_authorized": False,
            },
            state=terminal_state,
            disposition=controller_disposition,
            controller_disposition=controller_disposition,
            scientific_conclusion=sealed.scientific_record.conclusion.value,
            pending_round_plan_contract_sha256=None,
            final_record_sha256=sealed.scientific_record.sha256,
            cleanup_complete=cleanup_complete,
        )
        visuals = self._visual_paths()
        if visual_summary is not None:
            visuals = (*visuals, visual_summary)
        return ResearchSessionRunResult(
            sealed,
            disposition,
            self.controller.current_bundle,
            self.controller.attempts_consumed,
            alternate_available,
            visuals,
            controller_disposition,
        )

    def _visual_paths(self) -> tuple[Path, ...]:
        paths: list[Path] = []
        for evidence in self.controller.execution_history:
            if evidence.proof is not None and evidence.proof.candidate_display_path is not None:
                paths.append(evidence.proof.candidate_display_path)
            if evidence.sweep is not None and evidence.sweep.web_review_dir is not None:
                contact = evidence.sweep.web_review_dir / "contact-sheet.png"
                if contact.is_file():
                    paths.append(contact.resolve())
        return tuple(paths)

    def _seal_requested_value_evidence(self) -> Path | None:
        """Project proof-owned value receipts into one compact synthesis authority.

        The projection avoids uploading every full proof receipt while retaining
        the exact requested/emitted values and the hashes of the receipts that
        supplied them.  It is derived only from in-process proof results already
        owned by this run.
        """

        entries: dict[str, dict[str, Any]] = {}
        for execution in self.controller.execution_history:
            proofs: list[tuple[Any, str | None, int | None]] = []
            if execution.proof is not None:
                proofs.append((execution.proof, None, None))
            if execution.sweep is not None:
                for member in execution.sweep.members:
                    if member.proof_result is not None:
                        proofs.append(
                            (member.proof_result, execution.sweep.sweep_id, member.index)
                        )
            for proof, sweep_id, member_index in proofs:
                if sha256_file(proof.receipt_path) != proof.receipt_sha256:
                    raise ValueError(
                        f"Proof receipt changed before synthesis: {proof.proof_id}"
                    )
                document = loads_strict_no_duplicates(
                    proof.receipt_path.read_text(encoding="utf-8")
                )
                if not isinstance(document, dict):
                    raise ValueError(f"Proof receipt is not an object: {proof.proof_id}")
                receipts = document.get("requested_value_receipts")
                if isinstance(receipts, dict):
                    receipts = [receipts]
                if not isinstance(receipts, list):
                    raise ValueError(
                        f"Proof receipt has invalid requested values: {proof.proof_id}"
                    )
                for receipt in receipts:
                    if not isinstance(receipt, dict):
                        raise ValueError(
                            f"Proof receipt has malformed requested value: {proof.proof_id}"
                        )
                    path = receipt.get("path")
                    if (
                        not isinstance(path, str)
                        or not path
                        or "requested_value" not in receipt
                        or "engine_emitted_value" not in receipt
                    ):
                        raise ValueError(
                            f"Proof receipt has incomplete requested value: {proof.proof_id}"
                        )
                    value = {
                        "path": path,
                        "requested_value": receipt.get("requested_value"),
                        "canonical_value_status": (
                            "available" if "canonical_value" in receipt else "unavailable"
                        ),
                        "canonical_value": receipt.get("canonical_value"),
                        "engine_emitted_value": receipt.get("engine_emitted_value"),
                    }
                    identity = json.dumps(
                        {
                            "path": value["path"],
                            "requested_value": value["requested_value"],
                            "engine_emitted_value": value["engine_emitted_value"],
                        },
                        sort_keys=True,
                        ensure_ascii=False,
                        allow_nan=False,
                        separators=(",", ":"),
                    )
                    source = {
                        "proof_id": proof.proof_id,
                        "proof_receipt_sha256": proof.receipt_sha256,
                        "sweep_id": sweep_id,
                        "member_index": member_index,
                    }
                    if identity not in entries:
                        entries[identity] = {**value, "sources": [source]}
                    else:
                        existing = entries[identity]
                        if (
                            existing["canonical_value_status"]
                            != value["canonical_value_status"]
                            or existing["canonical_value"] != value["canonical_value"]
                        ):
                            raise ValueError(
                                "Proof receipts disagree on canonical value for "
                                f"{path} requested as {value['requested_value']!r}"
                            )
                        if source not in existing["sources"]:
                            existing["sources"].append(source)
        if not entries:
            return None
        return self.controller.run_store.write_evidence_once_json(
            "synthesis/requested-emitted-evidence.json",
            {
                "requested_emitted_evidence_version": 1,
                "requested_value_receipts": list(entries.values()),
            },
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
        value_evidence_path = self._seal_requested_value_evidence()
        if value_evidence_path is not None:
            references.append(
                make_evidence_reference(
                    root=run_root,
                    path=value_evidence_path,
                    artifact_role="requested_value_evidence",
                )
            )
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
