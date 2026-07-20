from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from cuda_fractal_state_tool.validation_runs import (
  filter_validation_runs,
  latest_filtered_validation_run,
  latest_validation_run,
  list_validation_runs,
  load_validation_index,
  main,
  summarize_validation_runs,
)


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
      "runtime_status": "runtime_failure",
      "draft_override_present": false,
      "draft_lane_count": 0
    },
    {
      "run_id": "newer",
      "timestamp_utc": "2026-07-20T11:00:00+00:00",
      "status": "runtime_proof_succeeded",
      "runtime_status": "runtime_success",
      "promotion_profile": "none",
      "draft_override_present": true,
      "draft_lane_count": 1
    },
    {
      "run_id": "newest-promo",
      "timestamp_utc": "2026-07-20T12:00:00+00:00",
      "status": "runtime_proof_succeeded",
      "runtime_status": "runtime_success",
      "promotion_profile": "observed_runtime_enrichment_v1",
      "draft_override_present": true,
      "draft_lane_count": 2
    }
  ]
}
""",
                encoding="utf-8",
            )

            runs = list_validation_runs(path)
            self.assertEqual(runs[0]["run_id"], "newest-promo")
            self.assertEqual(runs[1]["run_id"], "newer")
            self.assertEqual(runs[2]["run_id"], "older")

            latest = latest_validation_run(path)
            self.assertIsNotNone(latest)
            self.assertEqual(latest["run_id"], "newest-promo")

            summary = summarize_validation_runs(path)
            self.assertEqual(summary["run_count"], 3)
            self.assertEqual(summary["status_counts"]["runtime_proof_succeeded"], 2)
            self.assertEqual(summary["status_counts"]["runtime_proof_failed"], 1)
            self.assertEqual(summary["runtime_status_counts"]["runtime_success"], 2)
            self.assertEqual(summary["runtime_status_counts"]["runtime_failure"], 1)
            self.assertEqual(summary["promotion_profile_counts"]["observed_runtime_enrichment_v1"], 1)
            self.assertEqual(summary["promotion_profile_counts"]["none"], 2)
            self.assertEqual(summary["draft_run_count"], 2)
            self.assertEqual(summary["draft_lane_total"], 3)
            self.assertIsNotNone(summary["latest_draft_run"])
            self.assertEqual(summary["latest_draft_run"]["run_id"], "newest-promo")

            filtered = filter_validation_runs(runs, promotion_profile="observed_runtime_enrichment_v1")
            self.assertEqual(len(filtered), 1)
            self.assertEqual(filtered[0]["run_id"], "newest-promo")

            latest_filtered = latest_filtered_validation_run(path, promotion_profile="none")
            self.assertIsNotNone(latest_filtered)
            self.assertEqual(latest_filtered["run_id"], "newer")

            summary_filtered = summarize_validation_runs(path, promotion_profile="observed_runtime_enrichment_v1")
            self.assertEqual(summary_filtered["run_count"], 1)
            self.assertEqual(summary_filtered["status_counts"]["runtime_proof_succeeded"], 1)
            self.assertEqual(summary_filtered["filters"]["promotion_profile"], "observed_runtime_enrichment_v1")

            summary_window = summarize_validation_runs(path, since="2026-07-20T11:30:00+00:00")
            self.assertEqual(summary_window["run_count"], 1)
            self.assertEqual(summary_window["latest_run"]["run_id"], "newest-promo")
            self.assertEqual(summary_window["filters"]["since"], "2026-07-20T11:30:00+00:00")

            latest_window = latest_filtered_validation_run(path, until="2026-07-20T11:30:00+00:00")
            self.assertIsNotNone(latest_window)
            self.assertEqual(latest_window["run_id"], "newer")

    def test_list_limit_returns_only_first_n_sorted_entries(self) -> None:
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
    },
    {
      "run_id": "newest",
      "timestamp_utc": "2026-07-20T12:00:00+00:00",
      "status": "runtime_proof_succeeded",
      "runtime_status": "runtime_success"
    }
  ]
}
""",
                encoding="utf-8",
            )

            runs = filter_validation_runs(list_validation_runs(path))
            limited = runs[:1]
            self.assertEqual(len(limited), 1)
            self.assertEqual(limited[0]["run_id"], "newest")

            # Smoke the CLI path with --list --limit to ensure it parses and exits.
            exit_code = main(["--index", str(path), "--list", "--limit", "1"])
            self.assertEqual(exit_code, 0)

        def test_invalid_since_timestamp_is_rejected(self) -> None:
          with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "index.json"
            path.write_text('{"entries": []}', encoding="utf-8")
            with self.assertRaises(ValueError):
              summarize_validation_runs(path, since="not-a-timestamp")


if __name__ == "__main__":
    unittest.main()
