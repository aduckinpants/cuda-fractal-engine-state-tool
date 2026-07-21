from __future__ import annotations

import hashlib
import json
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
    ui_salt_contract_path: Optional[str]


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
    ui_salt_contract = (
        launcher_directory
        / "ui_salt"
        / "generated"
        / "color_pipeline_function_library.contract.v1.json"
    )
    return LauncherResolution(
        runtime_cmd_path=str(runtime_cmd_path),
        launcher_directory=str(launcher_directory),
        active_file_path=str(active_file) if active_file.exists() else None,
        active_entry=active_entry,
        resolved_executable_path=resolved_executable_path,
        repo_root_hint=repo_root_hint,
        runtime_schema_path=str(runtime_schema) if runtime_schema.exists() else None,
        ui_salt_contract_path=str(ui_salt_contract) if ui_salt_contract.exists() else None,
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
        "ui_salt_contract_path": resolution.ui_salt_contract_path,
        "ui_salt_contract_sha256": None,
        "describe_parameter_surface_sha256": None,
        "describe_functions_sha256": None,
    }
    if resolution.resolved_executable_path:
        exe_path = Path(resolution.resolved_executable_path)
        identity["resolved_executable_sha256"] = sha256_file(exe_path)
        identity["resolved_executable_file_version"] = file_version(exe_path)
    if resolution.runtime_schema_path:
        identity["runtime_schema_sha256"] = sha256_file(Path(resolution.runtime_schema_path))
    if resolution.ui_salt_contract_path:
        identity["ui_salt_contract_sha256"] = sha256_file(Path(resolution.ui_salt_contract_path))
    return identity


def runtime_identity_summary(identity: dict[str, Any]) -> dict[str, Any]:
    """Return the stable runtime fields carried by immutable Packet V6 bindings."""
    return {
        "launcher_sha256": identity.get("launcher_sha256"),
        "resolved_executable_sha256": identity.get("resolved_executable_sha256"),
        "resolved_executable_file_version": identity.get("resolved_executable_file_version"),
        "runtime_schema_sha256": identity.get("runtime_schema_sha256"),
        "ui_salt_contract_sha256": identity.get("ui_salt_contract_sha256"),
    }


def runtime_identity_summary_sha256(summary: dict[str, Any]) -> str:
    payload = (
        json.dumps(summary, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n"
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


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
