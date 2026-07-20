from __future__ import annotations

import unittest

from cuda_fractal_state_tool.json_utils import DuplicateKeyError
from cuda_fractal_state_tool.proposal import parse_proposal_v1


BASE = '{"proposal_version": 1, "base_state": {"id": "runtime-default-v1", "sha256": "hash"}, "overrides": {}}'


class ProposalTests(unittest.TestCase):
    def test_duplicate_keys_are_rejected(self) -> None:
        with self.assertRaises(DuplicateKeyError):
            parse_proposal_v1('{"proposal_version": 1, "proposal_version": 1, "base_state": {"id": "runtime-default-v1", "sha256": "hash"}, "overrides": {}}', "runtime-default-v1", "hash")

    def test_unknown_envelope_field_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            parse_proposal_v1('{"proposal_version": 1, "base_state": {"id": "runtime-default-v1", "sha256": "hash"}, "overrides": {}, "extra": 1}', "runtime-default-v1", "hash")

    def test_baseline_hash_mismatch_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            parse_proposal_v1(BASE, "runtime-default-v1", "other")

    def test_null_override_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            parse_proposal_v1('{"proposal_version": 1, "base_state": {"id": "runtime-default-v1", "sha256": "hash"}, "overrides": {"params.max_iter": null}}', "runtime-default-v1", "hash")

    def test_unsupported_override_path_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            parse_proposal_v1('{"proposal_version": 1, "base_state": {"id": "runtime-default-v1", "sha256": "hash"}, "overrides": {"view.center_x": 1}}', "runtime-default-v1", "hash")

    def test_color_triplet_override_is_accepted(self) -> None:
        proposal = parse_proposal_v1(
            '{"proposal_version": 1, "base_state": {"id": "runtime-default-v1", "sha256": "hash"}, '
            '"overrides": {"params.color_signal": "iteration_count", "params.color_palette": "cyclic_escape", "params.color_grading": "escape_default"}}',
            "runtime-default-v1",
            "hash",
        )
        self.assertEqual(proposal.overrides["params.color_grading"], "escape_default")

    def test_newly_proven_color_triplet_is_accepted(self) -> None:
        proposal = parse_proposal_v1(
            '{"proposal_version": 1, "base_state": {"id": "runtime-default-v1", "sha256": "hash"}, '
            '"overrides": {"params.color_signal": "root_phase", "params.color_palette": "phase_wheel", "params.color_grading": "phase_default"}}',
            "runtime-default-v1",
            "hash",
        )
        self.assertEqual(proposal.overrides["params.color_signal"], "root_phase")

    def test_non_allowlisted_color_triplet_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            parse_proposal_v1(
                '{"proposal_version": 1, "base_state": {"id": "runtime-default-v1", "sha256": "hash"}, '
                '"overrides": {"params.color_signal": "root_phase", "params.color_palette": "cyclic_escape", "params.color_grading": "escape_default"}}',
                "runtime-default-v1",
                "hash",
            )

    def test_expanded_grading_triplet_is_accepted(self) -> None:
        proposal = parse_proposal_v1(
            '{"proposal_version": 1, "base_state": {"id": "runtime-default-v1", "sha256": "hash"}, '
            '"overrides": {"params.color_signal": "iteration_count", "params.color_palette": "cyclic_escape", "params.color_grading": "tone_map_default"}}',
            "runtime-default-v1",
            "hash",
        )
        self.assertEqual(proposal.overrides["params.color_grading"], "tone_map_default")

    def test_phase_wheel_tone_map_combo_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            parse_proposal_v1(
                '{"proposal_version": 1, "base_state": {"id": "runtime-default-v1", "sha256": "hash"}, '
                '"overrides": {"params.color_signal": "phase_angle", "params.color_palette": "phase_wheel", "params.color_grading": "tone_map_default"}}',
                "runtime-default-v1",
                "hash",
            )

    def test_partial_color_triplet_override_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            parse_proposal_v1(
                '{"proposal_version": 1, "base_state": {"id": "runtime-default-v1", "sha256": "hash"}, "overrides": {"params.color_grading": "basin_default"}}',
                "runtime-default-v1",
                "hash",
            )

    def test_parent_child_overlap_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            parse_proposal_v1('{"proposal_version": 1, "base_state": {"id": "runtime-default-v1", "sha256": "hash"}, "overrides": {"params": 1, "params.max_iter": 2}}', "runtime-default-v1", "hash")


if __name__ == "__main__":
    unittest.main()
