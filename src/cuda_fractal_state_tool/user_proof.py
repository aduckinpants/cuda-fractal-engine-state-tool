from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from PIL import Image, ImageChops, ImageStat

from .async_jobs import JobContext
from .json_utils import loads_no_duplicates
from .lane_catalog import (
    load_lane_catalog_from_ui_salt_contract,
    ordered_selection_actions,
    validate_lane_function_reference,
)
from .materializer import materialize_transport_candidate
from .proposal import ProposalV1, parse_proposal_v1
from .runtime_surface import (
    build_detached_viewer_launch_command,
    build_runtime_command,
    build_runtime_identity,
    resolve_launcher,
    sha256_file,
)
from .state_compare import compare_json_documents
from .user_workflow import CAPABILITY_PROFILE, FindingContext, PacketContext


@dataclass(frozen=True)
class ProofResult:
    status: str
    proof_id: str
    proposal_text_sha256: str
    message: str
    receipt_path: Path
    packet_id: str
    packet_sha256: str
    capability_profile: str
    repair_packet_text: Optional[str] = None
    candidate_path: Optional[Path] = None
    candidate_sha256: Optional[str] = None
    replay_state_path: Optional[Path] = None
    replay_frame_path: Optional[Path] = None


class ProofBindingError(ValueError):
    pass


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _canonical_sha256(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f"{path.name}.tmp.{uuid.uuid4().hex}")
    with temporary.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(str(temporary), str(path))


