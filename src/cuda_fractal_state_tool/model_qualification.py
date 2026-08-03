from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Any, Iterable

from .agent_bundle import AgentBundle, load_existing_agent_bundle
from .automated_protocol import (
    AGENT_SESSION_PROTOCOL_SCHEMA,
    ControllerDisposition,
    ModelGateProposal,
    SessionBudgets,
)
from .automated_run_store import AutomatedRunStore
from .automated_session import (
    AUTHOR_ROUND_PROMPT,
    AUTOMATED_SESSION_INSTRUCTIONS,
    REVIEW_AND_GATE_PROMPT,
    AutomatedRouteServices,
    AutomatedSessionController,
    AutomatedSessionResult,
    InitialAuthorCountResult,
)
from .enrichment_disclosure import DisclosureProfile
from .model_profile import ModelProfileV1
from .openai_transport import PromptCachePolicy, TransportTurnResult
from .pricing_policy import PricingPolicy, decimal_text
from .json_utils import loads_strict_no_duplicates


QUALIFICATION_CASE_VERSION = 1
QUALIFICATION_RECEIPT_VERSION = 1
QUALIFICATION_RUBRIC_VERSION = "v9-economic-qualification-rubric.v1"
CAMPAIGN_CEILING_USD = Decimal("8.00")
AUTOMATIC_GATE_IDS = (
    "terminal_controller",
    "packet_binding",
    "model_profile",
    "resolved_model_family",
    "explicit_no_cache",
    "disclosure_binding",
    "replay_proof",
    "cost_ceiling",
    "immutable_evidence",
    "no_fabricated_human_acceptance",
)


class QualificationRole(str, Enum):
    HARD_CALIBRATOR = "hard_calibrator"
    DYNAMICS_CONFIRMATION = "dynamics_confirmation"
    OBSERVATION_CONFIRMATION = "observation_confirmation"


