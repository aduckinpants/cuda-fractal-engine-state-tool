from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from cuda_fractal_state_tool.validation_runs import latest_validation_run, list_validation_runs, load_validation_index, summarize_validation_runs


class ValidationRunsTests(unittest.TestCase):
    def test_missing_index_returns_empty_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "index.json"
            index = load_validation_index(path)
            self.assertEqual(index, {"entries": []})
            self.assertEqual(list_validation_runs(path), [])
            self.assertIsNone(latest_validation_run(path))

    def test_listing_and_summary_are_sorted_and_counted(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "index.json"
            path.write_text(
                """{
  "entries": [
    {
      "run_id": "older",
      "timestamp_utc": "2026-07-20T10:00:00+00:00",
      "status": "runtime_proof_failed",
      "runtime_status": "runtime_failure"
    },
    {
      "run_id": "newer",
      "timestamp_utc": "2026-07-20T11:00:00+00:00",
      "status": "runtime_proof_succeeded",
      "runtime_status": "runtime_success"
    }
  ]
}
""",
                encoding="utf-8",
            )

            runs = list_validation_runs(path)
            self.assertEqual(runs[0]["run_id"], "newer")
            self.assertEqual(runs[1]["run_id"], "older")

            latest = latest_validation_run(path)
            self.assertIsNotNone(latest)
            self.assertEqual(latest["run_id"], "newer")

            summary = summarize_validation_runs(path)
            self.assertEqual(summary["run_count"], 2)
            self.assertEqual(summary["status_counts"]["runtime_proof_succeeded"], 1)
            self.assertEqual(summary["status_counts"]["runtime_proof_failed"], 1)
            self.assertEqual(summary["runtime_status_counts"]["runtime_success"], 1)
            self.assertEqual(summary["runtime_status_counts"]["runtime_failure"], 1)


if __name__ == "__main__":
    unittest.main()
