from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from cuda_fractal_state_tool.research_run_store import ResearchRunStore


class ResearchRunStoreTests(unittest.TestCase):
    def _store(self, root: Path) -> ResearchRunStore:
        return ResearchRunStore.create(
            root,
            run_id="research-test",
            protocol_snapshot={"schema": "question_research_protocol.v1"},
            initial_packet={
                "packet_id": "packet-base",
                "manifest_sha256": "a" * 64,
                "finding_id": "finding-base",
            },
            research_brief={"question": "Why?", "hard_dollar_budget": "0"},
        )

    def test_manifest_is_sealed_under_question_runs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            store = self._store(root)
            manifest = json.loads(store.manifest_path.read_text(encoding="utf-8"))

            self.assertEqual(store.run_dir.parent.name, "question-runs")
            self.assertEqual(manifest["research_run_manifest_version"], 1)
            self.assertEqual(manifest["research_brief"]["question"], "Why?")
            self.assertTrue((store.run_dir / "attempts").is_dir())
            with self.assertRaisesRegex(FileExistsError, "already exists"):
                self._store(root)

    def test_events_projection_and_recovery_use_shared_owner(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = self._store(Path(temp_dir))
            store.record_transition("session_started", {}, {"state": "PLAN"})
            store.record_transition("planner_ready", {}, {"state": "PLAN_READY"})

            store.active_turn_path.unlink()
            self.assertEqual(store.recover_active_turn(), {"state": "PLAN_READY"})
            self.assertEqual([event["sequence"] for event in store.read_events()], [1, 2])

    def test_immutable_research_artifacts_cannot_be_replaced(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = self._store(Path(temp_dir))
            path = store.write_evidence_once_bytes("attempts/001/round-plan.json", b"{}\n")

            self.assertEqual(path.read_bytes(), b"{}\n")
            self.assertEqual(
                store.write_evidence_once_bytes("attempts/001/round-plan.json", b"{}\n"),
                path,
            )
            with self.assertRaises(FileExistsError):
                store.write_evidence_once_bytes("attempts/001/round-plan.json", b"changed\n")

    def test_open_rejects_non_research_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            store = self._store(root)
            manifest = json.loads(store.manifest_path.read_text(encoding="utf-8"))
            manifest.pop("research_run_manifest_version")
            store.manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "Unsupported research run"):
                ResearchRunStore.open(store.run_dir)


if __name__ == "__main__":
    unittest.main()
