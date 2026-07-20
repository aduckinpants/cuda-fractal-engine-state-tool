from __future__ import annotations

import argparse
import json
import shutil
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Optional

from .json_utils import dumps_pretty, loads_no_duplicates
from .runtime_metadata_cache import cache_probe_output, restore_probe_output, runtime_cache_dir, runtime_identity_cache_key
from .process_utils import run_command
from .runtime_surface import (
    DEFAULT_RUNTIME_CMD,
    build_runtime_command,
    build_runtime_identity,
    resolve_launcher,
    sha256_file,
)
from .state_compare import compare_json_documents
from .workspace_layout import WorkspaceLayout


_COMMAND_NAMES = (
    "describe_parameter_surface",
    "describe_functions",
    "capture_one",
    "capture_two",
    "invalid_json_capture",
    "replay_one",
)


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dumps_pretty(value), encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _sanitize_command(command: list[str]) -> list[str]:
    return command


def _classify_command_record(record: dict[str, Any]) -> str:
    name = record.get("name")
    exit_code = record.get("exit_code")
    timed_out = bool(record.get("timed_out"))
    replay_state_exists = bool(record.get("replay_state_exists"))
    if timed_out:
        return "runtime_timeout"
    if exit_code not in (0, None):
        if name == "invalid_json_capture":
            return "runtime_rejected_input"
        return "runtime_failure"
    if name in {"capture_one", "capture_two", "replay_one"} and not replay_state_exists:
        return "runtime_failure"
    return "runtime_success"


def _load_json(path: Path) -> Any:
    return loads_no_duplicates(path.read_text(encoding="utf-8"))


def _rewrite_cached_record(record: dict[str, Any], output_root: Path) -> dict[str, Any]:
    rewritten = dict(record)
    old_root: Optional[Path] = None
    stdout_path = record.get("stdout_path")
    if isinstance(stdout_path, str):
        old_root = Path(stdout_path).parent
    name = rewritten.get("name")
    if isinstance(name, str):
        rewritten["stdout_path"] = str((output_root / f"{name}.stdout.txt").resolve())
        rewritten["stderr_path"] = str((output_root / f"{name}.stderr.txt").resolve())
    if old_root is not None and isinstance(rewritten.get("command"), list):
        old_root_text = str(old_root)
        old_root_posix = old_root.as_posix()
        new_root_text = str(output_root.resolve())
        new_root_posix = output_root.resolve().as_posix()
        rewritten["command"] = [
            arg.replace(old_root_posix, new_root_posix).replace(old_root_text, new_root_text) if isinstance(arg, str) else arg
            for arg in rewritten["command"]
        ]
    name = rewritten.get("name")
    if name in {"capture_one", "capture_two"}:
        rewritten["replay_state_exists"] = (output_root / str(name) / "state.json").exists()
    elif name == "replay_one":
        rewritten["replay_state_exists"] = (output_root / "replay_one" / "state.json").exists()
    else:
        rewritten["replay_state_exists"] = False
    rewritten["status"] = _classify_command_record(rewritten)
    return rewritten


def _load_command_records(output_root: Path) -> list[dict[str, Any]]:
    commands: list[dict[str, Any]] = []
    for name in _COMMAND_NAMES:
        record_path = output_root / f"{name}.json"
        if not record_path.exists():
            continue
        record = _load_json(record_path)
        if not isinstance(record, dict):
            continue
        rewritten = _rewrite_cached_record(record, output_root)
        _write_json(record_path, rewritten)
        commands.append(rewritten)
    return commands


def _build_summary(output_root: Path, commands: list[dict[str, Any]], cache_hit: bool, cache_key: str) -> dict[str, Any]:
    comparison_path = output_root / "capture_comparison.json"
    command_status_counts: dict[str, int] = {}
    for record in commands:
        status = str(record.get("status") or "runtime_unknown")
        command_status_counts[status] = command_status_counts.get(status, 0) + 1
    return {
        "runtime_identity_path": str((output_root / "runtime_identity.json").resolve()),
        "launcher_resolution_path": str((output_root / "launcher_resolution.json").resolve()),
        "commands": commands,
        "command_status_counts": command_status_counts,
        "capture_comparison_path": str(comparison_path.resolve()) if comparison_path.exists() else None,
        "capture_one_state_exists": (output_root / "capture_one" / "state.json").exists(),
        "capture_two_state_exists": (output_root / "capture_two" / "state.json").exists(),
        "replay_one_state_exists": (output_root / "replay_one" / "state.json").exists(),
        "cache_hit": cache_hit,
        "cache_key": cache_key,
        "cache_path": str((output_root.parent / "cache" / "runtime" / cache_key).resolve()),
    }


def _cache_is_ready(cache_dir: Path) -> bool:
    required_files = [
        "launcher_resolution.json",
        "runtime_identity.json",
        "describe_parameter_surface.json",
        "describe_functions.json",
        "capture_one.json",
        "capture_two.json",
        "invalid_json_capture.json",
        "replay_one.json",
        "summary.json",
    ]
    if not all((cache_dir / file_name).exists() for file_name in required_files):
        return False
    required_dirs = [
        cache_dir / "capture_one",
        cache_dir / "capture_two",
        cache_dir / "replay_one",
    ]
    return all(directory.exists() for directory in required_dirs)