def _atomic_write_json(path: Path, value: Any) -> None:
    _atomic_write_text(path, json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n")


def _runtime_binding(runtime_cmd_path: Path) -> tuple[dict[str, Any], str, Path, str]:
    runtime_cmd_path = runtime_cmd_path.resolve()
    identity = build_runtime_identity(runtime_cmd_path, runtime_cmd_path.parent)
    resolution = resolve_launcher(runtime_cmd_path)
    if not resolution.ui_salt_contract_path:
        raise ProofBindingError("Published runtime has no deployed UI-Salt contract")
    contract_path = Path(resolution.ui_salt_contract_path).resolve()
    contract_sha256 = sha256_file(contract_path)
    summary = {
        "launcher_sha256": identity.get("launcher_sha256"),
        "resolved_executable_sha256": identity.get("resolved_executable_sha256"),
        "resolved_executable_file_version": identity.get("resolved_executable_file_version"),
        "runtime_schema_sha256": identity.get("runtime_schema_sha256"),
        "source_schema_sha256": identity.get("source_schema_sha256"),
        "ui_salt_contract_sha256": contract_sha256,
    }
    return identity, _canonical_sha256(summary), contract_path, contract_sha256


def _validate_packet_binding(
    finding: FindingContext,
    packet: PacketContext,
    runtime_identity_sha256: str,
    contract_sha256: str,
) -> dict[str, Any]:
    if packet.capability_profile != CAPABILITY_PROFILE:
        raise ProofBindingError(f"Unsupported packet capability profile: {packet.capability_profile}")
    if packet.packet_sha256 != _sha256_text(packet.packet_text):
        raise ProofBindingError("Packet payload no longer matches its recorded SHA-256")
    if not packet.packet_path.is_file() or packet.packet_path.read_text(encoding="utf-8") != packet.packet_text:
        raise ProofBindingError("Persisted packet payload no longer matches the active packet")
    if packet.ui_salt_contract_sha256 != contract_sha256:
        raise ProofBindingError("UI-Salt contract changed after this packet was built")
    if packet.runtime_identity_sha256 != runtime_identity_sha256:
        raise ProofBindingError("Runtime identity changed after this packet was built")
    if sha256_file(finding.authoring_base_state_path) != finding.authoring_base_sha256:
        raise ProofBindingError("Authoritative finding base changed after packet generation")

    manifest = loads_no_duplicates(packet.manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict):
        raise ProofBindingError("Packet manifest must be a JSON object")
    expected = {
        "packet_id": packet.packet_id,
        "packet_sha256": packet.packet_sha256,
        "capability_profile": packet.capability_profile,
        "finding_id": finding.finding_id,
        "authoring_base_sha256": finding.authoring_base_sha256,
        "runtime_identity_sha256": runtime_identity_sha256,
        "ui_salt_contract_sha256": contract_sha256,
    }
    for key, value in expected.items():
        if manifest.get(key) != value:
            raise ProofBindingError(f"Packet manifest binding mismatch for {key}")
    return expected


def _requested_selections(proposal: ProposalV1, contract_path: Path) -> tuple[dict[str, str], tuple[str, ...]]:
    draft = proposal.overrides.get("color_pipeline_draft")
    if draft is None:
        return {}, ()
    if not isinstance(draft, dict) or not isinstance(draft.get("lanes"), list):
        raise ValueError("color_pipeline_draft must contain a lanes array")
    catalog = load_lane_catalog_from_ui_salt_contract(contract_path)
    selections: dict[str, str] = {}
    for lane in draft["lanes"]:
        lane_id = lane["lane_id"]
        function_id = lane["function_id"]
        validate_lane_function_reference(catalog, lane_id, function_id)
        selections[lane_id] = function_id
    return selections, ordered_selection_actions(catalog, selections)


def _selection_survived(candidate: dict[str, Any], requested: dict[str, str]) -> tuple[bool, list[str]]:
    if not requested:
        return True, []
    draft = candidate.get("color_pipeline_draft")
    lanes = draft.get("lanes") if isinstance(draft, dict) else None
    if not isinstance(lanes, list):
        return False, ["Engine-emitted candidate has no complete color_pipeline_draft.lanes"]
    observed: dict[str, str] = {}
    for lane in lanes:
        if not isinstance(lane, dict) or not isinstance(lane.get("lane_id"), str):
            continue
        rows = lane.get("rows")
        if isinstance(rows, list) and rows and isinstance(rows[0], dict) and isinstance(rows[0].get("function_id"), str):
            observed[lane["lane_id"]] = rows[0]["function_id"]
    errors = [
        f"Requested {lane_id}:0={function_id}, engine emitted {observed.get(lane_id, 'missing')}"
        for lane_id, function_id in requested.items()
        if observed.get(lane_id) != function_id
    ]
    return not errors, errors


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


def _repair_packet(
    packet: PacketContext,
    proposal_text: str,
    proposal_sha256: str,
    proof_id: str,
    errors: list[str],
) -> str:
    lines = [
        "# CUDA Fractal Proposal Repair Packet",
        "",
        "The proposal below was rejected before launch readiness. Discuss the errors with the user, then return",
        "a corrected `proposal_v1` JSON code block bound to the same exact exploration packet.",
        "",
        "## Rejection",
        *[f"- {error}" for error in errors],
        "",
        "## Original proposal text",
        "```json",
        proposal_text,
        "```",
        "",
        "## Exact original binding",
        f"- packet_id: `{packet.packet_id}`",
        f"- packet_sha256: `{packet.packet_sha256}`",
        f"- capability_profile: `{packet.capability_profile}`",
        f"- proposal_text_sha256: `{proposal_sha256}`",
        f"- rejection_receipt_id: `{proof_id}`",
    ]
    return "\n".join(lines)


def _rejected_result(
    proof_root: Path,
    proof_id: str,
    binding: dict[str, Any],
    packet: PacketContext,
    proposal_text: str,
    proposal_sha256: str,
    errors: list[str],
    actionable: bool = True,
) -> ProofResult:
    repair = _repair_packet(packet, proposal_text, proposal_sha256, proof_id, errors) if actionable else None
    receipt_path = proof_root / "receipt.json"
    _atomic_write_text(proof_root / "proposal.txt", proposal_text)
    if repair is not None:
        _atomic_write_text(proof_root / "repair_packet.md", repair)
    _atomic_write_json(
        receipt_path,
        {
            "proof_receipt_version": 1,
            "proof_id": proof_id,
            "status": "rejected",
            "timestamp_utc": _utc_now(),
            "binding": binding,
            "errors": errors,
            "repair_packet_path": "repair_packet.md" if repair is not None else None,
        },
    )
    return ProofResult(
        status="rejected",
        proof_id=proof_id,
        proposal_text_sha256=proposal_sha256,
        message="\n".join(errors),
        receipt_path=receipt_path.resolve(),
        packet_id=packet.packet_id,
        packet_sha256=packet.packet_sha256,
        capability_profile=packet.capability_profile,
        repair_packet_text=repair,
    )


def execute_bound_proof(
    finding: FindingContext,
    packet: PacketContext,
    proposal_text: str,
    runtime_cmd_path: Path,
    job: JobContext,
    timeout_seconds: float = 90.0,
) -> ProofResult:
    proposal_sha256 = _sha256_text(proposal_text)
    proof_id = str(uuid.uuid4())
    proof_root = finding.import_result.finding_dir / "proofs" / proof_id
    proof_root.mkdir(parents=True, exist_ok=False)

    runtime_identity, runtime_identity_sha256, contract_path, contract_sha256 = _runtime_binding(runtime_cmd_path)
    try:
        packet_binding = _validate_packet_binding(
            finding,
            packet,
            runtime_identity_sha256,
            contract_sha256,
        )
    except Exception as exc:
        packet_binding = {
            "packet_id": packet.packet_id,
            "packet_sha256": packet.packet_sha256,
            "capability_profile": packet.capability_profile,
            "finding_id": finding.finding_id,
            "authoring_base_sha256": finding.authoring_base_sha256,
            "runtime_identity_sha256": runtime_identity_sha256,
            "ui_salt_contract_sha256": contract_sha256,
            "proposal_text_sha256": proposal_sha256,
        }
        return _rejected_result(
            proof_root, proof_id, packet_binding, packet, proposal_text, proposal_sha256, [str(exc)], actionable=False
        )

    binding = {
        **packet_binding,
        "proposal_text_sha256": proposal_sha256,
    }
    _atomic_write_text(proof_root / "packet.txt", packet.packet_text)
    _atomic_write_text(proof_root / "proposal.txt", proposal_text)
    _atomic_write_json(proof_root / "binding.json", binding)

    try:
        proposal = parse_proposal_v1(proposal_text, finding.finding_id, finding.authoring_base_sha256)
        requested, actions = _requested_selections(proposal, contract_path)
    except Exception as exc:
        return _rejected_result(
            proof_root, proof_id, binding, packet, proposal_text, proposal_sha256, [str(exc)]
        )

    scalar_proposal = ProposalV1(
        proposal_version=proposal.proposal_version,
        base_state_id=proposal.base_state_id,
        base_state_sha256=proposal.base_state_sha256,
        overrides={key: value for key, value in proposal.overrides.items() if key != "color_pipeline_draft"},
        raw_text=proposal.raw_text,
    )
    intermediate_path = proof_root / "intermediate_base.json"
    materialize_transport_candidate(finding.authoring_base_state_path, scalar_proposal, intermediate_path)

    materialization_dir = proof_root / "materialization"
    materialization_command = build_runtime_command(
        runtime_cmd_path.resolve(),
        "--load-state-json",
        str(intermediate_path.resolve()),
        "--capture-diagnostic",
        "--diagnostics-out-dir",
        str(materialization_dir.resolve()),
    )
    for action in actions:
        materialization_command.extend(("--color-pipeline-action", action))
    materialization_result = job.run_process(
        materialization_command,
        runtime_cmd_path.resolve().parent,
        timeout_seconds=timeout_seconds,
    )
    _atomic_write_text(proof_root / "materialization.stdout.txt", materialization_result.stdout)
    _atomic_write_text(proof_root / "materialization.stderr.txt", materialization_result.stderr)
    candidate_path = materialization_dir / "state.json"
    candidate_frame_path = materialization_dir / "frame.bmp"
    if (
        materialization_result.timed_out
        or materialization_result.exit_code not in (0, None)
        or not candidate_path.is_file()
        or not candidate_frame_path.is_file()
    ):
        detail = materialization_result.stderr.strip() or materialization_result.stdout.strip() or "missing state/frame output"
        errors = [f"Engine materialization failed: {detail}"]
        return _rejected_result(
            proof_root, proof_id, binding, packet, proposal_text, proposal_sha256, errors, actionable=False
        )

    candidate = loads_no_duplicates(candidate_path.read_text(encoding="utf-8"))
    if not isinstance(candidate, dict):
        return _rejected_result(
            proof_root, proof_id, binding, packet, proposal_text, proposal_sha256,
            ["Engine-emitted candidate state is not a JSON object"], actionable=False,
        )
    survived, selection_errors = _selection_survived(candidate, requested)
    if not survived:
        return _rejected_result(
            proof_root,
            proof_id,
            binding,
            packet,
            proposal_text,
            proposal_sha256,
            selection_errors,
            actionable=True,
        )

    replay_dir = proof_root / "replay"
    replay_command = build_runtime_command(
        runtime_cmd_path.resolve(),
        "--load-state-json",
        str(candidate_path.resolve()),
        "--capture-diagnostic",
        "--diagnostics-out-dir",
        str(replay_dir.resolve()),
    )
    replay_result = job.run_process(replay_command, runtime_cmd_path.resolve().parent, timeout_seconds=timeout_seconds)
    _atomic_write_text(proof_root / "replay.stdout.txt", replay_result.stdout)
    _atomic_write_text(proof_root / "replay.stderr.txt", replay_result.stderr)
    replay_state_path = replay_dir / "state.json"
    replay_frame_path = replay_dir / "frame.bmp"
    if (
        replay_result.timed_out
        or replay_result.exit_code not in (0, None)
        or not replay_state_path.is_file()
        or not replay_frame_path.is_file()
    ):
        detail = replay_result.stderr.strip() or replay_result.stdout.strip() or "missing state/frame output"
        return _rejected_result(
            proof_root, proof_id, binding, packet, proposal_text, proposal_sha256,
            [f"Action-free engine replay failed: {detail}"], actionable=False,
        )

    comparison = compare_json_documents(
        candidate_path.read_text(encoding="utf-8"),
        replay_state_path.read_text(encoding="utf-8"),
    )
    frame_comparison = _image_comparison(candidate_frame_path, replay_frame_path)
    errors: list[str] = []
    replay_document = loads_no_duplicates(replay_state_path.read_text(encoding="utf-8"))
    if not isinstance(replay_document, dict):
        errors.append("Action-free replay state is not a JSON object")
        replay_selection_survived = False
    else:
        replay_selection_survived, replay_selection_errors = _selection_survived(replay_document, requested)
        errors.extend(f"Action-free replay lost selection: {error}" for error in replay_selection_errors)
    if comparison.has_disallowed_difference:
        errors.append("Action-free replay changed stable authoring state")
    if not frame_comparison.get("decoded_equal"):
        errors.append("Action-free replay produced different decoded pixels")
    _, current_runtime_sha, _, current_contract_sha = _runtime_binding(runtime_cmd_path)
    if current_runtime_sha != runtime_identity_sha256:
        errors.append("Runtime identity changed during proof")
    if current_contract_sha != contract_sha256:
        errors.append("UI-Salt contract changed during proof")
    if errors:
        return _rejected_result(
            proof_root, proof_id, binding, packet, proposal_text, proposal_sha256, errors, actionable=False
        )

    proven_candidate_path = proof_root / "proven_candidate.json"
    shutil.copyfile(candidate_path, proven_candidate_path)
    candidate_sha256 = sha256_file(proven_candidate_path)
    receipt_path = proof_root / "receipt.json"
    receipt = {
        "proof_receipt_version": 1,
        "proof_id": proof_id,
        "status": "proven",
        "timestamp_utc": _utc_now(),
        "binding": binding,
        "runtime_identity": runtime_identity,
        "requested_selections": requested,
        "actions": list(actions),
        "intermediate_base": {
            "path": "intermediate_base.json",
            "sha256": sha256_file(intermediate_path),
        },
        "materialization": {
            "command": materialization_command,
            "exit_code": materialization_result.exit_code,
            "timed_out": materialization_result.timed_out,
            "elapsed_seconds": materialization_result.elapsed_seconds,
            "candidate_state_path": "materialization/state.json",
            "candidate_state_sha256": sha256_file(candidate_path),
            "frame_path": "materialization/frame.bmp",
            "frame_sha256": sha256_file(candidate_frame_path),
        },
        "replay": {
            "command": replay_command,
            "exit_code": replay_result.exit_code,
            "timed_out": replay_result.timed_out,
            "elapsed_seconds": replay_result.elapsed_seconds,
            "state_path": "replay/state.json",
            "state_sha256": sha256_file(replay_state_path),
            "frame_path": "replay/frame.bmp",
            "frame_sha256": sha256_file(replay_frame_path),
            "state_comparison": {
                "raw_equal": comparison.raw_equal,
                "semantic_equal": comparison.semantic_equal,
                "differences": [asdict(item) for item in comparison.differences],
            },
            "requested_selection_survived": replay_selection_survived,
            "frame_comparison": frame_comparison,
        },
        "proven_candidate": {
            "path": "proven_candidate.json",
            "sha256": candidate_sha256,
            "launch_ready": True,
            "launch_command": build_detached_viewer_launch_command(
                runtime_cmd_path.resolve(), proven_candidate_path.resolve()
            ),
        },
    }
    _atomic_write_json(receipt_path, receipt)
    return ProofResult(
        status="proven",
        proof_id=proof_id,
        proposal_text_sha256=proposal_sha256,
        message="Engine materialization and action-free replay succeeded; exact candidate is launch-ready.",
        receipt_path=receipt_path.resolve(),
        packet_id=packet.packet_id,
        packet_sha256=packet.packet_sha256,
        capability_profile=packet.capability_profile,
        candidate_path=proven_candidate_path.resolve(),
        candidate_sha256=candidate_sha256,
        replay_state_path=replay_state_path.resolve(),
        replay_frame_path=replay_frame_path.resolve(),
    )


def validate_launch_readiness(
    result: ProofResult,
    packet: PacketContext,
    proposal_text: str,
    runtime_cmd_path: Path,
) -> list[str]:
    errors: list[str] = []
    if result.status != "proven" or result.candidate_path is None or result.candidate_sha256 is None:
        errors.append("No exact proven candidate is available")
        return errors
    if result.proposal_text_sha256 != _sha256_text(proposal_text):
        errors.append("Proposal text changed after proof")
    if result.packet_id != packet.packet_id:
        errors.append("Packet ID changed after proof")
    if result.packet_sha256 != packet.packet_sha256:
        errors.append("Packet payload binding changed after proof")
    if result.capability_profile != packet.capability_profile:
        errors.append("Capability profile changed after proof")
    if not result.candidate_path.is_file() or sha256_file(result.candidate_path) != result.candidate_sha256:
        errors.append("Proven candidate changed after proof")
    try:
        _, runtime_sha, _, contract_sha = _runtime_binding(runtime_cmd_path)
        if runtime_sha != packet.runtime_identity_sha256:
            errors.append("Runtime identity changed after proof")
        if contract_sha != packet.ui_salt_contract_sha256:
            errors.append("UI-Salt contract changed after proof")
        if packet.packet_sha256 != _sha256_text(packet.packet_text):
            errors.append("Packet payload changed after proof")
        if not packet.packet_path.is_file() or sha256_file(packet.packet_path) != packet.packet_sha256:
            errors.append("Persisted packet payload changed after proof")
    except Exception as exc:
        errors.append(str(exc))
    return errors


def launch_proven_result(
    result: ProofResult,
    packet: PacketContext,
    proposal_text: str,
    runtime_cmd_path: Path,
) -> subprocess.Popen[str]:
    errors = validate_launch_readiness(result, packet, proposal_text, runtime_cmd_path)
    if errors:
        raise ProofBindingError("; ".join(errors))
    assert result.candidate_path is not None
    command = build_detached_viewer_launch_command(runtime_cmd_path.resolve(), result.candidate_path)
    return subprocess.Popen(
        command,
        cwd=str(runtime_cmd_path.resolve().parent),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS,
        text=True,
    )
