from __future__ import annotations

import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .json_utils import dumps_pretty, loads_no_duplicates
from .runtime_surface import sha256_file


BASELINE_ID = "runtime-default-v1"
BASELINE_ROLE = "runtime-default"


@dataclass
class FrozenBaseline:
    baseline_id: str
    state_path: Path
    manifest_path: Path
    manifest: dict[str, Any]


def _utc_iso(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()


def freeze_phase0_baseline(probe_root: Path, baselines_root: Path, baseline_id: str = BASELINE_ID) -> FrozenBaseline:
    probe_root = probe_root.resolve()
    baselines_root = baselines_root.resolve()
    source_state = probe_root / "capture_one" / "state.json"
    replay_state = probe_root / "replay_one" / "state.json"
    runtime_identity_path = probe_root / "runtime_identity.json"
    summary_path = probe_root / "summary.json"
    if not source_state.exists():
        raise FileNotFoundError(f"Expected Phase 0 baseline candidate is missing: {source_state}")
    if not replay_state.exists():
        raise FileNotFoundError(f"Expected Phase 0 replay proof artifact is missing: {replay_state}")
    if not runtime_identity_path.exists():
        raise FileNotFoundError(f"Expected runtime identity manifest is missing: {runtime_identity_path}")
    if not summary_path.exists():
        raise FileNotFoundError(f"Expected Phase 0 summary manifest is missing: {summary_path}")

    runtime_identity = loads_no_duplicates(runtime_identity_path.read_text(encoding="utf-8"))
    summary = loads_no_duplicates(summary_path.read_text(encoding="utf-8"))
    if not isinstance(summary, dict) or not summary.get("replay_one_state_exists"):
        raise ValueError("Phase 0 evidence does not show a replay-proven baseline candidate")

    baseline_dir = baselines_root / baseline_id
    baseline_dir.mkdir(parents=True, exist_ok=True)
    frozen_state = baseline_dir / "state.json"
    manifest_path = baseline_dir / "manifest.json"

    if frozen_state.exists():
        existing_hash = sha256_file(frozen_state)
        source_hash = sha256_file(source_state)
        if existing_hash != source_hash:
            raise ValueError("Frozen baseline already exists with different contents; refusing in-place replacement")
    else:
        shutil.copyfile(source_state, frozen_state)

    manifest = {
        "baseline_id": baseline_id,
        "baseline_role": BASELINE_ROLE,
        "state_sha256": sha256_file(frozen_state),
        "runtime_identity": runtime_identity,
        "source_probe_path": str(probe_root),
        "source_state_path": str(source_state),
        "source_replay_state_path": str(replay_state),
        "capture_timestamp_utc": _utc_iso(source_state.stat().st_mtime),
        "freeze_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "replay_proven": True,
    }
    manifest_path.write_text(dumps_pretty(manifest), encoding="utf-8")
    return FrozenBaseline(baseline_id=baseline_id, state_path=frozen_state, manifest_path=manifest_path, manifest=manifest)


def load_frozen_baseline(manifest_path: Path) -> FrozenBaseline:
    manifest_path = manifest_path.resolve()
    manifest = loads_no_duplicates(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict):
        raise ValueError("Baseline manifest must be a JSON object")
    baseline_id = manifest.get("baseline_id")
    state_path = manifest_path.with_name("state.json")
    if not state_path.exists():
        raise FileNotFoundError(f"Frozen baseline state is missing: {state_path}")
    expected_hash = manifest.get("state_sha256")
    if expected_hash != sha256_file(state_path):
        raise ValueError("Frozen baseline hash no longer matches its manifest")
    return FrozenBaseline(baseline_id=baseline_id, state_path=state_path, manifest_path=manifest_path, manifest=manifest)