def _canonical_json_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class QualificationCaseV1:
    role: QualificationRole
    packet_dir: Path
    packet_id: str
    packet_manifest_sha256: str
    finding_id: str
    selected_fractal_type: str
    disclosure_profile: DisclosureProfile
    expected_analysis_id: str | None
    model_profile: ModelProfileV1
    budgets: SessionBudgets
    pricing_policy_identity: dict[str, Any]
    pricing_policy_sha256: str
    rubric_version: str = QUALIFICATION_RUBRIC_VERSION
    campaign_ceiling_usd: Decimal = CAMPAIGN_CEILING_USD

    def __post_init__(self) -> None:
        if self.budgets.maximum_proven_rounds != 1:
            raise ValueError("Qualification Case V1 permits exactly one proven round")
        if self.budgets.maximum_model_responses != 2:
            raise ValueError("Qualification Case V1 permits exactly one author and one review response")
        if self.budgets.maximum_calculated_cost_usd > self.campaign_ceiling_usd:
            raise ValueError("Qualification cell ceiling exceeds the approved campaign ceiling")
        if self.disclosure_profile is DisclosureProfile.BLIND and self.expected_analysis_id:
            raise ValueError("Blind qualification cases cannot bind an enrichment analysis")
        if self.disclosure_profile is not DisclosureProfile.BLIND and not self.expected_analysis_id:
            raise ValueError("Non-blind qualification cases require an exact enrichment analysis ID")

    @classmethod
    def create(
        cls,
        *,
        role: QualificationRole,
        packet_dir: Path,
        disclosure_profile: DisclosureProfile,
        expected_analysis_id: str | None,
        model_profile: ModelProfileV1,
        budgets: SessionBudgets,
        pricing_policy: PricingPolicy,
    ) -> "QualificationCaseV1":
        model_profile.validate(pricing_policy)
        bundle = load_existing_agent_bundle(packet_dir)
        if bundle.packet_version != 8:
            raise ValueError("Qualification cases require immutable Packet V8 authority")
        return cls(
            role=QualificationRole(role),
            packet_dir=bundle.packet_dir,
            packet_id=bundle.packet_id,
            packet_manifest_sha256=bundle.manifest_sha256,
            finding_id=bundle.finding_id,
            selected_fractal_type=bundle.selected_fractal_type,
            disclosure_profile=DisclosureProfile(disclosure_profile),
            expected_analysis_id=expected_analysis_id,
            model_profile=model_profile,
            budgets=budgets,
            pricing_policy_identity=pricing_policy.identity_dict(),
            pricing_policy_sha256=pricing_policy.sha256,
        )

    def packet_binding(self) -> dict[str, str]:
        return {
            "packet_id": self.packet_id,
            "manifest_sha256": self.packet_manifest_sha256,
            "finding_id": self.finding_id,
            "selected_fractal_type": self.selected_fractal_type,
        }

    def prompt_identities(self) -> dict[str, str]:
        return {
            "instructions_sha256": _sha256_text(AUTOMATED_SESSION_INSTRUCTIONS),
            "author_prompt_sha256": _sha256_text(AUTHOR_ROUND_PROMPT),
            "review_prompt_sha256": _sha256_text(REVIEW_AND_GATE_PROMPT),
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "qualification_case_version": QUALIFICATION_CASE_VERSION,
            "role": self.role.value,
            "packet": self.packet_binding(),
            "disclosure": {
                "profile": self.disclosure_profile.value,
                "expected_analysis_id": self.expected_analysis_id,
            },
            "model_profile": self.model_profile.identity_dict(),
            "budgets": self.budgets.to_dict(),
            "prompt_identities": self.prompt_identities(),
            "protocol_schema": AGENT_SESSION_PROTOCOL_SCHEMA,
            "pricing_policy": self.pricing_policy_identity,
            "pricing_policy_sha256": self.pricing_policy_sha256,
            "rubric_version": self.rubric_version,
            "campaign_ceiling_usd": decimal_text(self.campaign_ceiling_usd),
        }

    @property
    def sha256(self) -> str:
        return hashlib.sha256(_canonical_json_bytes(self.to_dict())).hexdigest()

    def identity_dict(self) -> dict[str, Any]:
        return {**self.to_dict(), "sha256": self.sha256}

    def validate_bundle(self, bundle: AgentBundle) -> None:
        actual = {
            "packet_id": bundle.packet_id,
            "manifest_sha256": bundle.manifest_sha256,
            "finding_id": bundle.finding_id,
            "selected_fractal_type": bundle.selected_fractal_type,
        }
        if actual != self.packet_binding():
            raise ValueError("Qualification case packet authority changed")

    @classmethod
    def from_dict(
        cls,
        value: Any,
        *,
        packet_dir: Path,
        pricing_policy: PricingPolicy,
    ) -> "QualificationCaseV1":
        if not isinstance(value, dict) or value.get("qualification_case_version") != 1:
            raise ValueError("Unsupported qualification-case schema")
        profile_value = value.get("model_profile")
        budget_value = value.get("budgets")
        disclosure_value = value.get("disclosure")
        if not all(isinstance(item, dict) for item in (profile_value, budget_value, disclosure_value)):
            raise ValueError("Qualification case has malformed profile, budget, or disclosure data")
        try:
            profile = ModelProfileV1(
                model=profile_value["model"],
                reasoning_effort=profile_value["reasoning_effort"],
                pricing_tier=profile_value["pricing_tier"],
                prompt_cache_policy=PromptCachePolicy(profile_value["prompt_cache_policy"]),
            )
            budgets = SessionBudgets(
                maximum_proven_rounds=budget_value["maximum_proven_rounds"],
                maximum_model_responses=budget_value["maximum_model_responses"],
                maximum_cumulative_input_tokens=budget_value[
                    "maximum_cumulative_input_tokens"
                ],
                maximum_cumulative_output_tokens=budget_value[
                    "maximum_cumulative_output_tokens"
                ],
                maximum_input_tokens_per_response=budget_value[
                    "maximum_input_tokens_per_response"
                ],
                maximum_output_tokens_per_response=budget_value[
                    "maximum_output_tokens_per_response"
                ],
                maximum_review_output_tokens_per_response=budget_value[
                    "maximum_review_output_tokens_per_response"
                ],
                maximum_correction_output_tokens_per_response=budget_value[
                    "maximum_correction_output_tokens_per_response"
                ],
                maximum_calculated_cost_usd=Decimal(
                    budget_value["maximum_calculated_cost_usd"]
                ),
            )
            case = cls.create(
                role=QualificationRole(value["role"]),
                packet_dir=packet_dir,
                disclosure_profile=DisclosureProfile(disclosure_value["profile"]),
                expected_analysis_id=disclosure_value.get("expected_analysis_id"),
                model_profile=profile,
                budgets=budgets,
                pricing_policy=pricing_policy,
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"Qualification case fields are invalid: {exc}") from exc
        if case.identity_dict() != value:
            raise ValueError("Qualification case identity or current authority disagrees")
        return case


