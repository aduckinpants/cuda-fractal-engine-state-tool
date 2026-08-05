from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Protocol

from .agent_bundle import AgentBundle, build_agent_bundle
from .async_jobs import JobContext
from .automated_protocol import PacketAuthorityBinding
from .derived_finding import promote_replay_proven_candidate
from .research_protocol import (
    PlannerDecision,
    ResearchAction,
    ResearchBrief,
    ResearchResultSelection,
    ResearchReviewDecision,
    ResearchReviewGate,
    authorize_scalar_sweep,
    authorize_single_override,
    canonical_json_sha256,
    parse_planner_response,
    parse_review_response,
    round_plan_document,
)
from .research_run_store import ResearchRunStore
from .scalar_sweep import ScalarBracketSweepService, ScalarSweepResult, ScalarSweepValidation
from .state_override import StateOverrideMaterialization, materialize_state_override
from .state_override_proof import StateOverrideProofResult, execute_state_override_proof


class ResearchSessionState(str, Enum):
    PLANNING = "PLANNING"
    PLAN_READY = "PLAN_READY"
    EXECUTING = "EXECUTING"
    REVIEW_READY = "REVIEW_READY"
    READY_FOR_SYNTHESIS = "READY_FOR_SYNTHESIS"


class ResearchSessionDisposition(str, Enum):
    RUNNING = "RUNNING"
    ANSWER_READY = "ANSWER_READY"
    UNRESOLVED = "UNRESOLVED"
    REVIEW_COMPLETE = "REVIEW_COMPLETE"


class SingleValidationService(Protocol):
    def __call__(
        self,
        bundle: AgentBundle,
        payload_text: str,
        output_path: Path,
    ) -> StateOverrideMaterialization: ...


class SingleExecutionService(Protocol):
    def __call__(self, bundle: AgentBundle, payload_text: str) -> StateOverrideProofResult: ...


class SweepValidationService(Protocol):
    def __call__(self, bundle: AgentBundle, payload_text: str) -> ScalarSweepValidation: ...


class SweepExecutionService(Protocol):
    def __call__(self, bundle: AgentBundle, payload_text: str) -> ScalarSweepResult: ...


class ResearchPromotionService(Protocol):
    def __call__(
        self,
        bundle: AgentBundle,
        selection: ResearchResultSelection,
        evidence: "ResearchExecutionEvidence",
        promotion_dir: Path,
    ) -> AgentBundle: ...


@dataclass(frozen=True)
class ResearchRouteServices:
    validate_single: SingleValidationService
    execute_single: SingleExecutionService
    validate_sweep: SweepValidationService
    execute_sweep: SweepExecutionService
    promote: ResearchPromotionService


@dataclass(frozen=True)
class PreparedResearchExperiment:
    attempt_number: int
    decision: PlannerDecision
    round_plan: dict[str, Any]
    round_plan_sha256: str
    validation: StateOverrideMaterialization | ScalarSweepValidation


@dataclass(frozen=True)
class ResearchExecutionEvidence:
    attempt_number: int
    action: ResearchAction
    round_plan_sha256: str
    proof: StateOverrideProofResult | None = None
    sweep: ScalarSweepResult | None = None
    execution_error: str | None = None


