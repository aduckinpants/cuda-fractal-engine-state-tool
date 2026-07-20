from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from cuda_fractal_state_tool.materializer import materialize_transport_candidate
from cuda_fractal_state_tool.proposal import parse_proposal_v1


BASELINE = '''{
  "state_version": 3,
  "fractal_type": "explaino_all",
  "view": {},
  "params": {
    "max_iter": 500,
    "color_shape": "identity",
    "color_grading": "basin_default",
    "unknown_field": 123
  },
  "render": {}
}
'''


class MaterializerTests(unittest.TestCase):
    def test_noop_materialization_preserves_exact_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            baseline_path = root / "state.json"
            baseline_path.write_text(BASELINE, encoding="utf-8")
            proposal = parse_proposal_v1('{"proposal_version": 1, "base_state": {"id": "runtime-default-v1", "sha256": "hash"}, "overrides": {}}', "runtime-default-v1", "hash")
            output_path = root / "candidate.json"
            result = materialize_transport_candidate(baseline_path, proposal, output_path)
            self.assertTrue(result.byte_identical_to_baseline)
            self.assertEqual(output_path.read_text(encoding="utf-8"), BASELINE)

    def test_non_empty_materialization_replaces_allowed_path_and_preserves_unknowns(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            baseline_path = root / "state.json"
            baseline_path.write_text(BASELINE, encoding="utf-8")
            proposal = parse_proposal_v1('{"proposal_version": 1, "base_state": {"id": "runtime-default-v1", "sha256": "hash"}, "overrides": {"params.max_iter": 700, "params.color_shape": "repeat"}}', "runtime-default-v1", "hash")
            output_path = root / "candidate.json"
            result = materialize_transport_candidate(baseline_path, proposal, output_path)
            self.assertFalse(result.byte_identical_to_baseline)
            text = output_path.read_text(encoding="utf-8")
            self.assertIn('"max_iter": 700', text)
            self.assertIn('"color_shape": "repeat"', text)
            self.assertIn('"unknown_field": 123', text)

    def test_color_grading_materialization_replaces_scalar_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            baseline_path = root / "state.json"
            baseline_path.write_text(BASELINE, encoding="utf-8")
            proposal = parse_proposal_v1('{"proposal_version": 1, "base_state": {"id": "runtime-default-v1", "sha256": "hash"}, "overrides": {"params.color_grading": "basin_default"}}', "runtime-default-v1", "hash")
            output_path = root / "candidate.json"
            result = materialize_transport_candidate(baseline_path, proposal, output_path)
            self.assertFalse(result.byte_identical_to_baseline)
            self.assertIn('"color_grading": "basin_default"', output_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
