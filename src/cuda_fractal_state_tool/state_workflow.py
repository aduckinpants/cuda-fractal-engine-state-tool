from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from .baseline import FrozenBaseline, load_frozen_baseline
from .json_utils import dumps_pretty
from .materializer import materialize_transport_candidate
from .process_utils import ProcessResult, run_command
from .proposal import ProposalV1, parse_proposal_v1
from .runtime_surface import (
    DEFAULT_RUNTIME_CMD,
    build_detached_viewer_launch_command,
    build_replay_command,
    build_runtime_identity,
)
from .state_compare import DocumentComparison, compare_json_documents
from .workspace_layout import WorkspaceLayout


@dataclass
class WorkflowResult:
    status: str
    working_state_dir: Path
    validation_run_dir: Path
    validation_run_manifest_path: Path
    runtime_status: str
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


def _copy_if_exists(source: Path, destination: Path) -> bool:
    if not source.exists():
        return False
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)
    return True


def _build_validation_run_manifest(
    state_id: str,
    status: str,
    runtime_status: str,
    baseline: FrozenBaseline,
    proposal: ProposalV1,
    state_dir: Path,
    validation_path: Path,
    replay_state_path: Path,
    replay_frame_path: Path,
    proven_state_path: Optional[Path],
    diff_result: Optional[DocumentComparison],
    replay_result: ProcessResult,
    runtime_cmd_path: Path,
) -> dict[str, Any]:
    return {
        "run_id": state_id,
        "status": status,
        "runtime_status": runtime_status,
        "timestamp_utc": _utc_now(),
        "baseline_id": baseline.baseline_id,
        "baseline_sha256": baseline.manifest["state_sha256"],
        "proposal_version": proposal.proposal_version,
        "overrides": dict(proposal.overrides),
        "working_state_dir": str(state_dir.resolve()),
        "transport_candidate_path": str((state_dir / "transport_candidate.json").resolve()),
        "proven_state_path": str(proven_state_path) if proven_state_path else None,
        "replay_state_path": str(replay_state_path) if replay_state_path.exists() else None,
        "replay_frame_path": str(replay_frame_path) if replay_frame_path.exists() else None,
        "validation_path": str(validation_path.resolve()),
        "candidate_replay_diff_path": str((state_dir / "candidate_replay_diff.json").resolve()) if diff_result else None,
        "runtime_identity": build_runtime_identity(runtime_cmd_path.resolve(), runtime_cmd_path.resolve().parent),
        "command": build_replay_command(runtime_cmd_path.resolve(), state_dir / "transport_candidate.json", state_dir / "replay"),
        "exit_code": replay_result.exit_code,
        "timed_out": replay_result.timed_out,
        "elapsed_seconds": replay_result.elapsed_seconds,
        "stdout_path": str((state_dir / "stdout.txt").resolve()),
        "stderr_path": str((state_dir / "stderr.txt").resolve()),
    }


def replay_transport_candidate(runtime_cmd_path: Path, candidate_path: Path, replay_dir: Path, timeout_seconds: float = 90.0) -> ProcessResult:
    runtime_cmd_path = runtime_cmd_path.resolve()
    replay_dir = replay_dir.resolve()
    replay_dir.mkdir(parents=True, exist_ok=True)
    runtime_cwd = runtime_cmd_path.parent
    command = build_replay_command(runtime_cmd_path, candidate_path, replay_dir)
    return run_command(command, cwd=runtime_cwd, timeout_seconds=timeout_seconds)


def execute_proposal_workflow(
    proposal_text: str,
    baseline_manifest_path: Path,
    working_states_root: Path,
    state_id: str,
    runtime_cmd_path: Path = DEFAULT_RUNTIME_CMD,
    timeout_seconds: float = 90.0,
) -> WorkflowResult:
    baseline = load_frozen_baseline(baseline_manifest_path)
    proposal = parse_proposal_v1(proposal_text, baseline.baseline_id, baseline.manifest["state_sha256"])

    state_dir = working_states_root.resolve() / state_id
    validation_run_dir = state_dir.parent.parent / "validation_runs" / state_id
    validation_run_dir.mkdir(parents=True, exist_ok=True)
    validation_run_manifest_path = validation_run_dir / "manifest.json"
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
    if status == "runtime_proof_succeeded":
        proven_state_path = state_dir / "state.json"
        shutil.copyfile(candidate_path, proven_state_path)

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
        "stdout_path": str((state_dir / 'stdout.txt').resolve()),
        "stderr_path": str((state_dir / 'stderr.txt').resolve()),
        "candidate_replay_diff_path": str((state_dir / 'candidate_replay_diff.json').resolve()) if diff_result else None,
    }
    _write_json(validation_path, validation)

    validation_run_manifest = _build_validation_run_manifest(
        state_id,
        status,
        runtime_status,
        baseline,
        proposal,
        state_dir,
        validation_path,
        replay_state_path,
        replay_frame_path,
        proven_state_path,
        diff_result,
        replay_result,
        runtime_cmd_path,
    )
    _write_json_with_stdlib(validation_run_manifest_path, validation_run_manifest)

    return WorkflowResult(
        status=status,
        working_state_dir=state_dir,
        validation_run_dir=validation_run_dir,
        validation_run_manifest_path=validation_run_manifest_path,
        runtime_status=runtime_status,
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
