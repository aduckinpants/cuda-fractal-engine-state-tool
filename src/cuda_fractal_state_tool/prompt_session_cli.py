from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any, Optional

from .baseline import BASELINE_ID
from .runtime_surface import DEFAULT_RUNTIME_CMD
from .state_workflow import WorkflowResult, execute_proposal_workflow
from .workspace_layout import WorkspaceLayout


def _default_baseline_manifest(repo_root: Optional[Path]) -> Path:
    layout = WorkspaceLayout.from_repo_root(repo_root)
    return layout.baseline_manifest_path(BASELINE_ID)


def _default_working_root(repo_root: Optional[Path]) -> Path:
    layout = WorkspaceLayout.from_repo_root(repo_root)
    return layout.working_states_root


def _load_pack(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Prompt session pack root must be an object")
    cases = payload.get("cases")
    if not isinstance(cases, list) or not cases:
        raise ValueError("Prompt session pack requires a non-empty cases array")
    for index, case in enumerate(cases):
        if not isinstance(case, dict):
            raise ValueError(f"Case at index {index} must be an object")
        if not isinstance(case.get("case_id"), str) or not case["case_id"].strip():
            raise ValueError(f"Case at index {index} requires non-empty case_id")
        if not isinstance(case.get("proposal_path"), str) or not case["proposal_path"].strip():
            raise ValueError(f"Case {case.get('case_id', index)} requires proposal_path")
        if not isinstance(case.get("state_id"), str) or not case["state_id"].strip():
            raise ValueError(f"Case {case.get('case_id', index)} requires state_id")
    return payload


def _run_case(
    case: dict[str, Any],
    baseline_manifest: Path,
    working_root: Path,
    runtime_cmd: Path,
    timeout_seconds: float,
) -> dict[str, Any]:
    case_id = str(case["case_id"])
    proposal_path = Path(str(case["proposal_path"])).resolve()
    state_id = str(case["state_id"])
    promotion_profile = str(case.get("promotion_profile") or "none")
    expected_status = case.get("expected_status")
    expected_runtime_status = case.get("expected_runtime_status")

    proposal_text = proposal_path.read_text(encoding="utf-8")
    result: WorkflowResult = execute_proposal_workflow(
        proposal_text,
        baseline_manifest,
        working_root,
        state_id,
        runtime_cmd_path=runtime_cmd,
        timeout_seconds=timeout_seconds,
        promotion_profile=promotion_profile,
    )

    checks: list[dict[str, Any]] = []
    if isinstance(expected_status, str):
        checks.append(
            {
                "name": "status",
                "expected": expected_status,
                "actual": result.status,
                "ok": result.status == expected_status,
            }
        )
    if isinstance(expected_runtime_status, str):
        checks.append(
            {
                "name": "runtime_status",
                "expected": expected_runtime_status,
                "actual": result.runtime_status,
                "ok": result.runtime_status == expected_runtime_status,
            }
        )

    checks_ok = all(bool(item["ok"]) for item in checks)
    return {
        "case_id": case_id,
        "state_id": state_id,
        "proposal_path": str(proposal_path),
        "promotion_profile": promotion_profile,
        "status": result.status,
        "runtime_status": result.runtime_status,
        "validation_path": str(result.validation_path.resolve()),
        "validation_run_manifest_path": str(result.validation_run_manifest_path.resolve()),
        "validation_runs_index_path": str(result.validation_runs_index_path.resolve()),
        "checks": checks,
        "ok": checks_ok,
    }


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Execute prompt-session test packs against proposal/workflow runtime proof path",
        epilog="Returns non-zero when any case expectation fails.",
    )
    parser.add_argument("--pack", type=Path, required=True, help="Path to prompt session pack JSON")
    parser.add_argument("--repo-root", type=Path, default=None, help="Optional repository root for default paths")
    parser.add_argument("--baseline-manifest", type=Path, default=None, help="Baseline manifest path")
    parser.add_argument("--working-root", type=Path, default=None, help="Working states root")
    parser.add_argument("--runtime-cmd", type=Path, default=DEFAULT_RUNTIME_CMD, help="Runtime command path")
    parser.add_argument("--timeout-seconds", type=float, default=90.0)
    parser.add_argument("--out", type=Path, default=None, help="Optional output report path")
    args = parser.parse_args(argv)

    pack_path = args.pack.resolve()
    pack = _load_pack(pack_path)
    baseline_manifest = args.baseline_manifest.resolve() if args.baseline_manifest else _default_baseline_manifest(args.repo_root)
    working_root = args.working_root.resolve() if args.working_root else _default_working_root(args.repo_root)

    case_reports: list[dict[str, Any]] = []
    for case in pack["cases"]:
        case_reports.append(
            _run_case(
                case,
                baseline_manifest,
                working_root,
                args.runtime_cmd,
                args.timeout_seconds,
            )
        )

    overall_ok = all(bool(item["ok"]) for item in case_reports)
    report = {
        "pack_path": str(pack_path),
        "session_id": pack.get("session_id"),
        "case_count": len(case_reports),
        "ok": overall_ok,
        "cases": case_reports,
    }

    rendered = json.dumps(report, indent=2, sort_keys=True)
    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0 if overall_ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
