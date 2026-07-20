from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Optional

from .json_utils import dumps_pretty
from .process_utils import run_command
from .runtime_surface import (
    DEFAULT_RUNTIME_CMD,
    build_runtime_command,
    build_runtime_identity,
    resolve_launcher,
    sha256_file,
)
from .state_compare import compare_json_documents


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dumps_pretty(value), encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _sanitize_command(command: list[str]) -> list[str]:
    return command


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
    _write_json(output_root / f"{name}.json", record)
    return record


def run_probe(runtime_cmd_path: Path, output_root: Path, timeout_seconds: float = 90.0) -> dict[str, Any]:
    output_root = output_root.resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    runtime_cwd = runtime_cmd_path.parent
    identity = build_runtime_identity(runtime_cmd_path, runtime_cwd)

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

    summary = {
        "runtime_identity_path": str((output_root / "runtime_identity.json").resolve()),
        "launcher_resolution_path": str((output_root / "launcher_resolution.json").resolve()),
        "commands": commands,
        "capture_comparison_path": str((output_root / "capture_comparison.json").resolve()) if comparison else None,
        "capture_one_state_exists": capture_one_state.exists(),
        "capture_two_state_exists": capture_two_state.exists(),
        "replay_one_state_exists": (replay_one_dir / "state.json").exists(),
    }
    _write_json(output_root / "summary.json", summary)
    return summary


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Run the Phase 0 runtime authority probe")
    parser.add_argument("--runtime-cmd", type=Path, default=DEFAULT_RUNTIME_CMD)
    parser.add_argument("--output-root", type=Path, default=Path(".local") / "runtime_probe")
    parser.add_argument("--timeout-seconds", type=float, default=90.0)
    args = parser.parse_args(argv)
    summary = run_probe(args.runtime_cmd, args.output_root, args.timeout_seconds)
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

