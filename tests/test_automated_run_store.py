from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from cuda_fractal_state_tool.automated_run_store import AutomatedRunStore
from cuda_fractal_state_tool.workspace_layout import initialize_workspace_root


class AutomatedRunStoreTests(unittest.TestCase):
    def _store(self, root: Path) -> AutomatedRunStore:
        initialize_workspace_root(root)
        return AutomatedRunStore.create(
            root,
            run_id="run-test",
            protocol_snapshot={"schema": "agent_session_protocol.v1"},
            initial_packet={
                "packet_id": "packet-base",
                "manifest_sha256": "a" * 64,
                "finding_id": "finding-base",
            },
        )

    def test_events_are_append_only_and_active_turn_is_last_projection(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = self._store(Path(temp_dir))
            first = {"state": "OBSERVE", "current_packet_id": "packet-base"}
            second = {"state": "EXPLORE", "current_packet_id": "packet-base"}

            store.record_transition("session_started", {}, first)
            store.record_transition("prompt_requested", {"prompt": "notice"}, second)

            events = store.read_events()
            self.assertEqual([event["sequence"] for event in events], [1, 2])
            self.assertEqual(store.load_active_turn()["projection"], second)
            self.assertEqual(store.recover_active_turn(), second)

    def test_recovery_rebuilds_missing_or_stale_projection_from_events(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = self._store(Path(temp_dir))
            first = {"state": "OBSERVE"}
            second = {"state": "EXPLORE"}
            store.record_transition("one", {}, first)
            store.record_transition("two", {}, second)

            store.active_turn_path.unlink()
            self.assertEqual(store.recover_active_turn(), second)
            active = store.load_active_turn()
            self.assertEqual(active["last_event_sequence"], 2)

            active["last_event_sequence"] = 1
            store.active_turn_path.write_text(
                json.dumps(active, indent=2, sort_keys=True) + "\n", encoding="utf-8"
            )
            self.assertEqual(store.recover_active_turn(), second)

    def test_same_sequence_projection_disagreement_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = self._store(Path(temp_dir))
            store.record_transition("one", {}, {"state": "OBSERVE"})
            active = store.load_active_turn()
            active["projection"] = {"state": "PROVE_CANDIDATE"}
            store.active_turn_path.write_text(
                json.dumps(active, indent=2, sort_keys=True) + "\n", encoding="utf-8"
            )

            with self.assertRaisesRegex(ValueError, "disagrees with event history"):
                store.recover_active_turn()

    def test_run_manifest_is_immutable(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._store(root)
            with self.assertRaisesRegex(FileExistsError, "already exists"):
                self._store(root)


if __name__ == "__main__":
    unittest.main()
