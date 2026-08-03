from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .automated_protocol import PacketAuthorityBinding
from .agent_bundle import AgentBundle
from .json_utils import loads_strict_no_duplicates
from .openai_transport import TransportResource
from .state_override_proof import compare_image_files


ROUND_REVIEW_LEDGER_VERSION = 1
ROUND_REVIEW_COMPARISON_VERSION = 1


def _json_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n"
    ).encode("utf-8")


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


@dataclass(frozen=True)
class RoundReviewLedger:
    value: dict[str, Any]
    payload: bytes
    sha256: str


@dataclass(frozen=True)
class PacketWebFrame:
    filename: str
    role: str
    sha256: str
    size_bytes: int
    local_path: Path
    payload: bytes


@dataclass(frozen=True)
class RoundReviewComparison:
    value: dict[str, Any]
    payload: bytes
    sha256: str


def load_packet_web_frame(bundle: AgentBundle) -> PacketWebFrame:
    """Select the exact manifest-bound web discussion image from one Packet V8."""
    try:
        manifest_bytes = bundle.manifest_path.read_bytes()
        if _sha256(manifest_bytes) != bundle.manifest_sha256:
            raise ValueError("Packet manifest changed after bundle binding")
        manifest = loads_strict_no_duplicates(manifest_bytes.decode("utf-8"))
    except (OSError, UnicodeError, ValueError) as exc:
        raise ValueError("Packet manifest is unavailable or malformed during review binding") from exc
    if not isinstance(manifest, dict):
        raise ValueError("Packet manifest must be an object during review binding")
    records = manifest.get("files")
    if not isinstance(records, list):
        raise ValueError("Packet manifest has no file records during review binding")
    matches = [
        item
        for item in records
        if isinstance(item, dict) and item.get("role") == "web_discussion_derivative"
    ]
    if len(matches) != 1:
        raise ValueError("Packet must declare exactly one web discussion derivative")
    record = matches[0]
    filename = record.get("path")
    expected_sha = record.get("sha256")
    expected_size = record.get("size_bytes")
    if (
        not isinstance(filename, str)
        or Path(filename).name != filename
        or filename not in bundle.required_attachments
        or not isinstance(expected_sha, str)
        or not isinstance(expected_size, int)
    ):
        raise ValueError("Packet web discussion derivative record is invalid")
    path = bundle.packet_dir / filename
    payload = path.read_bytes()
    if _sha256(payload) != expected_sha or len(payload) != expected_size:
        raise ValueError("Packet web discussion derivative changed after manifest binding")
    return PacketWebFrame(
        filename=filename,
        role="web_discussion_derivative",
        sha256=expected_sha,
        size_bytes=expected_size,
        local_path=path.resolve(),
        payload=payload,
    )


def build_round_review_comparison(
    *,
    round_number: int,
    author_packet: PacketAuthorityBinding,
    derived_packet: PacketAuthorityBinding,
    base_frame: PacketWebFrame,
    result_frame: PacketWebFrame,
    base_frame_path: Path,
    result_frame_path: Path,
    materialization: Any,
    proof: Any,
) -> RoundReviewComparison:
    if round_number < 1:
        raise ValueError("Review comparison round number must be positive")
    if _sha256(base_frame_path.read_bytes()) != base_frame.sha256:
        raise ValueError("Stored review base frame disagrees with packet authority")
    if _sha256(result_frame_path.read_bytes()) != result_frame.sha256:
        raise ValueError("Stored review result frame disagrees with packet authority")
    changed_paths = [item.path for item in materialization.changed_paths]
    value = {
        "round_review_comparison_version": ROUND_REVIEW_COMPARISON_VERSION,
        "round_number": round_number,
        "author_packet": author_packet.to_dict(),
        "derived_packet": derived_packet.to_dict(),
        "base_web_frame": {
            "packet_filename": base_frame.filename,
            "sha256": base_frame.sha256,
            "size_bytes": base_frame.size_bytes,
        },
        "result_web_frame": {
            "packet_filename": result_frame.filename,
            "sha256": result_frame.sha256,
            "size_bytes": result_frame.size_bytes,
        },
        "decoded_pixel_comparison": compare_image_files(base_frame_path, result_frame_path),
        "changed_paths": changed_paths,
        "proof": {
            "proof_id": proof.proof_id,
            "status": proof.status,
            "receipt_sha256": proof.receipt_sha256,
            "engine_candidate_sha256": proof.engine_candidate_sha256,
            "candidate_frame_sha256": proof.candidate_frame_sha256,
            "replay_state_sha256": proof.replay_state_sha256,
            "replay_frame_sha256": proof.replay_frame_sha256,
        },
        "authority_note": (
            "This controller-owned comparison covers the exact transported Packet V8 web "
            "derivatives. Engine state and proof receipts remain domain authority."
        ),
    }
    payload = _json_bytes(value)
    return RoundReviewComparison(value=value, payload=payload, sha256=_sha256(payload))


