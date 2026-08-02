from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from cuda_fractal_state_tool.derived_finding import promote_replay_proven_candidate
from cuda_fractal_state_tool.state_override_proof import StateOverrideProofResult


def _json_bytes(value: object) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


class DerivedFindingTests(unittest.TestCase):
    def _proof(self, root: Path) -> tuple[StateOverrideProofResult, Path]:
        packet = root / "finding" / "packets" / "packet-1"
        packet.mkdir(parents=True)
        manifest_bytes = b'{"packet_version":8}\n'
        (packet / "manifest.json").write_bytes(manifest_bytes)
        proof_dir = root / "finding" / "proofs" / "proof-1"
        materialization = proof_dir / "materialization"
        materialization.mkdir(parents=True)
        state_bytes = b'{"state_version":3,"fractal_type":"explaino_all"}\n'
        display_bytes = b"exact-proof-owned-png"
        state_path = materialization / "state.json"
        display_path = materialization / "candidate-display.png"
        state_path.write_bytes(state_bytes)
        display_path.write_bytes(display_bytes)
        binding_bytes = _json_bytes({"proof_id": "proof-1"})
        (proof_dir / "binding.json").write_bytes(binding_bytes)
        receipt = {
            "proof_id": "proof-1",
            "status": "replay_proven",
            "visual_review": "pending",
            "launch_ready": False,
            "materialization": {"display_derivative": {"decoded_equal": True}},
            "engine_launch_candidate": {"sha256": _sha(state_bytes)},
            "binding": {"packet_manifest_sha256": _sha(manifest_bytes)},
        }
        receipt_bytes = _json_bytes(receipt)
        receipt_path = proof_dir / "receipt.json"
        receipt_path.write_bytes(receipt_bytes)
        result = StateOverrideProofResult(
            status="replay_proven",
            proof_id="proof-1",
            message="proven",
            proof_dir=proof_dir,
            receipt_path=receipt_path,
            receipt_sha256=_sha(receipt_bytes),
            binding_sha256=_sha(binding_bytes),
            packet_dir=packet,
            packet_id="packet-1",
            packet_manifest_sha256=_sha(manifest_bytes),
            override_text_sha256="a" * 64,
            merged_candidate_path=proof_dir / "merged_candidate.json",
            merged_candidate_sha256="b" * 64,
            engine_candidate_path=state_path,
            engine_candidate_sha256=_sha(state_bytes),
            candidate_display_path=display_path,
            candidate_display_sha256=_sha(display_bytes),
        )
        return result, packet

    def test_promotes_exact_proof_owned_png_through_canonical_importer(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            proof, packet = self._proof(root)
            promotion = promote_replay_proven_candidate(
                proof=proof,
                packet_dir=packet,
                workspace_root=root / "workspace",
                promotion_dir=root / "run" / "rounds" / "round-01" / "promotion",
            )
            self.assertEqual(
                (promotion.capture_dir / "state.json").read_bytes(),
                proof.engine_candidate_path.read_bytes(),
            )
            self.assertEqual(
                (promotion.capture_dir / "frame.png").read_bytes(),
                proof.candidate_display_path.read_bytes(),
            )
            finding = json.loads((promotion.capture_dir / "finding.json").read_text(encoding="utf-8"))
            self.assertFalse(finding["human_acceptance"])
            self.assertEqual(finding["lineage"]["source_proof_id"], proof.proof_id)
            workspace_source = promotion.import_result.finding_dir / "source"
            self.assertEqual((workspace_source / "frame.png").read_bytes(), proof.candidate_display_path.read_bytes())
            receipt = json.loads(promotion.promotion_receipt_path.read_text(encoding="utf-8"))
            self.assertEqual(receipt["status"], "promoted_through_canonical_importer")
            self.assertFalse(receipt["human_acceptance"])

    def test_tampering_or_non_proven_status_fails_before_publication(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            proof, packet = self._proof(root)
            proof.candidate_display_path.write_bytes(b"tampered")
            with self.assertRaisesRegex(ValueError, "changed"):
                promote_replay_proven_candidate(
                    proof=proof,
                    packet_dir=packet,
                    workspace_root=root / "workspace",
                    promotion_dir=root / "promotion",
                )
            self.assertFalse((root / "promotion").exists())

    def test_existing_promotion_is_never_rewritten(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            proof, packet = self._proof(root)
            target = root / "promotion"
            target.mkdir()
            with self.assertRaisesRegex(FileExistsError, "already exists"):
                promote_replay_proven_candidate(
                    proof=proof,
                    packet_dir=packet,
                    workspace_root=root / "workspace",
                    promotion_dir=target,
                )


if __name__ == "__main__":
    unittest.main()
