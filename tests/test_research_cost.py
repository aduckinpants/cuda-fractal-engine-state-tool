from __future__ import annotations

import unittest
from decimal import Decimal

from cuda_fractal_state_tool.model_profile import ModelProfileV1
from cuda_fractal_state_tool.openai_transport import PromptCachePolicy
from cuda_fractal_state_tool.pricing_policy import load_pricing_policy
from cuda_fractal_state_tool.research_cost import (
    ResearchCostController,
    ResearchProviderStage,
)


class ResearchCostControllerTests(unittest.TestCase):
    def _controller(self, budget: str) -> ResearchCostController:
        policy = load_pricing_policy()
        profile = ModelProfileV1(
            model="gpt-5.6-luna",
            reasoning_effort="high",
            pricing_tier="standard",
            prompt_cache_policy=PromptCachePolicy.EXPLICIT_NO_CACHE,
        )
        return ResearchCostController(
            pricing_policy=policy,
            model_profile=profile,
            hard_budget_usd=Decimal(budget),
        )

    def test_zero_budget_rejects_before_dispatch(self) -> None:
        decision = self._controller("0").authorize_dispatch(
            ResearchProviderStage.PLANNER,
            exact_input_tokens=10_000,
            planner_may_execute=True,
            correction_available=True,
        )
        self.assertFalse(decision.authorized)
        self.assertEqual(
            decision.reserved_stages,
            (
                ResearchProviderStage.REVIEW,
                ResearchProviderStage.SYNTHESIS,
                ResearchProviderStage.CORRECTION,
            ),
        )

    def test_planner_reserves_review_synthesis_render_and_correction(self) -> None:
        decision = self._controller("10").authorize_dispatch(
            ResearchProviderStage.PLANNER,
            exact_input_tokens=150_000,
            planner_may_execute=True,
            correction_available=True,
            alternate_communication_required=True,
        )
        self.assertTrue(decision.authorized)
        self.assertEqual(
            decision.reserved_stages,
            (
                ResearchProviderStage.REVIEW,
                ResearchProviderStage.SYNTHESIS,
                ResearchProviderStage.CORRECTION,
                ResearchProviderStage.COMMUNICATION,
            ),
        )

    def test_answer_ready_path_releases_experiment_reserves(self) -> None:
        decision = self._controller("10").authorize_dispatch(
            ResearchProviderStage.SYNTHESIS,
            exact_input_tokens=30_000,
            alternate_communication_required=False,
        )
        self.assertEqual(decision.reserved_stages, ())

    def test_exact_count_must_fit_stage_input_ceiling(self) -> None:
        with self.assertRaisesRegex(ValueError, "exceeds the stage ceiling"):
            self._controller("10").authorize_dispatch(
                ResearchProviderStage.REVIEW,
                exact_input_tokens=200_001,
            )

    def test_adaptive_ceiling_is_not_described_as_exact_count(self) -> None:
        controller = self._controller("10")
        ceiling = controller.conservative_adaptive_ceiling(
            experiment_attempts_remaining=2,
            correction_available=True,
            alternate_communication_required=True,
        )
        first = controller.exact_next_call(
            ResearchProviderStage.PLANNER,
            exact_input_tokens=42_000,
        )
        self.assertGreater(ceiling, first.cost_usd)

    def test_live_proven_review_and_synthesis_output_ceilings_are_locked(self) -> None:
        controller = self._controller("10")
        self.assertEqual(
            controller.stage_limits[ResearchProviderStage.REVIEW].maximum_output_tokens,
            8_000,
        )
        self.assertEqual(
            controller.stage_limits[ResearchProviderStage.SYNTHESIS].maximum_output_tokens,
            12_000,
        )


if __name__ == "__main__":
    unittest.main()
