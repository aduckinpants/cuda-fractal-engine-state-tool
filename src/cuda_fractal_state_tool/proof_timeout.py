from __future__ import annotations

import hashlib
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .agent_bundle import load_agent_bundle_handoff
from .json_utils import loads_strict_no_duplicates


DEFAULT_PROOF_TIMEOUT_SECONDS = 90.0
MINIMUM_ADAPTIVE_TIMEOUT_SECONDS = 90.0
MAXIMUM_ADAPTIVE_TIMEOUT_SECONDS = 600.0
ADAPTIVE_RENDER_MULTIPLIER = 2.0
ADAPTIVE_OVERHEAD_SECONDS = 30.0


@dataclass(frozen=True)
class ProofTimeoutResolution:
    timeout_seconds: float
    source: str
    captured_last_render_ms: float | None
    default_seconds: float = DEFAULT_PROOF_TIMEOUT_SECONDS
    minimum_seconds: float = MINIMUM_ADAPTIVE_TIMEOUT_SECONDS
    maximum_seconds: float = MAXIMUM_ADAPTIVE_TIMEOUT_SECONDS
    render_multiplier: float = ADAPTIVE_RENDER_MULTIPLIER
    overhead_seconds: float = ADAPTIVE_OVERHEAD_SECONDS

    def to_receipt(self) -> dict[str, Any]:
        return asdict(self)


def _finite_positive_number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    return number if math.isfinite(number) and number > 0.0 else None


def resolve_proof_timeout(
    captured_last_render_ms: Any,
    *,
    explicit_timeout_seconds: float | None = None,
) -> ProofTimeoutResolution:
    captured = _finite_positive_number(captured_last_render_ms)
    if explicit_timeout_seconds is not None:
        explicit = _finite_positive_number(explicit_timeout_seconds)
        if explicit is None:
            raise ValueError("Explicit proof timeout must be a finite positive number")
        return ProofTimeoutResolution(
            timeout_seconds=explicit,
            source="explicit",
            captured_last_render_ms=captured,
        )
    if captured is None:
        return ProofTimeoutResolution(
            timeout_seconds=DEFAULT_PROOF_TIMEOUT_SECONDS,
            source="default",
            captured_last_render_ms=None,
        )
    calculated = (captured / 1000.0) * ADAPTIVE_RENDER_MULTIPLIER + ADAPTIVE_OVERHEAD_SECONDS
    bounded = min(
        MAXIMUM_ADAPTIVE_TIMEOUT_SECONDS,
        max(MINIMUM_ADAPTIVE_TIMEOUT_SECONDS, calculated),
    )
    return ProofTimeoutResolution(
        timeout_seconds=float(math.ceil(bounded)),
        source="captured_last_render_ms",
        captured_last_render_ms=captured,
    )


def resolve_packet_proof_timeout(
    packet_dir: Path,
    *,
    expected_manifest_sha256: str | None = None,
    explicit_timeout_seconds: float | None = None,
) -> ProofTimeoutResolution:
    packet_dir = packet_dir.resolve()
    manifest_path = packet_dir / "manifest.json"
    manifest_bytes = manifest_path.read_bytes()
    manifest_sha256 = hashlib.sha256(manifest_bytes).hexdigest()
    if (
        expected_manifest_sha256 is not None
        and manifest_sha256 != expected_manifest_sha256
    ):
        raise ValueError("Agent-packet manifest hash does not match the bound session")
    load_agent_bundle_handoff(packet_dir)
    try:
        manifest = loads_strict_no_duplicates(manifest_bytes.decode("utf-8"))
    except (UnicodeError, ValueError) as exc:
        raise ValueError("Agent-packet manifest is malformed") from exc
    if not isinstance(manifest, dict) or not isinstance(manifest.get("files"), list):
        raise ValueError("Agent-packet manifest has no files array")
    state_records = [
        record
        for record in manifest["files"]
        if isinstance(record, dict) and record.get("path") == "state.json"
    ]
    if len(state_records) != 1:
        raise ValueError("Agent-packet manifest must identify state.json exactly once")
    state_bytes = (packet_dir / "state.json").read_bytes()
    state_record = state_records[0]
    if (
        hashlib.sha256(state_bytes).hexdigest() != state_record.get("sha256")
        or len(state_bytes) != state_record.get("size_bytes")
    ):
        raise ValueError("Packet state.json changed while resolving proof timeout")
    try:
        state = loads_strict_no_duplicates(state_bytes.decode("utf-8"))
    except (OSError, UnicodeError, ValueError) as exc:
        raise ValueError("Packet state.json is unavailable or malformed") from exc
    if not isinstance(state, dict):
        raise ValueError("Packet state.json is not a JSON object")
    if manifest_path.read_bytes() != manifest_bytes:
        raise ValueError("Agent-packet manifest changed while resolving proof timeout")
    stats = state.get("stats")
    captured_last_render_ms = stats.get("last_render_ms") if isinstance(stats, dict) else None
    return resolve_proof_timeout(
        captured_last_render_ms,
        explicit_timeout_seconds=explicit_timeout_seconds,
    )
