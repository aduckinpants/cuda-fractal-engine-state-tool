from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Callable, Protocol

from .agent_bundle import AgentBundle, build_agent_bundle
from .async_jobs import JobCancelledError, JobContext
from .automated_context import build_round_review_ledger, ledger_transport_resource
from .automated_protocol import (
    BudgetUsage,
    ControllerDisposition,
    ModelGateProposal,
    PacketAuthorityBinding,
    ProtocolState,
    SessionBudgets,
    budget_exhaustion_reason,
    classify_override_effect,
    parse_model_gate_proposal,
    resolve_round_authority,
    validate_protocol_transition,
)
from .automated_run_store import AutomatedRunStore, RunStoreWriteError
from .derived_finding import DerivedFindingPromotion, promote_replay_proven_candidate
from .enrichment_disclosure import (
    DisclosureProfile,
    EnrichmentDisclosure,
    FindingDisclosureService,
    build_blind_disclosure,
)
from .openai_transport import (
    DEFAULT_MODEL,
    AmbiguousRemoteCompletion,
    DispatchAuthorizationRejected,
    PacketV8ResponsesTransport,
    ProviderTransportError,
    TransportCancelled,
    TransportTurnResult,
    TransportResource,
)
from .pricing_policy import (
    PROVIDER_BILLING_DISCLAIMER,
    PricingPolicy,
    calculate_usage_cost,
    decimal_text,
    estimate_maximum_call_cost,
    load_pricing_policy,
)
from .state_override import StateOverrideMaterialization, materialize_state_override, parse_state_override
from .state_override_proof import StateOverrideProofResult, execute_state_override_proof
from .runtime_surface import resolve_launcher


AUTOMATED_SESSION_INSTRUCTIONS = """You are participating in a bounded fractal-finding exploration session.
The current attached Packet V8 is the sole domain and authoring authority. Follow its behavioral contract.
Answer only the current stage request. Do not claim that automation promotion is human visual acceptance.
Do not provide private chain-of-thought; provide only the concise conclusions and artifacts requested.
"""

AUTHOR_ROUND_PROMPT = """Complete one bounded experiment-authoring round in this single response.

1. Briefly state what you notice and what seems mathematically interesting.
2. List a small set of possible experiments and classify each as state-authorable, analysis-only, or unavailable.
3. Select exactly one observable experiment expressible as one sparse state override.
4. Lock a falsifiable prediction: expected visible effect, observation channel, camera intent, viewport containment when derivable, uncertainty, and an honest failure/disconfirmation condition.
5. Give one brief hostile self-review conclusion covering authority, observability, camera safety, and narrative/JSON alignment.
6. Return the exact non-empty sparse state override for that experiment, following the Packet V8 output contract: exactly one fenced json block and no other code block.

Do not propose a controller gate in this response.
"""

REVIEW_AND_GATE_PROMPT = """The attached Packet V8 is the replay-proven derived finding. This is a fresh provider context.
The attached controller round-review ledger carries the exact prior author decision, locked prediction, sparse override, and proof identities needed for comparison. It is not state authority.
In one concise response:

1. Compare the result with the locked prediction and identify what changed, what did not, and whether the experiment was informative.
2. Perform a brief hostile self-audit of authority use, observability, camera handling, and prediction alignment.
3. Propose exactly one controller gate on the final line using this form:
GATE_DECISION: ROUND_ADVANCE | ROUND_REVISE | SESSION_PASS | SESSION_FAIL | MANUAL_REVIEW_REQUIRED
Use ROUND_ADVANCE only to author the next round against the derived packet. Use ROUND_REVISE only to keep the preceding base packet authoritative.
"""


_CODE_FENCE = re.compile(r"```([^\r\n`]*)\r?\n(.*?)```", re.DOTALL)
_GATE = re.compile(r"(?m)^GATE_DECISION:\s*([A-Z_]+)\s*$")


class ValidationService(Protocol):
    def __call__(
        self,
        packet_dir: Path,
        override_text: str,
        output_path: Path,
        expected_manifest_sha256: str,
    ) -> StateOverrideMaterialization: ...


class ProofService(Protocol):
    def __call__(
        self,
        packet_dir: Path,
        override_text: str,
        expected_manifest_sha256: str,
    ) -> StateOverrideProofResult: ...