def build_round_review_ledger(
    *,
    round_number: int,
    author_packet: PacketAuthorityBinding,
    derived_packet: PacketAuthorityBinding,
    author_response_text: str,
    override_text: str,
    materialization: Any,
    proof: Any,
) -> RoundReviewLedger:
    if round_number < 1:
        raise ValueError("Review ledger round number must be positive")
    changed_paths = [
        {
            "path": item.path,
            "conceptual_domain": getattr(item, "conceptual_domain", None),
        }
        for item in materialization.changed_paths
    ]
    value = {
        "round_review_ledger_version": ROUND_REVIEW_LEDGER_VERSION,
        "round_number": round_number,
        "author_packet": author_packet.to_dict(),
        "derived_packet": derived_packet.to_dict(),
        "author_decision_record": {
            "exact_text": author_response_text,
            "sha256": _sha256(author_response_text.encode("utf-8")),
        },
        "state_override": {
            "exact_text": override_text,
            "sha256": _sha256(override_text.encode("utf-8")),
            "changed_paths": changed_paths,
        },
        "proof": {
            "proof_id": proof.proof_id,
            "status": proof.status,
            "message": proof.message,
            "receipt_sha256": proof.receipt_sha256,
            "engine_candidate_sha256": proof.engine_candidate_sha256,
            "candidate_frame_sha256": proof.candidate_frame_sha256,
            "replay_state_sha256": proof.replay_state_sha256,
            "replay_frame_sha256": proof.replay_frame_sha256,
        },
        "authority_note": (
            "The refreshed derived packet is result authority. This ledger is a controller-owned "
            "projection of the exact prior decision, override, and proof; it is not state authority."
        ),
    }
    payload = _json_bytes(value)
    return RoundReviewLedger(value=value, payload=payload, sha256=_sha256(payload))


def ledger_transport_resource(path: Path, ledger: RoundReviewLedger) -> TransportResource:
    return TransportResource(
        filename="round-review-ledger.json",
        role="controller_round_review_ledger",
        media_role="file",
        sha256=ledger.sha256,
        size_bytes=len(ledger.payload),
        local_path=path.resolve(),
        payload=ledger.payload,
    )


def comparison_transport_resource(
    path: Path,
    comparison: RoundReviewComparison,
) -> TransportResource:
    return TransportResource(
        filename="round-review-comparison.json",
        role="controller_round_review_comparison",
        media_role="file",
        sha256=comparison.sha256,
        size_bytes=len(comparison.payload),
        local_path=path.resolve(),
        payload=comparison.payload,
    )


def base_frame_transport_resource(path: Path, frame: PacketWebFrame) -> TransportResource:
    return TransportResource(
        filename="review-base-web-agent-frame.png",
        role="controller_review_base_frame",
        media_role="vision",
        sha256=frame.sha256,
        size_bytes=frame.size_bytes,
        local_path=path.resolve(),
        payload=frame.payload,
    )
