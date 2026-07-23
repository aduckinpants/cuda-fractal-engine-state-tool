from __future__ import annotations

import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import threading
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional, Sequence

from PIL import Image, ImageChops, ImageStat

from .agent_bundle import SUPPORTED_PACKET_MANIFEST_VERSIONS, load_agent_bundle_handoff
from .async_jobs import AsyncJobRunner, JobCancelledError, JobContext, JobRequestIdentity
from .json_utils import loads_strict_no_duplicates
from .runtime_surface import (
    build_detached_viewer_launch_command,
    build_materialization_command,
    build_replay_command,
    build_runtime_identity,
    runtime_identity_summary,
    runtime_identity_summary_sha256,
    sha256_file,
)
from .state_compare import compare_json_documents
from .state_override import StateOverrideMaterialization, materialize_state_override


PROOF_RECEIPT_VERSION = 2
REVIEW_DECISION_VERSION = 1
LAUNCH_RECEIPT_VERSION = 2
_PATH_PART = re.compile(r"([^.[\]]+)|\[(\d+)\]")


@dataclass(frozen=True)
class StateOverrideProofResult:
    status: str
    proof_id: str
    message: str
    proof_dir: Path
    receipt_path: Path
    receipt_sha256: str
    binding_sha256: str
    packet_dir: Path
    packet_id: str
    packet_manifest_sha256: str
    override_text_sha256: str
    merged_candidate_path: Path
    merged_candidate_sha256: str
    engine_candidate_path: Optional[Path] = None
    engine_candidate_sha256: Optional[str] = None
    candidate_frame_path: Optional[Path] = None
    candidate_frame_sha256: Optional[str] = None
    replay_state_path: Optional[Path] = None
    replay_state_sha256: Optional[str] = None
    replay_frame_path: Optional[Path] = None
    replay_frame_sha256: Optional[str] = None
    empty_override_byte_exact: bool = False


class StateOverrideProofError(ValueError):
    pass


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _json_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n"
    ).encode("utf-8")


