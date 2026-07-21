from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from cuda_fractal_state_tool.lane_catalog_cli import main


class LaneCatalogCliTests(unittest.TestCase):
    def _write_contract(self, root: Path) -> Path:
        path = root / "contract.json"
        path.write_text(
            json.dumps(
                {
                    "function_library": {
                        "lanes": [
                            {
                                "id": "shape",
                                "default": "identity",
                                "functions": [{"id": "identity"}, {"id": "repeat"}],
                            }
                        ]
                    }
                }
            ),
            encoding="utf-8",
        )
        return path

    def test_cli_prints_and_validates_compiled_contract(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            contract = self._write_contract(Path(temp_dir))
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                exit_code = main(
                    [
                        "--ui-salt-contract",
                        str(contract),
                        "--check-lane",
                        "shape",
                        "--check-function",
                        "repeat",
                    ]
                )
            self.assertEqual(exit_code, 0)
            payload = json.loads(stdout.getvalue())
            self.assertEqual(payload["shape"], "ui_salt_function_library_v1")
            self.assertEqual(payload["lanes"]["shape"], ["identity", "repeat"])

    def test_cli_rejects_unsupported_shape_and_partial_check(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            bad = root / "bad.json"
            bad.write_text('{"functions": []}', encoding="utf-8")
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                self.assertEqual(main(["--ui-salt-contract", str(bad)]), 2)
            self.assertEqual(json.loads(stdout.getvalue())["status"], "runtime_metadata_shape_unsupported")

            contract = self._write_contract(root)
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                self.assertEqual(
                    main(["--ui-salt-contract", str(contract), "--check-lane", "shape"]),
                    2,
                )
            self.assertEqual(json.loads(stdout.getvalue())["status"], "invalid_arguments")


if __name__ == "__main__":
    unittest.main()
