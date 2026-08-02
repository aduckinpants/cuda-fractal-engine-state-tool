from __future__ import annotations

import json
import unittest

from cuda_fractal_state_tool.authority_container import (
    AuthorityArtifact,
    encode_authority_container,
    parse_authority_container,
)


class AuthorityContainerTests(unittest.TestCase):
    def _artifacts(self) -> tuple[AuthorityArtifact, ...]:
        return (
            AuthorityArtifact(
                filename="surface.json",
                role="finding-specific authoring index",
                media_type="application/json",
                payload=b'{"value": 1}',
            ),
            AuthorityArtifact(
                filename="notes.md",
                role="user context",
                media_type="text/markdown",
                payload=(
                    b"no trailing newline and marker-like prose "
                    b"<!-- CFST_AUTHORITY_RECORD_V1_BEGIN --> plus ```` ticks"
                ),
            ),
        )

    def test_exact_utf8_round_trip_and_declared_records(self) -> None:
        artifacts = self._artifacts()
        encoded = encode_authority_container(
            title="State Authoring Authorities",
            introduction="Navigation prose is not authority.",
            artifacts=artifacts,
        )
        parsed = parse_authority_container(
            encoded,
            expected_filenames={artifact.filename for artifact in artifacts},
        )

        self.assertEqual(parsed.version, 1)
        self.assertEqual(tuple(parsed.artifacts), ("surface.json", "notes.md"))
        for artifact in artifacts:
            record = parsed.artifacts[artifact.filename]
            self.assertEqual(record.payload, artifact.payload)
            self.assertEqual(record.byte_length, len(artifact.payload))
            self.assertEqual(record.encoding, "utf-8")
            self.assertEqual(record.role, artifact.role)
            self.assertEqual(record.media_type, artifact.media_type)
            self.assertEqual(len(record.sha256), 64)
            self.assertNotIn(record.fence.encode("ascii"), artifact.payload)

    def test_navigation_prose_does_not_create_authority(self) -> None:
        encoded = encode_authority_container(
            title="Container",
            introduction=(
                "The words fake.json and ```json are explanatory only. "
                "<!-- CFST_AUTHORITY_RECORD_V1_BEGIN --> is also prose."
            ),
            artifacts=(self._artifacts()[0],),
        )
        parsed = parse_authority_container(encoded, expected_filenames={"surface.json"})
        self.assertEqual(set(parsed.artifacts), {"surface.json"})

    def test_marker_shaped_payload_is_opaque_not_a_nested_authority(self) -> None:
        nested = encode_authority_container(
            "Nested",
            "This entire container is payload, not a child authority.",
            (self._artifacts()[0],),
        )
        outer = encode_authority_container(
            "Outer",
            "Only the outer record is authoritative.",
            (
                AuthorityArtifact(
                    filename="nested.md",
                    role="opaque text fixture",
                    media_type="text/markdown",
                    payload=nested,
                ),
            ),
        )
        parsed = parse_authority_container(outer, expected_filenames={"nested.md"})
        self.assertEqual(parsed.artifacts["nested.md"].payload, nested)

    def test_encode_rejects_duplicate_unsafe_or_non_utf8_artifacts(self) -> None:
        artifact = self._artifacts()[0]
        with self.assertRaisesRegex(ValueError, "duplicate"):
            encode_authority_container("Title", "Intro", (artifact, artifact))
        with self.assertRaisesRegex(ValueError, "safe base filename"):
            encode_authority_container(
                "Title",
                "Intro",
                (
                    AuthorityArtifact(
                        filename="../escape.json",
                        role="bad",
                        media_type="application/json",
                        payload=b"{}",
                    ),
                ),
            )
        with self.assertRaisesRegex(ValueError, "valid UTF-8"):
            encode_authority_container(
                "Title",
                "Intro",
                (
                    AuthorityArtifact(
                        filename="bad.json",
                        role="bad",
                        media_type="application/json",
                        payload=b"\xff",
                    ),
                ),
            )

    def test_parse_rejects_missing_and_unknown_records(self) -> None:
        encoded = encode_authority_container("Title", "Intro", self._artifacts())
        with self.assertRaisesRegex(ValueError, "missing expected embedded artifacts"):
            parse_authority_container(
                encoded,
                expected_filenames={"surface.json", "notes.md", "missing.json"},
            )
        with self.assertRaisesRegex(ValueError, "unknown embedded artifacts"):
            parse_authority_container(encoded, expected_filenames={"surface.json"})

    def test_parse_rejects_truncation_hash_length_fence_and_metadata_tampering(self) -> None:
        encoded = encode_authority_container(
            "Title", "Intro", (self._artifacts()[0],)
        )
        cases: list[tuple[bytes, str]] = [
            (encoded[:-20], "truncated|end marker"),
            (encoded.replace(b'{"value": 1}', b'{"value": 2}', 1), "SHA-256"),
        ]

        marker = b"<!-- CFST_AUTHORITY_RECORD_V1_BEGIN "
        marker_start = encoded.index(marker) + len(marker)
        marker_end = encoded.index(b" -->", marker_start)
        metadata = json.loads(encoded[marker_start:marker_end].decode("ascii"))

        wrong_length = dict(metadata)
        wrong_length["byte_length"] += 1
        cases.append(
            (
                encoded[:marker_start]
                + json.dumps(wrong_length, sort_keys=True, separators=(",", ":")).encode("ascii")
                + encoded[marker_end:],
                "payload boundary|closing fence|SHA-256",
            )
        )

        unknown_metadata = dict(metadata)
        unknown_metadata["surprise"] = True
        cases.append(
            (
                encoded[:marker_start]
                + json.dumps(unknown_metadata, sort_keys=True, separators=(",", ":")).encode("ascii")
                + encoded[marker_end:],
                "metadata fields",
            )
        )

        fence = metadata["fence"].encode("ascii")
        payload_start = encoded.index(b"\n", marker_end + 4) + 1
        payload_start = encoded.index(b"\n", payload_start) + 1
        ambiguous = encoded[:payload_start] + fence + encoded[payload_start:]
        cases.append((ambiguous, "ambiguous|payload boundary|SHA-256"))

        for payload, message in cases:
            with self.subTest(message=message):
                with self.assertRaisesRegex(ValueError, message):
                    parse_authority_container(payload)

    def test_parse_rejects_duplicate_record_names(self) -> None:
        encoded = encode_authority_container(
            "Title", "Intro", (self._artifacts()[0],)
        )
        marker = b"<!-- CFST_AUTHORITY_RECORD_V1_BEGIN "
        start = encoded.index(marker)
        duplicated = encoded + b"\n" + encoded[start:]
        with self.assertRaisesRegex(ValueError, "duplicate embedded artifact"):
            parse_authority_container(duplicated)


if __name__ == "__main__":
    unittest.main()
