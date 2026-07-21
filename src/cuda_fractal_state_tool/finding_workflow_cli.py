from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Optional

from .finding_workflow import execute_imported_finding_workflow
from .runtime_surface import DEFAULT_RUNTIME_CMD


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Execute proposal_v1 replay-proof workflow for an imported finding",
    )
    parser.add_argument("--workspace-root", type=Path, required=True, help="Durable findings workspace root")
    parser.add_argument("--source-capture", type=Path, required=True, help="Capture folder or artifact path")
    parser.add_argument("--proposal", type=Path, required=True, help="Path to proposal JSON")
    parser.add_argument("--runtime-cmd", type=Path, default=DEFAULT_RUNTIME_CMD, help="Runtime command path")
    parser.add_argument("--timeout-seconds", type=float, default=90.0)
    parser.add_argument("--promotion-profile", type=str, default="none")
    parser.add_argument("--run-id", type=str, default=None, help="Optional run id token")
    args = parser.parse_args(argv)

    proposal_text = args.proposal.read_text(encoding="utf-8")
    result = execute_imported_finding_workflow(
        source_capture_path=args.source_capture,
        proposal_text=proposal_text,
        workspace_root=args.workspace_root,
        runtime_cmd_path=args.runtime_cmd,
        timeout_seconds=args.timeout_seconds,
        promotion_profile=args.promotion_profile,
        run_id=args.run_id,
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
