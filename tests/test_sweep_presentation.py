from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from PIL import Image

from cuda_fractal_state_tool.sweep_presentation import render_scalar_sweep_presentation


class SweepPresentationTests(unittest.TestCase):
    def test_contact_sheet_uses_proof_owned_pngs_and_receipts_every_transform(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            members = []
            for index, color in enumerate(((255, 0, 0), (0, 255, 0), (0, 0, 255))):
                path = root / f"proof-{index}.png"
                Image.new("RGB", (160, 100), color).save(path)
                payload = path.read_bytes()
                members.append(
                    SimpleNamespace(
                        index=index,
                        value=index / 2,
                        status="REPLAY_PROVEN",
                        proof_id=f"proof-{index}",
                        candidate_display_path=path,
                        candidate_display_sha256=hashlib.sha256(payload).hexdigest(),
                    )
                )
            result = render_scalar_sweep_presentation(
                sweep_dir=root / "sweep",
                sweep_id="sweep-1",
                axis_path="params.x",
                members=members,
            )
            self.assertTrue(result.contact_sheet_path.is_file())
            self.assertTrue(result.receipt_path.is_file())
            with Image.open(result.contact_sheet_path) as image:
                self.assertEqual(image.size, (1536, 364))
            self.assertEqual(len(result.source_records), 3)
            self.assertTrue(all(item["source_sha256"] for item in result.source_records))

    def test_missing_or_mutated_proven_png_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            path = root / "candidate.png"
            Image.new("RGB", (16, 10), "red").save(path)
            member = SimpleNamespace(
                index=0,
                value=0,
                status="REPLAY_PROVEN",
                proof_id="proof-1",
                candidate_display_path=path,
                candidate_display_sha256="0" * 64,
            )
            with self.assertRaisesRegex(ValueError, "changed"):
                render_scalar_sweep_presentation(
                    sweep_dir=root / "sweep",
                    sweep_id="sweep-1",
                    axis_path="params.x",
                    members=[member],
                )

    def test_failed_member_gets_placeholder_without_fabricating_an_image_source(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            member = SimpleNamespace(
                index=0,
                value=0,
                status="PROOF_FAILED",
                proof_id="proof-1",
                candidate_display_path=None,
                candidate_display_sha256=None,
            )
            result = render_scalar_sweep_presentation(
                sweep_dir=root / "sweep",
                sweep_id="sweep-1",
                axis_path="params.x",
                members=[member],
            )
            self.assertIsNone(result.source_records[0]["source_path"])
            self.assertEqual(result.source_records[0]["status"], "PROOF_FAILED")


if __name__ == "__main__":
    unittest.main()
