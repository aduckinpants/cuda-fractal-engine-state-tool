from __future__ import annotations

import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from cuda_fractal_state_tool.agent_handoff_cli import main
from cuda_fractal_state_tool.json_utils import dumps_pretty
from cuda_fractal_state_tool.runtime_surface import sha256_file


class AgentHandoffCliTests(unittest.TestCase):
    def _make_baseline(self, root: Path) -> Path:
        baseline_dir = root / "baselines" / "runtime-default-v1"
        baseline_dir.mkdir(parents=True, exist_ok=True)
        state_path = baseline_dir / "state.json"
        state_path.write_text(
            '{"state_version": 3, "fractal_type": "explaino_all", "view": {}, "params": {"max_iter": 500, "color_shape": "identity", "color_signal": "root_index", "color_palette": "joy", "color_grading": "basin_default"}, "render": {}}\n',
            encoding="utf-8",
        )
        manifest = baseline_dir / "manifest.json"
        manifest.write_text(
            dumps_pretty(
                {
                    "baseline_id": "runtime-default-v1",
                    "state_sha256": sha256_file(state_path),
                    "runtime_identity": {
                        "launcher_sha256": "abc",
                        "resolved_executable_sha256": "def",
                        "runtime_schema_sha256": "one",
                        "source_schema_sha256": "two",
                    },
                    "replay_proven": True,
                }
            ),
            encoding="utf-8",
        )
        return manifest

    def test_cli_emits_packet_and_writes_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            manifest = self._make_baseline(root)
            replay = root / "replay.json"
            replay.write_text(
                '{"state_version": 3, "fractal_type": "explaino_all", "view": {}, "params": {"max_iter": 500, "color_shape": "identity", "color_signal": "root_index", "color_palette": "joy", "color_grading": "basin_default"}, "render": {}, "color_pipeline_draft": {"lanes": []}}\n',
                encoding="utf-8",
            )
            out_path = root / "packet.md"

            stdout = io.StringIO()
            with redirect_stdout(stdout):
                exit_code = main(
                    [
                        "--repo-root",
                        str(root),
                        "--baseline-manifest",
                        str(manifest),
                        "--replay-state",
                        str(replay),
                        "--runtime-cmd",
                        str(root / "runtime" / "fractal_ui.cmd"),
                        "--out",
                        str(out_path),
                    ]
                )

            self.assertEqual(exit_code, 0)
            emitted = stdout.getvalue()
            self.assertIn("# Agent Handoff Packet", emitted)
            self.assertIn("state.json: full runtime state snapshot", emitted)
            self.assertIn("proposal.json (proposal_v1): sparse overrides", emitted)
            self.assertTrue(out_path.exists())


if __name__ == "__main__":
    unittest.main()
