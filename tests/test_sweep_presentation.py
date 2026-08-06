from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from PIL import Image

from cuda_fractal_state_tool.sweep_presentation import (
    CapturedBaseReference,
    compose_research_visual_summary,
    render_scalar_sweep_presentation,
    resolve_captured_base_reference,
)


class SweepPresentationTests(unittest.TestCase):
    def _captured_base(self, root: Path) -> CapturedBaseReference:
        path = root / "captured-base.png"
        Image.new("RGB", (320, 200), (12, 34, 56)).save(path)
        return CapturedBaseReference(
            source_path=path,
            source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
            axis_value=1.0,
            packet_id="packet-1",
            finding_id="finding-1",
        )

    def test_captured_base_resolves_only_hash_bound_full_finding_source(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            finding = Path(temp_dir) / "finding"
            packet = finding / "packets" / "packet-1"
            source = finding / "source" / "frame.png"
            packet.mkdir(parents=True)
            source.parent.mkdir()
            Image.new("RGB", (64, 40), "navy").save(source)
            source_sha = hashlib.sha256(source.read_bytes()).hexdigest()
            (packet / "state.json").write_text(
                json.dumps({"params": {"x": 1.25}}), encoding="utf-8"
            )
            (packet / "manifest.json").write_text(
                json.dumps(
                    {
                        "packet_id": "packet-1",
                        "finding_id": "finding-1",
                        "web_frame_derivative": {
                            "source_finding_relative_path": "source/frame.png",
                            "source_sha256": source_sha,
                        },
                    }
                ),
                encoding="utf-8",
            )

            resolved = resolve_captured_base_reference(packet, "params.x")

            self.assertEqual(resolved.source_path, source.resolve())
            self.assertEqual(resolved.axis_value, 1.25)
            source.write_bytes(b"changed")
            with self.assertRaisesRegex(ValueError, "changed"):
                resolve_captured_base_reference(packet, "params.x")

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
                captured_base=self._captured_base(root),
                members=members,
            )
            self.assertTrue(result.contact_sheet_path.is_file())
            self.assertTrue(result.receipt_path.is_file())
            with Image.open(result.contact_sheet_path) as image:
                self.assertEqual(image.size, (1536, 728))
            self.assertEqual(len(result.source_records), 4)
            self.assertEqual(result.source_records[0]["kind"], "captured_base")
            self.assertFalse(result.source_records[0]["is_sweep_member"])
            self.assertFalse(result.source_records[0]["newly_replay_proven"])
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
                    captured_base=self._captured_base(root),
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
                captured_base=self._captured_base(root),
                members=[member],
            )
            self.assertIsNone(result.source_records[1]["source_path"])
            self.assertEqual(result.source_records[1]["status"], "PROOF_FAILED")

    def test_research_visual_summary_reuses_png_presentations(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            first = root / "first.png"
            second = root / "second.png"
            Image.new("RGB", (1800, 300), "navy").save(first)
            Image.new("RGB", (900, 200), "gold").save(second)

            payload, receipt = compose_research_visual_summary(
                (("Attempt 1", first), ("Attempt 2", second))
            )

            output = root / "summary.png"
            output.write_bytes(payload)
            with Image.open(output) as rendered:
                self.assertEqual(rendered.width, 1536)
            self.assertEqual(len(receipt["sources"]), 2)
            self.assertFalse(receipt["scientific_authority"])
            self.assertEqual(
                receipt["output"]["sha256"], hashlib.sha256(payload).hexdigest()
            )


if __name__ == "__main__":
    unittest.main()
