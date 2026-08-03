from __future__ import annotations

from decimal import Decimal
import unittest

from cuda_fractal_state_tool.automated_protocol import (
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


class AutomatedProtocolTests(unittest.TestCase):
    def setUp(self) -> None:
        self.base = PacketAuthorityBinding(
            packet_id="packet-base",
            manifest_sha256="a" * 64,
            finding_id="finding-base",
        )
        self.derived = PacketAuthorityBinding(
            packet_id="packet-derived",
            manifest_sha256="b" * 64,
            finding_id="finding-derived",
        )

    def test_exact_model_gate_vocabulary_is_closed(self) -> None:
        for proposal in ModelGateProposal:
            self.assertEqual(parse_model_gate_proposal(proposal.value), proposal)
        with self.assertRaisesRegex(ValueError, "Unsupported model gate proposal"):
            parse_model_gate_proposal("BUDGET_EXHAUSTED")

        self.assertIn(ControllerDisposition.BUDGET_EXHAUSTED, ControllerDisposition)

    def test_round_advance_rebinds_and_round_revise_retains_base(self) -> None:
        self.assertEqual(
            resolve_round_authority(
                ModelGateProposal.ROUND_ADVANCE,
                preceding=self.base,
                derived=self.derived,
            ),
            self.derived,
        )
        self.assertEqual(
            resolve_round_authority(
                ModelGateProposal.ROUND_REVISE,
                preceding=self.base,
                derived=self.derived,
            ),
            self.base,
        )
        with self.assertRaisesRegex(ValueError, "derived packet"):
            resolve_round_authority(
                ModelGateProposal.ROUND_ADVANCE,
                preceding=self.base,
                derived=None,
            )

    def test_no_op_is_valid_replay_but_unintended_experiment_result(self) -> None:
        self.assertEqual(
            classify_override_effect(
                changed_path_count=0,
                empty_override_byte_exact=True,
                explicit_unchanged_requested=False,
            ),
            "UNINTENDED_NO_EFFECT",
        )
        self.assertEqual(
            classify_override_effect(
                changed_path_count=0,
                empty_override_byte_exact=True,
                explicit_unchanged_requested=True,
            ),
            "EXACT_BASE_REPLAY",
        )
        self.assertEqual(
            classify_override_effect(
                changed_path_count=1,
                empty_override_byte_exact=False,
                explicit_unchanged_requested=False,
            ),
            "AUTHORIZED_CHANGE",
        )

    def test_transition_graph_allows_one_correction_and_next_round(self) -> None:
        validate_protocol_transition(ProtocolState.OBSERVE, ProtocolState.EXPLORE)
        validate_protocol_transition(
            ProtocolState.VALIDATE_OVERRIDE, ProtocolState.REQUEST_OVERRIDE
        )
        validate_protocol_transition(ProtocolState.GATE_DECISION, ProtocolState.OBSERVE)
        with self.assertRaisesRegex(ValueError, "Illegal protocol transition"):
            validate_protocol_transition(ProtocolState.OBSERVE, ProtocolState.PROVE_CANDIDATE)

    def test_budget_policy_uses_locked_defaults_and_projected_usage(self) -> None:
        budgets = SessionBudgets()
        self.assertEqual(budgets.maximum_proven_rounds, 2)
        self.assertEqual(budgets.maximum_model_responses, 6)
        self.assertEqual(budgets.maximum_cumulative_input_tokens, 2_000_000)
        self.assertEqual(budgets.maximum_cumulative_output_tokens, 48_000)
        self.assertEqual(budgets.maximum_input_tokens_per_response, 200_000)
        self.assertEqual(budgets.maximum_output_tokens_per_response, 8_000)
        self.assertEqual(budgets.maximum_review_output_tokens_per_response, 4_000)
        self.assertEqual(budgets.maximum_correction_output_tokens_per_response, 4_000)
        self.assertEqual(budgets.maximum_calculated_cost_usd, Decimal("10.00"))
        self.assertIsNone(
            budget_exhaustion_reason(
                budgets,
                BudgetUsage(model_responses=1, cumulative_input_tokens=100),
                next_input_tokens=100,
                next_output_tokens=1_000,
            )
        )
        self.assertEqual(
            budget_exhaustion_reason(
                budgets,
                BudgetUsage(proven_rounds=2),
            ),
            "maximum_proven_rounds",
        )
        self.assertEqual(
            budget_exhaustion_reason(
                budgets,
                BudgetUsage(),
                next_input_tokens=200_001,
            ),
            "maximum_input_tokens_per_response",
        )
        self.assertEqual(
            budget_exhaustion_reason(
                budgets,
                BudgetUsage(),
                next_output_tokens=8_001,
            ),
            "maximum_output_tokens_per_response",
        )
        encoded = budgets.to_dict()
        self.assertEqual(encoded["maximum_review_output_tokens_per_response"], 4_000)
        self.assertEqual(encoded["maximum_correction_output_tokens_per_response"], 4_000)
        self.assertEqual(
            budget_exhaustion_reason(
                budgets,
                BudgetUsage(cumulative_calculated_cost_usd=Decimal("9.75")),
                next_calculated_cost_usd=Decimal("0.26"),
            ),
            "maximum_calculated_cost_usd",
        )


if __name__ == "__main__":
    unittest.main()
