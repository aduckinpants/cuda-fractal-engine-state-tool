from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum


AGENT_SESSION_PROTOCOL_SCHEMA = "agent_session_protocol.v1"


class ProtocolState(str, Enum):
    OBSERVE = "OBSERVE"
    EXPLORE = "EXPLORE"
    SELECT_EXPERIMENT = "SELECT_EXPERIMENT"
    LOCK_PREDICTION = "LOCK_PREDICTION"
    REQUEST_OVERRIDE = "REQUEST_OVERRIDE"
    VALIDATE_OVERRIDE = "VALIDATE_OVERRIDE"
    PROVE_CANDIDATE = "PROVE_CANDIDATE"
    PROMOTE_DERIVED_FINDING = "PROMOTE_DERIVED_FINDING"
    REFRESH_PACKET = "REFRESH_PACKET"
    REVIEW_RESULT = "REVIEW_RESULT"
    SELF_AUDIT = "SELF_AUDIT"
    GATE_DECISION = "GATE_DECISION"


class ModelGateProposal(str, Enum):
    ROUND_ADVANCE = "ROUND_ADVANCE"
    ROUND_REVISE = "ROUND_REVISE"
    SESSION_PASS = "SESSION_PASS"
    SESSION_FAIL = "SESSION_FAIL"
    MANUAL_REVIEW_REQUIRED = "MANUAL_REVIEW_REQUIRED"


class ControllerDisposition(str, Enum):
    RUNNING = "RUNNING"
    SESSION_PASSED = "SESSION_PASSED"
    SESSION_FAILED = "SESSION_FAILED"
    MANUAL_REVIEW_REQUIRED = "MANUAL_REVIEW_REQUIRED"
    BUDGET_EXHAUSTED = "BUDGET_EXHAUSTED"
    CANCELLED = "CANCELLED"
    PROOF_FAILED = "PROOF_FAILED"
    TRANSPORT_FAILED = "TRANSPORT_FAILED"
    RUN_STORE_FAILED = "RUN_STORE_FAILED"
    RUNTIME_FAILED = "RUNTIME_FAILED"


@dataclass(frozen=True)
class SessionBudgets:
    maximum_proven_rounds: int = 2
    maximum_model_responses: int = 6
    maximum_cumulative_input_tokens: int = 2_000_000
    maximum_cumulative_output_tokens: int = 48_000
    maximum_input_tokens_per_response: int = 200_000
    maximum_output_tokens_per_response: int = 8_000
    maximum_review_output_tokens_per_response: int = 4_000
    maximum_correction_output_tokens_per_response: int = 4_000
    maximum_calculated_cost_usd: Decimal = Decimal("10.00")

    def __post_init__(self) -> None:
        if any(
            value < 1
            for value in (
                self.maximum_proven_rounds,
                self.maximum_model_responses,
                self.maximum_cumulative_input_tokens,
                self.maximum_cumulative_output_tokens,
                self.maximum_input_tokens_per_response,
                self.maximum_output_tokens_per_response,
                self.maximum_review_output_tokens_per_response,
                self.maximum_correction_output_tokens_per_response,
            )
        ):
            raise ValueError("Automated session budgets must be positive")
        if (
            not self.maximum_calculated_cost_usd.is_finite()
            or self.maximum_calculated_cost_usd < 0
        ):
            raise ValueError("Automated session dollar budget must be finite and non-negative")
        if (
            self.maximum_review_output_tokens_per_response
            > self.maximum_output_tokens_per_response
            or self.maximum_correction_output_tokens_per_response
            > self.maximum_output_tokens_per_response
        ):
            raise ValueError("Stage output-token caps cannot exceed the response maximum")

    def to_dict(self) -> dict[str, int | str]:
        return {
            "maximum_proven_rounds": self.maximum_proven_rounds,
            "maximum_model_responses": self.maximum_model_responses,
            "maximum_cumulative_input_tokens": self.maximum_cumulative_input_tokens,
            "maximum_cumulative_output_tokens": self.maximum_cumulative_output_tokens,
            "maximum_input_tokens_per_response": self.maximum_input_tokens_per_response,
            "maximum_output_tokens_per_response": self.maximum_output_tokens_per_response,
            "maximum_review_output_tokens_per_response": (
                self.maximum_review_output_tokens_per_response
            ),
            "maximum_correction_output_tokens_per_response": (
                self.maximum_correction_output_tokens_per_response
            ),
            "maximum_calculated_cost_usd": format(self.maximum_calculated_cost_usd, "f"),
        }


