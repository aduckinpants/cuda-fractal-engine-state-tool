from __future__ import annotations

import argparse
import json
from datetime import datetime
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


def _parse_timestamp(value: Optional[str]) -> Optional[datetime]:
    if value is None:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _matches_filter(
    run: dict[str, Any],
    status: Optional[str],
    runtime_status: Optional[str],
    promotion_profile: Optional[str],
    since: Optional[str],
    until: Optional[str],
) -> bool:
    if status is not None and str(run.get("status") or "") != status:
        return False
    if runtime_status is not None and str(run.get("runtime_status") or "") != runtime_status:
        return False
    if promotion_profile is not None and str(run.get("promotion_profile") or "") != promotion_profile:
        return False
    if since is not None or until is not None:
        run_ts = _parse_timestamp(run.get("timestamp_utc"))
        if run_ts is None:
            return False
        since_ts = _parse_timestamp(since)
        until_ts = _parse_timestamp(until)
        if since is not None and since_ts is None:
            raise ValueError(f"Invalid --since timestamp: {since}")
        if until is not None and until_ts is None:
            raise ValueError(f"Invalid --until timestamp: {until}")
        if since_ts is not None and run_ts < since_ts:
            return False
        if until_ts is not None and run_ts > until_ts:
            return False
    return True


def filter_validation_runs(
    runs: list[dict[str, Any]],
    *,
    status: Optional[str] = None,
    runtime_status: Optional[str] = None,
    promotion_profile: Optional[str] = None,
    since: Optional[str] = None,
    until: Optional[str] = None,
) -> list[dict[str, Any]]:
    return [
        run
        for run in runs
        if _matches_filter(
            run,
            status=status,
            runtime_status=runtime_status,
            promotion_profile=promotion_profile,
            since=since,
            until=until,
        )
    ]


def latest_validation_run(path: Path) -> Optional[dict[str, Any]]:
    runs = list_validation_runs(path)
    return runs[0] if runs else None


def latest_filtered_validation_run(
    path: Path,
    *,
    status: Optional[str] = None,
    runtime_status: Optional[str] = None,
    promotion_profile: Optional[str] = None,
    since: Optional[str] = None,
    until: Optional[str] = None,
) -> Optional[dict[str, Any]]:
    runs = filter_validation_runs(
        list_validation_runs(path),
        status=status,
        runtime_status=runtime_status,
        promotion_profile=promotion_profile,
        since=since,
        until=until,
    )
    return runs[0] if runs else None


def summarize_validation_runs(
    path: Path,
    *,
    status: Optional[str] = None,
    runtime_status: Optional[str] = None,
    promotion_profile: Optional[str] = None,
    since: Optional[str] = None,
    until: Optional[str] = None,
) -> dict[str, Any]:
    runs = filter_validation_runs(
        list_validation_runs(path),
        status=status,
        runtime_status=runtime_status,
        promotion_profile=promotion_profile,
        since=since,
        until=until,
    )
    status_counts: dict[str, int] = {}
    runtime_status_counts: dict[str, int] = {}
    promotion_profile_counts: dict[str, int] = {}
    draft_run_count = 0
    draft_lane_total = 0
    latest_draft_run: Optional[dict[str, Any]] = None
    for run in runs:
        status = str(run.get("status") or "unknown")
        runtime_status = str(run.get("runtime_status") or "unknown")
        profile = str(run.get("promotion_profile") or "none")
        status_counts[status] = status_counts.get(status, 0) + 1
        runtime_status_counts[runtime_status] = runtime_status_counts.get(runtime_status, 0) + 1
        promotion_profile_counts[profile] = promotion_profile_counts.get(profile, 0) + 1
        if bool(run.get("draft_override_present")):
            draft_run_count += 1
            draft_lane_total += int(run.get("draft_lane_count") or 0)
            if latest_draft_run is None:
                latest_draft_run = run
    return {
        "index_path": str(path.resolve()),
        "run_count": len(runs),
        "filters": {
            "status": status,
            "runtime_status": runtime_status,
            "promotion_profile": promotion_profile,
            "since": since,
            "until": until,
        },
        "status_counts": status_counts,
        "runtime_status_counts": runtime_status_counts,
        "promotion_profile_counts": promotion_profile_counts,
        "draft_run_count": draft_run_count,
        "draft_lane_total": draft_lane_total,
        "latest_draft_run": latest_draft_run,
        "latest_run": runs[0] if runs else None,
    }


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Inspect validation-run index artifacts")
    parser.add_argument("--repo-root", type=Path, default=None)
    parser.add_argument("--index", type=Path, default=None, help="Override index path")
    parser.add_argument("--list", action="store_true", help="Print filtered run entries")
    parser.add_argument("--limit", type=int, default=None, help="Limit list output to the first N runs")
    parser.add_argument("--latest", action="store_true", help="Print only the latest run entry")
    parser.add_argument("--status", type=str, default=None, help="Filter by validation status")
    parser.add_argument("--runtime-status", type=str, default=None, help="Filter by runtime status")
    parser.add_argument("--promotion-profile", type=str, default=None, help="Filter by promotion profile")
    parser.add_argument("--since", type=str, default=None, help="Include runs at or after this ISO timestamp")
    parser.add_argument("--until", type=str, default=None, help="Include runs at or before this ISO timestamp")
    args = parser.parse_args(argv)

    index_path = args.index.resolve() if args.index else validation_index_path(args.repo_root)
    if args.list:
        runs = filter_validation_runs(
            list_validation_runs(index_path),
            status=args.status,
            runtime_status=args.runtime_status,
            promotion_profile=args.promotion_profile,
            since=args.since,
            until=args.until,
        )
        if args.limit is not None:
            runs = runs[: max(args.limit, 0)]
        print(json.dumps(runs, indent=2, sort_keys=True))
        return 0

    if args.latest:
        latest = latest_filtered_validation_run(
            index_path,
            status=args.status,
            runtime_status=args.runtime_status,
            promotion_profile=args.promotion_profile,
            since=args.since,
            until=args.until,
        )
        print(json.dumps(latest, indent=2, sort_keys=True))
        return 0

    summary = summarize_validation_runs(
        index_path,
        status=args.status,
        runtime_status=args.runtime_status,
        promotion_profile=args.promotion_profile,
        since=args.since,
        until=args.until,
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
