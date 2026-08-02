from __future__ import annotations

import json
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from cuda_fractal_state_tool.automated_run_store import AutomatedRunStore, RunStoreWriteError
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

    def test_evidence_writes_are_atomic_and_cannot_escape_run(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = self._store(Path(temp_dir))
            json_path = store.write_evidence_json("transport/turn-1/request.json", {"ok": True})
            bytes_path = store.write_evidence_bytes("transport/turn-1/raw.txt", b"raw\n")
            self.assertEqual(json.loads(json_path.read_text(encoding="utf-8")), {"ok": True})
            self.assertEqual(bytes_path.read_bytes(), b"raw\n")
            for unsafe in ("", "../escape.json", str(Path(temp_dir).resolve() / "absolute.json")):
                with self.subTest(unsafe=unsafe), self.assertRaisesRegex(ValueError, "safe relative"):
                    store.write_evidence_json(unsafe, {})

    def test_retryable_windows_projection_collision_recovers(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = self._store(Path(temp_dir))
            from cuda_fractal_state_tool import automated_run_store as module

            real_replace = module.os.replace
            attempts = {"count": 0}

            def replace_with_collisions(source, target):
                if Path(target) == store.active_turn_path and attempts["count"] < 2:
                    attempts["count"] += 1
                    error = PermissionError("sharing collision")
                    error.winerror = 5
                    raise error
                return real_replace(source, target)

            with patch.object(module.os, "replace", side_effect=replace_with_collisions), patch.object(
                module.time, "sleep", return_value=None
            ):
                event = store.record_transition("one", {}, {"state": "OBSERVE"})

            self.assertEqual(attempts["count"], 2)
            self.assertEqual(event["sequence"], 1)
            self.assertEqual(store.load_active_turn()["last_event_sequence"], 1)

    def test_persistent_projection_collision_reports_event_append_precisely(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = self._store(Path(temp_dir))
            from cuda_fractal_state_tool import automated_run_store as module

            error = PermissionError("sharing collision")
            error.winerror = 5
            with patch.object(module.os, "replace", side_effect=error), patch.object(
                module.time, "sleep", return_value=None
            ), self.assertRaises(RunStoreWriteError) as captured:
                store.record_transition("one", {}, {"state": "OBSERVE"})

            self.assertEqual(
                captured.exception.code,
                "ACTIVE_TURN_PROJECTION_WRITE_FAILED_AFTER_EVENT_APPEND",
            )
            self.assertTrue(captured.exception.event_appended)
            self.assertEqual(captured.exception.event_sequence, 1)
            self.assertEqual(store.read_events()[0]["event_type"], "one")

    def test_persistent_evidence_write_failure_has_run_store_taxonomy(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = self._store(Path(temp_dir))
            from cuda_fractal_state_tool import automated_run_store as module

            error = PermissionError("sharing collision")
            error.winerror = 5
            with patch.object(module.os, "replace", side_effect=error), patch.object(
                module.time, "sleep", return_value=None
            ), self.assertRaises(RunStoreWriteError) as captured:
                store.write_evidence_json("transport/turn/request.json", {"ok": True})

            self.assertEqual(captured.exception.code, "EVIDENCE_JSON_WRITE_FAILED")
            self.assertFalse(captured.exception.event_appended)

    def test_concurrent_ui_style_reads_and_writes_share_one_lock(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = self._store(Path(temp_dir))
            failures: list[Exception] = []
            done = threading.Event()

            def reader() -> None:
                while not done.is_set():
                    try:
                        if store.active_turn_path.exists():
                            store.load_active_turn()
                        store.read_events()
                    except Exception as exc:  # pragma: no cover - asserted below
                        failures.append(exc)
                        done.set()

            thread = threading.Thread(target=reader)
            thread.start()
            try:
                for number in range(1, 31):
                    store.record_transition(
                        "step",
                        {"number": number},
                        {"state": "OBSERVE", "number": number},
                    )
            finally:
                done.set()
                thread.join(timeout=2)

            self.assertEqual(failures, [])
            self.assertEqual(store.load_active_turn()["last_event_sequence"], 30)


if __name__ == "__main__":
    unittest.main()
