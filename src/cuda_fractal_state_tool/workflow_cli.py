from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .baseline import BASELINE_ID
from .runtime_surface import DEFAULT_RUNTIME_CMD
from .state_workflow import execute_proposal_workflow
from .workspace_layout import WorkspaceLayout


def _default_baseline_manifest(repo_root: Optional[Path]) -> Path:
    layout = WorkspaceLayout.from_repo_root(repo_root)
    return layout.baseline_manifest_path(BASELINE_ID)


def _default_working_root(repo_root: Optional[Path]) -> Path:
    layout = WorkspaceLayout.from_repo_root(repo_root)
    return layout.working_states_root


def _default_state_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_cli")


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Execute a proposal workflow from a proposal JSON file")
    parser.add_argument("--proposal", type=Path, required=True, help="Path to proposal JSON")
    parser.add_argument("--repo-root", type=Path, default=None, help="Optional repository root for default paths")
    parser.add_argument("--baseline-manifest", type=Path, default=None, help="Baseline manifest path")
    parser.add_argument("--working-root", type=Path, default=None, help="Working states root")
    parser.add_argument("--state-id", type=str, default=None, help="State run id (defaults to UTC timestamp)")
    parser.add_argument("--runtime-cmd", type=Path, default=DEFAULT_RUNTIME_CMD, help="Runtime command path")
    parser.add_argument("--timeout-seconds", type=float, default=90.0)
    parser.add_argument("--promotion-profile", type=str, default="none")
    args = parser.parse_args(argv)

    proposal_text = args.proposal.read_text(encoding="utf-8")
    baseline_manifest = args.baseline_manifest.resolve() if args.baseline_manifest else _default_baseline_manifest(args.repo_root)
    working_root = args.working_root.resolve() if args.working_root else _default_working_root(args.repo_root)
    state_id = args.state_id if args.state_id else _default_state_id()

    result = execute_proposal_workflow(
        proposal_text,
        baseline_manifest,
        working_root,
        state_id,
        runtime_cmd_path=args.runtime_cmd,
        timeout_seconds=args.timeout_seconds,
        promotion_profile=args.promotion_profile,
    )

    payload = {
        "status": result.status,
        "runtime_status": result.runtime_status,
        "promotion_profile": result.promotion_profile,
        "working_state_dir": str(result.working_state_dir.resolve()),
        "validation_run_dir": str(result.validation_run_dir.resolve()),
        "validation_run_manifest_path": str(result.validation_run_manifest_path.resolve()),
        "validation_runs_index_path": str(result.validation_runs_index_path.resolve()),
        "transport_candidate_path": str(result.transport_candidate_path.resolve()),
        "proven_state_path": str(result.proven_state_path.resolve()) if result.proven_state_path else None,
        "promoted_state_path": str(result.promoted_state_path.resolve()) if result.promoted_state_path else None,
        "promotion_report_path": str(result.promotion_report_path.resolve()) if result.promotion_report_path else None,
        "replay_state_path": str(result.replay_state_path.resolve()) if result.replay_state_path else None,
        "validation_path": str(result.validation_path.resolve()),
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if result.status == "runtime_proof_succeeded" else 2


if __name__ == "__main__":
    raise SystemExit(main())
