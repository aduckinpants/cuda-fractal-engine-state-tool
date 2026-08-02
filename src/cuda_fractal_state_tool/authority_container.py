from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


AUTHORITY_CONTAINER_VERSION = 1

_CONTAINER_MARKER = b"<!-- CFST_AUTHORITY_CONTAINER_V1 -->"
_CONTAINER_LINE_PATTERN = re.compile(
    rb"^<!-- CFST_AUTHORITY_CONTAINER_V1 -->$", re.MULTILINE
)
_BEGIN_PREFIX = b"<!-- CFST_AUTHORITY_RECORD_V1_BEGIN "
_END_PREFIX = "<!-- CFST_AUTHORITY_RECORD_V1_END "
_BEGIN_PATTERN = re.compile(
    rb"^<!-- CFST_AUTHORITY_RECORD_V1_BEGIN (?P<metadata>\{[^\r\n]*\}) -->$",
    re.MULTILINE,
)
_BEGIN_LINE_PATTERN = re.compile(
    rb"^<!-- CFST_AUTHORITY_RECORD_V1_BEGIN .*$", re.MULTILINE
)
_END_LINE_PATTERN = re.compile(
    rb"^<!-- CFST_AUTHORITY_RECORD_V1_END .*$", re.MULTILINE
)
_METADATA_KEYS = {
    "artifact_filename",
    "authority_role",
    "byte_length",
    "encoding",
    "fence",
    "language",
    "media_type",
    "record_id",
    "sha256",
}


@dataclass(frozen=True)
class AuthorityArtifact:
    filename: str
    role: str
    media_type: str
    payload: bytes


@dataclass(frozen=True)
class EmbeddedAuthority:
    filename: str
    role: str
    media_type: str
    encoding: str
    byte_length: int
    sha256: str
    fence: str
    record_id: str
    payload: bytes


@dataclass(frozen=True)
class ParsedAuthorityContainer:
    version: int
    artifacts: dict[str, EmbeddedAuthority]


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _language_for_media_type(media_type: str) -> str:
    return {
        "application/json": "json",
        "text/markdown": "markdown",
        "text/plain": "text",
    }.get(media_type, "text")


def _validate_filename(filename: str) -> None:
    if (
        not filename
        or Path(filename).name != filename
        or "/" in filename
        or "\\" in filename
        or filename in {".", ".."}
    ):
        raise ValueError(f"Authority artifact filename must be a safe base filename: {filename!r}")


def _select_fence(text: str) -> str:
    longest = 0
    for run in re.findall(r"`+", text):
        longest = max(longest, len(run))
    return "`" * max(3, longest + 1)


def _record_id(filename: str, role: str, media_type: str, payload: bytes) -> str:
    identity = (
        filename.encode("utf-8")
        + b"\x00"
        + role.encode("utf-8")
        + b"\x00"
        + media_type.encode("utf-8")
        + b"\x00"
        + payload
    )
    return _sha256(identity)


