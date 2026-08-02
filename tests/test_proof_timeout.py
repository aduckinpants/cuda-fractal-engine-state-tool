from __future__ import annotations

import hashlib
import json
import math
import tempfile
import unittest
from pathlib import Path

from cuda_fractal_state_tool.proof_timeout import (
    resolve_packet_proof_timeout,
    resolve_proof_timeout,
)


def _json_bytes(value: object) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


class ProofTimeoutTests(unittest.TestCase):
    def test_fixture_f_render_time_resolves_to_438_seconds(self) -> None:
        resolution = resolve_proof_timeout(203542.34375)

        self.assertEqual(resolution.timeout_seconds, 438.0)
        self.assertEqual(resolution.source, "captured_last_render_ms")
        self.assertEqual(resolution.captured_last_render_ms, 203542.34375)

    def test_adaptive_timeout_is_bounded_and_invalid_values_use_default(self) -> None:
        self.assertEqual(resolve_proof_timeout(1.0).timeout_seconds, 90.0)
        self.assertEqual(resolve_proof_timeout(900000.0).timeout_seconds, 600.0)
        for value in (None, True, 0, -1, float("inf"), float("nan"), "203542"):
            with self.subTest(value=value):
                resolution = resolve_proof_timeout(value)
                self.assertEqual(resolution.timeout_seconds, 90.0)
                self.assertEqual(resolution.source, "default")

    def test_explicit_timeout_remains_supported_through_the_shared_resolver(self) -> None:
        resolution = resolve_proof_timeout(203542.34375, explicit_timeout_seconds=2.5)

        self.assertEqual(resolution.timeout_seconds, 2.5)
        self.assertEqual(resolution.source, "explicit")
        with self.assertRaisesRegex(ValueError, "finite positive"):
            resolve_proof_timeout(None, explicit_timeout_seconds=math.inf)

    def test_packet_resolution_validates_manifest_and_reads_exact_state(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            packet = Path(temp_dir) / "packet"
            packet.mkdir()
            state_bytes = _json_bytes({"stats": {"last_render_ms": 203542.34375}})
            packet_bytes = b"# packet\n"
            (packet / "state.json").write_bytes(state_bytes)
            (packet / "packet.md").write_bytes(packet_bytes)
            files = [
                {
                    "path": "packet.md",
                    "role": "behavior_and_authority_index",
                    "sha256": hashlib.sha256(packet_bytes).hexdigest(),
                    "size_bytes": len(packet_bytes),
                    "web_handoff": "required",
                },
                {
                    "path": "state.json",
                    "role": "complete_replay_base",
                    "sha256": hashlib.sha256(state_bytes).hexdigest(),
                    "size_bytes": len(state_bytes),
                    "web_handoff": "required",
                },
            ]
            manifest = {
                "packet_version": 6,
                "bundle_manifest_version": 2,
                "packet_id": "packet",
                "finding_id": "finding",
                "selected_fractal_type": "explaino_all",
                "required_attachments": ["packet.md", "state.json"],
                "recommended_attachments": [],
                "unavailable_optional_attachments": [],
                "files": files,
            }
            manifest_bytes = _json_bytes(manifest)
            (packet / "manifest.json").write_bytes(manifest_bytes)
            manifest_sha = hashlib.sha256(manifest_bytes).hexdigest()

            resolution = resolve_packet_proof_timeout(
                packet, expected_manifest_sha256=manifest_sha
            )
            self.assertEqual(resolution.timeout_seconds, 438.0)

            with self.assertRaisesRegex(ValueError, "manifest hash"):
                resolve_packet_proof_timeout(
                    packet, expected_manifest_sha256="0" * 64
                )


if __name__ == "__main__":
    unittest.main()
