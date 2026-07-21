from __future__ import annotations

import hashlib
import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from PIL import Image, ImageChops, ImageStat

from .json_utils import dumps_pretty, loads_no_duplicates
from .lane_catalog import (
    LaneCatalog,
    lane_function_known,
    load_lane_catalog_from_ui_salt_contract,
)
from .process_utils import ProcessResult, run_command
from .runtime_surface import (
    build_detached_viewer_launch_command,
    build_runtime_command,
    build_runtime_identity,
    resolve_launcher,
    sha256_file,
)


class ColorAuthorityProofError(RuntimeError):
    pass


@dataclass(frozen=True)
class CaptureRecord:
    name: str
    command: tuple[str, ...]
    output_dir: Path
    state_path: Path
    frame_path: Path
    result: ProcessResult


@dataclass(frozen=True)
class ColorAuthorityProofResult:
    status: str
    output_root: Path
    receipt_path: Path
    controlled_base_state_path: Path
    materialized_state_path: Path
    replay_state_path: Path
    selected_lane_id: str
    selected_function_id: str


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dumps_pretty(value), encoding="utf-8")


def _write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8")


def _ensure_empty_output_root(output_root: Path) -> Path:
    output_root = output_root.resolve()
    if output_root.exists() and any(output_root.iterdir()):
        raise ColorAuthorityProofError(f"Proof output directory is not empty: {output_root}")
    output_root.mkdir(parents=True, exist_ok=True)
    return output_root


def _command_record(record: CaptureRecord) -> dict[str, Any]:
    return {
        "name": record.name,
        "command": list(record.command),
        "cwd": record.result.cwd,
        "pid": record.result.pid,
        "exit_code": record.result.exit_code,
        "timed_out": record.result.timed_out,
        "elapsed_seconds": record.result.elapsed_seconds,
        "process_tree": record.result.observed_process_tree,
        "state_path": str(record.state_path),
        "state_sha256": sha256_file(record.state_path) if record.state_path.exists() else None,
        "frame_path": str(record.frame_path),
        "frame_sha256": sha256_file(record.frame_path) if record.frame_path.exists() else None,
    }


def _run_capture(
    name: str,
    runtime_cmd_path: Path,
    state_path: Path,
    output_dir: Path,
    timeout_seconds: float,
    actions: tuple[str, ...] = (),
) -> CaptureRecord:
    command = build_runtime_command(
        runtime_cmd_path,
        "--load-state-json",
        str(state_path.resolve()),
        "--capture-diagnostic",
        "--diagnostics-out-dir",
        str(output_dir.resolve()),
    )
    for action in actions:
        command.extend(("--color-pipeline-action", action))
    result = run_command(command, cwd=runtime_cmd_path.resolve().parent, timeout_seconds=timeout_seconds)
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_text(output_dir / "stdout.txt", result.stdout)
    _write_text(output_dir / "stderr.txt", result.stderr)
    record = CaptureRecord(
        name=name,
        command=tuple(command),
        output_dir=output_dir.resolve(),
        state_path=(output_dir / "state.json").resolve(),
        frame_path=(output_dir / "frame.bmp").resolve(),
        result=result,
    )
    _write_json(output_dir / "command.json", _command_record(record))
    if result.timed_out:
        raise ColorAuthorityProofError(f"{name} timed out")
    if result.exit_code not in (0, None):
        detail = result.stderr.strip() or result.stdout.strip()
        raise ColorAuthorityProofError(f"{name} failed with exit code {result.exit_code}: {detail}")
    if not record.state_path.exists() or not record.frame_path.exists():
        raise ColorAuthorityProofError(f"{name} did not emit both state.json and frame.bmp")
    return record


def _validate_contract(
    runtime_cmd_path: Path,
    contract_path: Path,
    output_root: Path,
    timeout_seconds: float,
) -> dict[str, Any]:
    validation_dir = output_root / "contract_validation"
    report_path = validation_dir / "report.json"
    validation_dir.mkdir(parents=True, exist_ok=True)
    command = build_runtime_command(
        runtime_cmd_path,
        "--validate-ui-salt-contract",
        "--ui-salt-contract-json",
        str(contract_path.resolve()),
        "--ui-salt-contract-report-json",
        str(report_path.resolve()),
    )
    result = run_command(command, cwd=runtime_cmd_path.resolve().parent, timeout_seconds=timeout_seconds)
    _write_text(validation_dir / "stdout.txt", result.stdout)
    _write_text(validation_dir / "stderr.txt", result.stderr)
    command_record = {
        "command": command,
        "cwd": result.cwd,
        "pid": result.pid,
        "exit_code": result.exit_code,
        "timed_out": result.timed_out,
        "elapsed_seconds": result.elapsed_seconds,
        "process_tree": result.observed_process_tree,
        "report_path": str(report_path.resolve()),
    }
    _write_json(validation_dir / "command.json", command_record)
    if result.timed_out or result.exit_code not in (0, None) or not report_path.exists():
        raise ColorAuthorityProofError("Deployed UI-Salt contract validation failed")
    report = loads_no_duplicates(report_path.read_text(encoding="utf-8"))
    if not isinstance(report, dict) or report.get("ok") is not True:
        raise ColorAuthorityProofError("Deployed UI-Salt contract report did not return ok=true")
    return command_record


