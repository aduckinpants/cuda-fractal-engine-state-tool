from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from .model_profile import ModelProfileV1
from .openai_transport import (
    DispatchAuthorizationRejected,
    PacketV8ResponsesTransport,
    TransportInputCountResult,
    TransportResource,
    TransportTurnResult,
)
from .pricing_policy import calculate_usage_cost, decimal_text
from .research_cost import (
    ResearchCostController,
    ResearchDispatchBudgetDecision,
    ResearchProviderStage,
)
from .research_run_store import ResearchRunStore


RESEARCH_PROVIDER_INSTRUCTIONS = """You are participating in a bounded fractal research session.
Use only the attached Packet V8 and controller evidence as authority.
Answer only the requested stage contract. Never equate replay proof or automated promotion with human acceptance.
Do not provide private chain-of-thought; provide the concise conclusions and exact structured artifact requested.
"""


@dataclass(frozen=True)
class ResearchCountGate:
    count: TransportInputCountResult
    budget: ResearchDispatchBudgetDecision
    conservative_adaptive_ceiling_usd: str


class ResearchProviderDispatcher:
    """Fresh-context provider dispatch with one exact dollar gate per call."""

    def __init__(
        self,
        *,
        transport: PacketV8ResponsesTransport,
        run_store: ResearchRunStore,
        cost: ResearchCostController,
        model_profile: ModelProfileV1,
        cancelled: Callable[[], bool] = lambda: False,
    ) -> None:
        if cost.model_profile != model_profile:
            raise ValueError("Research provider dispatcher model profile disagrees with cost authority")
        self.transport = transport
        self.run_store = run_store
        self.cost = cost
        self.model_profile = model_profile
        self.cancelled = cancelled

    def _record_budget(
        self,
        turn_id: str,
        decision: ResearchDispatchBudgetDecision,
    ) -> None:
        self.run_store.write_evidence_once_json(
            f"cost/{turn_id}-authorization.json",
            {
                "stage": decision.stage.value,
                "exact_input_tokens": decision.exact_input_tokens,
                "current_call": decision.current_call.to_dict(),
                "reserved_stages": [stage.value for stage in decision.reserved_stages],
                "reserved_cost_usd": decimal_text(decision.reserved_cost_usd),
                "spent_cost_usd": decimal_text(decision.spent_cost_usd),
                "hard_budget_usd": decimal_text(decision.hard_budget_usd),
                "required_available_cost_usd": decimal_text(
                    decision.required_available_cost_usd
                ),
                "authorized": decision.authorized,
                "rejection_reason": decision.rejection_reason,
            },
        )

    def count_only(
        self,
        *,
        stage: ResearchProviderStage,
        turn_id: str,
        prompt: str,
        packet_dir: Path | None,
        additional_resources: tuple[TransportResource, ...] = (),
        planner_may_execute: bool = False,
        correction_available: bool = False,
        alternate_communication_required: bool = False,
        experiment_attempts_remaining: int = 0,
    ) -> ResearchCountGate:
        stage = ResearchProviderStage(stage)
        limit = self.cost.stage_limits[stage]
        counted = self.transport.count_turn_input(
            instructions=RESEARCH_PROVIDER_INSTRUCTIONS,
            prompt=prompt,
            packet_dir=packet_dir,
            run_store=self.run_store,
            turn_id=turn_id,
            cancelled=self.cancelled,
            model=self.model_profile.model,
            reasoning_effort=self.model_profile.reasoning_effort,
            model_profile_sha256=self.model_profile.sha256,
            max_output_tokens=limit.maximum_output_tokens,
            prompt_cache_policy=self.model_profile.prompt_cache_policy,
            additional_resources=additional_resources,
        )
        decision = self.cost.authorize_dispatch(
            stage,
            exact_input_tokens=counted.input_tokens,
            planner_may_execute=planner_may_execute,
            correction_available=correction_available,
            alternate_communication_required=alternate_communication_required,
        )
        self._record_budget(turn_id, decision)
        ceiling = self.cost.conservative_adaptive_ceiling(
            experiment_attempts_remaining=experiment_attempts_remaining,
            correction_available=correction_available,
            alternate_communication_required=alternate_communication_required,
        )
        return ResearchCountGate(counted, decision, decimal_text(ceiling))

    def dispatch(
        self,
        *,
        stage: ResearchProviderStage,
        turn_id: str,
        prompt: str,
        packet_dir: Path | None,
        additional_resources: tuple[TransportResource, ...] = (),
        planner_may_execute: bool = False,
        correction_available: bool = False,
        alternate_communication_required: bool = False,
    ) -> TransportTurnResult:
        stage = ResearchProviderStage(stage)
        limit = self.cost.stage_limits[stage]

        def authorize(exact_input_tokens: int) -> None:
            decision = self.cost.authorize_dispatch(
                stage,
                exact_input_tokens=exact_input_tokens,
                planner_may_execute=planner_may_execute,
                correction_available=correction_available,
                alternate_communication_required=alternate_communication_required,
            )
            self._record_budget(turn_id, decision)
            if not decision.authorized:
                raise DispatchAuthorizationRejected(decision.rejection_reason or "Dollar gate rejected")

        result = self.transport.send_turn(
            instructions=RESEARCH_PROVIDER_INSTRUCTIONS,
            prompt=prompt,
            packet_dir=packet_dir,
            previous_response_id=None,
            run_store=self.run_store,
            turn_id=turn_id,
            cancelled=self.cancelled,
            model=self.model_profile.model,
            reasoning_effort=self.model_profile.reasoning_effort,
            model_profile_sha256=self.model_profile.sha256,
            max_output_tokens=limit.maximum_output_tokens,
            prompt_cache_policy=self.model_profile.prompt_cache_policy,
            authorize_dispatch=authorize,
            additional_resources=additional_resources,
        )
        actual = calculate_usage_cost(
            self.cost.pricing_policy,
            model_name=result.model,
            input_tokens=result.input_tokens,
            cached_input_tokens=result.cached_input_tokens,
            cache_write_tokens=result.cache_write_tokens,
            output_tokens=result.output_tokens,
        )
        self.cost.record_actual_cost(actual)
        self.run_store.write_evidence_once_json(
            f"cost/{turn_id}-actual.json",
            {
                "stage": stage.value,
                "actual": actual.to_dict(),
                "cumulative_calculated_cost_usd": decimal_text(
                    self.cost.spent_cost_usd
                ),
            },
        )
        return result
