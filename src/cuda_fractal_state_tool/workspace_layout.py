from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Optional


WORKSPACE_MARKER_FILENAME = ".cuda-fractal-state-workspace.json"
WORKSPACE_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class WorkspaceLayout:
    repo_root: Path
    data_root: Path
    runtime_probe_root: Path
    baselines_root: Path
    cache_root: Path
    validation_runs_root: Path
    working_states_root: Path

    @classmethod
    def from_repo_root(cls, repo_root: Optional[Path] = None) -> "WorkspaceLayout":
        root = (repo_root or Path.cwd()).resolve()
        data_root = root / ".local"
        return cls(
            repo_root=root,
            data_root=data_root,
            runtime_probe_root=data_root / "runtime_probe",
            baselines_root=data_root / "baselines",
            cache_root=data_root / "cache",
            validation_runs_root=data_root / "validation_runs",
            working_states_root=data_root / "working_states",
        )

    def baseline_manifest_path(self, baseline_id: str) -> Path:
        return self.baselines_root / baseline_id / "manifest.json"

    def validation_run_dir(self, run_id: str) -> Path:
        return self.validation_runs_root / run_id

    def working_state_dir(self, state_id: str) -> Path:
        return self.working_states_root / state_id

    def cache_namespace_dir(self, namespace: str) -> Path:
        return self.cache_root / namespace

    def cache_dir(self, namespace: str, cache_key: str) -> Path:
        return self.cache_namespace_dir(namespace) / cache_key


def workspace_marker_path(workspace_root: Path) -> Path:
    return workspace_root.resolve() / WORKSPACE_MARKER_FILENAME


def initialize_workspace_root(workspace_root: Path, tool_name: str = "cuda-fractal-state-tool") -> Path:
    root = workspace_root.resolve()
    if root.exists() and not root.is_dir():
        raise ValueError(f"Workspace root is not a directory: {root}")

    root.mkdir(parents=True, exist_ok=True)
    marker_path = workspace_marker_path(root)

    if marker_path.exists():
        marker = json.loads(marker_path.read_text(encoding="utf-8"))
        if not isinstance(marker, dict):
            raise ValueError(f"Workspace marker is not a JSON object: {marker_path}")
        if marker.get("workspace_schema_version") != WORKSPACE_SCHEMA_VERSION:
            raise ValueError(
                "Workspace marker schema version mismatch: "
                f"expected {WORKSPACE_SCHEMA_VERSION}, got {marker.get('workspace_schema_version')}"
            )
        return marker_path

    if any(root.iterdir()):
        raise ValueError(
            "Workspace root is non-empty and not initialized. "
            f"Refusing broad writes: {root}"
        )

    marker = {
        "workspace_schema_version": WORKSPACE_SCHEMA_VERSION,
        "tool": tool_name,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    marker_path.write_text(json.dumps(marker, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return marker_path