class ResearchSessionController:
    """Offline semantic controller; provider dispatch and cost live in Slice 3."""

    def __init__(
        self,
        *,
        brief: ResearchBrief,
        run_store: ResearchRunStore,
        initial_bundle: AgentBundle,
        services: ResearchRouteServices,
    ) -> None:
        if initial_bundle.packet_version != 8:
            raise ValueError("Question-driven research requires Packet V8")
        manifest = json.loads(run_store.manifest_path.read_text(encoding="utf-8"))
        if manifest.get("research_brief") != brief.to_dict():
            raise ValueError("Research run manifest disagrees with the sealed brief")
        initial = manifest.get("initial_packet")
        if initial != self._binding(initial_bundle).to_dict():
            raise ValueError("Research run manifest disagrees with the initial packet")
        self.brief = brief
        self.run_store = run_store
        self.services = services
        self.current_bundle = initial_bundle
        self.current_packet = self._binding(initial_bundle)
        self.current_packet_lineage = [self.current_packet.to_dict()]
        self.state = ResearchSessionState.PLANNING
        self.disposition = ResearchSessionDisposition.RUNNING
        self.attempts_consumed = 0
        self.prepared: PreparedResearchExperiment | None = None
        self.last_execution: ResearchExecutionEvidence | None = None
        self.last_review: ResearchReviewDecision | None = None
        self.execution_history: list[ResearchExecutionEvidence] = []
        self.review_history: list[ResearchReviewDecision] = []
        self.terminal_planner_decision: PlannerDecision | None = None
        self._correction_used = False
        self._correction_available = False
        self._record("research_session_started", {"initial_packet": self.current_packet.to_dict()})

    @staticmethod
    def _binding(bundle: AgentBundle) -> PacketAuthorityBinding:
        return PacketAuthorityBinding(
            packet_id=bundle.packet_id,
            manifest_sha256=bundle.manifest_sha256,
            finding_id=bundle.finding_id,
        )

    def _projection(self) -> dict[str, Any]:
        return {
            "state": self.state.value,
            "disposition": self.disposition.value,
            "attempts_consumed": self.attempts_consumed,
            "maximum_experiment_rounds": self.brief.maximum_experiment_rounds,
            "correction_used": self._correction_used,
            "current_research_base": self.current_packet.to_dict(),
            "current_packet_lineage": list(self.current_packet_lineage),
            "pending_round_plan_sha256": (
                self.prepared.round_plan_sha256 if self.prepared else None
            ),
        }

    def _record(self, event_type: str, payload: dict[str, Any]) -> None:
        self.run_store.record_transition(event_type, payload, self._projection())

    def _attempt_dir(self, attempt_number: int) -> Path:
        return self.run_store.run_dir / "attempts" / f"{attempt_number:03d}"

    @property
    def correction_used(self) -> bool:
        return self._correction_used

    @property
    def correction_available(self) -> bool:
        return self._correction_available

    def prepare_planner_response(
        self, response_text: str, *, correction: bool = False
    ) -> PlannerDecision:
        if self.state is not ResearchSessionState.PLANNING:
            raise RuntimeError("Planner response is not legal in the current research state")
        if correction:
            if self._correction_used or not self._correction_available:
                raise RuntimeError("No executable correction turn is available")
            self._correction_used = True
        elif self._correction_available:
            raise RuntimeError("The next planner response must be the one bounded correction")
        attempt_number = self.attempts_consumed + 1
        response_name = "planner-response-correction.txt" if correction else "planner-response.txt"
        response_path = self.run_store.write_evidence_once_bytes(
            f"attempts/{attempt_number:03d}/{response_name}", response_text.encode("utf-8")
        )
        try:
            decision = parse_planner_response(response_text)
            if decision.action is ResearchAction.SINGLE_OVERRIDE:
                authorize_single_override(decision, self.brief.experiment_permissions)
            elif decision.action is ResearchAction.SCALAR_SWEEP:
                authorize_scalar_sweep(decision, self.brief.experiment_permissions)
        except Exception as exc:
            self._correction_available = not correction and not self._correction_used
            self._record(
                "planner_response_rejected",
                {
                    "attempt_number": attempt_number,
                    "response_path": str(response_path.relative_to(self.run_store.run_dir)),
                    "response_sha256": hashlib.sha256(response_text.encode("utf-8")).hexdigest(),
                    "error": str(exc),
                    "correction_available": self._correction_available,
                },
            )
            raise
        self._correction_available = False
        if decision.action in {ResearchAction.ANSWER_READY, ResearchAction.UNRESOLVED_REPORT}:
            self.terminal_planner_decision = decision
            self.state = ResearchSessionState.READY_FOR_SYNTHESIS
            self.disposition = (
                ResearchSessionDisposition.ANSWER_READY
                if decision.action is ResearchAction.ANSWER_READY
                else ResearchSessionDisposition.UNRESOLVED
            )
            self._record(
                "planner_terminal_decision",
                {
                    "action": decision.action.value,
                    "response_sha256": decision.source_response_sha256,
                    "unresolved_reason": (
                        decision.unresolved_reason.value if decision.unresolved_reason else None
                    ),
                },
            )
            return decision
        if attempt_number > self.brief.maximum_experiment_rounds:
            raise RuntimeError("Maximum experiment attempts are exhausted")

        output = self._attempt_dir(attempt_number) / "validation" / "merged-candidate.json"
        if decision.payload_text is None:
            raise RuntimeError("Executable decision has no payload")
        try:
            validation: StateOverrideMaterialization | ScalarSweepValidation
            if decision.action is ResearchAction.SINGLE_OVERRIDE:
                validation = self.services.validate_single(
                    self.current_bundle, decision.payload_text, output
                )
                if not validation.changed_paths:
                    raise ValueError("UNINTENDED_NO_EFFECT")
            else:
                validation = self.services.validate_sweep(
                    self.current_bundle, decision.payload_text
                )
        except Exception as exc:
            self._correction_available = not correction and not self._correction_used
            self._record(
                "planner_payload_validation_failed",
                {
                    "attempt_number": attempt_number,
                    "action": decision.action.value,
                    "payload_sha256": decision.payload_sha256,
                    "error": str(exc),
                    "correction_available": self._correction_available,
                },
            )
            raise

        plan = round_plan_document(decision, attempt_number=attempt_number)
        plan["packet_binding"] = self.current_packet.to_dict()
        plan["research_brief_sha256"] = canonical_json_sha256(self.brief.to_dict())
        plan_sha = canonical_json_sha256(plan)
        self.run_store.write_evidence_once_bytes(
            f"attempts/{attempt_number:03d}/payload.json",
            decision.payload_text.encode("utf-8"),
        )
        self.run_store.write_evidence_once_json(
            f"attempts/{attempt_number:03d}/round-plan.json", plan
        )
        self.prepared = PreparedResearchExperiment(
            attempt_number, decision, plan, plan_sha, validation
        )
        self.state = ResearchSessionState.PLAN_READY
        self._record(
            "research_plan_ready",
            {
                "attempt_number": attempt_number,
                "action": decision.action.value,
                "round_plan_sha256": plan_sha,
                "packet_binding": self.current_packet.to_dict(),
                "correction_used": correction,
            },
        )
        return decision

    def execute_prepared(self) -> ResearchExecutionEvidence:
        if self.state is not ResearchSessionState.PLAN_READY or self.prepared is None:
            raise RuntimeError("No validated research experiment is ready")
        prepared = self.prepared
        self.attempts_consumed += 1
        self.state = ResearchSessionState.EXECUTING
        self._record(
            "experiment_attempt_started",
            {
                "attempt_number": prepared.attempt_number,
                "action": prepared.decision.action.value,
                "round_plan_sha256": prepared.round_plan_sha256,
            },
        )
        proof = None
        sweep = None
        error = None
        try:
            if prepared.decision.payload_text is None:
                raise RuntimeError("Prepared experiment payload is unavailable")
            if prepared.decision.action is ResearchAction.SINGLE_OVERRIDE:
                proof = self.services.execute_single(
                    self.current_bundle, prepared.decision.payload_text
                )
            else:
                sweep = self.services.execute_sweep(
                    self.current_bundle, prepared.decision.payload_text
                )
        except Exception as exc:
            error = str(exc)
        evidence = ResearchExecutionEvidence(
            attempt_number=prepared.attempt_number,
            action=prepared.decision.action,
            round_plan_sha256=prepared.round_plan_sha256,
            proof=proof,
            sweep=sweep,
            execution_error=error,
        )
        reference = {
            "attempt_number": evidence.attempt_number,
            "action": evidence.action.value,
            "round_plan_sha256": evidence.round_plan_sha256,
            "execution_error": error,
            "proof": (
                {
                    "proof_id": proof.proof_id,
                    "status": proof.status,
                    "receipt_sha256": proof.receipt_sha256,
                }
                if proof is not None
                else None
            ),
            "sweep": (
                {
                    "sweep_id": sweep.sweep_id,
                    "disposition": sweep.disposition,
                    "members": [
                        {
                            "index": member.index,
                            "status": member.status,
                            "proof_id": member.proof_id,
                        }
                        for member in sweep.members
                    ],
                }
                if sweep is not None
                else None
            ),
        }
        self.run_store.write_evidence_once_json(
            f"attempts/{prepared.attempt_number:03d}/execution-ref.json", reference
        )
        self.last_execution = evidence
        self.execution_history.append(evidence)
        self.state = ResearchSessionState.REVIEW_READY
        self._record("experiment_attempt_finished", reference)
        return evidence

    def apply_review(self, response_text: str) -> ResearchReviewDecision:
        if self.state is not ResearchSessionState.REVIEW_READY or self.last_execution is None:
            raise RuntimeError("Research review is not legal in the current state")
        decision = parse_review_response(response_text)
        attempt = self.last_execution.attempt_number
        if decision.gate in {
            ResearchReviewGate.CONTINUE_PROMOTE_RESULT,
            ResearchReviewGate.CONTINUE_RETAIN_BASE,
        } and self.attempts_consumed >= self.brief.maximum_experiment_rounds:
            raise RuntimeError("Review cannot continue after the final experiment attempt")
        if decision.gate is ResearchReviewGate.CONTINUE_PROMOTE_RESULT:
            self._validate_selected_result(decision.selected_result, self.last_execution)
        self.run_store.write_evidence_once_bytes(
            f"attempts/{attempt:03d}/review-response.txt", response_text.encode("utf-8")
        )
        self.run_store.write_evidence_once_json(
            f"attempts/{attempt:03d}/review-decision.json",
            {
                "gate": decision.gate.value,
                "source_response_sha256": decision.source_response_sha256,
                "round_plan_sha256": self.last_execution.round_plan_sha256,
                "prediction_outcome": decision.prediction_outcome,
                "evidence_assessment": decision.evidence_assessment,
                "selected_result": {
                    "kind": decision.selected_result.kind,
                    "proof_id": decision.selected_result.proof_id,
                    "sweep_id": decision.selected_result.sweep_id,
                    "member_index": decision.selected_result.member_index,
                },
                "next_research_step": decision.next_research_step,
                "hostile_self_review_conclusion": decision.hostile_self_review_conclusion,
            },
        )
        if decision.gate is ResearchReviewGate.CONTINUE_PROMOTE_RESULT:
            promoted = self.services.promote(
                self.current_bundle,
                decision.selected_result,
                self.last_execution,
                self._attempt_dir(attempt) / "promotion",
            )
            self.current_bundle = promoted
            self.current_packet = self._binding(promoted)
            self.current_packet_lineage.append(self.current_packet.to_dict())
            self.prepared = None
            self.state = ResearchSessionState.PLANNING
        elif decision.gate is ResearchReviewGate.CONTINUE_RETAIN_BASE:
            self.prepared = None
            self.state = ResearchSessionState.PLANNING
        else:
            self.state = ResearchSessionState.READY_FOR_SYNTHESIS
            self.disposition = (
                ResearchSessionDisposition.REVIEW_COMPLETE
                if decision.gate is ResearchReviewGate.COMPLETE_RESEARCH
                else ResearchSessionDisposition.UNRESOLVED
            )
        self.last_review = decision
        self.review_history.append(decision)
        self._record(
            "research_review_applied",
            {
                "attempt_number": attempt,
                "gate": decision.gate.value,
                "round_plan_sha256": self.last_execution.round_plan_sha256,
                "current_research_base": self.current_packet.to_dict(),
            },
        )
        return decision

    @staticmethod
    def _validate_selected_result(
        selection: ResearchResultSelection,
        evidence: ResearchExecutionEvidence,
    ) -> None:
        if selection.kind == "single":
            if (
                evidence.proof is None
                or evidence.proof.status != "replay_proven"
                or evidence.proof.proof_id != selection.proof_id
            ):
                raise ValueError("Selected single result is not the exact replay-proven proof")
            return
        if selection.kind == "sweep_member":
            if evidence.sweep is None or evidence.sweep.sweep_id != selection.sweep_id:
                raise ValueError("Selected sweep result disagrees with executed sweep")
            member = next(
                (
                    item
                    for item in evidence.sweep.members
                    if item.index == selection.member_index
                ),
                None,
            )
            if member is None or member.status != "REPLAY_PROVEN" or not member.proof_id:
                raise ValueError("Selected sweep member is not replay-proven")
            return
        raise ValueError("Promotion requires one exact result")