class PromotionService(Protocol):
    def __call__(
        self,
        proof: StateOverrideProofResult,
        packet_dir: Path,
        promotion_dir: Path,
    ) -> DerivedFindingPromotion: ...


class BundleService(Protocol):
    def __call__(self, finding_dir: Path) -> AgentBundle: ...


class DisclosureService(Protocol):
    def __call__(
        self,
        packet_dir: Path,
        profile: DisclosureProfile,
    ) -> EnrichmentDisclosure: ...


@dataclass(frozen=True)
class AutomatedRouteServices:
    proof: ProofService
    promote: PromotionService
    build_bundle: BundleService
    validate: ValidationService | None = None
    disclosure: DisclosureService | None = None


@dataclass(frozen=True)
class AutomatedSessionResult:
    disposition: ControllerDisposition
    message: str
    current_packet: PacketAuthorityBinding
    proven_rounds: int
    usage: BudgetUsage
    model_gate_proposal: ModelGateProposal | None
    last_proof: StateOverrideProofResult | None
    last_derived_bundle: AgentBundle | None


def extract_sparse_override(response_text: str) -> str:
    fences = _CODE_FENCE.findall(response_text)
    if len(fences) != 1 or response_text.count("```") != 2:
        raise ValueError("Override response must contain exactly one fenced code block")
    language, payload = fences[0]
    if language.strip().lower() != "json":
        raise ValueError("Override response code block must use the json language tag")
    parsed = parse_state_override(payload)
    return parsed.exact_text


def extract_model_gate_proposal(response_text: str) -> ModelGateProposal:
    matches = _GATE.findall(response_text)
    lines = [line.strip() for line in response_text.splitlines() if line.strip()]
    if len(matches) != 1 or not lines or lines[-1] != f"GATE_DECISION: {matches[0]}":
        raise ValueError("Gate response must contain exactly one GATE_DECISION line")
    return parse_model_gate_proposal(matches[0])


def _default_validate(
    packet_dir: Path,
    override_text: str,
    output_path: Path,
    expected_manifest_sha256: str,
) -> StateOverrideMaterialization:
    return materialize_state_override(
        packet_dir,
        override_text,
        output_path,
        expected_manifest_sha256=expected_manifest_sha256,
    )


def create_job_bound_automated_route_services(
    *,
    runtime_cmd_path: Path,
    workspace_root: Path,
    job: JobContext,
    runtime_compatibility_mode: str | None = None,
) -> AutomatedRouteServices:
    """Bind automation to the manual route's canonical semantic owners."""
    runtime_cmd_path = runtime_cmd_path.resolve()
    workspace_root = workspace_root.resolve()

    def proof(
        packet_dir: Path,
        override_text: str,
        expected_manifest_sha256: str,
    ) -> StateOverrideProofResult:
        return execute_state_override_proof(
            packet_dir,
            override_text,
            runtime_cmd_path,
            job,
            expected_manifest_sha256=expected_manifest_sha256,
            runtime_compatibility_mode=runtime_compatibility_mode,
        )

    def promote(
        result: StateOverrideProofResult,
        packet_dir: Path,
        promotion_dir: Path,
    ) -> DerivedFindingPromotion:
        return promote_replay_proven_candidate(
            proof=result,
            packet_dir=packet_dir,
            workspace_root=workspace_root,
            promotion_dir=promotion_dir,
        )

    def bundle(finding_dir: Path) -> AgentBundle:
        return build_agent_bundle(finding_dir, runtime_cmd_path, job=job)

    launcher = resolve_launcher(runtime_cmd_path)
    runtime_executable = Path(launcher.resolved_executable_path or runtime_cmd_path)
    disclosure = FindingDisclosureService(
        workspace_root=workspace_root,
        runtime_executable=runtime_executable,
        runtime_compatibility_mode=runtime_compatibility_mode,
    )

    return AutomatedRouteServices(
        proof=proof,
        promote=promote,
        build_bundle=bundle,
        validate=_default_validate,
        disclosure=disclosure.prepare,
    )


