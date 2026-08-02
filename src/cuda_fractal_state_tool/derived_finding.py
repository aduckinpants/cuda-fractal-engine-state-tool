from __future__ import annotations

import hashlib
import json
import os
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .finding_workspace import ImportResult, SourceCaptureImporter
from .json_utils import loads_strict_no_duplicates
from .runtime_surface import sha256_file
from .state_override_proof import StateOverrideProofResult


AUTOMATED_PROMOTION_VERSION = 1


@dataclass(frozen=True)
class DerivedFindingPromotion:
    promotion_dir: Path
    capture_dir: Path
    promotion_receipt_path: Path
    import_result: ImportResult
    source_packet_id: str
    source_proof_id: str


def _json_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n"
    ).encode("utf-8")


def _write_new(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        with temporary.open("xb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        if path.exists():
            raise FileExistsError(f"Immutable derived-finding artifact already exists: {path}")
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _load_object(path: Path, label: str) -> dict[str, Any]:
    try:
        value = loads_strict_no_duplicates(path.read_bytes().decode("utf-8"))
    except (OSError, UnicodeError, ValueError) as exc:
        raise ValueError(f"{label} is unavailable or malformed: {path}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a JSON object: {path}")
    return value


def promote_replay_proven_candidate(
    *,
    proof: StateOverrideProofResult,
    packet_dir: Path,
    workspace_root: Path,
    promotion_dir: Path,
) -> DerivedFindingPromotion:
    """Publish proof-owned state/PNG through the canonical capture importer."""
    packet_dir = packet_dir.resolve()
    workspace_root = workspace_root.resolve()
    promotion_dir = promotion_dir.resolve()
    if promotion_dir.exists():
        raise FileExistsError(f"Derived-finding promotion directory already exists: {promotion_dir}")
    if proof.status != "replay_proven":
        raise ValueError("Only a replay-proven candidate can become an automated derived finding")
    if proof.packet_dir.resolve() != packet_dir or proof.packet_id != packet_dir.name:
        raise ValueError("Proof packet binding disagrees with the requested promotion authority")
    manifest_path = packet_dir / "manifest.json"
    if sha256_file(manifest_path) != proof.packet_manifest_sha256:
        raise ValueError("Packet manifest changed before automated promotion")
    if sha256_file(proof.receipt_path) != proof.receipt_sha256:
        raise ValueError("Proof receipt changed before automated promotion")
    binding_path = proof.proof_dir / "binding.json"
    if sha256_file(binding_path) != proof.binding_sha256:
        raise ValueError("Proof binding changed before automated promotion")
    if proof.engine_candidate_path is None or proof.engine_candidate_sha256 is None:
        raise ValueError("Replay-proven proof has no engine-emitted candidate state")
    if proof.candidate_display_path is None or proof.candidate_display_sha256 is None:
        raise ValueError("Replay-proven proof has no proof-owned candidate PNG")
    if sha256_file(proof.engine_candidate_path) != proof.engine_candidate_sha256:
        raise ValueError("Engine-emitted candidate changed before automated promotion")
    if sha256_file(proof.candidate_display_path) != proof.candidate_display_sha256:
        raise ValueError("Proof-owned candidate PNG changed before automated promotion")

    receipt = _load_object(proof.receipt_path, "State override proof receipt")
    display = (receipt.get("materialization") or {}).get("display_derivative")
    launch_candidate = receipt.get("engine_launch_candidate")
    if (
        receipt.get("proof_id") != proof.proof_id
        or receipt.get("status") != "replay_proven"
        or receipt.get("visual_review") != "pending"
        or receipt.get("launch_ready") is not False
        or not isinstance(display, dict)
        or display.get("decoded_equal") is not True
        or not isinstance(launch_candidate, dict)
        or launch_candidate.get("sha256") != proof.engine_candidate_sha256
        or (receipt.get("binding") or {}).get("packet_manifest_sha256")
        != proof.packet_manifest_sha256
    ):
        raise ValueError("Proof receipt does not authorize exact automated promotion")

    capture_dir = promotion_dir / "capture"
    capture_dir.mkdir(parents=True, exist_ok=False)
    state_bytes = proof.engine_candidate_path.read_bytes()
    display_bytes = proof.candidate_display_path.read_bytes()
    finding_manifest = {
        "finding_schema_version": 1,
        "origin": "automated_replay_proven_candidate",
        "automation_promotion_version": AUTOMATED_PROMOTION_VERSION,
        "human_acceptance": False,
        "lineage": {
            "source_packet_id": proof.packet_id,
            "source_packet_manifest_sha256": proof.packet_manifest_sha256,
            "source_proof_id": proof.proof_id,
            "source_proof_receipt_sha256": proof.receipt_sha256,
            "source_override_text_sha256": proof.override_text_sha256,
            "engine_candidate_sha256": proof.engine_candidate_sha256,
            "candidate_display_sha256": proof.candidate_display_sha256,
        },
    }
    _write_new(capture_dir / "state.json", state_bytes)
    _write_new(capture_dir / "frame.png", display_bytes)
    finding_bytes = _json_bytes(finding_manifest)
    _write_new(capture_dir / "finding.json", finding_bytes)

    imported = SourceCaptureImporter(workspace_root).import_capture(capture_dir)
    if imported.authoring_base_state_sha256 != proof.engine_candidate_sha256:
        raise ValueError("Canonical importer changed the engine-emitted authoring base identity")
    promotion_receipt = {
        "automated_promotion_version": AUTOMATED_PROMOTION_VERSION,
        "status": "promoted_through_canonical_importer",
        "human_acceptance": False,
        "source_packet_id": proof.packet_id,
        "source_packet_manifest_sha256": proof.packet_manifest_sha256,
        "source_proof_id": proof.proof_id,
        "source_proof_receipt_sha256": proof.receipt_sha256,
        "source_override_text_sha256": proof.override_text_sha256,
        "capture_artifacts": {
            "state.json": {
                "sha256": hashlib.sha256(state_bytes).hexdigest(),
                "size_bytes": len(state_bytes),
            },
            "frame.png": {
                "sha256": hashlib.sha256(display_bytes).hexdigest(),
                "size_bytes": len(display_bytes),
                "source": "proof-owned materialization/candidate-display.png",
            },
            "finding.json": {
                "sha256": hashlib.sha256(finding_bytes).hexdigest(),
                "size_bytes": len(finding_bytes),
            },
        },
        "imported_finding": {
            "finding_id": imported.finding_id,
            "finding_dir": str(imported.finding_dir),
            "authoring_base_state_sha256": imported.authoring_base_state_sha256,
        },
    }
    promotion_receipt_path = promotion_dir / "receipt.json"
    _write_new(promotion_receipt_path, _json_bytes(promotion_receipt))
    return DerivedFindingPromotion(
        promotion_dir=promotion_dir,
        capture_dir=capture_dir,
        promotion_receipt_path=promotion_receipt_path,
        import_result=imported,
        source_packet_id=proof.packet_id,
        source_proof_id=proof.proof_id,
    )
