from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .automated_protocol import PacketAuthorityBinding
from .openai_transport import TransportResource


ROUND_REVIEW_LEDGER_VERSION = 1


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
