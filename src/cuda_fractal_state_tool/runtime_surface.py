from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from .process_utils import file_version


DEFAULT_RUNTIME_CMD = Path(r"D:\salt-fractal\cuda_newton_fractal_clone\runtime\fractal_ui.cmd")


@dataclass
class LauncherResolution:
    runtime_cmd_path: str
    launcher_directory: str
    active_file_path: Optional[str]
    active_entry: Optional[str]
    resolved_executable_path: Optional[str]
    repo_root_hint: Optional[str]
    runtime_schema_path: Optional[str]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(65536)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def resolve_launcher(runtime_cmd_path: Path) -> LauncherResolution:
    launcher_directory = runtime_cmd_path.parent
    active_file = launcher_directory / "fractal_ui_active.txt"
    active_entry: Optional[str] = None
    resolved_executable_path: Optional[str] = None
    if active_file.exists():
        active_entry = active_file.read_text(encoding="utf-8").strip() or None
        if active_entry:
            candidate = launcher_directory / active_entry
            if candidate.exists():
                resolved_executable_path = str(candidate)
    repo_root_file = launcher_directory / "fractal_ui_repo_root.txt"
    repo_root_hint = repo_root_file.read_text(encoding="utf-8").strip() if repo_root_file.exists() else None
    runtime_schema = launcher_directory / "ui" / "fractal_binding_surface_v1.ui_schema.json"
    return LauncherResolution(
        runtime_cmd_path=str(runtime_cmd_path),
        launcher_directory=str(launcher_directory),
        active_file_path=str(active_file) if active_file.exists() else None,
        active_entry=active_entry,
        resolved_executable_path=resolved_executable_path,
        repo_root_hint=repo_root_hint,
        runtime_schema_path=str(runtime_schema) if runtime_schema.exists() else None,
    )


def build_runtime_identity(runtime_cmd_path: Path, cwd: Path) -> dict[str, Any]:
    resolution = resolve_launcher(runtime_cmd_path)
    source_schema_path: Optional[str] = None
    source_schema_sha256: Optional[str] = None
    if resolution.repo_root_hint:
        source_schema = Path(resolution.repo_root_hint) / "ui" / "fractal_binding_surface_v1.ui_schema.json"
        if source_schema.exists():
            source_schema_path = str(source_schema)
            source_schema_sha256 = sha256_file(source_schema)
    identity: dict[str, Any] = {
        "launcher_path": str(runtime_cmd_path),
        "launcher_sha256": sha256_file(runtime_cmd_path),
        "working_directory": str(cwd),
        "resolved_executable_path": resolution.resolved_executable_path,
        "resolved_executable_sha256": None,
        "resolved_executable_file_version": None,
        "runtime_schema_path": resolution.runtime_schema_path,
        "runtime_schema_sha256": None,
        "source_schema_path": source_schema_path,
        "source_schema_sha256": source_schema_sha256,
        "describe_parameter_surface_sha256": None,
        "describe_functions_sha256": None,
    }
    if resolution.resolved_executable_path:
        exe_path = Path(resolution.resolved_executable_path)
        identity["resolved_executable_sha256"] = sha256_file(exe_path)
        identity["resolved_executable_file_version"] = file_version(exe_path)
    if resolution.runtime_schema_path:
        identity["runtime_schema_sha256"] = sha256_file(Path(resolution.runtime_schema_path))
    return identity


def build_runtime_command(runtime_cmd_path: Path, *args: str) -> list[str]:
    return ["cmd.exe", "/d", "/c", str(runtime_cmd_path), *args]


def build_replay_command(runtime_cmd_path: Path, candidate_path: Path, replay_dir: Path) -> list[str]:
    return build_runtime_command(
        runtime_cmd_path,
        "--load-state-json",
        os.path.abspath(str(candidate_path)),
        "--capture-diagnostic",
        "--diagnostics-out-dir",
        os.path.abspath(str(replay_dir)),
    )


def build_detached_viewer_launch_command(runtime_cmd_path: Path, state_path: Path) -> list[str]:
    return build_runtime_command(runtime_cmd_path, "--load-state-json", os.path.abspath(str(state_path)))
