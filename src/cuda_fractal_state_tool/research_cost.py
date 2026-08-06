from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum

from .model_profile import ModelProfileV1
from .pricing_policy import CallCost, PricingPolicy, estimate_maximum_call_cost


class ResearchProviderStage(str, Enum):
    PLANNER = "planner"
    REVIEW = "review"
    CORRECTION = "correction"
    SYNTHESIS = "synthesis"
    COMMUNICATION = "communication"


@dataclass(frozen=True)
class ResearchStageLimit:
    maximum_input_tokens: int
    maximum_output_tokens: int


DEFAULT_RESEARCH_STAGE_LIMITS = {
    ResearchProviderStage.PLANNER: ResearchStageLimit(200_000, 8_000),
    ResearchProviderStage.REVIEW: ResearchStageLimit(200_000, 8_000),
    ResearchProviderStage.CORRECTION: ResearchStageLimit(200_000, 4_000),
    ResearchProviderStage.SYNTHESIS: ResearchStageLimit(100_000, 8_000),
    ResearchProviderStage.COMMUNICATION: ResearchStageLimit(50_000, 6_000),
}


@dataclass(frozen=True)
class ResearchDispatchBudgetDecision:
    stage: ResearchProviderStage
    exact_input_tokens: int
    current_call: CallCost
    reserved_stages: tuple[ResearchProviderStage, ...]
    reserved_cost_usd: Decimal
    spent_cost_usd: Decimal
    hard_budget_usd: Decimal
    authorized: bool
    rejection_reason: str | None

    @property
    def required_available_cost_usd(self) -> Decimal:
        return self.current_call.cost_usd + self.reserved_cost_usd


class ResearchCostController:
    """Pure local dollar gate over exact next-call counts and stage reserves."""

    def __init__(
        self,
        *,
        pricing_policy: PricingPolicy,
        model_profile: ModelProfileV1,
        hard_budget_usd: Decimal,
        stage_limits: dict[ResearchProviderStage, ResearchStageLimit] | None = None,
    ) -> None:
        model_profile.validate(pricing_policy)
        if not hard_budget_usd.is_finite() or hard_budget_usd < 0:
            raise ValueError("Research hard dollar budget must be finite and non-negative")
        self.pricing_policy = pricing_policy
        self.model_profile = model_profile
        self.hard_budget_usd = hard_budget_usd
        self.stage_limits = dict(stage_limits or DEFAULT_RESEARCH_STAGE_LIMITS)
        if set(self.stage_limits) != set(ResearchProviderStage):
            raise ValueError("Research stage limits must cover every provider stage exactly")
        for stage, limit in self.stage_limits.items():
            if limit.maximum_input_tokens < 1 or limit.maximum_output_tokens < 1:
                raise ValueError(f"Research stage limit is invalid: {stage.value}")
        self.spent_cost_usd = Decimal("0")

    def _maximum(self, stage: ResearchProviderStage) -> CallCost:
        limit = self.stage_limits[stage]
        return estimate_maximum_call_cost(
            self.pricing_policy,
            model_name=self.model_profile.model,
            maximum_input_tokens=limit.maximum_input_tokens,
            maximum_output_tokens=limit.maximum_output_tokens,
            prompt_cache_policy=self.model_profile.prompt_cache_policy.value,
        )

    def exact_next_call(
        self,
        stage: ResearchProviderStage,
        *,
        exact_input_tokens: int,
    ) -> CallCost:
        stage = ResearchProviderStage(stage)
        limit = self.stage_limits[stage]
        if exact_input_tokens < 0 or exact_input_tokens > limit.maximum_input_tokens:
            raise ValueError(
                f"Exact {stage.value} input count exceeds the stage ceiling: "
                f"{exact_input_tokens} > {limit.maximum_input_tokens}"
            )
        return estimate_maximum_call_cost(
            self.pricing_policy,
            model_name=self.model_profile.model,
            maximum_input_tokens=exact_input_tokens,
            maximum_output_tokens=limit.maximum_output_tokens,
            prompt_cache_policy=self.model_profile.prompt_cache_policy.value,
        )

    def conservative_adaptive_ceiling(
        self,
        *,
        experiment_attempts_remaining: int,
        correction_available: bool,
        alternate_communication_required: bool,
    ) -> Decimal:
        if experiment_attempts_remaining < 0 or experiment_attempts_remaining > 2:
            raise ValueError("Experiment attempts remaining must be from zero through two")
        stages = [
            ResearchProviderStage.PLANNER,
            ResearchProviderStage.REVIEW,
        ] * experiment_attempts_remaining
        if correction_available:
            stages.append(ResearchProviderStage.CORRECTION)
        stages.append(ResearchProviderStage.SYNTHESIS)
        if alternate_communication_required:
            stages.append(ResearchProviderStage.COMMUNICATION)
        return sum((self._maximum(stage).cost_usd for stage in stages), Decimal("0"))

    def authorize_dispatch(
        self,
        stage: ResearchProviderStage,
        *,
        exact_input_tokens: int,
        planner_may_execute: bool = False,
        correction_available: bool = False,
        alternate_communication_required: bool = False,
    ) -> ResearchDispatchBudgetDecision:
        stage = ResearchProviderStage(stage)
        current = self.exact_next_call(stage, exact_input_tokens=exact_input_tokens)
        reserves: list[ResearchProviderStage] = []
        if stage in {ResearchProviderStage.PLANNER, ResearchProviderStage.CORRECTION}:
            if planner_may_execute:
                reserves.append(ResearchProviderStage.REVIEW)
            reserves.append(ResearchProviderStage.SYNTHESIS)
            if correction_available and stage is ResearchProviderStage.PLANNER:
                reserves.append(ResearchProviderStage.CORRECTION)
        elif stage is ResearchProviderStage.REVIEW:
            reserves.append(ResearchProviderStage.SYNTHESIS)
        elif stage is ResearchProviderStage.SYNTHESIS:
            pass
        elif stage is not ResearchProviderStage.COMMUNICATION:
            raise ValueError(f"Unsupported research provider stage: {stage}")
        if (
            alternate_communication_required
            and stage is not ResearchProviderStage.COMMUNICATION
        ):
            reserves.append(ResearchProviderStage.COMMUNICATION)
        reserve_cost = sum(
            (self._maximum(reserved).cost_usd for reserved in reserves), Decimal("0")
        )
        available = self.hard_budget_usd - self.spent_cost_usd
        required = current.cost_usd + reserve_cost
        authorized = required <= available
        reason = None
        if not authorized:
            reason = (
                "hard dollar budget cannot cover exact next dispatch plus mandatory "
                f"reserves: required {required}, available {available}"
            )
        return ResearchDispatchBudgetDecision(
            stage=stage,
            exact_input_tokens=exact_input_tokens,
            current_call=current,
            reserved_stages=tuple(reserves),
            reserved_cost_usd=reserve_cost,
            spent_cost_usd=self.spent_cost_usd,
            hard_budget_usd=self.hard_budget_usd,
            authorized=authorized,
            rejection_reason=reason,
        )

    def record_actual_cost(self, call_cost: CallCost) -> None:
        new_total = self.spent_cost_usd + call_cost.cost_usd
        if new_total > self.hard_budget_usd:
            raise RuntimeError("Provider usage exceeded the sealed research hard dollar budget")
        self.spent_cost_usd = new_total
