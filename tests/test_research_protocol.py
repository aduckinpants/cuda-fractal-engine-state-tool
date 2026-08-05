from __future__ import annotations

import unittest
from decimal import Decimal

from cuda_fractal_state_tool.research_protocol import (
    ExperimentPermissions,
    ResearchAction,
    ResearchBrief,
    UnresolvedReason,
    authorize_scalar_sweep,
    authorize_single_override,
    parse_planner_response,
    parse_review_response,
    round_plan_document,
)


def _brief(**changes):
    value = {
        "question": "Why does the circle change?",
        "attention_context": "Study the central termination circle.",
        "user_hypotheses": ["Its radius depends on epsilon."],
        "experiment_permissions": {
            "domains": ["params"],
            "allowed_paths": ["params.epsilon"],
            "allow_scalar_sweep": True,
        },
        "fixed_conditions": {"notes": ["Keep camera and Color Pipeline fixed."]},
        "useful_answer": {"kind": "bounded_relationship", "details": "Return a bracket."},
        "maximum_experiment_rounds": 2,
        "communication_profile": "working_session",
        "hard_dollar_budget": "0",
    }
    value.update(changes)
    return value


def _override_response(payload: str = '{"params":{"epsilon":0.000002}}') -> str:
    return f"""RESEARCH_ACTION: SINGLE_OVERRIDE

Chosen experiment: Raise epsilon once.
Why this experiment: It tests the radius claim.
Locked prediction: The central circle grows.
Observation channel: Phase Orbit [phase_orbit] -> Phase Wheel [phase_wheel_palette].
Disconfirmation condition: The circle does not change.
Camera and fixed-state policy: Preserve the exact camera and all non-epsilon state.
Hostile self-review conclusion: One authorized observable leaf is changed.

```json
{payload}
```
"""


def _sweep_response(path: str = "params.epsilon") -> str:
    return f"""RESEARCH_ACTION: SCALAR_SWEEP

Selected bracket: Five epsilon values around the base.
Why this bracket: It tests an ordered radius trend.
Locked trend prediction: Radius increases with epsilon.
Observation channel: Phase Orbit [phase_orbit] -> Phase Wheel [phase_wheel_palette].
Disconfirmation condition: Radius is unordered or unchanged.
Fixed-state and camera policy: Every member retains the exact base except epsilon.
Hostile self-review conclusion: The axis is authorized and the members are independent.

```json
{{"sweep_version":1,"axis":{{"path":"{path}","values":[0.0000005,0.00000075,0.00000125] }},"member_failure_policy":"continue_independent"}}
```
"""