def load_qualification_case(
    path: Path,
    *,
    packet_dir: Path,
    pricing_policy: PricingPolicy,
) -> QualificationCaseV1:
    try:
        value = loads_strict_no_duplicates(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError) as exc:
        raise ValueError(f"Qualification case is unavailable or malformed: {path}") from exc
    return QualificationCaseV1.from_dict(
        value,
        packet_dir=packet_dir,
        pricing_policy=pricing_policy,
    )


@dataclass(frozen=True)
class RecordedTurn:
    output_text: str
    input_tokens: int
    output_tokens: int
    resolved_model: str
    response_id: str
    cached_input_tokens: int = 0
    cache_write_tokens: int = 0
    latency_seconds: float = 0.0


class RecordedResponsesTransport:
    """Offline transport that exercises controller behavior without provider access."""

    def __init__(self, turns: Iterable[RecordedTurn]) -> None:
        self._turns = list(turns)
        self._index = 0

    def send_turn(self, **kwargs: Any) -> TransportTurnResult:
        if self._index >= len(self._turns):
            raise RuntimeError("Recorded response script is exhausted")
        turn = self._turns[self._index]
        self._index += 1
        authorize = kwargs.get("authorize_dispatch")
        if authorize is not None:
            authorize(turn.input_tokens)
        requested_model = str(kwargs["model"])
        reasoning_effort = str(kwargs["reasoning_effort"])
        cache_policy = PromptCachePolicy(kwargs["prompt_cache_policy"])
        run_store = kwargs.get("run_store")
        turn_id = str(kwargs.get("turn_id", f"turn-{self._index:04d}"))
        request_path = None
        response_path = None
        if run_store is not None:
            request_path = run_store.write_evidence_json(
                f"transport/{turn_id}/request.json",
                {
                    "offline_recorded_response": True,
                    "requested_model": requested_model,
                    "reasoning_effort": reasoning_effort,
                    "prompt_cache_policy": cache_policy.value,
                    "maximum_output_tokens": kwargs["max_output_tokens"],
                    "packet_dir": str(kwargs.get("packet_dir") or ""),
                    "previous_response_id": kwargs.get("previous_response_id"),
                    "prompt_sha256": _sha256_text(str(kwargs["prompt"])),
                    "instructions_sha256": _sha256_text(str(kwargs["instructions"])),
                    "additional_resources": [
                        resource.to_evidence()
                        for resource in kwargs.get("additional_resources", ())
                    ],
                },
            )
            run_store.write_evidence_json(
                f"transport/{turn_id}/input-token-count.json",
                {"input_tokens": turn.input_tokens, "phase": "offline_recorded_response"},
            )
            response_path = run_store.write_evidence_json(
                f"transport/{turn_id}/response.json",
                {
                    "offline_recorded_response": True,
                    "response_id": turn.response_id,
                    "requested_model": requested_model,
                    "resolved_model": turn.resolved_model,
                    "reasoning_effort": reasoning_effort,
                    "input_tokens": turn.input_tokens,
                    "cached_input_tokens": turn.cached_input_tokens,
                    "cache_write_tokens": turn.cache_write_tokens,
                    "output_tokens": turn.output_tokens,
                    "output_text_sha256": _sha256_text(turn.output_text),
                },
            )
        return TransportTurnResult(
            response_id=turn.response_id,
            previous_response_id=kwargs.get("previous_response_id"),
            model=turn.resolved_model,
            output_text=turn.output_text,
            input_tokens=turn.input_tokens,
            output_tokens=turn.output_tokens,
            resources=(),
            unavailable_optional_attachments=(),
            requested_model=requested_model,
            reasoning_effort=reasoning_effort,
            model_profile_sha256=kwargs.get("model_profile_sha256"),
            cached_input_tokens=turn.cached_input_tokens,
            cache_write_tokens=turn.cache_write_tokens,
            prompt_cache_policy=cache_policy.value,
            latency_seconds=turn.latency_seconds,
            request_evidence_path=request_path,
            response_evidence_path=response_path,
        )

    def close_owned_files(self, **kwargs: Any) -> None:
        run_store = kwargs.get("run_store")
        if run_store is not None:
            run_store.write_evidence_json(
                "transport/provider-file-cleanup.json",
                {
                    "offline_recorded_response": True,
                    "cleanup_complete": True,
                    "remaining_provider_file_ids": [],
                    "reason": kwargs.get("reason"),
                },
            )


