from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from PIL import Image

from cuda_fractal_state_tool.agent_bundle import AgentBundle
from cuda_fractal_state_tool.automated_context import (
    build_round_review_comparison,
    build_round_review_ledger,
    load_packet_web_frame,
    ledger_transport_resource,
)
from cuda_fractal_state_tool.automated_protocol import PacketAuthorityBinding


class AutomatedContextTests(unittest.TestCase):
    @staticmethod
    def _bundle(root: Path, name: str, color: tuple[int, int, int]) -> AgentBundle:
        packet_dir = root / name
        packet_dir.mkdir()
        packet = packet_dir / "packet.md"
        frame = packet_dir / "web-agent-frame.png"
        manifest = packet_dir / "manifest.json"
        packet.write_text("# packet\n", encoding="utf-8")
        Image.new("RGB", (4, 3), color).save(frame, format="PNG")
        frame_bytes = frame.read_bytes()
        manifest.write_text(
            json.dumps(
                {
                    "files": [
                        {
                            "path": frame.name,
                            "role": "web_discussion_derivative",
                            "sha256": hashlib.sha256(frame_bytes).hexdigest(),
                            "size_bytes": len(frame_bytes),
                        }
                    ]
                }
            )
            + "\n",
            encoding="utf-8",
        )
        return AgentBundle(
            packet_version=8,
            packet_id=name,
            packet_dir=packet_dir,
            packet_path=packet,
            packet_sha256=hashlib.sha256(packet.read_bytes()).hexdigest(),
            manifest_path=manifest,
            manifest_sha256=hashlib.sha256(manifest.read_bytes()).hexdigest(),
            finding_id=f"finding-{name}",
            selected_fractal_type="explaino_all",
            required_attachments=("packet.md", "manifest.json", frame.name),
            recommended_attachments=(),
            unavailable_optional_attachments=(),
        )

    def test_review_ledger_binds_exact_decision_override_proof_and_packets(self) -> None:
        author = PacketAuthorityBinding("packet-a", "a" * 64, "finding-a")
        derived = PacketAuthorityBinding("packet-b", "b" * 64, "finding-b")
        decision = "Selected experiment and locked prediction.\n```json\n{}\n```"
        override = '{"params":{"x":1}}'
        proof = SimpleNamespace(
            proof_id="proof-1",
            status="replay_proven",
            message="proven",
            receipt_sha256="c" * 64,
            engine_candidate_sha256="d" * 64,
            candidate_frame_sha256="e" * 64,
            replay_state_sha256="f" * 64,
            replay_frame_sha256="0" * 64,
        )
        materialization = SimpleNamespace(
            changed_paths=(SimpleNamespace(path="params.x", conceptual_domain="dynamics"),)
        )
        ledger = build_round_review_ledger(
            round_number=1,
            author_packet=author,
            derived_packet=derived,
            author_response_text=decision,
            override_text=override,
            materialization=materialization,
            proof=proof,
        )
        value = json.loads(ledger.payload)
        self.assertEqual(value["author_packet"]["packet_id"], "packet-a")
        self.assertEqual(value["derived_packet"]["packet_id"], "packet-b")
        self.assertEqual(value["author_decision_record"]["exact_text"], decision)
        self.assertEqual(value["state_override"]["exact_text"], override)
        self.assertEqual(value["proof"]["proof_id"], "proof-1")
        self.assertEqual(hashlib.sha256(ledger.payload).hexdigest(), ledger.sha256)
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "ledger.json"
            path.write_bytes(ledger.payload)
            resource = ledger_transport_resource(path, ledger)
            self.assertEqual(resource.role, "controller_round_review_ledger")
            self.assertEqual(resource.payload, ledger.payload)

    def test_review_comparison_uses_exact_manifest_bound_packet_images(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            author_bundle = self._bundle(root, "packet-a", (1, 2, 3))
            derived_bundle = self._bundle(root, "packet-b", (4, 5, 6))
            base = load_packet_web_frame(author_bundle)
            result = load_packet_web_frame(derived_bundle)
            proof = SimpleNamespace(
                proof_id="proof-1",
                status="replay_proven",
                receipt_sha256="c" * 64,
                engine_candidate_sha256="d" * 64,
                candidate_frame_sha256="e" * 64,
                replay_state_sha256="f" * 64,
                replay_frame_sha256="0" * 64,
            )
            materialization = SimpleNamespace(
                changed_paths=(SimpleNamespace(path="params.x"),)
            )
            comparison = build_round_review_comparison(
                round_number=1,
                author_packet=PacketAuthorityBinding(
                    author_bundle.packet_id,
                    author_bundle.manifest_sha256,
                    author_bundle.finding_id,
                ),
                derived_packet=PacketAuthorityBinding(
                    derived_bundle.packet_id,
                    derived_bundle.manifest_sha256,
                    derived_bundle.finding_id,
                ),
                base_frame=base,
                result_frame=result,
                base_frame_path=base.local_path,
                result_frame_path=result.local_path,
                materialization=materialization,
                proof=proof,
            )
            value = json.loads(comparison.payload)
            self.assertEqual(value["changed_paths"], ["params.x"])
            self.assertFalse(value["decoded_pixel_comparison"]["decoded_equal"])
            self.assertEqual(value["base_web_frame"]["sha256"], base.sha256)
            self.assertEqual(value["result_web_frame"]["sha256"], result.sha256)

            base.local_path.write_bytes(b"tampered")
            with self.assertRaisesRegex(ValueError, "changed after manifest binding"):
                load_packet_web_frame(author_bundle)

    def test_review_frame_requires_exactly_one_declared_web_derivative(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            bundle = self._bundle(root, "packet-a", (1, 2, 3))
            manifest = json.loads(bundle.manifest_path.read_text(encoding="utf-8"))
            manifest["files"] = []
            bundle.manifest_path.write_text(json.dumps(manifest) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "manifest is unavailable or malformed"):
                load_packet_web_frame(bundle)


if __name__ == "__main__":
    unittest.main()
