from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from .baseline import FrozenBaseline, load_frozen_baseline
from .json_utils import dumps_pretty, loads_no_duplicates
from .materializer import materialize_transport_candidate
from .process_utils import ProcessResult, run_command
from .proposal import ProposalV1, parse_proposal_v1
from .runtime_metadata_cache import restore_probe_output, runtime_cache_dir, runtime_identity_cache_key
from .runtime_surface import (
    DEFAULT_RUNTIME_CMD,
    build_runtime_command,
    build_detached_viewer_launch_command,
    build_replay_command,
    build_runtime_identity,
    sha256_file,
)
from .state_compare import DocumentComparison, compare_json_documents
from .workspace_layout import WorkspaceLayout


PROMOTION_PROFILES: dict[str, set[str]] = {
    "none": set(),
    # Promote only the replay artifact lane/function draft payload.
    "color_pipeline_draft_only_v1": {"color_pipeline_draft"},
    # Promote only runtime-derived sidecar orientation fields.
    "sidecar_orientation_only_v1": {"sidecar_orientation"},
    # Observed replay enrichments from probe evidence; applied as an explicit side artifact.
    "observed_runtime_enrichment_v1": {"color_pipeline_draft", "sidecar_orientation"},
}

PROMOTION_ALLOWED_CLASSIFICATIONS = {"runtime_replay_artifact_enrichment", "derived_runtime_state"}


@dataclass
class WorkflowResult:
    status: str
    working_state_dir: Path
    validation_run_dir: Path
    validation_run_manifest_path: Path
    validation_runs_index_path: Path
    runtime_status: str
    promotion_profile: str
    promoted_state_path: Optional[Path]
    promotion_report_path: Optional[Path]
    transport_candidate_path: Path
    proven_state_path: Optional[Path]
    replay_state_path: Optional[Path]
    diff: Optional[DocumentComparison]
    validation_path: Path


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dumps_pretty(value), encoding="utf-8")


