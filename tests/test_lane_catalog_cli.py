from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from cuda_fractal_state_tool.lane_catalog_cli import main


class LaneCatalogCliTests(unittest.TestCase):
    def test_cli_prints_catalog_for_supported_shape(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            describe_functions = root / "describe-functions.json"
            describe_functions.write_text(
                json.dumps(
                    {
                        "lane_functions": [
                            {"lane_id": "shape", "function_id": "identity"},
                            {"lane_id": "shape", "function_id": "repeat"},
                        ]
                    }
                ),
                encoding="utf-8",
            )

            stdout = io.StringIO()
            with redirect_stdout(stdout):
                exit_code = main(["--describe-functions", str(describe_functions)])

            self.assertEqual(exit_code, 0)
            payload = json.loads(stdout.getvalue())
            self.assertEqual(payload["status"], "ok")
            self.assertEqual(payload["lane_count"], 1)
            self.assertIn("shape", payload["lanes"])

    def test_cli_reports_unsupported_shape(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            describe_functions = root / "describe-functions.json"
            describe_functions.write_text(json.dumps({"unexpected": []}), encoding="utf-8")

            stdout = io.StringIO()
            with redirect_stdout(stdout):
                exit_code = main(["--describe-functions", str(describe_functions)])

            self.assertEqual(exit_code, 2)
            payload = json.loads(stdout.getvalue())
            self.assertEqual(payload["status"], "runtime_metadata_shape_unsupported")


if __name__ == "__main__":
    unittest.main()