@dataclass(frozen=True)
class AutomaticGateResult:
    gate_id: str
    passed: bool
    detail: str

    def to_dict(self) -> dict[str, Any]:
        return {"gate_id": self.gate_id, "passed": self.passed, "detail": self.detail}


@dataclass(frozen=True)
class QualificationReceipt:
    case_sha256: str
    passed: bool
    gates: tuple[AutomaticGateResult, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "qualification_receipt_version": QUALIFICATION_RECEIPT_VERSION,
            "case_sha256": self.case_sha256,
            "automatic_gates_passed": self.passed,
            "gates": [gate.to_dict() for gate in self.gates],
            "human_rubric": "pending_independent_review",
            "human_acceptance_recorded": False,
        }


@dataclass(frozen=True)
class QualificationCountReceipt:
    case_sha256: str
    input_tokens: int
    maximum_output_tokens: int
    estimated_maximum_cost_usd: Decimal
    within_case_budget: bool
    budget_exhaustion_reason: str | None
    request_evidence_path: Path | None
    count_evidence_path: Path | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "qualification_count_receipt_version": 1,
            "case_sha256": self.case_sha256,
            "input_tokens": self.input_tokens,
            "maximum_output_tokens": self.maximum_output_tokens,
            "estimated_maximum_cost_usd": decimal_text(
                self.estimated_maximum_cost_usd
            ),
            "within_case_budget": self.within_case_budget,
            "budget_exhaustion_reason": self.budget_exhaustion_reason,
            "request_evidence_path": (
                str(self.request_evidence_path) if self.request_evidence_path else None
            ),
            "count_evidence_path": (
                str(self.count_evidence_path) if self.count_evidence_path else None
            ),
            "generation_dispatched": False,
            "provider_billing_authority": "provider billing remains authoritative",
        }


def _contains_true_human_acceptance(value: Any) -> bool:
    if isinstance(value, dict):
        return any(
            (key == "human_acceptance" and item is True)
            or _contains_true_human_acceptance(item)
            for key, item in value.items()
        )
    if isinstance(value, list):
        return any(_contains_true_human_acceptance(item) for item in value)
    return False


def _expected_effective_disclosure_profile(
    configured: DisclosureProfile,
    phase: str,
) -> DisclosureProfile:
    if configured is DisclosureProfile.ASSISTED:
        return DisclosureProfile.ASSISTED
    if configured is DisclosureProfile.BREAK_BLIND and phase == "review":
        return DisclosureProfile.BREAK_BLIND
    return DisclosureProfile.BLIND


def _disclosure_binding_matches(
    *,
    case: QualificationCaseV1,
    result: AutomatedSessionResult,
    run_store: AutomatedRunStore,
    disclosures: list[dict[str, Any]],
) -> bool:
    if len(disclosures) != 2:
        return False
    by_phase: dict[str, dict[str, Any]] = {}
    for event in disclosures:
        payload = event.get("payload")
        if not isinstance(payload, dict):
            return False
        phase = payload.get("phase")
        if phase not in {"author", "review"} or phase in by_phase:
            return False
        by_phase[phase] = payload
    expected_packets = {
        "author": {
            "packet_id": case.packet_id,
            "packet_manifest_sha256": case.packet_manifest_sha256,
            "finding_id": case.finding_id,
        },
        "review": {
            "packet_id": result.current_packet.packet_id,
            "packet_manifest_sha256": result.current_packet.manifest_sha256,
            "finding_id": result.current_packet.finding_id,
        },
    }
    for phase in ("author", "review"):
        payload = by_phase[phase]
        expected_profile = _expected_effective_disclosure_profile(
            case.disclosure_profile,
            phase,
        )
        if (
            payload.get("round_number") != 1
            or payload.get("configured_profile") != case.disclosure_profile.value
            or payload.get("effective_profile") != expected_profile.value
            or any(payload.get(key) != value for key, value in expected_packets[phase].items())
        ):
            return False
        path = (
            run_store.run_dir
            / "rounds"
            / "round-01"
            / "context"
            / f"{phase}-enrichment-disclosure.json"
        )
        if not path.is_file():
            return False
        try:
            manifest = loads_strict_no_duplicates(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, ValueError):
            return False
        if not isinstance(manifest, dict):
            return False
        expected_manifest_fields = {
            "profile": expected_profile.value,
            **expected_packets[phase],
            "disclosure_id": payload.get("disclosure_id"),
            "analysis_id": payload.get("analysis_id"),
        }
        if any(manifest.get(key) != value for key, value in expected_manifest_fields.items()):
            return False
        resources = manifest.get("resources")
        if not isinstance(resources, list) or payload.get("resource_count") != len(resources):
            return False
        analysis_id = payload.get("analysis_id")
        if expected_profile is DisclosureProfile.BLIND:
            if analysis_id is not None:
                return False
        elif not isinstance(analysis_id, str) or not analysis_id:
            return False
        if phase == "author" and expected_profile is DisclosureProfile.ASSISTED:
            if analysis_id != case.expected_analysis_id:
                return False
    return True