@dataclass(frozen=True)
class BudgetUsage:
    proven_rounds: int = 0
    model_responses: int = 0
    cumulative_input_tokens: int = 0
    cumulative_cached_input_tokens: int = 0
    cumulative_output_tokens: int = 0
    cumulative_cache_write_tokens: int = 0
    cumulative_calculated_cost_usd: Decimal = Decimal("0")

    def __post_init__(self) -> None:
        if any(
            value < 0
            for value in (
                self.proven_rounds,
                self.model_responses,
                self.cumulative_input_tokens,
                self.cumulative_cached_input_tokens,
                self.cumulative_output_tokens,
                self.cumulative_cache_write_tokens,
            )
        ):
            raise ValueError("Automated session budget usage cannot be negative")
        if self.cumulative_cached_input_tokens > self.cumulative_input_tokens:
            raise ValueError("Cached input tokens cannot exceed total input tokens")
        if (
            self.cumulative_cached_input_tokens + self.cumulative_cache_write_tokens
            > self.cumulative_input_tokens
        ):
            raise ValueError("Cache reads and writes cannot exceed total input tokens")
        if (
            not self.cumulative_calculated_cost_usd.is_finite()
            or self.cumulative_calculated_cost_usd < 0
        ):
            raise ValueError("Calculated cost usage must be finite and non-negative")

    @property
    def cumulative_uncached_input_tokens(self) -> int:
        return self.cumulative_input_tokens - self.cumulative_cached_input_tokens


def budget_exhaustion_reason(
    budgets: SessionBudgets,
    usage: BudgetUsage,
    *,
    next_input_tokens: int = 0,
    next_output_tokens: int = 0,
    next_calculated_cost_usd: Decimal = Decimal("0"),
) -> str | None:
    if next_input_tokens < 0 or next_output_tokens < 0:
        raise ValueError("Projected token use cannot be negative")
    if not next_calculated_cost_usd.is_finite() or next_calculated_cost_usd < 0:
        raise ValueError("Projected calculated cost cannot be negative or non-finite")
    if usage.proven_rounds >= budgets.maximum_proven_rounds:
        return "maximum_proven_rounds"
    if usage.model_responses >= budgets.maximum_model_responses:
        return "maximum_model_responses"
    if (
        usage.cumulative_input_tokens + next_input_tokens
        > budgets.maximum_cumulative_input_tokens
    ):
        return "maximum_cumulative_input_tokens"
    if (
        usage.cumulative_output_tokens + next_output_tokens
        > budgets.maximum_cumulative_output_tokens
    ):
        return "maximum_cumulative_output_tokens"
    if next_input_tokens > budgets.maximum_input_tokens_per_response:
        return "maximum_input_tokens_per_response"
    if next_output_tokens > budgets.maximum_output_tokens_per_response:
        return "maximum_output_tokens_per_response"
    if (
        usage.cumulative_calculated_cost_usd + next_calculated_cost_usd
        > budgets.maximum_calculated_cost_usd
    ):
        return "maximum_calculated_cost_usd"
    return None


@dataclass(frozen=True)
class PacketAuthorityBinding:
    packet_id: str
    manifest_sha256: str
    finding_id: str

    def __post_init__(self) -> None:
        if not self.packet_id or not self.finding_id:
            raise ValueError("Packet authority binding requires packet and finding identities")
        if len(self.manifest_sha256) != 64 or any(
            character not in "0123456789abcdef" for character in self.manifest_sha256
        ):
            raise ValueError("Packet authority binding requires a SHA-256 manifest identity")

    def to_dict(self) -> dict[str, str]:
        return {
            "packet_id": self.packet_id,
            "manifest_sha256": self.manifest_sha256,
            "finding_id": self.finding_id,
        }


_LINEAR_STATES = tuple(ProtocolState)
_ALLOWED_TRANSITIONS = {
    (_LINEAR_STATES[index], _LINEAR_STATES[index + 1])
    for index in range(len(_LINEAR_STATES) - 1)
}
_ALLOWED_TRANSITIONS.update(
    {
        (ProtocolState.VALIDATE_OVERRIDE, ProtocolState.REQUEST_OVERRIDE),
        (ProtocolState.GATE_DECISION, ProtocolState.OBSERVE),
    }
)


def parse_model_gate_proposal(value: str) -> ModelGateProposal:
    try:
        return ModelGateProposal(value)
    except ValueError as exc:
        raise ValueError(f"Unsupported model gate proposal: {value}") from exc


def validate_protocol_transition(current: ProtocolState, target: ProtocolState) -> None:
    if (current, target) not in _ALLOWED_TRANSITIONS:
        raise ValueError(f"Illegal protocol transition: {current.value} -> {target.value}")


def resolve_round_authority(
    proposal: ModelGateProposal,
    *,
    preceding: PacketAuthorityBinding,
    derived: PacketAuthorityBinding | None,
) -> PacketAuthorityBinding:
    if proposal is ModelGateProposal.ROUND_ADVANCE:
        if derived is None:
            raise ValueError("ROUND_ADVANCE requires a replay-proven derived packet")
        return derived
    if proposal is ModelGateProposal.ROUND_REVISE:
        return preceding
    raise ValueError(f"Model gate does not select another round authority: {proposal.value}")


def classify_override_effect(
    *,
    changed_path_count: int,
    empty_override_byte_exact: bool,
    explicit_unchanged_requested: bool,
) -> str:
    if changed_path_count < 0:
        raise ValueError("Changed path count cannot be negative")
    if changed_path_count > 0:
        return "AUTHORIZED_CHANGE"
    if empty_override_byte_exact and explicit_unchanged_requested:
        return "EXACT_BASE_REPLAY"
    if empty_override_byte_exact:
        return "UNINTENDED_NO_EFFECT"
    return "NO_EFFECT"