def _image_fingerprint(path: Path) -> dict[str, Any]:
    with Image.open(path) as image:
        image.load()
        rgba = image.convert("RGBA")
        decoded = rgba.tobytes()
        return {
            "encoded_sha256": sha256_file(path),
            "decoded_rgba_sha256": hashlib.sha256(decoded).hexdigest(),
            "width": rgba.width,
            "height": rgba.height,
            "mode": "RGBA",
        }


def compare_frames(left_path: Path, right_path: Path) -> dict[str, Any]:
    left_fingerprint = _image_fingerprint(left_path)
    right_fingerprint = _image_fingerprint(right_path)
    result: dict[str, Any] = {
        "left": left_fingerprint,
        "right": right_fingerprint,
        "encoded_equal": left_fingerprint["encoded_sha256"] == right_fingerprint["encoded_sha256"],
        "decoded_equal": left_fingerprint["decoded_rgba_sha256"] == right_fingerprint["decoded_rgba_sha256"],
        "difference_bbox": None,
        "mean_absolute_channel_difference": None,
    }
    if (left_fingerprint["width"], left_fingerprint["height"]) != (
        right_fingerprint["width"],
        right_fingerprint["height"],
    ):
        return result
    with Image.open(left_path) as left_image, Image.open(right_path) as right_image:
        difference = ImageChops.difference(left_image.convert("RGBA"), right_image.convert("RGBA"))
        bbox = difference.getbbox()
        result["difference_bbox"] = list(bbox) if bbox is not None else None
        result["mean_absolute_channel_difference"] = list(ImageStat.Stat(difference).mean)
    return result


