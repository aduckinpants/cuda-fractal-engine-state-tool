from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from cuda_fractal_state_tool.agent_bundle import AgentBundle
from cuda_fractal_state_tool.enrichment_disclosure import (
    DisclosureProfile,
    FindingDisclosureService,
)


def _json_bytes(value: object) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


class EnrichmentDisclosureTests(unittest.TestCase):
    def _bundle(self, root: Path) -> AgentBundle:
        packet = root / "packet"
        packet.mkdir()
        manifest = packet / "manifest.json"
        manifest.write_bytes(b"{}\n")
        packet_md = packet / "packet.md"
        packet_md.write_bytes(b"# packet\n")
        return AgentBundle(
            packet_version=8,
            packet_id="packet-1",
            packet_dir=packet,
            packet_path=packet_md,
            packet_sha256=hashlib.sha256(packet_md.read_bytes()).hexdigest(),
            manifest_path=manifest,
            manifest_sha256=hashlib.sha256(manifest.read_bytes()).hexdigest(),
            finding_id="finding-1",
            selected_fractal_type="explaino_rational_escape",
            required_attachments=("packet.md", "manifest.json"),
            recommended_attachments=(),
            unavailable_optional_attachments=(),
        )

    def _analysis(self, root: Path) -> tuple[Path, str]:
        analysis_id = "a" * 64
        directory = root / "analysis" / analysis_id
        directory.mkdir(parents=True)
        artifacts = {
            "common-facts.json": b'{"fact":1}\n',
            "provider-result.json": b'{"status":"available"}\n',
            "summary.md": b"# summary\n",
            "annotated-web-frame.png": b"png",
        }
        for name, payload in artifacts.items():
            (directory / name).write_bytes(payload)
        receipt = {
            "analysis_id": analysis_id,
            "status": "complete",
            "artifact_sha256": {
                name: hashlib.sha256(payload).hexdigest() for name, payload in artifacts.items()
            },
        }
        (directory / "receipt.json").write_bytes(_json_bytes(receipt))
        return directory, analysis_id

    def test_blind_does_not_run_analysis_or_disclose_resources(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            bundle = self._bundle(root)
            enrichment = SimpleNamespace(analyze=lambda *_args, **_kwargs: self.fail("analyzed"))
            service = FindingDisclosureService(
                workspace_root=root,
                runtime_executable=root / "runtime.exe",
                enrichment=enrichment,
            )
            with patch(
                "cuda_fractal_state_tool.enrichment_disclosure.load_existing_agent_bundle",
                return_value=bundle,
            ):
                disclosure = service.prepare(bundle.packet_dir, DisclosureProfile.BLIND)
            self.assertIsNone(disclosure.analysis_id)
            self.assertEqual(disclosure.resources, ())
            self.assertEqual(disclosure.manifest["profile"], "blind")

    def test_assisted_selects_only_receipted_outputs_in_fixed_order(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            bundle = self._bundle(root)
            analysis_dir, analysis_id = self._analysis(root)
            enrichment = SimpleNamespace(
                analyze=lambda *_args, **_kwargs: SimpleNamespace(
                    analysis_dir=analysis_dir,
                    analysis_id=analysis_id,
                )
            )
            service = FindingDisclosureService(
                workspace_root=root,
                runtime_executable=root / "runtime.exe",
                enrichment=enrichment,
            )
            with patch(
                "cuda_fractal_state_tool.enrichment_disclosure.load_existing_agent_bundle",
                return_value=bundle,
            ):
                disclosure = service.prepare(bundle.packet_dir, DisclosureProfile.ASSISTED)
            self.assertEqual(
                [item.analysis_filename for item in disclosure.resources],
                [
                    "common-facts.json",
                    "provider-result.json",
                    "summary.md",
                    "annotated-web-frame.png",
                ],
            )
            self.assertEqual(disclosure.resources[-1].media_role, "vision")
            self.assertNotIn("disclosure", disclosure.analysis_id)

    def test_mutated_receipted_output_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            bundle = self._bundle(root)
            analysis_dir, analysis_id = self._analysis(root)
            (analysis_dir / "common-facts.json").write_bytes(b"changed")
            enrichment = SimpleNamespace(
                analyze=lambda *_args, **_kwargs: SimpleNamespace(
                    analysis_dir=analysis_dir,
                    analysis_id=analysis_id,
                )
            )
            service = FindingDisclosureService(
                workspace_root=root,
                runtime_executable=root / "runtime.exe",
                enrichment=enrichment,
            )
            with (
                patch(
                    "cuda_fractal_state_tool.enrichment_disclosure.load_existing_agent_bundle",
                    return_value=bundle,
                ),
                self.assertRaisesRegex(ValueError, "changed"),
            ):
                service.prepare(bundle.packet_dir, DisclosureProfile.BREAK_BLIND)


if __name__ == "__main__":
    unittest.main()
