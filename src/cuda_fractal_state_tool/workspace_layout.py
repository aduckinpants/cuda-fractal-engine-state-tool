from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional


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
