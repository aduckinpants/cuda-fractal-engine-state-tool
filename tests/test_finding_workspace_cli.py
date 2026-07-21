from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from cuda_fractal_state_tool.finding_workspace_cli import main


def _write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


class FindingWorkspaceCliTests(unittest.TestCase):
    def test_import_command_emits_expected_json(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            workspace_root = root / "workspace"
            capture_root = root / "capture"
            _write_json(capture_root / "state.json", {"state_version": 3, "params": {"max_iter": 500}})

            out = io.StringIO()
            with redirect_stdout(out):
                exit_code = main(
                    [
                        "import",
                        "--workspace-root",
                        str(workspace_root),
                        "--source",
                        str(capture_root),
                    ]
                )

            self.assertEqual(exit_code, 0)
            payload = json.loads(out.getvalue())
            self.assertEqual(payload["command"], "import")
            self.assertTrue(payload["finding_id"])
            self.assertTrue(Path(payload["workspace_manifest_path"]).exists())

    def test_rebuild_index_command_emits_expected_json(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            workspace_root = root / "workspace"
            capture_root = root / "capture"
            _write_json(capture_root / "state.json", {"state_version": 3, "params": {"max_iter": 500}})

            with redirect_stdout(io.StringIO()):
                main(
                    [
                        "import",
                        "--workspace-root",
                        str(workspace_root),
                        "--source",
                        str(capture_root),
                    ]
                )

            out = io.StringIO()
            with redirect_stdout(out):
                exit_code = main(["rebuild-index", "--workspace-root", str(workspace_root)])

            self.assertEqual(exit_code, 0)
            payload = json.loads(out.getvalue())
            self.assertEqual(payload["command"], "rebuild-index")
            self.assertTrue(Path(payload["findings_index_path"]).exists())


if __name__ == "__main__":
    unittest.main()