def _load_state(path: Path) -> dict[str, Any]:
    payload = loads_no_duplicates(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ColorAuthorityProofError(f"Engine state must be a JSON object: {path}")
    return payload


def _draft_first_row_selections(state_path: Path, catalog: LaneCatalog) -> dict[str, str]:
    state = _load_state(state_path)
    draft = state.get("color_pipeline_draft")
    if not isinstance(draft, dict) or not isinstance(draft.get("next_row_id"), int):
        raise ColorAuthorityProofError("Engine-emitted state is missing a complete color_pipeline_draft")
    lanes = draft.get("lanes")
    if not isinstance(lanes, list):
        raise ColorAuthorityProofError("Engine-emitted color_pipeline_draft is missing lanes")
    selections: dict[str, str] = {}
    for lane in lanes:
        if not isinstance(lane, dict) or not isinstance(lane.get("lane_id"), str):
            raise ColorAuthorityProofError("Engine-emitted draft contains an invalid lane")
        rows = lane.get("rows")
        if not isinstance(rows, list) or not rows or not isinstance(rows[0], dict):
            raise ColorAuthorityProofError("Engine-emitted draft lane is missing its first row")
        first_row = rows[0]
        if not isinstance(first_row.get("ui_row_id"), int) or not isinstance(first_row.get("function_id"), str):
            raise ColorAuthorityProofError("Engine-emitted draft first row is incomplete")
        selections[lane["lane_id"]] = first_row["function_id"]
    expected_lanes = tuple(lane.lane_id for lane in catalog.lanes)
    if tuple(selections) != expected_lanes:
        raise ColorAuthorityProofError(
            f"Engine-emitted draft lane order mismatch: expected {expected_lanes}, got {tuple(selections)}"
        )
    return selections


def _candidate_selections(
    catalog: LaneCatalog,
    current: dict[str, str],
    preferred_lane_id: str,
    preferred_function_id: str,
) -> tuple[tuple[str, str], ...]:
    ordered: list[tuple[str, str]] = []
    if (
        current.get(preferred_lane_id) != preferred_function_id
        and lane_function_known(catalog, preferred_lane_id, preferred_function_id)
    ):
        ordered.append((preferred_lane_id, preferred_function_id))
    for lane in catalog.lanes:
        for function_id in lane.function_ids:
            candidate = (lane.lane_id, function_id)
            if function_id == current.get(lane.lane_id) or candidate in ordered:
                continue
            ordered.append(candidate)
    return tuple(ordered)


def run_controlled_color_authority_proof(
    runtime_cmd_path: Path,
    base_state_path: Path,
    output_root: Path,
    timeout_seconds: float = 90.0,
    preferred_lane_id: str = "shape",
    preferred_function_id: str = "repeat",
) -> ColorAuthorityProofResult:
    runtime_cmd_path = runtime_cmd_path.resolve()
    base_state_path = base_state_path.resolve()
    output_root = _ensure_empty_output_root(output_root)
    if not runtime_cmd_path.exists():
        raise ColorAuthorityProofError(f"Runtime launcher not found: {runtime_cmd_path}")
    if not base_state_path.exists():
        raise ColorAuthorityProofError(f"Base state not found: {base_state_path}")

    resolution = resolve_launcher(runtime_cmd_path)
    if not resolution.ui_salt_contract_path:
        raise ColorAuthorityProofError("Published runtime UI-Salt contract was not found")
    contract_path = Path(resolution.ui_salt_contract_path).resolve()
    runtime_identity = build_runtime_identity(runtime_cmd_path, runtime_cmd_path.parent)
    _write_json(output_root / "runtime_identity.json", runtime_identity)
    shutil.copyfile(contract_path, output_root / "ui_salt_contract.json")
    contract_validation = _validate_contract(runtime_cmd_path, contract_path, output_root, timeout_seconds)
    catalog = load_lane_catalog_from_ui_salt_contract(contract_path)
    if not lane_function_known(catalog, "shape", "identity"):
        raise ColorAuthorityProofError("Deployed UI-Salt contract does not contain shape/identity")

    original_state = _load_state(base_state_path)
    params = original_state.get("params")
    if not isinstance(params, dict) or params.get("color_shape") != "identity":
        raise ColorAuthorityProofError("Controlled proof base must begin with params.color_shape=identity")

    bootstrap = _run_capture(
        "bootstrap_identity",
        runtime_cmd_path,
        base_state_path,
        output_root / "bootstrap_identity",
        timeout_seconds,
        ("select_function:shape:0:identity",),
    )
    controlled_selections = _draft_first_row_selections(bootstrap.state_path, catalog)
    if controlled_selections.get("shape") != "identity":
        raise ColorAuthorityProofError("Bootstrap did not establish shape:0=identity")

    controlled_base_path = output_root / "controlled_base_state.json"
    shutil.copyfile(bootstrap.state_path, controlled_base_path)
    controlled_base_hash = sha256_file(controlled_base_path)
    base_one = _run_capture(
        "base_one", runtime_cmd_path, controlled_base_path, output_root / "base_one", timeout_seconds
    )
    base_two = _run_capture(
        "base_two", runtime_cmd_path, controlled_base_path, output_root / "base_two", timeout_seconds
    )
    base_parity = compare_frames(base_one.frame_path, base_two.frame_path)
    if not base_parity["decoded_equal"]:
        raise ColorAuthorityProofError("Controlled base is not pixel-deterministic across two action-free captures")

    attempts: list[dict[str, Any]] = []
    selected_capture: Optional[CaptureRecord] = None
    selected_lane_id = ""
    selected_function_id = ""
    selected_effect: Optional[dict[str, Any]] = None
    for index, (lane_id, function_id) in enumerate(
        _candidate_selections(catalog, controlled_selections, preferred_lane_id, preferred_function_id),
        start=1,
    ):
        attempt_dir = output_root / "attempts" / f"{index:02d}_{lane_id}_{function_id}"
        action = f"select_function:{lane_id}:0:{function_id}"
        try:
            capture = _run_capture(
                f"attempt_{index}",
                runtime_cmd_path,
                controlled_base_path,
                attempt_dir,
                timeout_seconds,
                (action,),
            )
            emitted_selections = _draft_first_row_selections(capture.state_path, catalog)
            effect = compare_frames(base_one.frame_path, capture.frame_path)
            attempt = {
                "lane_id": lane_id,
                "function_id": function_id,
                "action": action,
                "status": "visible_effect" if not effect["decoded_equal"] else "visually_inert",
                "requested_selection_present": emitted_selections.get(lane_id) == function_id,
                "capture": _command_record(capture),
                "base_effect": effect,
            }
            attempts.append(attempt)
            if emitted_selections.get(lane_id) == function_id and not effect["decoded_equal"]:
                selected_capture = capture
                selected_lane_id = lane_id
                selected_function_id = function_id
                selected_effect = effect
                break
        except ColorAuthorityProofError as exc:
            attempts.append(
                {
                    "lane_id": lane_id,
                    "function_id": function_id,
                    "action": action,
                    "status": "runtime_rejected_or_failed",
                    "error": str(exc),
                }
            )
    _write_json(output_root / "attempts.json", attempts)
    if selected_capture is None or selected_effect is None:
        raise ColorAuthorityProofError("No grounded non-default first-row selection produced a rendered effect")

    materialized_state_path = output_root / "materialized_state.json"
    shutil.copyfile(selected_capture.state_path, materialized_state_path)
    replay_one = _run_capture(
        "replay_one", runtime_cmd_path, materialized_state_path, output_root / "replay_one", timeout_seconds
    )
    replay_two = _run_capture(
        "replay_two", runtime_cmd_path, materialized_state_path, output_root / "replay_two", timeout_seconds
    )
    replay_one_selections = _draft_first_row_selections(replay_one.state_path, catalog)
    replay_two_selections = _draft_first_row_selections(replay_two.state_path, catalog)
    selection_survived = (
        replay_one_selections.get(selected_lane_id) == selected_function_id
        and replay_two_selections.get(selected_lane_id) == selected_function_id
    )
    materialization_replay_parity = compare_frames(selected_capture.frame_path, replay_one.frame_path)
    replay_stability = compare_frames(replay_one.frame_path, replay_two.frame_path)

    if not selection_survived:
        parity_classification = "selection_did_not_survive_replay"
        status = "failed"
    elif not replay_stability["decoded_equal"]:
        parity_classification = "runtime_nondeterminism"
        status = "failed"
    elif not materialization_replay_parity["decoded_equal"]:
        parity_classification = "action_to_replay_authority_failure"
        status = "failed"
    elif materialization_replay_parity["encoded_equal"]:
        parity_classification = "exact_encoded_frame_match"
        status = "passed"
    else:
        parity_classification = "encoding_only_difference"
        status = "passed"

    controlled_state = _load_state(controlled_base_path)
    receipt = {
        "status": status,
        "runtime_identity": runtime_identity,
        "contract": {
            "path": str(contract_path),
            "sha256": sha256_file(contract_path),
            "validation": contract_validation,
            "lane_order": [lane.lane_id for lane in catalog.lanes],
        },
        "controlled_base": {
            "source_state_path": str(base_state_path),
            "source_state_sha256": sha256_file(base_state_path),
            "state_path": str(controlled_base_path),
            "state_sha256": controlled_base_hash,
            "render": controlled_state.get("render"),
            "view": controlled_state.get("view"),
            "params_max_iter": (controlled_state.get("params") or {}).get("max_iter")
            if isinstance(controlled_state.get("params"), dict)
            else None,
            "selections": controlled_selections,
            "capture_one": _command_record(base_one),
            "capture_two": _command_record(base_two),
            "parity": base_parity,
        },
        "selected_change": {
            "lane_id": selected_lane_id,
            "row_index": 0,
            "function_id": selected_function_id,
            "action": f"select_function:{selected_lane_id}:0:{selected_function_id}",
            "materialization_capture": _command_record(selected_capture),
            "materialized_state_path": str(materialized_state_path.resolve()),
            "materialized_state_sha256": sha256_file(materialized_state_path),
            "rendered_effect": selected_effect,
        },
        "replay": {
            "selection_survived": selection_survived,
            "replay_one": _command_record(replay_one),
            "replay_two": _command_record(replay_two),
            "materialization_replay_parity": materialization_replay_parity,
            "replay_stability": replay_stability,
            "parity_classification": parity_classification,
        },
        "launch": {
            "state_path": str(materialized_state_path.resolve()),
            "command": build_detached_viewer_launch_command(runtime_cmd_path, materialized_state_path),
            "launchable": status == "passed",
        },
        "attempts_path": str((output_root / "attempts.json").resolve()),
    }
    receipt_path = output_root / "receipt.json"
    _write_json(receipt_path, receipt)
    if status != "passed":
        raise ColorAuthorityProofError(f"Controlled proof failed: {parity_classification}")
    return ColorAuthorityProofResult(
        status=status,
        output_root=output_root,
        receipt_path=receipt_path,
        controlled_base_state_path=controlled_base_path,
        materialized_state_path=materialized_state_path,
        replay_state_path=replay_one.state_path,
        selected_lane_id=selected_lane_id,
        selected_function_id=selected_function_id,
    )
