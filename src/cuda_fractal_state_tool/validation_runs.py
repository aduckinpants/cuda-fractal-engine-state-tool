from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Optional

from .workspace_layout import WorkspaceLayout


def validation_index_path(repo_root: Optional[Path] = None) -> Path:
    layout = WorkspaceLayout.from_repo_root(repo_root)
    return layout.validation_runs_root / "index.json"


def load_validation_index(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"entries": []}
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        return {"entries": []}
    entries = raw.get("entries")
    if not isinstance(entries, list):
        raw["entries"] = []
    return raw


def list_validation_runs(path: Path) -> list[dict[str, Any]]:
    index = load_validation_index(path)
    entries = index.get("entries", [])
    if not isinstance(entries, list):
        return []
    normalized = [entry for entry in entries if isinstance(entry, dict)]
    normalized.sort(key=lambda item: str(item.get("timestamp_utc") or ""), reverse=True)
    return normalized


def latest_validation_run(path: Path) -> Optional[dict[str, Any]]:
    runs = list_validation_runs(path)
    return runs[0] if runs else None


def summarize_validation_runs(path: Path) -> dict[str, Any]:
    runs = list_validation_runs(path)
    status_counts: dict[str, int] = {}
    runtime_status_counts: dict[str, int] = {}
    for run in runs:
        status = str(run.get("status") or "unknown")
        runtime_status = str(run.get("runtime_status") or "unknown")
        status_counts[status] = status_counts.get(status, 0) + 1
        runtime_status_counts[runtime_status] = runtime_status_counts.get(runtime_status, 0) + 1
    return {
        "index_path": str(path.resolve()),
        "run_count": len(runs),
        "status_counts": status_counts,
        "runtime_status_counts": runtime_status_counts,
        "latest_run": latest_validation_run(path),
    }


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Inspect validation-run index artifacts")
    parser.add_argument("--repo-root", type=Path, default=None)
    parser.add_argument("--index", type=Path, default=None, help="Override index path")
    parser.add_argument("--latest", action="store_true", help="Print only the latest run entry")
    args = parser.parse_args(argv)

    index_path = args.index.resolve() if args.index else validation_index_path(args.repo_root)
    if args.latest:
        latest = latest_validation_run(index_path)
        print(json.dumps(latest, indent=2, sort_keys=True))
        return 0

    summary = summarize_validation_runs(index_path)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