def _atomic_write(path: Path, payload: bytes) -> None:
    if path.exists():
        raise FileExistsError(f"Immutable proof artifact already exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp.{uuid.uuid4().hex}")
    try:
        with temporary.open("xb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(str(temporary), str(path))
    finally:
        if temporary.exists():
            temporary.unlink()


def _atomic_write_json(path: Path, value: Any) -> None:
    _atomic_write(path, _json_bytes(value))


def _load_object(path: Path, label: str) -> dict[str, Any]:
    try:
        value = loads_strict_no_duplicates(path.read_bytes().decode("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        raise StateOverrideProofError(f"{label} is not valid strict UTF-8 JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise StateOverrideProofError(f"{label} must be a JSON object")
    return value


def _packet_manifest(packet_dir: Path, expected_sha256: str | None) -> tuple[dict[str, Any], str]:
    load_agent_bundle_handoff(packet_dir)
    manifest_path = packet_dir / "manifest.json"
    manifest_sha256 = sha256_file(manifest_path)
    if expected_sha256 is not None and manifest_sha256 != expected_sha256:
        raise StateOverrideProofError("Packet manifest hash does not match the active binding")
    manifest = _load_object(manifest_path, "Agent packet manifest")
    packet_version = manifest.get("packet_version")
    expected_manifest_version = SUPPORTED_PACKET_MANIFEST_VERSIONS.get(packet_version)
    if expected_manifest_version is None:
        raise StateOverrideProofError(f"Unsupported packet version: {packet_version}")
    if manifest.get("bundle_manifest_version") != expected_manifest_version:
        raise StateOverrideProofError(
            f"Unsupported Packet V{packet_version} manifest version"
        )
    records = manifest.get("files")
    recorded = {
        record.get("path")
        for record in records
        if isinstance(record, dict) and isinstance(record.get("path"), str)
    } if isinstance(records, list) else set()
    required_authorities = {
        "packet.md",
        "state.json",
        "fractal-parameter-surface.json",
        "fractal_binding_surface_v1.ui_schema.json",
        "color_pipeline_function_library.contract.v1.json",
        "fractal-descriptive-catalog.json",
        "fractal-viewport-facts.json",
        "state-override-authoring-surface.json",
    }
    missing = sorted(required_authorities - recorded)
    if missing:
        raise StateOverrideProofError(
            f"Packet V{packet_version} is missing required authority files: {', '.join(missing)}"
        )
    return manifest, manifest_sha256


def _validate_runtime_binding(
    manifest: dict[str, Any], runtime_cmd_path: Path
) -> tuple[dict[str, Any], dict[str, Any], str]:
    identity = build_runtime_identity(runtime_cmd_path.resolve(), runtime_cmd_path.resolve().parent)
    summary = runtime_identity_summary(identity)
    expected_summary = manifest.get("runtime_identity")
    expected_hash = manifest.get("runtime_identity_sha256")
    actual_hash = runtime_identity_summary_sha256(summary)
    if summary != expected_summary or actual_hash != expected_hash:
        raise StateOverrideProofError("Published runtime identity differs from the immutable Packet V6 binding")
    return identity, summary, actual_hash


def _resolve_path(document: Any, path: str) -> tuple[bool, Any]:
    current = document
    consumed = "".join(match.group(0) for match in _PATH_PART.finditer(path))
    if consumed.replace(".", "") != path.replace(".", ""):
        return False, None
    for match in _PATH_PART.finditer(path):
        key, index_text = match.groups()
        if key is not None:
            if not isinstance(current, dict) or key not in current:
                return False, None
            current = current[key]
        else:
            index = int(index_text)
            if not isinstance(current, list) or index >= len(current):
                return False, None
            current = current[index]
    return True, current


def _numeric(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value))


def _requested_value_receipts(
    materialization: StateOverrideMaterialization,
    emitted: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[str]]:
    receipts: list[dict[str, Any]] = []
    errors: list[str] = []
    for change in materialization.changed_paths:
        present, emitted_value = _resolve_path(emitted, change.path)
        classification = "survived"
        if not present:
            classification = "missing"
        elif emitted_value == change.merged_value:
            classification = "survived"
        elif emitted_value == change.base_value:
            classification = "reverted"
        elif _numeric(emitted_value) and _numeric(change.merged_value) and math.isclose(
            float(emitted_value), float(change.merged_value), rel_tol=1e-6, abs_tol=1e-9
        ):
            classification = "representation_normalization"
        else:
            classification = "contradicted"
        receipt = {
            "path": change.path,
            "conceptual_domain": change.conceptual_domain,
            "base_value": change.base_value,
            "requested_value": change.merged_value,
            "engine_emitted_value": emitted_value if present else None,
            "classification": classification,
        }
        receipts.append(receipt)
        if classification in {"missing", "reverted", "contradicted"}:
            errors.append(
                f"Engine {classification} requested value at {change.path}: "
                f"requested {change.merged_value!r}, emitted {emitted_value!r}"
            )
    return receipts, errors


def _image_fingerprint(path: Path) -> dict[str, Any]:
    with Image.open(path) as image:
        image.load()
        rgba = image.convert("RGBA")
        return {
            "encoded_sha256": sha256_file(path),
            "decoded_rgba_sha256": hashlib.sha256(rgba.tobytes()).hexdigest(),
            "width": rgba.width,
            "height": rgba.height,
        }


def _image_comparison(left_path: Path, right_path: Path) -> dict[str, Any]:
    left_fp = _image_fingerprint(left_path)
    right_fp = _image_fingerprint(right_path)
    with Image.open(left_path) as left_image, Image.open(right_path) as right_image:
        left = left_image.convert("RGBA")
        right = right_image.convert("RGBA")
        if left.size != right.size:
            return {"left": left_fp, "right": right_fp, "decoded_equal": False, "size_mismatch": True}
        difference = ImageChops.difference(left, right)
        means = ImageStat.Stat(difference).mean
    return {
        "left": left_fp,
        "right": right_fp,
        "decoded_equal": left_fp["decoded_rgba_sha256"] == right_fp["decoded_rgba_sha256"],
        "encoded_equal": left_fp["encoded_sha256"] == right_fp["encoded_sha256"],
        "mean_absolute_channel_difference": means,
    }


def _manifest_file_with_role(manifest: dict[str, Any], role: str) -> str | None:
    files = manifest.get("files")
    if not isinstance(files, list):
        return None
    matches = [
        entry.get("path")
        for entry in files
        if isinstance(entry, dict) and entry.get("role") == role and isinstance(entry.get("path"), str)
    ]
    return matches[0] if len(matches) == 1 else None


def _process_receipt(result: Any, command: Sequence[str]) -> dict[str, Any]:
    return {
        "command": list(command),
        "cwd": result.cwd,
        "pid": result.pid,
        "exit_code": result.exit_code,
        "timed_out": result.timed_out,
        "elapsed_seconds": result.elapsed_seconds,
        "stdout_path": "stdout.txt",
        "stderr_path": "stderr.txt",
    }


def _run_capture(
    job: JobContext,
    runtime_cmd_path: Path,
    state_path: Path,
    output_dir: Path,
    timeout_seconds: float,
    *,
    apply_loaded_draft: bool = False,
) -> tuple[Any, list[str]]:
    if apply_loaded_draft:
        command = build_materialization_command(
            runtime_cmd_path.resolve(),
            state_path.resolve(),
            output_dir.resolve(),
            apply_loaded_draft=True,
        )
    else:
        command = build_replay_command(
            runtime_cmd_path.resolve(), state_path.resolve(), output_dir.resolve()
        )
    result = job.run_process(command, runtime_cmd_path.resolve().parent, timeout_seconds=timeout_seconds)
    _atomic_write(output_dir / "stdout.txt", result.stdout.encode("utf-8"))
    _atomic_write(output_dir / "stderr.txt", result.stderr.encode("utf-8"))
    _atomic_write_json(output_dir / "process.json", _process_receipt(result, command))
    return result, command


def _runtime_attempt_receipt(result: Any, output_dir: Path, command: list[str]) -> dict[str, Any]:
    expected = (output_dir / "state.json", output_dir / "frame.bmp")
    return {
        "process_receipt": str((output_dir / "process.json").name),
        "command": command,
        "exit_code": result.exit_code,
        "timed_out": result.timed_out,
        "stdout_path": "stdout.txt",
        "stderr_path": "stderr.txt",
        "missing_artifacts": [path.name for path in expected if not path.is_file()],
    }


def _runtime_failure_detail(result: Any, output_dir: Path) -> str:
    details: list[str] = []
    if result.timed_out:
        details.append("timed out")
    if result.exit_code is not None and result.exit_code != 0:
        details.append(f"exit code {result.exit_code}")
    missing = [name for name in ("state.json", "frame.bmp") if not (output_dir / name).is_file()]
    if missing:
        details.append(f"missing artifacts: {', '.join(missing)}")
    diagnostic = result.stderr.strip() or result.stdout.strip()
    details.append(diagnostic if diagnostic else "runtime emitted no stdout or stderr")
    return "; ".join(details)


def _proof_result(
    *,
    status: str,
    proof_id: str,
    message: str,
    proof_dir: Path,
    packet_dir: Path,
    packet_id: str,
    manifest_sha256: str,
    override_sha256: str,
    merged_path: Path,
    merged_sha256: str,
    engine_state: Path | None = None,
    engine_frame: Path | None = None,
    replay_state: Path | None = None,
    replay_frame: Path | None = None,
    empty_override_byte_exact: bool = False,
) -> StateOverrideProofResult:
    return StateOverrideProofResult(
        status=status,
        proof_id=proof_id,
        message=message,
        proof_dir=proof_dir.resolve(),
        receipt_path=(proof_dir / "receipt.json").resolve(),
        receipt_sha256=sha256_file(proof_dir / "receipt.json") if (proof_dir / "receipt.json").is_file() else "",
        binding_sha256=sha256_file(proof_dir / "binding.json") if (proof_dir / "binding.json").is_file() else "",
        packet_dir=packet_dir.resolve(),
        packet_id=packet_id,
        packet_manifest_sha256=manifest_sha256,
        override_text_sha256=override_sha256,
        merged_candidate_path=merged_path.resolve(),
        merged_candidate_sha256=merged_sha256,
        engine_candidate_path=engine_state.resolve() if engine_state and engine_state.is_file() else None,
        engine_candidate_sha256=sha256_file(engine_state) if engine_state and engine_state.is_file() else None,
        candidate_frame_path=engine_frame.resolve() if engine_frame and engine_frame.is_file() else None,
        candidate_frame_sha256=sha256_file(engine_frame) if engine_frame and engine_frame.is_file() else None,
        replay_state_path=replay_state.resolve() if replay_state and replay_state.is_file() else None,
        replay_state_sha256=sha256_file(replay_state) if replay_state and replay_state.is_file() else None,
        replay_frame_path=replay_frame.resolve() if replay_frame and replay_frame.is_file() else None,
        replay_frame_sha256=sha256_file(replay_frame) if replay_frame and replay_frame.is_file() else None,
        empty_override_byte_exact=empty_override_byte_exact,
    )


def execute_state_override_proof(
    packet_dir: Path,
    override_text: str,
    runtime_cmd_path: Path,
    job: JobContext,
    *,
    proofs_root: Path | None = None,
    expected_manifest_sha256: str | None = None,
    timeout_seconds: float = 90.0,
) -> StateOverrideProofResult:
    packet_dir = packet_dir.resolve()
    runtime_cmd_path = runtime_cmd_path.resolve()
    proof_id = str(uuid.uuid4())
    if proofs_root is None:
        if packet_dir.parent.name != "packets":
            raise StateOverrideProofError("Packet V6 directory is not beneath a finding packets directory")
        proofs_root = packet_dir.parent.parent / "proofs"
    proof_dir = proofs_root.resolve() / proof_id
    proof_dir.mkdir(parents=True, exist_ok=False)
    override_bytes = override_text.encode("utf-8")
    override_sha256 = _sha256_bytes(override_bytes)
    _atomic_write(proof_dir / "override.json", override_bytes)
    merged_path = proof_dir / "merged_candidate.json"
    packet_id = packet_dir.name
    manifest_sha256 = ""
    binding: dict[str, Any] = {
        "proof_id": proof_id,
        "packet_dir": str(packet_dir),
        "packet_id": packet_id,
        "override_text_sha256": override_sha256,
    }
    runtime_identity: dict[str, Any] | None = None
    materialization: StateOverrideMaterialization | None = None
    runtime_attempts: dict[str, Any] = {}
    materialization_dir = proof_dir / "materialization"
    replay_dir = proof_dir / "replay"
    materialization_dir.mkdir()
    replay_dir.mkdir()

    def rejected(errors: list[str]) -> StateOverrideProofResult:
        binding_path = proof_dir / "binding.json"
        if not binding_path.exists():
            _atomic_write_json(binding_path, binding)
        receipt = {
            "proof_receipt_version": PROOF_RECEIPT_VERSION,
            "proof_id": proof_id,
            "status": "rejected",
            "created_at_utc": _utc_now(),
            "binding": binding,
            "runtime_identity": runtime_identity,
            "errors": errors,
            "runtime_attempts": runtime_attempts,
            "visual_review": "not_available",
            "launch_ready": False,
        }
        _atomic_write_json(proof_dir / "receipt.json", receipt)
        return _proof_result(
            status="rejected",
            proof_id=proof_id,
            message="; ".join(errors),
            proof_dir=proof_dir,
            packet_dir=packet_dir,
            packet_id=packet_id,
            manifest_sha256=manifest_sha256,
            override_sha256=override_sha256,
            merged_path=merged_path,
            merged_sha256=sha256_file(merged_path) if merged_path.is_file() else "",
            engine_state=materialization_dir / "state.json",
            engine_frame=materialization_dir / "frame.bmp",
            replay_state=replay_dir / "state.json",
            replay_frame=replay_dir / "frame.bmp",
        )

    try:
        manifest, manifest_sha256 = _packet_manifest(packet_dir, expected_manifest_sha256)
        packet_id = manifest.get("packet_id")
        if not isinstance(packet_id, str) or packet_id != packet_dir.name:
            raise StateOverrideProofError("Packet ID does not match its immutable directory name")
        runtime_identity, runtime_summary, runtime_sha256 = _validate_runtime_binding(manifest, runtime_cmd_path)
        authority_identities = manifest.get("authority_identities")
        if not isinstance(authority_identities, dict):
            raise StateOverrideProofError("Packet V6 manifest has no authority identities")
        binding.update(
            {
                "packet_id": packet_id,
                "packet_manifest_sha256": manifest_sha256,
                "packet_markdown_sha256": sha256_file(packet_dir / "packet.md"),
                "finding_id": manifest.get("finding_id"),
                "base_state_sha256": authority_identities.get("state_sha256"),
                "runtime_identity_sha256": runtime_sha256,
                "authority_identities": authority_identities,
            }
        )
        _atomic_write_json(proof_dir / "binding.json", binding)
        materialization = materialize_state_override(
            packet_dir,
            override_text,
            merged_path,
            expected_manifest_sha256=manifest_sha256,
        )
        if materialization.base_state_sha256 != authority_identities.get("state_sha256"):
            raise StateOverrideProofError("Merged candidate base hash differs from the packet authority binding")
    except JobCancelledError:
        raise
    except Exception as exc:
        return rejected([str(exc)])


    try:
        materialization_result, materialization_command = _run_capture(
            job,
            runtime_cmd_path,
            merged_path,
            materialization_dir,
            timeout_seconds,
            apply_loaded_draft=materialization.apply_loaded_color_pipeline_draft,
        )
        runtime_attempts["materialization"] = _runtime_attempt_receipt(
            materialization_result, materialization_dir, materialization_command
        )
        engine_state = materialization_dir / "state.json"
        engine_frame = materialization_dir / "frame.bmp"
        if (
            materialization_result.timed_out
            or materialization_result.exit_code != 0
            or not engine_state.is_file()
            or not engine_frame.is_file()
        ):
            detail = _runtime_failure_detail(materialization_result, materialization_dir)
            return rejected([f"Direct-state engine materialization failed: {detail}"])
        emitted = _load_object(engine_state, "Engine-emitted candidate state")
        materialization_comparison = compare_json_documents(
            merged_path.read_text(encoding="utf-8"), engine_state.read_text(encoding="utf-8")
        )
        captured_frame_name = _manifest_file_with_role(manifest, "captured_visual_evidence")
        base_to_candidate_frame_comparison = None
        if captured_frame_name is not None:
            captured_frame_path = (packet_dir / captured_frame_name).resolve()
            if captured_frame_path.parent != packet_dir or not captured_frame_path.is_file():
                return rejected(["Packet captured visual evidence path is invalid"])
            base_to_candidate_frame_comparison = _image_comparison(captured_frame_path, engine_frame)
        requested_values, requested_errors = _requested_value_receipts(materialization, emitted)
        if requested_errors:
            return rejected(requested_errors)

        replay_result, replay_command = _run_capture(
            job, runtime_cmd_path, engine_state, replay_dir, timeout_seconds
        )
        runtime_attempts["replay"] = _runtime_attempt_receipt(
            replay_result, replay_dir, replay_command
        )
        replay_state = replay_dir / "state.json"
        replay_frame = replay_dir / "frame.bmp"
        if (
            replay_result.timed_out
            or replay_result.exit_code != 0
            or not replay_state.is_file()
            or not replay_frame.is_file()
        ):
            detail = _runtime_failure_detail(replay_result, replay_dir)
            return rejected([f"Action-free engine replay failed: {detail}"])

        comparison = compare_json_documents(
            engine_state.read_text(encoding="utf-8"), replay_state.read_text(encoding="utf-8")
        )
        frame_comparison = _image_comparison(engine_frame, replay_frame)
        errors: list[str] = []
        if any(difference.classification != "volatile_diagnostic_data" for difference in comparison.differences):
            errors.append("Action-free replay changed stable authoring state")
        if not frame_comparison.get("decoded_equal"):
            errors.append("Action-free replay produced different decoded pixels")
        current_identity, current_summary, current_sha256 = _validate_runtime_binding(manifest, runtime_cmd_path)
        if current_summary != runtime_summary or current_sha256 != binding["runtime_identity_sha256"]:
            errors.append("Published runtime identity changed during proof")
        if sha256_file(packet_dir / "manifest.json") != manifest_sha256:
            errors.append("Packet manifest changed during proof")
        if errors:
            return rejected(errors)

        receipt = {
            "proof_receipt_version": PROOF_RECEIPT_VERSION,
            "proof_id": proof_id,
            "status": "replay_proven",
            "created_at_utc": _utc_now(),
            "binding": binding,
            "runtime_identity": current_identity,
            "override": {
                "path": "override.json",
                "sha256": override_sha256,
                "requested_paths": list(materialization.requested_paths),
                "changed_paths": [asdict(change) for change in materialization.changed_paths],
                "conceptual_domains": list(materialization.conceptual_domains),
                "camera_edits": list(materialization.camera_edits),
                "apply_loaded_color_pipeline_draft": (
                    materialization.apply_loaded_color_pipeline_draft
                ),
            },
            "merged_candidate": {
                "path": "merged_candidate.json",
                "sha256": materialization.merged_candidate_sha256,
                "empty_override_byte_exact": materialization.empty_override_byte_exact,
            },
            "requested_value_receipts": requested_values,
            "materialization": {
                **_process_receipt(materialization_result, materialization_command),
                "applied_loaded_color_pipeline_draft": (
                    materialization.apply_loaded_color_pipeline_draft
                ),
                "state_path": "materialization/state.json",
                "state_sha256": sha256_file(engine_state),
                "frame_path": "materialization/frame.bmp",
                "frame": _image_fingerprint(engine_frame),
                "merged_to_emitted_state_comparison": {
                    "raw_equal": materialization_comparison.raw_equal,
                    "semantic_equal": materialization_comparison.semantic_equal,
                    "differences": [
                        asdict(difference) for difference in materialization_comparison.differences
                    ],
                },
                "base_to_candidate_frame_comparison": base_to_candidate_frame_comparison,
            },
            "replay": {
                **_process_receipt(replay_result, replay_command),
                "state_path": "replay/state.json",
                "state_sha256": sha256_file(replay_state),
                "frame_path": "replay/frame.bmp",
                "frame": _image_fingerprint(replay_frame),
                "state_comparison": {
                    "raw_equal": comparison.raw_equal,
                    "semantic_equal": comparison.semantic_equal,
                    "differences": [asdict(difference) for difference in comparison.differences],
                },
                "frame_comparison": frame_comparison,
            },
            "engine_launch_candidate": {
                "path": "materialization/state.json",
                "sha256": sha256_file(engine_state),
            },
            "visual_review": "pending",
            "launch_ready": False,
        }
        _atomic_write_json(proof_dir / "receipt.json", receipt)
        return _proof_result(
            status="replay_proven",
            proof_id=proof_id,
            message="Engine materialization and action-free replay are proven; visual review is pending.",
            proof_dir=proof_dir,
            packet_dir=packet_dir,
            packet_id=packet_id,
            manifest_sha256=manifest_sha256,
            override_sha256=override_sha256,
            merged_path=merged_path,
            merged_sha256=materialization.merged_candidate_sha256,
            engine_state=engine_state,
            engine_frame=engine_frame,
            replay_state=replay_state,
            replay_frame=replay_frame,
            empty_override_byte_exact=materialization.empty_override_byte_exact,
        )
    except JobCancelledError:
        raise
    except Exception as exc:
        return rejected([str(exc)])


def run_state_override_proof_sync(
    packet_dir: Path,
    override_text: str,
    runtime_cmd_path: Path,
    *,
    proofs_root: Path | None = None,
    expected_manifest_sha256: str | None = None,
    timeout_seconds: float = 90.0,
) -> StateOverrideProofResult:
    """Run the same owned-process worker path used by the desktop controller."""
    completed = threading.Event()
    outcome_box: list[Any] = []
    runner = AsyncJobRunner(lambda callback: callback(), max_workers=1, max_pending_jobs=1)
    identity = JobRequestIdentity(
        generation=0,
        packet_id=packet_dir.resolve().name,
        packet_manifest_sha256=(
            expected_manifest_sha256
            or (sha256_file(packet_dir.resolve() / "manifest.json") if (packet_dir.resolve() / "manifest.json").is_file() else None)
        ),
        override_text_sha256=_sha256_bytes(override_text.encode("utf-8")),
    )

    def completion(outcome: Any) -> None:
        outcome_box.append(outcome)
        completed.set()

    runner.submit(
        "state_override_proof",
        identity,
        lambda context: execute_state_override_proof(
            packet_dir,
            override_text,
            runtime_cmd_path,
            context,
            proofs_root=proofs_root,
            expected_manifest_sha256=expected_manifest_sha256,
            timeout_seconds=timeout_seconds,
        ),
        completion,
    )
    try:
        if not completed.wait(timeout_seconds * 2 + 15.0):
            runner.cancel_all()
            raise TimeoutError("State override proof worker did not finish within the bounded wait")
        outcome = outcome_box[0]
        if outcome.cancelled:
            raise JobCancelledError("State override proof was cancelled")
        if outcome.error:
            raise StateOverrideProofError(outcome.error)
        return outcome.value
    finally:
        runner.shutdown(wait=True)


def record_state_override_review(
    result: StateOverrideProofResult,
    decision: str,
    note: str = "",
) -> Path:
    if result.status != "replay_proven" or result.engine_candidate_path is None or result.candidate_frame_path is None:
        raise StateOverrideProofError("Only a replay-proven candidate can receive a review decision")
    if decision not in {"accepted", "revision_needed"}:
        raise StateOverrideProofError("Review decision must be accepted or revision_needed")
    receipt_sha256 = sha256_file(result.receipt_path)
    if receipt_sha256 != result.receipt_sha256:
        raise StateOverrideProofError("Proof receipt changed before review")
    if sha256_file(result.proof_dir / "binding.json") != result.binding_sha256:
        raise StateOverrideProofError("Proof binding changed before review")
    if sha256_file(result.engine_candidate_path) != result.engine_candidate_sha256:
        raise StateOverrideProofError("Engine launch candidate changed before review")
    if sha256_file(result.candidate_frame_path) != result.candidate_frame_sha256:
        raise StateOverrideProofError("Candidate frame changed before review")
    path = result.proof_dir / "review-decision.json"
    _atomic_write_json(
        path,
        {
            "review_decision_version": REVIEW_DECISION_VERSION,
            "proof_id": result.proof_id,
            "decided_at_utc": _utc_now(),
            "decision": decision,
            "note": note,
            "receipt_sha256": receipt_sha256,
            "packet_manifest_sha256": result.packet_manifest_sha256,
            "override_text_sha256": result.override_text_sha256,
            "engine_candidate_sha256": result.engine_candidate_sha256,
            "candidate_frame_sha256": result.candidate_frame_sha256,
        },
    )
    return path.resolve()


def validate_state_override_launch_readiness(
    result: StateOverrideProofResult,
    packet_dir: Path,
    override_text: str,
    runtime_cmd_path: Path,
) -> list[str]:
    errors: list[str] = []
    if result.status != "replay_proven" or result.engine_candidate_path is None:
        return ["No replay-proven engine candidate is available"]
    review_path = result.proof_dir / "review-decision.json"
    if not review_path.is_file():
        errors.append("Visual review is still pending")
    else:
        try:
            review = _load_object(review_path, "Review decision")
            if review.get("decision") != "accepted":
                errors.append("User requested revision instead of accepting this candidate")
            expected_review = {
                "proof_id": result.proof_id,
                "receipt_sha256": sha256_file(result.receipt_path),
                "packet_manifest_sha256": result.packet_manifest_sha256,
                "override_text_sha256": result.override_text_sha256,
                "engine_candidate_sha256": result.engine_candidate_sha256,
                "candidate_frame_sha256": result.candidate_frame_sha256,
            }
            for key, expected in expected_review.items():
                if review.get(key) != expected:
                    errors.append(f"Review decision binding changed for {key}")
        except Exception as exc:
            errors.append(str(exc))
    if packet_dir.resolve() != result.packet_dir:
        errors.append("Active packet directory changed after proof")
    if _sha256_bytes(override_text.encode("utf-8")) != result.override_text_sha256:
        errors.append("State override text changed after proof")
    checks = (
        (result.receipt_path, result.receipt_sha256, "Proof receipt"),
        (result.proof_dir / "binding.json", result.binding_sha256, "Proof binding"),
        (result.proof_dir / "override.json", result.override_text_sha256, "Preserved override"),
        (result.merged_candidate_path, result.merged_candidate_sha256, "Merged candidate"),
        (result.engine_candidate_path, result.engine_candidate_sha256, "Engine launch candidate"),
        (result.candidate_frame_path, result.candidate_frame_sha256, "Candidate frame"),
        (result.replay_state_path, result.replay_state_sha256, "Replay state"),
        (result.replay_frame_path, result.replay_frame_sha256, "Replay frame"),
    )
    for path, expected, label in checks:
        if path is None or expected is None or not path.is_file() or sha256_file(path) != expected:
            errors.append(f"{label} changed after proof")
    try:
        manifest, manifest_sha256 = _packet_manifest(result.packet_dir, result.packet_manifest_sha256)
        if manifest_sha256 != result.packet_manifest_sha256:
            errors.append("Packet manifest changed after proof")
        _validate_runtime_binding(manifest, runtime_cmd_path.resolve())
    except Exception as exc:
        errors.append(str(exc))
    return errors


def launch_state_override_candidate(
    result: StateOverrideProofResult,
    packet_dir: Path,
    override_text: str,
    runtime_cmd_path: Path,
    *,
    launcher: Callable[..., Any] = subprocess.Popen,
) -> Any:
    errors = validate_state_override_launch_readiness(result, packet_dir, override_text, runtime_cmd_path)
    if errors:
        raise StateOverrideProofError("; ".join(errors))
    assert result.engine_candidate_path is not None
    launch_path = result.proof_dir / "launch.json"
    if launch_path.exists():
        raise StateOverrideProofError("This reviewed candidate already has a launch receipt")
    command = build_detached_viewer_launch_command(runtime_cmd_path.resolve(), result.engine_candidate_path)
    process = launcher(
        command,
        cwd=str(runtime_cmd_path.resolve().parent),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS,
        text=True,
    )
    _atomic_write_json(
        launch_path,
        {
            "launch_receipt_version": LAUNCH_RECEIPT_VERSION,
            "launch_status": "launcher_process_created",
            "proof_id": result.proof_id,
            "launched_at_utc": _utc_now(),
            "launcher_process_pid": process.pid,
            "pid": process.pid,
            "viewer_health_verified": False,
            "viewer_health_note": (
                "The tool proved launcher-process creation only; it did not machine-verify viewer startup or rendering."
            ),
            "command": command,
            "review_decision_sha256": sha256_file(result.proof_dir / "review-decision.json"),
            "engine_candidate_sha256": result.engine_candidate_sha256,
            "runtime_identity_sha256": _load_object(result.proof_dir / "binding.json", "Proof binding").get(
                "runtime_identity_sha256"
            ),
        },
    )
    return process