def _write_json_with_stdlib(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8")


def _load_json_or_default(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        return raw
    except Exception:
        return default


def _copy_if_exists(source: Path, destination: Path) -> bool:
    if not source.exists():
        return False
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)
    return True


def _metadata_cache_root_from_working_root(working_states_root: Path) -> Path:
    return working_states_root.resolve().parent / "cache" / "runtime"


def _metadata_cache_is_ready(cache_dir: Path) -> bool:
    return (
        (cache_dir / "describe-parameter-surface.json").exists()
        and (cache_dir / "describe-functions.json").exists()
        and (cache_dir / "runtime_identity.json").exists()
    )


def _ensure_runtime_metadata_snapshot(runtime_cmd_path: Path, metadata_cache_root: Path, timeout_seconds: float) -> dict[str, Any]:
    runtime_cmd_path = runtime_cmd_path.resolve()
    runtime_cwd = runtime_cmd_path.parent
    identity = build_runtime_identity(runtime_cmd_path, runtime_cwd)
    cache_key = runtime_identity_cache_key(identity)
    cache_dir = runtime_cache_dir(metadata_cache_root, identity)
    metadata_cache_root.mkdir(parents=True, exist_ok=True)

    if _metadata_cache_is_ready(cache_dir):
        return {
            "cache_hit": True,
            "cache_key": cache_key,
            "cache_dir": str(cache_dir.resolve()),
            "describe_parameter_surface_path": str((cache_dir / "describe-parameter-surface.json").resolve()),
            "describe_functions_path": str((cache_dir / "describe-functions.json").resolve()),
            "runtime_identity_path": str((cache_dir / "runtime_identity.json").resolve()),
            "commands": [],
        }

    temp_output = metadata_cache_root.parent / "runtime_metadata_probe_tmp" / cache_key
    shutil.rmtree(temp_output, ignore_errors=True)
    temp_output.mkdir(parents=True, exist_ok=True)

    describe_surface_path = temp_output / "describe-parameter-surface.json"
    describe_functions_path = temp_output / "describe-functions.json"
    commands: list[dict[str, Any]] = []

    for name, cmd in (
        (
            "describe_parameter_surface",
            build_runtime_command(runtime_cmd_path, "--describe-parameter-surface-json", str(describe_surface_path)),
        ),
        (
            "describe_functions",
            build_runtime_command(runtime_cmd_path, "--describe-functions-json", str(describe_functions_path)),
        ),
    ):
        result = run_command(cmd, cwd=runtime_cwd, timeout_seconds=timeout_seconds)
        stdout_path = temp_output / f"{name}.stdout.txt"
        stderr_path = temp_output / f"{name}.stderr.txt"
        _write_text(stdout_path, result.stdout)
        _write_text(stderr_path, result.stderr)
        commands.append(
            {
                "name": name,
                "command": cmd,
                "exit_code": result.exit_code,
                "timed_out": result.timed_out,
                "elapsed_seconds": result.elapsed_seconds,
                "stdout_path": str(stdout_path.resolve()),
                "stderr_path": str(stderr_path.resolve()),
            }
        )

    if describe_surface_path.exists():
        identity["describe_parameter_surface_sha256"] = sha256_file(describe_surface_path)
    if describe_functions_path.exists():
        identity["describe_functions_sha256"] = sha256_file(describe_functions_path)
    _write_json(temp_output / "runtime_identity.json", identity)

    if _metadata_cache_is_ready(temp_output):
        if cache_dir.exists():
            shutil.rmtree(cache_dir, ignore_errors=True)
        cache_dir.parent.mkdir(parents=True, exist_ok=True)
        restore_probe_output(temp_output, cache_dir)

    return {
        "cache_hit": False,
        "cache_key": cache_key,
        "cache_dir": str(cache_dir.resolve()),
        "describe_parameter_surface_path": str((cache_dir / "describe-parameter-surface.json").resolve()) if (cache_dir / "describe-parameter-surface.json").exists() else None,
        "describe_functions_path": str((cache_dir / "describe-functions.json").resolve()) if (cache_dir / "describe-functions.json").exists() else None,
        "runtime_identity_path": str((cache_dir / "runtime_identity.json").resolve()) if (cache_dir / "runtime_identity.json").exists() else None,
        "commands": commands,
    }


def _build_validation_run_manifest(
    state_id: str,
    status: str,
    runtime_status: str,
    promotion_profile: str,
    baseline: FrozenBaseline,
    proposal: ProposalV1,
    state_dir: Path,
    validation_path: Path,
    replay_state_path: Path,
    replay_frame_path: Path,
    proven_state_path: Optional[Path],
    promoted_state_path: Optional[Path],
    promotion_report_path: Optional[Path],
    diff_result: Optional[DocumentComparison],
    replay_result: ProcessResult,
    runtime_cmd_path: Path,
    metadata_cache: dict[str, Any],
) -> dict[str, Any]:
    return {
        "run_id": state_id,
        "status": status,
        "runtime_status": runtime_status,
        "promotion_profile": promotion_profile,
        "timestamp_utc": _utc_now(),
        "baseline_id": baseline.baseline_id,
        "baseline_sha256": baseline.manifest["state_sha256"],
        "proposal_version": proposal.proposal_version,
        "overrides": dict(proposal.overrides),
        "working_state_dir": str(state_dir.resolve()),
        "transport_candidate_path": str((state_dir / "transport_candidate.json").resolve()),
        "proven_state_path": str(proven_state_path) if proven_state_path else None,
        "promoted_state_path": str(promoted_state_path) if promoted_state_path else None,
        "promotion_report_path": str(promotion_report_path) if promotion_report_path else None,
        "replay_state_path": str(replay_state_path) if replay_state_path.exists() else None,
        "replay_frame_path": str(replay_frame_path) if replay_frame_path.exists() else None,
        "validation_path": str(validation_path.resolve()),
        "candidate_replay_diff_path": str((state_dir / "candidate_replay_diff.json").resolve()) if diff_result else None,
        "runtime_identity": build_runtime_identity(runtime_cmd_path.resolve(), runtime_cmd_path.resolve().parent),
        "runtime_metadata_cache": metadata_cache,
        "command": build_replay_command(runtime_cmd_path.resolve(), state_dir / "transport_candidate.json", state_dir / "replay"),
        "exit_code": replay_result.exit_code,
        "timed_out": replay_result.timed_out,
        "elapsed_seconds": replay_result.elapsed_seconds,
        "stdout_path": str((state_dir / "stdout.txt").resolve()),
        "stderr_path": str((state_dir / "stderr.txt").resolve()),
    }


def _update_validation_runs_index(index_path: Path, manifest: dict[str, Any]) -> None:
    root = _load_json_or_default(index_path, {"entries": []})
    if not isinstance(root, dict):
        root = {"entries": []}
    entries = root.get("entries")
    if not isinstance(entries, list):
        entries = []
    run_id = manifest.get("run_id")
    if isinstance(run_id, str):
        entries = [item for item in entries if not (isinstance(item, dict) and item.get("run_id") == run_id)]
    entry = {
        "run_id": manifest.get("run_id"),
        "timestamp_utc": manifest.get("timestamp_utc"),
        "status": manifest.get("status"),
        "runtime_status": manifest.get("runtime_status"),
        "promotion_profile": manifest.get("promotion_profile"),
        "baseline_id": manifest.get("baseline_id"),
        "manifest_path": manifest.get("manifest_path"),
        "working_state_dir": manifest.get("working_state_dir"),
        "promoted_state_path": manifest.get("promoted_state_path"),
    }
    entries.append(entry)
    root["entries"] = entries
    _write_json(index_path, root)


def replay_transport_candidate(runtime_cmd_path: Path, candidate_path: Path, replay_dir: Path, timeout_seconds: float = 90.0) -> ProcessResult:
    runtime_cmd_path = runtime_cmd_path.resolve()
    replay_dir = replay_dir.resolve()
    replay_dir.mkdir(parents=True, exist_ok=True)
    runtime_cwd = runtime_cmd_path.parent
    command = build_replay_command(runtime_cmd_path, candidate_path, replay_dir)
    return run_command(command, cwd=runtime_cwd, timeout_seconds=timeout_seconds)


def _top_level_path(path: str) -> str:
    return path.split(".", 1)[0].split("[", 1)[0]


def _build_promoted_state(
    candidate_path: Path,
    replay_state_path: Path,
    promoted_state_path: Path,
    promotion_profile: str,
    diff_result: Optional[DocumentComparison],
) -> tuple[Path, dict[str, Any]]:
    allowed_keys = PROMOTION_PROFILES[promotion_profile]
    candidate = loads_no_duplicates(candidate_path.read_text(encoding="utf-8"))
    replay = loads_no_duplicates(replay_state_path.read_text(encoding="utf-8"))
    if not isinstance(candidate, dict) or not isinstance(replay, dict):
        raise ValueError("Candidate and replay state must be JSON objects for promotion")

    promoted: dict[str, Any] = dict(candidate)
    applied_keys: list[str] = []
    missing_keys: list[str] = []
    unchanged_keys: list[str] = []
    blocked_keys: dict[str, list[str]] = {}

    key_classifications: dict[str, set[str]] = {key: set() for key in allowed_keys}
    if diff_result is not None:
        for diff in diff_result.differences:
            top = _top_level_path(diff.path)
            if top in key_classifications:
                key_classifications[top].add(diff.classification)

    for key in sorted(allowed_keys):
        if key not in replay:
            missing_keys.append(key)
            continue
        classifications = key_classifications.get(key, set())
        disallowed = sorted(classification for classification in classifications if classification not in PROMOTION_ALLOWED_CLASSIFICATIONS)
        if disallowed:
            blocked_keys[key] = disallowed
            continue
        previous = promoted.get(key)
        promoted[key] = replay[key]
        if previous == replay[key]:
            unchanged_keys.append(key)
        else:
            applied_keys.append(key)

    promoted_state_path.parent.mkdir(parents=True, exist_ok=True)
    promoted_state_path.write_text(json.dumps(promoted, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report = {
        "promotion_profile": promotion_profile,
        "allowed_keys": sorted(allowed_keys),
        "allowed_classifications": sorted(PROMOTION_ALLOWED_CLASSIFICATIONS),
        "applied_keys": applied_keys,
        "unchanged_keys": unchanged_keys,
        "missing_keys": missing_keys,
        "blocked_keys": blocked_keys,
    }
    return promoted_state_path, report


def execute_proposal_workflow(
    proposal_text: str,
    baseline_manifest_path: Path,
    working_states_root: Path,
    state_id: str,
    runtime_cmd_path: Path = DEFAULT_RUNTIME_CMD,
    timeout_seconds: float = 90.0,
    promotion_profile: str = "none",
) -> WorkflowResult:
    if promotion_profile not in PROMOTION_PROFILES:
        raise ValueError(f"Unknown promotion profile: {promotion_profile}")

    baseline = load_frozen_baseline(baseline_manifest_path)
    proposal = parse_proposal_v1(proposal_text, baseline.baseline_id, baseline.manifest["state_sha256"])

    metadata_cache_root = _metadata_cache_root_from_working_root(working_states_root)
    metadata_cache = _ensure_runtime_metadata_snapshot(runtime_cmd_path, metadata_cache_root, timeout_seconds)

    state_dir = working_states_root.resolve() / state_id
    validation_run_dir = state_dir.parent.parent / "validation_runs" / state_id
    validation_run_dir.mkdir(parents=True, exist_ok=True)
    validation_run_manifest_path = validation_run_dir / "manifest.json"
    validation_runs_index_path = validation_run_dir.parent / "index.json"
    replay_dir = state_dir / "replay"
    candidate_path = state_dir / "transport_candidate.json"
    proposal_path = state_dir / "proposal.json"
    validation_path = state_dir / "validation.json"
    _write_text(proposal_path, proposal.raw_text)
    materialization = materialize_transport_candidate(baseline.state_path, proposal, candidate_path)

    replay_result = replay_transport_candidate(runtime_cmd_path, candidate_path, replay_dir, timeout_seconds)
    _write_text(state_dir / "stdout.txt", replay_result.stdout)
    _write_text(state_dir / "stderr.txt", replay_result.stderr)

    replay_state_path = replay_dir / "state.json"
    replay_frame_path = replay_dir / "frame.bmp"
    diff_result: Optional[DocumentComparison] = None
    if replay_state_path.exists():
        diff_result = compare_json_documents(
            candidate_path.read_text(encoding="utf-8"),
            replay_state_path.read_text(encoding="utf-8"),
        )
        _write_json(
            state_dir / "candidate_replay_diff.json",
            {
                "raw_equal": diff_result.raw_equal,
                "semantic_equal": diff_result.semantic_equal,
                "has_unexplained_difference": diff_result.has_unexplained_difference,
                "has_stable_authoring_state_difference": diff_result.has_stable_authoring_state_difference,
                "differences": [asdict(item) for item in diff_result.differences],
            },
        )

    if replay_result.timed_out or replay_result.exit_code not in (0, None):
        status = "runtime_proof_failed"
    elif not replay_state_path.exists() or diff_result is None:
        status = "runtime_proof_failed"
    elif diff_result.has_disallowed_difference:
        status = "runtime_proof_failed"
    else:
        status = "runtime_proof_succeeded"

    if replay_result.timed_out:
        runtime_status = "runtime_timeout"
    elif replay_result.exit_code not in (0, None):
        runtime_status = "runtime_failure"
    elif not replay_state_path.exists():
        runtime_status = "runtime_failure"
    elif diff_result is not None and diff_result.has_disallowed_difference:
        runtime_status = "runtime_replay_failure"
    else:
        runtime_status = "runtime_success"

    proven_state_path: Optional[Path] = None
    promoted_state_path: Optional[Path] = None
    promotion_report_path: Optional[Path] = None
    if status == "runtime_proof_succeeded":
        proven_state_path = state_dir / "state.json"
        shutil.copyfile(candidate_path, proven_state_path)
        if promotion_profile != "none" and replay_state_path.exists():
            promoted_state_path = state_dir / "promoted_state.json"
            promotion_report_path = state_dir / "promotion_report.json"
            _, promotion_report = _build_promoted_state(
                candidate_path,
                replay_state_path,
                promoted_state_path,
                promotion_profile,
                diff_result,
            )
            _write_json(promotion_report_path, promotion_report)

    validation = {
        "status": status,
        "timestamp_utc": _utc_now(),
        "baseline_id": baseline.baseline_id,
        "baseline_sha256": baseline.manifest["state_sha256"],
        "proposal_version": proposal.proposal_version,
        "overrides": dict(proposal.overrides),
        "transport_candidate_path": str(candidate_path),
        "proven_state_path": str(proven_state_path) if proven_state_path else None,
        "replay_state_path": str(replay_state_path) if replay_state_path.exists() else None,
        "replay_frame_path": str(replay_frame_path) if replay_frame_path.exists() else None,
        "runtime_identity": build_runtime_identity(runtime_cmd_path.resolve(), runtime_cmd_path.resolve().parent),
        "command": build_replay_command(runtime_cmd_path.resolve(), candidate_path, replay_dir),
        "exit_code": replay_result.exit_code,
        "timed_out": replay_result.timed_out,
        "elapsed_seconds": replay_result.elapsed_seconds,
        "promotion_profile": promotion_profile,
        "promoted_state_path": str(promoted_state_path) if promoted_state_path else None,
        "promotion_report_path": str(promotion_report_path) if promotion_report_path else None,
        "stdout_path": str((state_dir / 'stdout.txt').resolve()),
        "stderr_path": str((state_dir / 'stderr.txt').resolve()),
        "candidate_replay_diff_path": str((state_dir / 'candidate_replay_diff.json').resolve()) if diff_result else None,
        "runtime_metadata_cache": metadata_cache,
    }
    _write_json(validation_path, validation)

    validation_run_manifest = _build_validation_run_manifest(
        state_id,
        status,
        runtime_status,
        promotion_profile,
        baseline,
        proposal,
        state_dir,
        validation_path,
        replay_state_path,
        replay_frame_path,
        proven_state_path,
        promoted_state_path,
        promotion_report_path,
        diff_result,
        replay_result,
        runtime_cmd_path,
        metadata_cache,
    )
    validation_run_manifest["manifest_path"] = str(validation_run_manifest_path.resolve())
    _write_json_with_stdlib(validation_run_manifest_path, validation_run_manifest)
    _update_validation_runs_index(validation_runs_index_path, validation_run_manifest)

    return WorkflowResult(
        status=status,
        working_state_dir=state_dir,
        validation_run_dir=validation_run_dir,
        validation_run_manifest_path=validation_run_manifest_path,
        validation_runs_index_path=validation_runs_index_path,
        runtime_status=runtime_status,
        promotion_profile=promotion_profile,
        promoted_state_path=promoted_state_path,
        promotion_report_path=promotion_report_path,
        transport_candidate_path=candidate_path,
        proven_state_path=proven_state_path,
        replay_state_path=replay_state_path if replay_state_path.exists() else None,
        diff=diff_result,
        validation_path=validation_path,
    )


def launch_proven_candidate(runtime_cmd_path: Path, candidate_path: Path) -> subprocess.Popen[str]:
    runtime_cmd_path = runtime_cmd_path.resolve()
    command = build_detached_viewer_launch_command(runtime_cmd_path, candidate_path.resolve())
    return subprocess.Popen(
        command,
        cwd=str(runtime_cmd_path.parent),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS,
        text=True,
    )