def _run_and_record(name: str, command: list[str], cwd: Path, output_root: Path, timeout_seconds: float) -> dict[str, Any]:
    result = run_command(command, cwd=cwd, timeout_seconds=timeout_seconds)
    record = {
        "name": name,
        "command": _sanitize_command(command),
        "cwd": str(cwd),
        "pid": result.pid,
        "exit_code": result.exit_code,
        "timed_out": result.timed_out,
        "elapsed_seconds": result.elapsed_seconds,
        "stdout_path": str((output_root / f"{name}.stdout.txt").resolve()),
        "stderr_path": str((output_root / f"{name}.stderr.txt").resolve()),
        "process_tree": result.observed_process_tree,
    }
    _write_text(output_root / f"{name}.stdout.txt", result.stdout)
    _write_text(output_root / f"{name}.stderr.txt", result.stderr)
    if name in {"capture_one", "capture_two"}:
        record["replay_state_exists"] = (output_root / name / "state.json").exists()
    elif name == "replay_one":
        record["replay_state_exists"] = (output_root / "replay_one" / "state.json").exists()
    else:
        record["replay_state_exists"] = False
    record["status"] = _classify_command_record(record)
    _write_json(output_root / f"{name}.json", record)
    return record


def run_probe(runtime_cmd_path: Path, output_root: Path, timeout_seconds: float = 90.0) -> dict[str, Any]:
    output_root = output_root.resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    runtime_cwd = runtime_cmd_path.parent
    identity = build_runtime_identity(runtime_cmd_path, runtime_cwd)
    cache_key = runtime_identity_cache_key(identity)
    cache_root = output_root.parent / "cache" / "runtime"
    cache_dir = runtime_cache_dir(cache_root, identity)

    if _cache_is_ready(cache_dir):
        restore_probe_output(cache_dir, output_root)
        commands = _load_command_records(output_root)
        summary = _build_summary(output_root, commands, cache_hit=True, cache_key=cache_key)
        _write_json(output_root / "summary.json", summary)
        return summary

    resolution = asdict(resolve_launcher(runtime_cmd_path))
    _write_json(output_root / "launcher_resolution.json", resolution)

    describe_surface_path = output_root / "describe-parameter-surface.json"
    describe_functions_path = output_root / "describe-functions.json"

    commands: list[dict[str, Any]] = []
    commands.append(
        _run_and_record(
            "describe_parameter_surface",
            build_runtime_command(runtime_cmd_path, "--describe-parameter-surface-json", str(describe_surface_path)),
            runtime_cwd,
            output_root,
            timeout_seconds,
        )
    )
    commands.append(
        _run_and_record(
            "describe_functions",
            build_runtime_command(runtime_cmd_path, "--describe-functions-json", str(describe_functions_path)),
            runtime_cwd,
            output_root,
            timeout_seconds,
        )
    )
    if describe_surface_path.exists():
        identity["describe_parameter_surface_sha256"] = sha256_file(describe_surface_path)
    if describe_functions_path.exists():
        identity["describe_functions_sha256"] = sha256_file(describe_functions_path)
    _write_json(output_root / "runtime_identity.json", identity)

    capture_one_dir = output_root / "capture_one"
    capture_two_dir = output_root / "capture_two"
    replay_one_dir = output_root / "replay_one"
    invalid_json_path = output_root / "invalid.json"
    invalid_json_path.write_text("{", encoding="utf-8")

    commands.append(
        _run_and_record(
            "capture_one",
            build_runtime_command(runtime_cmd_path, "--capture-diagnostic", "--diagnostics-out-dir", str(capture_one_dir)),
            runtime_cwd,
            output_root,
            timeout_seconds,
        )
    )
    commands.append(
        _run_and_record(
            "capture_two",
            build_runtime_command(runtime_cmd_path, "--capture-diagnostic", "--diagnostics-out-dir", str(capture_two_dir)),
            runtime_cwd,
            output_root,
            timeout_seconds,
        )
    )
    commands.append(
        _run_and_record(
            "invalid_json_capture",
            build_runtime_command(
                runtime_cmd_path,
                "--load-state-json",
                str(invalid_json_path),
                "--capture-diagnostic",
                "--diagnostics-out-dir",
                str(output_root / "invalid_capture"),
            ),
            runtime_cwd,
            output_root,
            timeout_seconds,
        )
    )

    capture_one_state = capture_one_dir / "state.json"
    capture_two_state = capture_two_dir / "state.json"
    replay_record: Optional[dict[str, Any]] = None
    if capture_one_state.exists():
        replay_record = _run_and_record(
            "replay_one",
            build_runtime_command(
                runtime_cmd_path,
                "--load-state-json",
                str(capture_one_state),
                "--capture-diagnostic",
                "--diagnostics-out-dir",
                str(replay_one_dir),
            ),
            runtime_cwd,
            output_root,
            timeout_seconds,
        )
        commands.append(replay_record)

    comparison: Optional[dict[str, Any]] = None
    if capture_one_state.exists() and capture_two_state.exists():
        compare_result = compare_json_documents(
            capture_one_state.read_text(encoding="utf-8"),
            capture_two_state.read_text(encoding="utf-8"),
        )
        comparison = {
            "raw_equal": compare_result.raw_equal,
            "semantic_equal": compare_result.semantic_equal,
            "differences": [asdict(item) for item in compare_result.differences],
        }
        _write_json(output_root / "capture_comparison.json", comparison)

    summary = _build_summary(output_root, commands, cache_hit=False, cache_key=cache_key)
    _write_json(output_root / "summary.json", summary)
    cache_probe_output(cache_root, cache_key, output_root)
    return summary


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Run the Phase 0 runtime authority probe")
    parser.add_argument("--runtime-cmd", type=Path, default=DEFAULT_RUNTIME_CMD)
    parser.add_argument("--output-root", type=Path, default=WorkspaceLayout.from_repo_root().runtime_probe_root)
    parser.add_argument("--timeout-seconds", type=float, default=90.0)
    args = parser.parse_args(argv)
    summary = run_probe(args.runtime_cmd, args.output_root, args.timeout_seconds)
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

