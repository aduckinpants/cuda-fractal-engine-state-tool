from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .finding_workspace import SourceCaptureImporter, build_validation_run_id, compute_proposal_id
from .proposal import parse_proposal_v1
from .runtime_surface import DEFAULT_RUNTIME_CMD
from .state_workflow import WorkflowResult, execute_proposal_workflow


def _load_workspace_manifest(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Finding workspace manifest must be a JSON object: {path}")
    return payload


def _build_authoring_base_manifest(finding_id: str, finding_manifest: dict[str, Any], finding_dir: Path) -> Path:
    authoring_base = finding_manifest.get("authoring_base")
    if not isinstance(authoring_base, dict):
        raise ValueError("Finding workspace manifest is missing authoring_base")
    state_rel = authoring_base.get("state_path")
    state_sha256 = authoring_base.get("sha256")
    if not isinstance(state_rel, str) or not state_rel:
        raise ValueError("Finding workspace manifest authoring_base.state_path must be a non-empty string")
    if not isinstance(state_sha256, str) or not state_sha256:
        raise ValueError("Finding workspace manifest authoring_base.sha256 must be a non-empty string")

    manifest = {
        "baseline_id": finding_id,
        "baseline_role": "imported-finding-authoring-base",
        "state_sha256": state_sha256,
        "state_path": state_rel,
        "finding_id": finding_id,
    }
    path = finding_dir / "authoring_base_manifest.json"
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def execute_imported_finding_workflow(
    source_capture_path: Path,
    proposal_text: str,
    workspace_root: Path,
    runtime_cmd_path: Path = DEFAULT_RUNTIME_CMD,
    timeout_seconds: float = 90.0,
    promotion_profile: str = "none",
    run_id: str | None = None,
) -> WorkflowResult:
    importer = SourceCaptureImporter(workspace_root)
    import_result = importer.import_capture(source_capture_path)
    finding_manifest = _load_workspace_manifest(import_result.workspace_manifest_path)
    finding_dir = import_result.finding_dir
    finding_id = import_result.finding_id
    base_sha256 = import_result.authoring_base_state_sha256

    proposal = parse_proposal_v1(proposal_text, finding_id, base_sha256)
    proposal_id = compute_proposal_id(proposal, finding_id, base_sha256)
    proposal_dir = finding_dir / "proposals" / proposal_id
    proposal_dir.mkdir(parents=True, exist_ok=True)
    (proposal_dir / "proposal.json").write_text(proposal.raw_text, encoding="utf-8")

    baseline_manifest = _build_authoring_base_manifest(finding_id, finding_manifest, finding_dir)

    run_token = run_id if run_id else build_validation_run_id()
    state_id = f"{proposal_id}_{run_token}"
    working_states_root = proposal_dir / "validation_runs"
    result = execute_proposal_workflow(
        proposal_text=proposal.raw_text,
        baseline_manifest_path=baseline_manifest,
        working_states_root=working_states_root,
        state_id=state_id,
        runtime_cmd_path=runtime_cmd_path,
        timeout_seconds=timeout_seconds,
        promotion_profile=promotion_profile,
    )
    return result
