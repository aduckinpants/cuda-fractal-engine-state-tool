from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from PIL import Image

from cuda_fractal_state_tool.agent_bundle import AgentBundle
from cuda_fractal_state_tool.user_workflow import (
    SessionState,
    UserWorkflowSession,
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
                    "render": {"width": 8, "height": 6, "device_id": 0},
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        (capture / "fractal-state.json").write_text(
            json.dumps({"schema_id": "viewer.finding_fractal_state.v1", "active_fractal_controls": {}}),
            encoding="utf-8",
        )
        (capture / "field-notes.md").write_text("A curious boundary.\n", encoding="utf-8")
        Image.new("RGB", (8, 6), (20, 40, 80)).save(capture / "frame.png")
        return capture

    @staticmethod
    def _bundle(root: Path, finding_id: str, packet_id: str) -> AgentBundle:
        packet_dir = root / "packets" / packet_id
        packet_dir.mkdir(parents=True, exist_ok=True)
        packet = packet_dir / "packet.md"
        manifest = packet_dir / "manifest.json"
        packet.write_text("# packet\n", encoding="utf-8")
        manifest.write_text("{}\n", encoding="utf-8")
        return AgentBundle(
            packet_id=packet_id,
            packet_dir=packet_dir,
            packet_path=packet,
            packet_sha256="packet-sha",
            manifest_path=manifest,
            manifest_sha256=f"manifest-{packet_id}",
            finding_id=finding_id,
            selected_fractal_type="explaino_all",
            required_attachments=("state.json",),
            recommended_attachments=(),
            unavailable_optional_attachments=(),
        )

    def test_finding_import_preserves_field_notes_and_exposes_exact_context(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            capture = self._capture(root)
            finding = load_finding_context(capture, root / "workspace")
            self.assertIn(finding.finding_id, finding.summary_text)
            self.assertIn("Fractal family: explaino_all", finding.summary_text)
            self.assertEqual(
                (finding.import_result.finding_dir / "source" / "field-notes.md").read_text(encoding="utf-8"),
                "A curious boundary.\n",
            )
            manifest = json.loads(finding.import_result.workspace_manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(manifest["paths"]["packets_dir"], "packets")
            self.assertEqual(manifest["paths"]["proofs_dir"], "proofs")
            self.assertNotIn("proposals_dir", manifest["paths"])

    def test_session_invalidates_exact_proof_on_override_bundle_and_finding_changes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            finding = load_finding_context(self._capture(root), root / "workspace")
            bundle_one = self._bundle(root, finding.finding_id, "packet-one")
            bundle_two = self._bundle(root, finding.finding_id, "packet-two")
            session = UserWorkflowSession()
            generation = session.begin_finding_change()
            session.accept_finding(finding)
            self.assertEqual(session.state, SessionState.FINDING_READY)
            session.accept_bundle(bundle_one)
            self.assertEqual(session.state, SessionState.PACKET_READY)
            session.set_override_text('{"params":{"explaino_damping":0.9}}')
            self.assertEqual(session.state, SessionState.OVERRIDE_DIRTY)
            session.begin_proof()
            self.assertEqual(session.state, SessionState.PROVING)
            proof = SimpleNamespace(status="replay_proven")
            session.accept_proof_result(proof)
            self.assertEqual(session.state, SessionState.VISUAL_REVIEW_PENDING)
            session.record_review("accepted")
            self.assertEqual(session.state, SessionState.USER_ACCEPTED)
            session.mark_launch_ready()
            self.assertEqual(session.state, SessionState.LAUNCH_READY)

            session.set_override_text('{"params":{"explaino_damping":0.8}}')
            self.assertEqual(session.state, SessionState.OVERRIDE_DIRTY)
            self.assertIsNone(session.proof_result)
            session.accept_bundle(bundle_two)
            self.assertEqual(session.state, SessionState.OVERRIDE_DIRTY)
            self.assertIsNone(session.review_decision)
            session.begin_finding_change()
            self.assertGreater(session.generation, generation)
            self.assertIsNone(session.bundle)
            self.assertTrue(session.override_text)

    def test_revision_is_immutable_boundary_and_reset_preserves_durable_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            finding = load_finding_context(self._capture(root), root / "workspace")
            session = UserWorkflowSession(finding=finding)
            session.accept_bundle(self._bundle(root, finding.finding_id, "packet"))
            session.set_override_text('{"params":{"explaino_damping":0.9}}')
            session.begin_proof()
            session.accept_proof_result(SimpleNamespace(status="replay_proven"))
            session.record_review("revision_needed")
            self.assertEqual(session.state, SessionState.REVISION_NEEDED)
            finding_dir = finding.import_result.finding_dir
            session.reset()
            self.assertEqual(session.state, SessionState.EMPTY)
            self.assertEqual(session.override_text, "")
            self.assertTrue(finding_dir.is_dir())


if __name__ == "__main__":
    unittest.main()