def evaluate_automatic_gates(
    *,
    case: QualificationCaseV1,
    result: AutomatedSessionResult,
    run_store: AutomatedRunStore,
    pricing_policy: PricingPolicy,
) -> QualificationReceipt:
    events = run_store.read_events()
    responses = [event for event in events if event.get("event_type") == "model_response"]
    disclosures = [
        event for event in events if event.get("event_type") == "enrichment_disclosure_prepared"
    ]
    expected_family = pricing_policy.model(case.model_profile.model).pricing_model
    resolved_families: list[str] = []
    resolved_error = ""
    try:
        resolved_families = [
            pricing_policy.model(str(event["payload"]["resolved_model"])).pricing_model
            for event in responses
        ]
    except (KeyError, TypeError, ValueError) as exc:
        resolved_error = str(exc)
    transport_paths_complete = bool(responses) and all(
        all(
            (run_store.run_dir / "transport" / f"turn-{index:04d}" / name).is_file()
            for name in ("request.json", "input-token-count.json", "response.json")
        )
        for index in range(1, len(responses) + 1)
    )
    cleanup_path = run_store.run_dir / "transport" / "provider-file-cleanup.json"
    cleanup_complete = False
    if cleanup_path.is_file():
        try:
            cleanup_complete = json.loads(cleanup_path.read_text(encoding="utf-8")).get(
                "cleanup_complete"
            ) is True
        except (OSError, UnicodeError, json.JSONDecodeError):
            cleanup_complete = False
    initial_matches = bool(events) and events[0].get("event_type") == "session_started" and (
        events[0].get("payload", {}).get("initial_packet")
        == {
            "packet_id": case.packet_id,
            "manifest_sha256": case.packet_manifest_sha256,
            "finding_id": case.finding_id,
        }
    )
    reasoning_matches = bool(responses) and all(
        event.get("payload", {}).get("reasoning_effort")
        == case.model_profile.reasoning_effort
        for event in responses
    )
    request_matches = bool(responses) and all(
        event.get("payload", {}).get("requested_model") == case.model_profile.model
        and event.get("payload", {}).get("model_profile", {}).get("sha256")
        == case.model_profile.sha256
        for event in responses
    )
    cache_clean = bool(responses) and all(
        event.get("payload", {}).get("cached_input_tokens") == 0
        and event.get("payload", {}).get("cache_write_tokens") == 0
        and event.get("payload", {}).get("prompt_cache_policy")
        == PromptCachePolicy.EXPLICIT_NO_CACHE.value
        for event in responses
    )
    disclosure_matches = _disclosure_binding_matches(
        case=case,
        result=result,
        run_store=run_store,
        disclosures=disclosures,
    )
    review_ledger_matches = False
    review_comparison_matches = False
    ledger_path = (
        run_store.run_dir
        / "rounds"
        / "round-01"
        / "context"
        / "round-review-ledger.json"
    )
    if ledger_path.is_file() and result.last_proof is not None:
        try:
            ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
            review_ledger_matches = (
                ledger.get("author_packet")
                == {
                    "packet_id": case.packet_id,
                    "manifest_sha256": case.packet_manifest_sha256,
                    "finding_id": case.finding_id,
                }
                and ledger.get("derived_packet") == result.current_packet.to_dict()
                and ledger.get("proof", {}).get("proof_id") == result.last_proof.proof_id
                and ledger.get("proof", {}).get("status") == "replay_proven"
                and ledger.get("proof", {}).get("receipt_sha256")
                == result.last_proof.receipt_sha256
            )
        except (OSError, UnicodeError, json.JSONDecodeError):
            review_ledger_matches = False
    comparison_path = (
        run_store.run_dir
        / "rounds"
        / "round-01"
        / "context"
        / "round-review-comparison.json"
    )
    base_review_frame = comparison_path.with_name("review-base-web-agent-frame.png")
    result_review_frame = comparison_path.with_name("review-result-web-agent-frame.png")
    review_events = [
        event for event in events if event.get("event_type") == "review_conversation_started"
    ]
    if (
        comparison_path.is_file()
        and base_review_frame.is_file()
        and result_review_frame.is_file()
        and len(review_events) == 1
        and result.last_proof is not None
    ):
        try:
            comparison_payload = comparison_path.read_bytes()
            comparison = loads_strict_no_duplicates(comparison_payload.decode("utf-8"))
            base_payload = base_review_frame.read_bytes()
            result_payload = result_review_frame.read_bytes()
            review_event = review_events[0].get("payload", {})
            review_comparison_matches = (
                hashlib.sha256(comparison_payload).hexdigest()
                == review_event.get("review_comparison_sha256")
                and hashlib.sha256(base_payload).hexdigest()
                == review_event.get("base_web_frame_sha256")
                == comparison.get("base_web_frame", {}).get("sha256")
                and hashlib.sha256(result_payload).hexdigest()
                == review_event.get("result_web_frame_sha256")
                == comparison.get("result_web_frame", {}).get("sha256")
                and comparison.get("author_packet")
                == {
                    "packet_id": case.packet_id,
                    "manifest_sha256": case.packet_manifest_sha256,
                    "finding_id": case.finding_id,
                }
                and comparison.get("derived_packet") == result.current_packet.to_dict()
                and comparison.get("proof", {}).get("proof_id") == result.last_proof.proof_id
                and comparison.get("proof", {}).get("status") == "replay_proven"
                and comparison.get("proof", {}).get("receipt_sha256")
                == result.last_proof.receipt_sha256
            )
        except (OSError, UnicodeError, json.JSONDecodeError):
            review_comparison_matches = False
    review_binding_complete = (
        sum(event.get("event_type") == "candidate_replay_proven" for event in events) == 1
        and sum(event.get("event_type") == "derived_packet_refreshed" for event in events) == 1
        and sum(event.get("event_type") == "review_conversation_started" for event in events)
        == 1
        and sum(event.get("event_type") == "model_gate_proposal" for event in events) == 1
        and review_ledger_matches
        and review_comparison_matches
    )
    bounded_round_limit = (
        result.disposition is ControllerDisposition.BUDGET_EXHAUSTED
        and result.proven_rounds == case.budgets.maximum_proven_rounds
        and result.model_gate_proposal
        in {ModelGateProposal.ROUND_ADVANCE, ModelGateProposal.ROUND_REVISE}
    )
    terminal_controller_passed = (
        result.disposition is ControllerDisposition.SESSION_PASSED or bounded_round_limit
    )
    terminal_detail = (
        f"bounded_round_limit_after_{result.model_gate_proposal.value}"
        if bounded_round_limit and result.model_gate_proposal is not None
        else result.disposition.value
    )
    gates = (
        AutomaticGateResult(
            "terminal_controller",
            terminal_controller_passed,
            terminal_detail,
        ),
        AutomaticGateResult("packet_binding", initial_matches, case.packet_id),
        AutomaticGateResult("model_profile", request_matches and reasoning_matches, case.model_profile.sha256),
        AutomaticGateResult(
            "resolved_model_family",
            bool(resolved_families)
            and not resolved_error
            and all(value == expected_family for value in resolved_families),
            resolved_error or ",".join(resolved_families),
        ),
        AutomaticGateResult("explicit_no_cache", cache_clean, f"responses={len(responses)}"),
        AutomaticGateResult(
            "disclosure_binding",
            disclosure_matches,
            f"profile={case.disclosure_profile.value};analysis={case.expected_analysis_id}",
        ),
        AutomaticGateResult(
            "replay_proof",
            result.proven_rounds == 1
            and result.last_proof is not None
            and result.last_proof.status == "replay_proven",
            f"proven_rounds={result.proven_rounds}",
        ),
        AutomaticGateResult(
            "cost_ceiling",
            result.usage.cumulative_calculated_cost_usd
            <= case.budgets.maximum_calculated_cost_usd
            <= case.campaign_ceiling_usd,
            decimal_text(result.usage.cumulative_calculated_cost_usd),
        ),
        AutomaticGateResult(
            "immutable_evidence",
            transport_paths_complete
            and cleanup_complete
            and review_binding_complete
            and result.last_proof is not None,
            (
                f"transport={transport_paths_complete};cleanup={cleanup_complete};"
                f"review_binding={review_binding_complete};ledger={review_ledger_matches};"
                f"comparison={review_comparison_matches}"
            ),
        ),
        AutomaticGateResult(
            "no_fabricated_human_acceptance",
            not _contains_true_human_acceptance(events),
            "human acceptance remains independently owned",
        ),
    )
    if tuple(gate.gate_id for gate in gates) != AUTOMATIC_GATE_IDS:
        raise RuntimeError("Automatic qualification gate implementation drifted")
    return QualificationReceipt(
        case_sha256=case.sha256,
        passed=all(gate.passed for gate in gates),
        gates=gates,
    )


