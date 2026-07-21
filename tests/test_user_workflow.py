from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from cuda_fractal_state_tool.user_workflow import (
    CAPABILITY_PROFILE,
    SessionState,
    UserWorkflowSession,
    build_finding_intake_packet,
    load_finding_context,
)


class UserWorkflowTests(unittest.TestCase):
    def _capture(self, root: Path) -> Path:
        capture = root / "capture"
        capture.mkdir()
        (capture / "state.json").write_text(
            json.dumps(
                {
                    "state_version": 3,
                    "fractal_type": "explaino_all",
                    "view": {"auto_max_iter": False},
                    "params": {
                        "max_iter": 500,
                        "color_signal": "root_index",
                        "color_shape": "identity",
                        "color_palette": "joy",
                        "color_grading": "basin_default",
                    },
                    "render": {"width": 80, "height": 60, "device_id": 0},
                }
            ),
            encoding="utf-8",
        )
        Image.new("RGB", (80, 60), (10, 20, 30)).save(capture / "frame.png")
        return capture

    def _runtime(self, root: Path) -> Path:
        runtime = root / "runtime"
        contract_dir = runtime / "ui_salt" / "generated"
        contract_dir.mkdir(parents=True)
        cmd = runtime / "fractal_ui.cmd"
        cmd.write_text("@echo off\n", encoding="utf-8")
        (runtime / "fractal_ui_active.txt").write_text("fractal_ui.exe\n", encoding="utf-8")
        (runtime / "fractal_ui.exe").write_bytes(b"engine")
        (contract_dir / "color_pipeline_function_library.contract.v1.json").write_text(
            json.dumps(
                {
                    "function_library": {
                        "lanes": [
                            {"id": "source", "default": "root_index", "functions": [{"id": "root_index"}]},
                            {"id": "shape", "default": "identity", "functions": [{"id": "identity"}, {"id": "repeat"}]},
                            {"id": "palette", "default": "joy_root_palette", "functions": [{"id": "joy_root_palette"}]},
                            {"id": "grading", "default": "basin_default", "functions": [{"id": "basin_default"}]},
                        ]
                    }
                }
            ),
            encoding="utf-8",
        )
        return cmd

    def test_real_import_summary_and_exact_packet_persistence(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            capture = self._capture(root)
            finding = load_finding_context(capture, root / "workspace")
            packet = build_finding_intake_packet(finding, self._runtime(root))
            self.assertIn(finding.finding_id, finding.summary_text)
            self.assertEqual(packet.capability_profile, CAPABILITY_PROFILE)
            self.assertEqual(hashlib.sha256(packet.packet_text.encode("utf-8")).hexdigest(), packet.packet_sha256)
            self.assertEqual(packet.packet_path.read_text(encoding="utf-8"), packet.packet_text)
            manifest = json.loads(packet.manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(manifest["packet_sha256"], packet.packet_sha256)
            self.assertEqual(manifest["finding_id"], finding.finding_id)
            self.assertNotIn(str(capture), packet.packet_text)
            self.assertNotIn(str(root / "workspace"), packet.packet_text)

    def test_session_transitions_packet_change_and_reset_invalidate_readiness(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            finding = load_finding_context(self._capture(root), root / "workspace")
            runtime = self._runtime(root)
            packet_one = build_finding_intake_packet(finding, runtime)
            packet_two = build_finding_intake_packet(finding, runtime)
            session = UserWorkflowSession()
            generation = session.begin_finding_change()
            session.accept_finding(finding)
            self.assertEqual(session.state, SessionState.FINDING_READY)
            session.accept_packet(packet_one)
            self.assertEqual(session.state, SessionState.PACKET_READY)
            session.set_proposal_text('{"proposal_version":1}')
            self.assertEqual(session.state, SessionState.PROPOSAL_DIRTY)
            session.accept_packet(packet_two)
            self.assertEqual(session.state, SessionState.PROPOSAL_DIRTY)
            self.assertNotEqual(packet_one.packet_id, packet_two.packet_id)
            session.reset()
            self.assertEqual(session.state, SessionState.EMPTY)
            self.assertGreater(session.generation, generation)
            self.assertIsNone(session.packet)
            self.assertEqual(session.proposal_text, "")


if __name__ == "__main__":
    unittest.main()