class AutomatedSessionController:
    def __init__(
        self,
        *,
        transport: PacketV8ResponsesTransport,
        run_store: AutomatedRunStore,
        initial_bundle: AgentBundle,
        services: AutomatedRouteServices,
        budgets: SessionBudgets = SessionBudgets(),
        pricing_policy: PricingPolicy | None = None,
        requested_model: str = DEFAULT_MODEL,
        disclosure_profile: DisclosureProfile = DisclosureProfile.BLIND,
        cancelled: Callable[[], bool] = lambda: False,
        auto_promote: bool = True,
    ) -> None:
        if initial_bundle.packet_version != 8:
            raise ValueError("Automated sessions require Packet V8")
        self.transport = transport
        self.run_store = run_store
        self.services = services
        self.budgets = budgets
        self.pricing_policy = pricing_policy or load_pricing_policy()
        self.requested_model = requested_model
        self.disclosure_profile = DisclosureProfile(disclosure_profile)
        self.pricing_policy.model(requested_model)
        self.cancelled = cancelled
        self.auto_promote = auto_promote
        self.current_bundle = initial_bundle
        self.current_packet = self._binding(initial_bundle)
        self.state = ProtocolState.OBSERVE
        self.disposition = ControllerDisposition.RUNNING
        self.usage = BudgetUsage()
        self.previous_response_id: str | None = None
        self.last_proof: StateOverrideProofResult | None = None
        self.last_derived_bundle: AgentBundle | None = None
        self.last_gate: ModelGateProposal | None = None
        self._turn_number = 0
        self._correction_used = False
        self._last_requested_model: str | None = None
        self._last_resolved_model: str | None = None
        self._cumulative_latency_seconds = 0.0
        self._last_estimated_call_cost_usd = Decimal("0")
        self._last_counted_input_tokens = 0

    @staticmethod
    def _binding(bundle: AgentBundle) -> PacketAuthorityBinding:
        return PacketAuthorityBinding(
            packet_id=bundle.packet_id,
            manifest_sha256=bundle.manifest_sha256,
            finding_id=bundle.finding_id,
        )

    def _projection(self) -> dict[str, object]:
        return {
            "state": self.state.value,
            "controller_disposition": self.disposition.value,
            "current_packet": self.current_packet.to_dict(),
            "proven_rounds": self.usage.proven_rounds,
            "model_responses": self.usage.model_responses,
            "cumulative_input_tokens": self.usage.cumulative_input_tokens,
            "cumulative_cached_input_tokens": self.usage.cumulative_cached_input_tokens,
            "cumulative_uncached_input_tokens": self.usage.cumulative_uncached_input_tokens,
            "cumulative_output_tokens": self.usage.cumulative_output_tokens,
            "cumulative_cache_write_tokens": self.usage.cumulative_cache_write_tokens,
            "cumulative_calculated_cost_usd": decimal_text(
                self.usage.cumulative_calculated_cost_usd
            ),
            "maximum_calculated_cost_usd": decimal_text(
                self.budgets.maximum_calculated_cost_usd
            ),
            "remaining_calculated_cost_usd": decimal_text(
                self.budgets.maximum_calculated_cost_usd
                - self.usage.cumulative_calculated_cost_usd
            ),
            "last_estimated_call_cost_usd": decimal_text(
                self._last_estimated_call_cost_usd
            ),
            "last_counted_input_tokens": self._last_counted_input_tokens,
            "pricing_policy": self.pricing_policy.identity_dict(),
            "disclosure_profile": self.disclosure_profile.value,
            "cumulative_provider_latency_seconds": self._cumulative_latency_seconds,
            "last_requested_model": self._last_requested_model,
            "last_resolved_model": self._last_resolved_model,
            "previous_response_id": self.previous_response_id,
            "model_gate_proposal": self.last_gate.value if self.last_gate else None,
        }

    def _record(self, event_type: str, payload: dict[str, object]) -> None:
        self.run_store.record_transition(event_type, payload, self._projection())

    def _move(self, target: ProtocolState) -> None:
        validate_protocol_transition(self.state, target)
        prior = self.state
        self.state = target
        self._record(
            "controller_transition",
            {"from": prior.value, "to": target.value},
        )

    def _ask(self, prompt: str, *, attach_packet: bool) -> TransportTurnResult:
        return self._ask_with_resources(prompt, attach_packet=attach_packet, additional_resources=())

    def _ask_with_resources(
        self,
        prompt: str,
        *,
        attach_packet: bool,
        additional_resources: tuple[TransportResource, ...],
    ) -> TransportTurnResult:
        response_usage = BudgetUsage(
            proven_rounds=0,
            model_responses=self.usage.model_responses,
            cumulative_input_tokens=self.usage.cumulative_input_tokens,
            cumulative_cached_input_tokens=self.usage.cumulative_cached_input_tokens,
            cumulative_output_tokens=self.usage.cumulative_output_tokens,
            cumulative_cache_write_tokens=self.usage.cumulative_cache_write_tokens,
            cumulative_calculated_cost_usd=self.usage.cumulative_calculated_cost_usd,
        )
        exhaustion = budget_exhaustion_reason(
            self.budgets,
            response_usage,
            next_output_tokens=self.budgets.maximum_output_tokens_per_response,
        )
        if exhaustion is not None:
            raise RuntimeError(f"Automated session budget exhausted before response: {exhaustion}")

        def authorize_dispatch(exact_input_tokens: int) -> None:
            self._last_counted_input_tokens = exact_input_tokens
            estimate = estimate_maximum_call_cost(
                self.pricing_policy,
                model_name=self.requested_model,
                maximum_input_tokens=exact_input_tokens,
                maximum_output_tokens=self.budgets.maximum_output_tokens_per_response,
            )
            self._last_estimated_call_cost_usd = estimate.cost_usd
            reason = budget_exhaustion_reason(
                self.budgets,
                response_usage,
                next_input_tokens=exact_input_tokens,
                next_output_tokens=self.budgets.maximum_output_tokens_per_response,
                next_calculated_cost_usd=estimate.cost_usd,
            )
            payload = {
                "reason": reason,
                "exact_counted_input_tokens": exact_input_tokens,
                "estimate": estimate.to_dict(),
                "pricing_policy": self.pricing_policy.identity_dict(),
                "remaining_calculated_cost_usd_before_dispatch": decimal_text(
                    self.budgets.maximum_calculated_cost_usd
                    - self.usage.cumulative_calculated_cost_usd
                ),
                "provider_billing_disclaimer": PROVIDER_BILLING_DISCLAIMER,
            }
            self._record(
                "provider_dispatch_rejected" if reason else "provider_dispatch_estimated",
                payload,
            )
            if reason is not None:
                raise DispatchAuthorizationRejected(
                    f"Automated session budget exhausted before response: {reason}"
                )

        self._turn_number += 1
        result = self.transport.send_turn(
            instructions=AUTOMATED_SESSION_INSTRUCTIONS,
            prompt=prompt,
            packet_dir=self.current_bundle.packet_dir if attach_packet else None,
            previous_response_id=self.previous_response_id,
            run_store=self.run_store,
            turn_id=f"turn-{self._turn_number:04d}",
            cancelled=self.cancelled,
            max_output_tokens=self.budgets.maximum_output_tokens_per_response,
            model=self.requested_model,
            authorize_dispatch=authorize_dispatch,
            additional_resources=additional_resources,
        )
        actual_cost = calculate_usage_cost(
            self.pricing_policy,
            model_name=result.model,
            input_tokens=result.input_tokens,
            cached_input_tokens=result.cached_input_tokens,
            cache_write_tokens=result.cache_write_tokens,
            output_tokens=result.output_tokens,
        )
        self.previous_response_id = result.response_id
        self._last_requested_model = result.requested_model
        self._last_resolved_model = result.model
        self._cumulative_latency_seconds += result.latency_seconds
        self.usage = BudgetUsage(
            proven_rounds=self.usage.proven_rounds,
            model_responses=self.usage.model_responses + 1,
            cumulative_input_tokens=self.usage.cumulative_input_tokens + result.input_tokens,
            cumulative_cached_input_tokens=(
                self.usage.cumulative_cached_input_tokens + result.cached_input_tokens
            ),
            cumulative_output_tokens=self.usage.cumulative_output_tokens + result.output_tokens,
            cumulative_cache_write_tokens=(
                self.usage.cumulative_cache_write_tokens + result.cache_write_tokens
            ),
            cumulative_calculated_cost_usd=(
                self.usage.cumulative_calculated_cost_usd + actual_cost.cost_usd
            ),
        )
        self._record(
            "model_response",
            {
                "response_id": result.response_id,
                "requested_model": result.requested_model,
                "resolved_model": result.model,
                "input_tokens": result.input_tokens,
                "pre_dispatch_counted_input_tokens": self._last_counted_input_tokens,
                "input_token_count_delta": (
                    result.input_tokens - self._last_counted_input_tokens
                ),
                "cached_input_tokens": result.cached_input_tokens,
                "cache_write_tokens": result.cache_write_tokens,
                "uncached_input_tokens": result.uncached_input_tokens,
                "output_tokens": result.output_tokens,
                "latency_seconds": result.latency_seconds,
                "cumulative_input_tokens": self.usage.cumulative_input_tokens,
                "cumulative_cached_input_tokens": self.usage.cumulative_cached_input_tokens,
                "cumulative_uncached_input_tokens": self.usage.cumulative_uncached_input_tokens,
                "cumulative_output_tokens": self.usage.cumulative_output_tokens,
                "calculated_call_cost": actual_cost.to_dict(),
                "cumulative_calculated_cost_usd": decimal_text(
                    self.usage.cumulative_calculated_cost_usd
                ),
                "pricing_policy": self.pricing_policy.identity_dict(),
                "provider_billing_disclaimer": PROVIDER_BILLING_DISCLAIMER,
                "cumulative_provider_latency_seconds": self._cumulative_latency_seconds,
                "response_text_sha256": hashlib.sha256(result.output_text.encode("utf-8")).hexdigest(),
            },
        )
        if self.usage.cumulative_input_tokens > self.budgets.maximum_cumulative_input_tokens:
            raise RuntimeError(
                "Automated session budget exhausted after response: maximum_cumulative_input_tokens"
            )
        if self.usage.cumulative_output_tokens > self.budgets.maximum_cumulative_output_tokens:
            raise RuntimeError(
                "Automated session budget exhausted after response: maximum_cumulative_output_tokens"
            )
        if (
            self.usage.cumulative_calculated_cost_usd
            > self.budgets.maximum_calculated_cost_usd
        ):
            raise RuntimeError(
                "Automated session budget exhausted after response: maximum_calculated_cost_usd"
            )
        return result

    def _phase_disclosure_profile(self, phase: str) -> DisclosureProfile:
        if self.disclosure_profile is DisclosureProfile.ASSISTED:
            return DisclosureProfile.ASSISTED
        if self.disclosure_profile is DisclosureProfile.BREAK_BLIND and phase == "review":
            return DisclosureProfile.BREAK_BLIND
        return DisclosureProfile.BLIND

    def _raise_if_no_dollar_budget(self) -> None:
        if (
            self.usage.cumulative_calculated_cost_usd
            >= self.budgets.maximum_calculated_cost_usd
        ):
            raise RuntimeError(
                "Automated session budget exhausted before context preparation: "
                "maximum_calculated_cost_usd"
            )

    def _disclosure_resources(
        self,
        *,
        round_number: int,
        phase: str,
    ) -> tuple[TransportResource, ...]:
        profile = self._phase_disclosure_profile(phase)
        if profile is DisclosureProfile.BLIND:
            disclosure = build_blind_disclosure(self.current_bundle)
        else:
            if self.services.disclosure is None:
                raise RuntimeError(
                    f"Enrichment disclosure service is unavailable for profile {profile.value}"
                )
            disclosure = self.services.disclosure(self.current_bundle.packet_dir, profile)
        if (
            disclosure.packet_id != self.current_packet.packet_id
            or disclosure.packet_manifest_sha256 != self.current_packet.manifest_sha256
            or disclosure.finding_id != self.current_packet.finding_id
        ):
            raise RuntimeError("Enrichment disclosure disagrees with current packet authority")
        relative = (
            f"rounds/round-{round_number:02d}/context/{phase}-enrichment-disclosure.json"
        )
        manifest_path = self.run_store.write_evidence_bytes(relative, disclosure.manifest_bytes)
        manifest_resource = TransportResource(
            filename="enrichment-disclosure.json",
            role="enrichment_disclosure_manifest",
            media_role="file",
            sha256=hashlib.sha256(disclosure.manifest_bytes).hexdigest(),
            size_bytes=len(disclosure.manifest_bytes),
            local_path=manifest_path,
            payload=disclosure.manifest_bytes,
        )
        resources = tuple(
            TransportResource(
                filename=item.transport_filename,
                role=item.role,
                media_role=item.media_role,
                sha256=item.sha256,
                size_bytes=item.size_bytes,
                local_path=item.local_path,
                payload=item.payload,
            )
            for item in disclosure.resources
        )
        self._record(
            "enrichment_disclosure_prepared",
            {
                "round_number": round_number,
                "phase": phase,
                "configured_profile": self.disclosure_profile.value,
                "effective_profile": profile.value,
                "disclosure_id": disclosure.disclosure_id,
                "analysis_id": disclosure.analysis_id,
                "resource_count": len(resources),
            },
        )
        return (manifest_resource, *resources)

    def _finish(
        self,
        disposition: ControllerDisposition,
        message: str,
    ) -> AutomatedSessionResult:
        self.disposition = disposition
        self._record("session_disposition", {"disposition": disposition.value, "message": message})
        try:
            self.transport.close_owned_files(run_store=self.run_store, reason=disposition.value)
        except ProviderTransportError as exc:
            self.disposition = ControllerDisposition.MANUAL_REVIEW_REQUIRED
            message = f"{message} Provider-file cleanup requires manual review: {exc}"
            self._record(
                "provider_file_cleanup_failed",
                {"controller_disposition": self.disposition.value, "error": str(exc)},
            )
        return AutomatedSessionResult(
            disposition=self.disposition,
            message=message,
            current_packet=self.current_packet,
            proven_rounds=self.usage.proven_rounds,
            usage=self.usage,
            model_gate_proposal=self.last_gate,
            last_proof=self.last_proof,
            last_derived_bundle=self.last_derived_bundle,
        )

    def _validation_output(self, round_number: int, correction: bool) -> Path:
        name = "merged-candidate-correction.json" if correction else "merged-candidate.json"
        return self.run_store.run_dir / "rounds" / f"round-{round_number:02d}" / "validation" / name

    def _raise_if_cancelled(self) -> None:
        if self.cancelled():
            raise TransportCancelled("Automated session was cancelled before the next operation")

    def _author_round_prompt(self, round_number: int) -> str:
        handoff = (
            f"Round {round_number} begins a fresh provider conversation. "
            f"The attached packet {self.current_packet.packet_id} for finding "
            f"{self.current_packet.finding_id} is the sole current authoring authority."
        )
        if self.last_gate is ModelGateProposal.ROUND_REVISE:
            handoff += (
                " The preceding base packet remains authoritative after ROUND_REVISE; "
                "the prior candidate is historical evidence only. Select a corrected or different experiment."
            )
        elif self.last_gate is ModelGateProposal.ROUND_ADVANCE:
            handoff += (
                " This packet is the replay-proven derived result selected by ROUND_ADVANCE. "
                "Author only against its attached state and schemas."
            )
        return f"{handoff}\n\n{AUTHOR_ROUND_PROMPT}"

    def _request_valid_override(
        self,
        round_number: int,
        response: TransportTurnResult,
    ) -> tuple[str, StateOverrideMaterialization] | None:
        for attempt in range(2):
            error: str | None = None
            try:
                override_text = extract_sparse_override(response.output_text)
                validator = self.services.validate or _default_validate
                materialization = validator(
                    self.current_bundle.packet_dir,
                    override_text,
                    self._validation_output(round_number, correction=attempt == 1),
                    self.current_bundle.manifest_sha256,
                )
                effect = classify_override_effect(
                    changed_path_count=len(materialization.changed_paths),
                    empty_override_byte_exact=materialization.empty_override_byte_exact,
                    explicit_unchanged_requested=False,
                )
                if effect != "AUTHORIZED_CHANGE":
                    error = effect
                else:
                    self._record(
                        "override_validated",
                        {
                            "override_text_sha256": materialization.override_text_sha256,
                            "changed_path_count": len(materialization.changed_paths),
                            "effect": effect,
                            "correction_used": attempt == 1,
                        },
                    )
                    return override_text, materialization
            except Exception as exc:
                error = str(exc)
            if attempt == 1:
                self._record("override_correction_failed", {"error": error or "unknown"})
                return None
            self._correction_used = True
            self._move(ProtocolState.VALIDATE_OVERRIDE)
            self._move(ProtocolState.REQUEST_OVERRIDE)
            response = self._ask(
                "The prior override was not an eligible automated experiment result. "
                f"Validation result: {error}. Return one corrected, non-empty, authorized sparse override "
                "for the already selected experiment, or ask exactly one clarification question with no JSON.",
                attach_packet=False,
            )
        return None

    def run(self) -> AutomatedSessionResult:
        try:
            self._record("session_started", {"initial_packet": self.current_packet.to_dict()})
            while True:
                round_number = self.usage.proven_rounds + 1
                self._correction_used = False
                self.previous_response_id = None
                self._record(
                    "round_conversation_started",
                    {
                        "round_number": round_number,
                        "current_packet": self.current_packet.to_dict(),
                        "prior_gate": self.last_gate.value if self.last_gate else None,
                        "provider_chain_reset": True,
                    },
                )
                self._raise_if_no_dollar_budget()
                author_response = self._ask_with_resources(
                    self._author_round_prompt(round_number),
                    attach_packet=True,
                    additional_resources=self._disclosure_resources(
                        round_number=round_number,
                        phase="author",
                    ),
                )
                self._move(ProtocolState.EXPLORE)
                self._move(ProtocolState.SELECT_EXPERIMENT)
                self._move(ProtocolState.LOCK_PREDICTION)
                self._move(ProtocolState.REQUEST_OVERRIDE)
                validated = self._request_valid_override(round_number, author_response)
                if validated is None:
                    return self._finish(
                        ControllerDisposition.MANUAL_REVIEW_REQUIRED,
                        "The model did not produce one valid observable state override after its correction turn.",
                    )
                override_text, materialization = validated
                self._move(ProtocolState.VALIDATE_OVERRIDE)
                self._move(ProtocolState.PROVE_CANDIDATE)
                self._raise_if_cancelled()
                proof = self.services.proof(
                    self.current_bundle.packet_dir,
                    override_text,
                    self.current_bundle.manifest_sha256,
                )
                self.last_proof = proof
                self._raise_if_cancelled()
                if proof.status != "replay_proven":
                    return self._finish(
                        ControllerDisposition.PROOF_FAILED,
                        f"Runtime proof did not replay-prove the candidate: {proof.message}",
                    )
                self.usage = BudgetUsage(
                    proven_rounds=self.usage.proven_rounds + 1,
                    model_responses=self.usage.model_responses,
                    cumulative_input_tokens=self.usage.cumulative_input_tokens,
                    cumulative_cached_input_tokens=self.usage.cumulative_cached_input_tokens,
                    cumulative_output_tokens=self.usage.cumulative_output_tokens,
                    cumulative_cache_write_tokens=self.usage.cumulative_cache_write_tokens,
                    cumulative_calculated_cost_usd=(
                        self.usage.cumulative_calculated_cost_usd
                    ),
                )
                self._record("candidate_replay_proven", {"proof_id": proof.proof_id})
                if not self.auto_promote:
                    return self._finish(
                        ControllerDisposition.MANUAL_REVIEW_REQUIRED,
                        "Replay proof succeeded; automatic derived-finding promotion is disabled.",
                    )
                self._move(ProtocolState.PROMOTE_DERIVED_FINDING)
                self._raise_if_cancelled()
                promotion = self.services.promote(
                    proof,
                    self.current_bundle.packet_dir,
                    self.run_store.run_dir / "rounds" / f"round-{round_number:02d}" / "promotion",
                )
                self._record(
                    "derived_finding_promoted",
                    {
                        "finding_id": promotion.import_result.finding_id,
                        "human_acceptance": False,
                    },
                )
                self._move(ProtocolState.REFRESH_PACKET)
                self._raise_if_cancelled()
                derived_bundle = self.services.build_bundle(promotion.import_result.finding_dir)
                self._raise_if_cancelled()
                if (
                    derived_bundle.packet_version != 8
                    or derived_bundle.finding_id != promotion.import_result.finding_id
                ):
                    return self._finish(
                        ControllerDisposition.RUNTIME_FAILED,
                        "Derived Packet V8 identity disagrees with canonical finding promotion.",
                    )
                self.last_derived_bundle = derived_bundle
                preceding_bundle = self.current_bundle
                preceding_binding = self.current_packet
                derived_binding = self._binding(derived_bundle)
                self.current_bundle = derived_bundle
                self.current_packet = derived_binding
                self._record("derived_packet_refreshed", {"packet": derived_binding.to_dict()})
                self._move(ProtocolState.REVIEW_RESULT)
                ledger = build_round_review_ledger(
                    round_number=round_number,
                    author_packet=preceding_binding,
                    derived_packet=derived_binding,
                    author_response_text=author_response.output_text,
                    override_text=override_text,
                    materialization=materialization,
                    proof=proof,
                )
                ledger_path = self.run_store.write_evidence_bytes(
                    f"rounds/round-{round_number:02d}/context/round-review-ledger.json",
                    ledger.payload,
                )
                self.previous_response_id = None
                self._record(
                    "review_conversation_started",
                    {
                        "round_number": round_number,
                        "provider_chain_reset": True,
                        "review_ledger_sha256": ledger.sha256,
                    },
                )
                self._raise_if_no_dollar_budget()
                review_resources = (
                    ledger_transport_resource(ledger_path, ledger),
                    *self._disclosure_resources(round_number=round_number, phase="review"),
                )
                gate_response = self._ask_with_resources(
                    REVIEW_AND_GATE_PROMPT,
                    attach_packet=True,
                    additional_resources=review_resources,
                )
                self._move(ProtocolState.SELF_AUDIT)
                self._move(ProtocolState.GATE_DECISION)
                try:
                    gate = extract_model_gate_proposal(gate_response.output_text)
                except ValueError as exc:
                    return self._finish(
                        ControllerDisposition.MANUAL_REVIEW_REQUIRED,
                        f"Model gate proposal is malformed: {exc}",
                    )
                self.last_gate = gate
                self._record("model_gate_proposal", {"model_gate_proposal": gate.value})
                if gate is ModelGateProposal.SESSION_PASS:
                    return self._finish(ControllerDisposition.SESSION_PASSED, "Model proposed SESSION_PASS.")
                if gate is ModelGateProposal.SESSION_FAIL:
                    return self._finish(ControllerDisposition.SESSION_FAILED, "Model proposed SESSION_FAIL.")
                if gate is ModelGateProposal.MANUAL_REVIEW_REQUIRED:
                    return self._finish(
                        ControllerDisposition.MANUAL_REVIEW_REQUIRED,
                        "Model proposed MANUAL_REVIEW_REQUIRED.",
                    )
                if self.usage.proven_rounds >= self.budgets.maximum_proven_rounds:
                    return self._finish(
                        ControllerDisposition.BUDGET_EXHAUSTED,
                        "Model requested another round after the maximum proven-round budget.",
                    )
                next_binding = resolve_round_authority(
                    gate,
                    preceding=preceding_binding,
                    derived=derived_binding,
                )
                if next_binding == preceding_binding:
                    self.current_bundle = preceding_bundle
                else:
                    self.current_bundle = derived_bundle
                self.current_packet = next_binding
                self._move(ProtocolState.OBSERVE)
        except RunStoreWriteError as exc:
            self.disposition = ControllerDisposition.RUN_STORE_FAILED
            message = (
                f"Run-store write failed ({exc.code}); event_appended={exc.event_appended}; "
                f"event_sequence={exc.event_sequence}: {exc}"
            )
            try:
                self.transport.close_owned_files(reason=ControllerDisposition.RUN_STORE_FAILED.value)
            except Exception as cleanup_exc:
                message = f"{message} Provider-file cleanup also failed: {cleanup_exc}"
            return AutomatedSessionResult(
                disposition=self.disposition,
                message=message,
                current_packet=self.current_packet,
                proven_rounds=self.usage.proven_rounds,
                usage=self.usage,
                model_gate_proposal=self.last_gate,
                last_proof=self.last_proof,
                last_derived_bundle=self.last_derived_bundle,
            )
        except TransportCancelled as exc:
            return self._finish(ControllerDisposition.CANCELLED, str(exc))
        except DispatchAuthorizationRejected as exc:
            return self._finish(ControllerDisposition.BUDGET_EXHAUSTED, str(exc))
        except JobCancelledError as exc:
            return self._finish(ControllerDisposition.CANCELLED, str(exc))
        except AmbiguousRemoteCompletion as exc:
            return self._finish(
                ControllerDisposition.MANUAL_REVIEW_REQUIRED,
                f"Remote completion is ambiguous and will not be resent: {exc}",
            )
        except ProviderTransportError as exc:
            disposition = (
                ControllerDisposition.MANUAL_REVIEW_REQUIRED
                if exc.remote_completion_ambiguous
                else ControllerDisposition.TRANSPORT_FAILED
            )
            return self._finish(disposition, f"Provider transport failed ({exc.kind.value}): {exc}")
        except RuntimeError as exc:
            if "budget exhausted" in str(exc):
                return self._finish(ControllerDisposition.BUDGET_EXHAUSTED, str(exc))
            return self._finish(ControllerDisposition.RUNTIME_FAILED, str(exc))
        except Exception as exc:
            return self._finish(ControllerDisposition.RUNTIME_FAILED, str(exc))
