from __future__ import annotations

import unittest

from cuda_fractal_state_tool.research_question_ui import ResearchQuestionFormData


class ResearchQuestionFormTests(unittest.TestCase):
    def test_form_seals_five_answers_and_exact_path_permissions(self) -> None:
        brief = ResearchQuestionFormData(
            question="Why does the circle grow?",
            attention_context="Watch the termination boundary.",
            user_hypotheses_text="epsilon controls the radius\ncolor does not move geometry",
            fixed_conditions_text="keep camera fixed\nkeep damping fixed",
            useful_answer_details="A bounded relationship or honest unresolved report.",
            allow_params=True,
            allow_view=False,
            allow_color_pipeline=False,
            allowed_paths_text="params.epsilon",
            allow_scalar_sweep=True,
            maximum_experiment_rounds=2,
            communication_profile="working_session",
            hard_dollar_budget_text="0.50",
        ).to_brief()
        self.assertEqual(brief.experiment_permissions.allowed_paths, ("params.epsilon",))
        self.assertEqual(len(brief.user_hypotheses), 2)
        self.assertEqual(len(brief.fixed_condition_notes), 2)

    def test_empty_allowed_paths_means_all_packet_authorable_paths_in_domains(self) -> None:
        brief = ResearchQuestionFormData(
            question="What changes?",
            attention_context="Inspect the frame.",
            user_hypotheses_text="",
            fixed_conditions_text="",
            useful_answer_details="A concise result.",
            allow_params=True,
            allow_view=False,
            allow_color_pipeline=True,
            allowed_paths_text="",
            allow_scalar_sweep=False,
            maximum_experiment_rounds=0,
            communication_profile="working_session",
            hard_dollar_budget_text="0",
        ).to_brief()
        self.assertIsNone(brief.experiment_permissions.allowed_paths)
        self.assertEqual(brief.experiment_permissions.domains, ("params", "color_pipeline_draft"))


if __name__ == "__main__":
    unittest.main()