def create_qualification_run_store(
    *,
    workspace_root: Path,
    run_id: str,
    case: QualificationCaseV1,
) -> AutomatedRunStore:
    store = AutomatedRunStore.create(
        workspace_root,
        run_id=run_id,
        protocol_snapshot={
            "schema": AGENT_SESSION_PROTOCOL_SCHEMA,
            "qualification_case": case.identity_dict(),
        },
        initial_packet=case.packet_binding(),
    )
    store.write_evidence_json("qualification/case.json", case.identity_dict())
    return store


def count_qualification_author_input(
    *,
    case: QualificationCaseV1,
    bundle: AgentBundle,
    transport: Any,
    run_store: AutomatedRunStore,
    services: AutomatedRouteServices,
    pricing_policy: PricingPolicy,
) -> tuple[InitialAuthorCountResult, QualificationCountReceipt]:
    case.validate_bundle(bundle)
    case.model_profile.validate(pricing_policy)
    if pricing_policy.sha256 != case.pricing_policy_sha256:
        raise ValueError("Qualification case pricing authority changed")
    controller = AutomatedSessionController(
        transport=transport,
        run_store=run_store,
        initial_bundle=bundle,
        services=services,
        budgets=case.budgets,
        pricing_policy=pricing_policy,
        model_profile=case.model_profile,
        disclosure_profile=case.disclosure_profile,
        auto_promote=True,
    )
    result = controller.count_initial_author_input()
    receipt = QualificationCountReceipt(
        case_sha256=case.sha256,
        input_tokens=result.transport_count.input_tokens,
        maximum_output_tokens=result.transport_count.maximum_output_tokens,
        estimated_maximum_cost_usd=result.estimated_maximum_cost_usd,
        within_case_budget=result.budget_exhaustion_reason is None,
        budget_exhaustion_reason=result.budget_exhaustion_reason,
        request_evidence_path=result.transport_count.request_evidence_path,
        count_evidence_path=result.transport_count.count_evidence_path,
    )
    run_store.write_evidence_json("qualification/count-only-receipt.json", receipt.to_dict())
    return result, receipt


def run_qualification_case(
    *,
    case: QualificationCaseV1,
    bundle: AgentBundle,
    transport: Any,
    run_store: AutomatedRunStore,
    services: AutomatedRouteServices,
    pricing_policy: PricingPolicy,
) -> tuple[AutomatedSessionResult, QualificationReceipt]:
    case.validate_bundle(bundle)
    case.model_profile.validate(pricing_policy)
    if pricing_policy.sha256 != case.pricing_policy_sha256:
        raise ValueError("Qualification case pricing authority changed")
    controller = AutomatedSessionController(
        transport=transport,
        run_store=run_store,
        initial_bundle=bundle,
        services=services,
        budgets=case.budgets,
        pricing_policy=pricing_policy,
        model_profile=case.model_profile,
        disclosure_profile=case.disclosure_profile,
        auto_promote=True,
    )
    result = controller.run()
    receipt = evaluate_automatic_gates(
        case=case,
        result=result,
        run_store=run_store,
        pricing_policy=pricing_policy,
    )
    run_store.write_evidence_json("qualification/automatic-gates.json", receipt.to_dict())
    return result, receipt
