from __future__ import annotations

import json
import unittest
from pathlib import Path

from cuda_fractal_state_tool.research_protocol import (
    ResearchAction,
    ResearchBrief,
    UnresolvedReason,
    parse_planner_response,
)
from cuda_fractal_state_tool.scalar_sweep import parse_scalar_sweep_plan


FIXTURE_ROOT = (
    Path(__file__).resolve().parents[1]
    / "docs"
    / "manual-test-results"
    / "question-research-golden"
)


class QuestionResearchQualificationTests(unittest.TestCase):
    def test_checked_in_golden_brief_is_zero_budget_and_epsilon_only(self) -> None:
        value = json.loads((FIXTURE_ROOT / "epsilon-research-brief.json").read_text(encoding="utf-8"))
        brief = ResearchBrief.from_dict(value)
        self.assertEqual(str(brief.hard_dollar_budget), "0.00")
        self.assertEqual(brief.maximum_experiment_rounds, 2)
        self.assertEqual(brief.experiment_permissions.domains, ("params",))
        self.assertEqual(brief.experiment_permissions.allowed_paths, ("params.epsilon",))
        self.assertTrue(brief.experiment_permissions.allow_scalar_sweep)
        self.assertTrue(brief.experiment_permissions.authorizes_path("params.epsilon"))
        self.assertFalse(brief.experiment_permissions.authorizes_path("params.damping"))
        self.assertFalse(brief.experiment_permissions.authorizes_path("view.zoom"))

    def test_checked_in_golden_sweep_is_one_bounded_epsilon_round(self) -> None:
        plan = parse_scalar_sweep_plan(
            (FIXTURE_ROOT / "epsilon-sweep-plan.json").read_text(encoding="utf-8")
        )
        self.assertEqual(plan.axis_path, "params.epsilon")
        self.assertEqual(plan.values, (5e-7, 7.5e-7, 1.25e-6, 1.5e-6, 2e-6))
        self.assertEqual(plan.member_failure_policy, "continue_independent")

    def test_all_unresolved_taxonomy_values_have_one_parseable_terminal_shape(self) -> None:
        for reason in UnresolvedReason:
            with self.subTest(reason=reason.value):
                decision = parse_planner_response(
                    f"""RESEARCH_ACTION: UNRESOLVED_REPORT

Unresolved reason: {reason.value}
What is missing: Exact evidence needed to answer the sealed question.
Why current authority cannot answer: The bounded Packet and controller do not establish it.
Best next step: Resolve the stated boundary under a separately authorized plan.
Hostile self-review conclusion: No executable claim is being fabricated.
"""
                )
                self.assertEqual(decision.action, ResearchAction.UNRESOLVED_REPORT)
                self.assertEqual(decision.unresolved_reason, reason)


if __name__ == "__main__":
    unittest.main()