def create_job_bound_research_route_services(
    *,
    runtime_cmd_path: Path,
    workspace_root: Path,
    job: JobContext,
    runtime_compatibility_mode: str | None = None,
) -> ResearchRouteServices:
    """Bind the research route to the existing manual/automation owners."""
    runtime_cmd_path = runtime_cmd_path.resolve()
    workspace_root = workspace_root.resolve()
    sweep_service = ScalarBracketSweepService()

    def validate_single(
        bundle: AgentBundle,
        payload_text: str,
        output_path: Path,
    ) -> StateOverrideMaterialization:
        return materialize_state_override(
            bundle.packet_dir,
            payload_text,
            output_path,
            expected_manifest_sha256=bundle.manifest_sha256,
        )

    def execute_single(
        bundle: AgentBundle,
        payload_text: str,
    ) -> StateOverrideProofResult:
        return execute_state_override_proof(
            bundle.packet_dir,
            payload_text,
            runtime_cmd_path,
            job,
            expected_manifest_sha256=bundle.manifest_sha256,
            runtime_compatibility_mode=runtime_compatibility_mode,
        )

    def validate_sweep(
        bundle: AgentBundle,
        payload_text: str,
    ) -> ScalarSweepValidation:
        return sweep_service.validate(
            packet_dir=bundle.packet_dir,
            fixed_override_text="{}",
            plan_text=payload_text,
            runtime_cmd_path=runtime_cmd_path,
        )

    def execute_sweep(
        bundle: AgentBundle,
        payload_text: str,
    ) -> ScalarSweepResult:
        return sweep_service.execute(
            packet_dir=bundle.packet_dir,
            fixed_override_text="{}",
            plan_text=payload_text,
            runtime_cmd_path=runtime_cmd_path,
            job=job,
            runtime_compatibility_mode=runtime_compatibility_mode,
        )

    def promote(
        bundle: AgentBundle,
        selection: ResearchResultSelection,
        evidence: ResearchExecutionEvidence,
        promotion_dir: Path,
    ) -> AgentBundle:
        proof: StateOverrideProofResult | None
        if selection.kind == "single":
            proof = evidence.proof
        elif selection.kind == "sweep_member" and evidence.sweep is not None:
            member = next(
                (
                    item
                    for item in evidence.sweep.members
                    if item.index == selection.member_index
                ),
                None,
            )
            proof = member.proof_result if member is not None else None
        else:
            proof = None
        if proof is None:
            raise ValueError("Selected result has no exact in-process proof authority")
        promotion = promote_replay_proven_candidate(
            proof=proof,
            packet_dir=bundle.packet_dir,
            workspace_root=workspace_root,
            promotion_dir=promotion_dir,
        )
        return build_agent_bundle(
            promotion.import_result.finding_dir,
            runtime_cmd_path,
            job=job,
        )

    return ResearchRouteServices(
        validate_single=validate_single,
        execute_single=execute_single,
        validate_sweep=validate_sweep,
        execute_sweep=execute_sweep,
        promote=promote,
    )
