from __future__ import annotations

from pathlib import Path
from typing import Any

from .automated_run_store import DurableRunStore, _atomic_write, _json_bytes, _load_object, _utc_now
from .workspace_layout import initialize_workspace_root


RESEARCH_RUN_MANIFEST_VERSION = 1


class ResearchRunStore(DurableRunStore):
    """Question-run specialization over the canonical durable run-store owner."""

    @classmethod
    def create(
        cls,
        workspace_root: Path,
        *,
        run_id: str,
        protocol_snapshot: dict[str, Any],
        initial_packet: dict[str, Any],
        research_brief: dict[str, Any],
    ) -> "ResearchRunStore":
        workspace_root = workspace_root.resolve()
        initialize_workspace_root(workspace_root)
        if not run_id or Path(run_id).name != run_id:
            raise ValueError("Research run ID must be a safe directory name")
        run_dir = workspace_root / "question-runs" / run_id
        try:
            run_dir.mkdir(parents=True, exist_ok=False)
        except FileExistsError as exc:
            raise FileExistsError(f"Research run already exists: {run_dir}") from exc
        manifest = {
            "research_run_manifest_version": RESEARCH_RUN_MANIFEST_VERSION,
            "run_id": run_id,
            "created_at_utc": _utc_now(),
            "protocol_snapshot": protocol_snapshot,
            "initial_packet": initial_packet,
            "research_brief": research_brief,
        }
        _atomic_write(run_dir / "manifest.json", _json_bytes(manifest))
        (run_dir / "attempts").mkdir()
        return cls(run_dir=run_dir.resolve())

    @classmethod
    def open(cls, run_dir: Path) -> "ResearchRunStore":
        store = cls(run_dir=run_dir.resolve())
        manifest = _load_object(store.manifest_path, "Research run manifest")
        if manifest.get("research_run_manifest_version") != RESEARCH_RUN_MANIFEST_VERSION:
            raise ValueError("Unsupported research run manifest version")
        if manifest.get("run_id") != store.run_dir.name:
            raise ValueError("Research run identity disagrees with its directory")
        if not isinstance(manifest.get("research_brief"), dict):
            raise ValueError("Research run manifest has no sealed research brief")
        return store