class ResearchProtocolTests(unittest.TestCase):
    def test_brief_locks_exact_permissions_and_budget(self) -> None:
        brief = ResearchBrief.from_dict(_brief())

        self.assertEqual(brief.maximum_experiment_rounds, 2)
        self.assertEqual(brief.hard_dollar_budget, Decimal("0"))
        self.assertTrue(brief.experiment_permissions.authorizes_path("params.epsilon"))
        self.assertFalse(brief.experiment_permissions.authorizes_path("params.explaino_damping"))
        self.assertEqual(brief.to_dict()["hard_dollar_budget"], "0")

    def test_brief_rejects_path_outside_domain_and_invalid_rounds(self) -> None:
        bad_permissions = _brief(
            experiment_permissions={
                "domains": ["view"],
                "allowed_paths": ["params.epsilon"],
                "allow_scalar_sweep": True,
            }
        )
        with self.assertRaisesRegex(ValueError, "outside permitted domains"):
            ResearchBrief.from_dict(bad_permissions)
        with self.assertRaisesRegex(ValueError, "zero through two"):
            ResearchBrief.from_dict(_brief(maximum_experiment_rounds=3))

    def test_single_override_parses_locked_prediction_and_exact_payload(self) -> None:
        response = _override_response()
        decision = parse_planner_response(response)

        self.assertEqual(decision.action, ResearchAction.SINGLE_OVERRIDE)
        self.assertEqual(decision.fields["Locked prediction"], "The central circle grows.")
        self.assertIsNotNone(decision.payload_sha256)
        override = authorize_single_override(
            decision, ResearchBrief.from_dict(_brief()).experiment_permissions
        )
        self.assertEqual(override.document, {"params": {"epsilon": 0.000002}})
        plan = round_plan_document(decision, attempt_number=1)
        self.assertEqual(plan["prediction"], "The central circle grows.")
        self.assertEqual(plan["payload_sha256"], decision.payload_sha256)

    def test_single_override_rejects_noop_and_unpermitted_path(self) -> None:
        permissions = ResearchBrief.from_dict(_brief()).experiment_permissions
        with self.assertRaisesRegex(ValueError, "UNINTENDED_NO_EFFECT"):
            authorize_single_override(parse_planner_response(_override_response("{}")), permissions)
        with self.assertRaisesRegex(ValueError, "outside research permission"):
            authorize_single_override(
                parse_planner_response(
                    _override_response('{"params":{"explaino_damping":1.5}}')
                ),
                permissions,
            )

    def test_scalar_sweep_requires_permission_and_exact_axis(self) -> None:
        decision = parse_planner_response(_sweep_response())
        permissions = ResearchBrief.from_dict(_brief()).experiment_permissions
        plan = authorize_scalar_sweep(decision, permissions)
        self.assertEqual(plan.axis_path, "params.epsilon")

        denied = ExperimentPermissions(("params",), ("params.epsilon",), False)
        with self.assertRaisesRegex(ValueError, "does not permit"):
            authorize_scalar_sweep(decision, denied)
        with self.assertRaisesRegex(ValueError, "outside research permission"):
            authorize_scalar_sweep(parse_planner_response(_sweep_response("params.max_iter")), permissions)

    def test_answer_ready_is_provisional_and_has_no_payload(self) -> None:
        decision = parse_planner_response(
            """RESEARCH_ACTION: ANSWER_READY

Proposed answer: The packet already answers the narrow question.
Evidence basis: The captured state and engine description.
Uncertainty: No new causal comparison exists.
Hostile self-review conclusion: This is a provisional answer, not new evidence.
"""
        )
        self.assertEqual(decision.action, ResearchAction.ANSWER_READY)
        self.assertIsNone(decision.payload_text)

    def test_unresolved_report_uses_locked_taxonomy(self) -> None:
        decision = parse_planner_response(
            """RESEARCH_ACTION: UNRESOLVED_REPORT

Unresolved reason: CAPABILITY_UNAVAILABLE
What is missing: A spatial diagnostic.
Why current authority cannot answer: The packet has no such observation channel.
Best next step: Add the diagnostic under a separate plan.
Hostile self-review conclusion: No authorized state change can answer this question.
"""
        )
        self.assertEqual(decision.unresolved_reason, UnresolvedReason.CAPABILITY_UNAVAILABLE)

    def test_parser_rejects_missing_locked_field_or_extra_code_block(self) -> None:
        with self.assertRaisesRegex(ValueError, "Disconfirmation condition"):
            parse_planner_response(
                _override_response().replace("Disconfirmation condition:", "Different label:")
            )
        with self.assertRaisesRegex(ValueError, "exactly one fenced"):
            parse_planner_response(_override_response() + "\n```json\n{}\n```\n")

    def test_review_requires_exact_promotion_identity(self) -> None:
        decision = parse_review_response(
            """RESEARCH_GATE: CONTINUE_PROMOTE_RESULT

Prediction outcome: The radius increased as predicted.
Evidence assessment: Member two is replay-proven and informative.
Selected result: sweep:sweep-1:2
Next research step: Rebind to the selected member.
Hostile self-review conclusion: The exact member identity is explicit.
"""
        )
        self.assertEqual(decision.gate.value, "CONTINUE_PROMOTE_RESULT")
        self.assertEqual(decision.selected_result.sweep_id, "sweep-1")
        self.assertEqual(decision.selected_result.member_index, 2)

        with self.assertRaisesRegex(ValueError, "requires one exact"):
            parse_review_response(
                """RESEARCH_GATE: CONTINUE_PROMOTE_RESULT

Prediction outcome: Unknown.
Evidence assessment: Incomplete.
Selected result: none
Next research step: Continue.
Hostile self-review conclusion: No exact result was selected.
"""
            )

    def test_nonpromotion_review_rejects_result_nomination(self) -> None:
        with self.assertRaisesRegex(ValueError, "must use Selected result: none"):
            parse_review_response(
                """RESEARCH_GATE: COMPLETE_RESEARCH

Prediction outcome: Supported.
Evidence assessment: Complete.
Selected result: single:proof-1
Next research step: none
Hostile self-review conclusion: Complete.
"""
            )


if __name__ == "__main__":
    unittest.main()
