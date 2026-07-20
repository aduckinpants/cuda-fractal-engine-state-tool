from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from cuda_fractal_state_tool.json_utils import dumps_pretty
from cuda_fractal_state_tool.proposal_cli import main
from cuda_fractal_state_tool.runtime_surface import sha256_file


class ProposalCliTests(unittest.TestCase):
    def _make_baseline_manifest(self, root: Path) -> Path:
        baseline_dir = root / "baselines" / "runtime-default-v1"
        baseline_dir.mkdir(parents=True, exist_ok=True)
        state_path = baseline_dir / "state.json"
        state_path.write_text(
            '{"state_version": 3, "fractal_type": "explaino_all", "view": {}, "params": {"max_iter": 500, "color_shape": "identity", "color_signal": "root_index", "color_palette": "joy", "color_grading": "basin_default"}, "render": {}}\n',
            encoding="utf-8",
        )
        manifest_path = baseline_dir / "manifest.json"
        manifest_path.write_text(
            dumps_pretty(
                {
                    "baseline_id": "runtime-default-v1",
                    "state_sha256": sha256_file(state_path),
                    "runtime_identity": {"launcher_sha256": "abc"},
                    "replay_proven": True,
                }
            ),
            encoding="utf-8",
        )
        return manifest_path

    def test_noop_example_prints_valid_json(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            manifest_path = self._make_baseline_manifest(root)
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                exit_code = main(["--example", "noop", "--baseline-manifest", str(manifest_path)])
            self.assertEqual(exit_code, 0)
            payload = json.loads(stdout.getvalue())
            self.assertEqual(payload["proposal_version"], 1)
            self.assertEqual(payload["overrides"], {})

    def test_max_iter_example_uses_override_value(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            manifest_path = self._make_baseline_manifest(root)
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                exit_code = main(["--example", "max-iter", "--max-iter", "900", "--baseline-manifest", str(manifest_path)])
            self.assertEqual(exit_code, 0)
            payload = json.loads(stdout.getvalue())
            self.assertEqual(payload["overrides"]["params.max_iter"], 900)

    def test_triplet_example_can_write_to_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            manifest_path = self._make_baseline_manifest(root)
            out_path = root / "proposal.json"
            exit_code = main(
                [
                    "--example",
                    "color-triplet",
                    "--signal",
                    "root_proximity",
                    "--palette",
                    "cyclic_escape",
                    "--grading",
                    "tone_map_default",
                    "--baseline-manifest",
                    str(manifest_path),
                    "--out",
                    str(out_path),
                ]
            )
            self.assertEqual(exit_code, 0)
            payload = json.loads(out_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["overrides"]["params.color_signal"], "root_proximity")
            self.assertEqual(payload["overrides"]["params.color_palette"], "cyclic_escape")
            self.assertEqual(payload["overrides"]["params.color_grading"], "tone_map_default")

    def test_list_color_triplets_mode_prints_catalog(self) -> None:
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            exit_code = main(["--list-color-triplets"])
        self.assertEqual(exit_code, 0)
        payload = json.loads(stdout.getvalue())
        self.assertIn("count", payload)
        self.assertIn("triplets", payload)
        self.assertGreater(payload["count"], 0)
        self.assertIsInstance(payload["triplets"], list)

    def test_color_pipeline_draft_example_can_write_to_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            manifest_path = self._make_baseline_manifest(root)
            out_path = root / "proposal_draft.json"
            exit_code = main(
                [
                    "--example",
                    "color-pipeline-draft",
                    "--draft-lane",
                    "shape",
                    "--draft-function",
                    "identity",
                    "--baseline-manifest",
                    str(manifest_path),
                    "--out",
                    str(out_path),
                ]
            )
            self.assertEqual(exit_code, 0)
            payload = json.loads(out_path.read_text(encoding="utf-8"))
            lanes = payload["overrides"]["color_pipeline_draft"]["lanes"]
            self.assertEqual(len(lanes), 1)
            self.assertEqual(lanes[0]["lane_id"], "shape")
            self.assertEqual(lanes[0]["function_id"], "identity")


if __name__ == "__main__":
    unittest.main()