def _metadata_bytes(metadata: dict[str, object]) -> bytes:
    return json.dumps(
        metadata,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")


def encode_authority_container(
    title: str,
    introduction: str,
    artifacts: Iterable[AuthorityArtifact],
) -> bytes:
    """Encode exact UTF-8 authority bytes inside a deterministic Markdown container."""

    artifact_list = tuple(artifacts)
    seen: set[str] = set()
    for artifact in artifact_list:
        _validate_filename(artifact.filename)
        if artifact.filename in seen:
            raise ValueError(f"Authority container has duplicate artifact filename: {artifact.filename}")
        seen.add(artifact.filename)
        if not artifact.role.strip() or not artifact.media_type.strip():
            raise ValueError(f"Authority artifact role and media type are required: {artifact.filename}")
        try:
            artifact.payload.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError(f"Authority artifact {artifact.filename} is not valid UTF-8") from exc

    prefix = (
        f"# {title}\n\n"
        f"{introduction.rstrip()}\n\n"
        f"{_CONTAINER_MARKER.decode('ascii')}\n\n"
    ).encode("utf-8")
    output = bytearray(prefix)
    for artifact in artifact_list:
        text = artifact.payload.decode("utf-8")
        fence = _select_fence(text)
        language = _language_for_media_type(artifact.media_type)
        record_id = _record_id(
            artifact.filename, artifact.role, artifact.media_type, artifact.payload
        )
        metadata = {
            "artifact_filename": artifact.filename,
            "authority_role": artifact.role,
            "byte_length": len(artifact.payload),
            "encoding": "utf-8",
            "fence": fence,
            "language": language,
            "media_type": artifact.media_type,
            "record_id": record_id,
            "sha256": _sha256(artifact.payload),
        }
        output.extend(_BEGIN_PREFIX)
        output.extend(_metadata_bytes(metadata))
        output.extend(b" -->\n")
        output.extend(f"{fence}{language}\n".encode("ascii"))
        output.extend(artifact.payload)
        output.extend(b"\n")
        output.extend(fence.encode("ascii"))
        output.extend(b"\n")
        output.extend(f"{_END_PREFIX}{record_id} -->\n\n".encode("ascii"))
    return bytes(output)


def _decode_metadata(payload: bytes) -> dict[str, object]:
    try:
        value = json.loads(payload.decode("ascii"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("Authority-container record metadata is malformed") from exc
    if not isinstance(value, dict) or set(value) != _METADATA_KEYS:
        raise ValueError("Authority-container record has invalid metadata fields")
    return value


def parse_authority_container(
    payload: bytes,
    *,
    expected_filenames: set[str] | None = None,
) -> ParsedAuthorityContainer:
    """Parse a V1 container without granting authority to ordinary Markdown prose."""

    try:
        payload.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("Authority container is not valid UTF-8") from exc
    container_match = _CONTAINER_LINE_PATTERN.search(payload)
    if container_match is None:
        raise ValueError("Authority container has no valid V1 marker")

    artifacts: dict[str, EmbeddedAuthority] = {}
    cursor = container_match.end()
    while True:
        match = _BEGIN_PATTERN.search(payload, cursor)
        prose_end = match.start() if match is not None else len(payload)
        prose = payload[cursor:prose_end]
        if _CONTAINER_LINE_PATTERN.search(prose):
            raise ValueError("Authority container contains more than one V1 marker")
        if _BEGIN_LINE_PATTERN.search(prose):
            raise ValueError("Authority container has a malformed record begin marker")
        if _END_LINE_PATTERN.search(prose):
            raise ValueError("Authority container has an unmatched or malformed end marker")
        if match is None:
            break
        metadata = _decode_metadata(match.group("metadata"))
        filename = metadata["artifact_filename"]
        role = metadata["authority_role"]
        media_type = metadata["media_type"]
        encoding = metadata["encoding"]
        byte_length = metadata["byte_length"]
        sha256 = metadata["sha256"]
        fence = metadata["fence"]
        language = metadata["language"]
        record_id = metadata["record_id"]
        if not all(
            isinstance(item, str)
            for item in (filename, role, media_type, encoding, sha256, fence, language, record_id)
        ):
            raise ValueError("Authority-container record metadata has invalid value types")
        assert isinstance(filename, str)
        assert isinstance(role, str)
        assert isinstance(media_type, str)
        assert isinstance(encoding, str)
        assert isinstance(sha256, str)
        assert isinstance(fence, str)
        assert isinstance(language, str)
        assert isinstance(record_id, str)
        _validate_filename(filename)
        if filename in artifacts:
            raise ValueError(f"Authority container has duplicate embedded artifact: {filename}")
        if encoding != "utf-8":
            raise ValueError(f"Authority artifact {filename} has unsupported encoding")
        if isinstance(byte_length, bool) or not isinstance(byte_length, int) or byte_length < 0:
            raise ValueError(f"Authority artifact {filename} has invalid byte length")
        if not re.fullmatch(r"[0-9a-f]{64}", sha256):
            raise ValueError(f"Authority artifact {filename} has invalid SHA-256")
        if not re.fullmatch(r"`{3,}", fence):
            raise ValueError(f"Authority artifact {filename} has invalid dynamic fence")
        if language != _language_for_media_type(media_type):
            raise ValueError(f"Authority artifact {filename} media type and fence language disagree")

        open_line_start = match.end() + 1
        if match.end() >= len(payload) or payload[match.end() : match.end() + 1] != b"\n":
            raise ValueError(f"Authority artifact {filename} begin marker is not line terminated")
        open_line_end = payload.find(b"\n", open_line_start)
        if open_line_end < 0:
            raise ValueError(f"Authority artifact {filename} is truncated before its opening fence")
        expected_open = f"{fence}{language}".encode("ascii")
        if payload[open_line_start:open_line_end] != expected_open:
            raise ValueError(f"Authority artifact {filename} has an invalid opening fence")

        artifact_start = open_line_end + 1
        artifact_end = artifact_start + byte_length
        if artifact_end > len(payload):
            raise ValueError(f"Authority artifact {filename} has a truncated payload boundary")
        artifact_payload = payload[artifact_start:artifact_end]
        if fence.encode("ascii") in artifact_payload:
            raise ValueError(f"Authority artifact {filename} has an ambiguous dynamic fence")
        if _sha256(artifact_payload) != sha256:
            raise ValueError(f"Authority artifact {filename} SHA-256 mismatch")
        expected_record_id = _record_id(filename, role, media_type, artifact_payload)
        if record_id != expected_record_id:
            raise ValueError(f"Authority artifact {filename} record identity is invalid")
        try:
            artifact_payload.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError(f"Authority artifact {filename} is not valid UTF-8") from exc

        close_and_end = (
            b"\n"
            + fence.encode("ascii")
            + b"\n"
            + f"{_END_PREFIX}{record_id} -->\n".encode("ascii")
        )
        if payload[artifact_end : artifact_end + len(close_and_end)] != close_and_end:
            raise ValueError(
                f"Authority artifact {filename} payload boundary, closing fence, or end marker is invalid"
            )
        artifacts[filename] = EmbeddedAuthority(
            filename=filename,
            role=role,
            media_type=media_type,
            encoding=encoding,
            byte_length=byte_length,
            sha256=sha256,
            fence=fence,
            record_id=record_id,
            payload=artifact_payload,
        )
        cursor = artifact_end + len(close_and_end)
    if expected_filenames is not None:
        actual = set(artifacts)
        missing = sorted(expected_filenames - actual)
        unknown = sorted(actual - expected_filenames)
        if missing:
            raise ValueError(
                "Authority container is missing expected embedded artifacts: "
                + ", ".join(missing)
            )
        if unknown:
            raise ValueError(
                "Authority container contains unknown embedded artifacts: "
                + ", ".join(unknown)
            )
    return ParsedAuthorityContainer(
        version=AUTHORITY_CONTAINER_VERSION,
        artifacts=artifacts,
    )
