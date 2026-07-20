from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .json_utils import loads_no_duplicates
from .proposal import ProposalV1


@dataclass(frozen=True)
class MaterializationResult:
    output_path: Path
    byte_identical_to_baseline: bool


def _set_exact_path(document: dict[str, Any], path: str, value: Any) -> None:
    parts = path.split(".")
    current: Any = document
    for part in parts[:-1]:
        if not isinstance(current, dict) or part not in current:
            raise ValueError(f"Materialization path is missing in the baseline: {path}")
        current = current[part]
    last = parts[-1]
    if not isinstance(current, dict) or last not in current:
        raise ValueError(f"Materialization path is missing in the baseline: {path}")
    current[last] = value


def materialize_transport_candidate(baseline_path: Path, proposal: ProposalV1, output_path: Path) -> MaterializationResult:
    baseline_path = baseline_path.resolve()
    output_path = output_path.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if not proposal.overrides:
        shutil.copyfile(baseline_path, output_path)
        return MaterializationResult(output_path=output_path, byte_identical_to_baseline=True)

    baseline_document = loads_no_duplicates(baseline_path.read_text(encoding="utf-8"))
    if not isinstance(baseline_document, dict):
        raise ValueError("Frozen baseline must be a JSON object")
    for path, value in proposal.overrides.items():
        if path == "color_pipeline_draft":
            baseline_document[path] = value
            continue
        _set_exact_path(baseline_document, path, value)
    output_path.write_text(json.dumps(baseline_document, indent=2) + "\n", encoding="utf-8")
    return MaterializationResult(output_path=output_path, byte_identical_to_baseline=False)
