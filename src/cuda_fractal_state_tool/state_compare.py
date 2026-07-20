from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from .json_utils import loads_no_duplicates


LOADER_TOP_LEVEL_KEYS = {
    "state_version",
    "fractal_type",
    "view",
    "params",
    "render",
    "lens",
    "sidecar_orientation",
    "sidecar_auto_demo_policy",
    "sidecar_mutation_history",
    "color_pipeline_draft",
}


@dataclass
class PathDifference:
    path: str
    left: Any
    right: Any
    classification: str


@dataclass
class DocumentComparison:
    raw_equal: bool
    semantic_equal: bool
    differences: list[PathDifference]


def _flatten(value: Any, prefix: str = "") -> Iterable[tuple[str, Any]]:
    if isinstance(value, dict):
        for key in sorted(value.keys()):
            next_prefix = f"{prefix}.{key}" if prefix else key
            yield from _flatten(value[key], next_prefix)
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            next_prefix = f"{prefix}[{index}]"
            yield from _flatten(item, next_prefix)
        return
    yield prefix, value


def _classify_path(path: str) -> str:
    if path == "stats" or path.startswith("stats."):
        return "volatile_diagnostic_data"
    top_level = path.split(".", 1)[0]
    if top_level not in LOADER_TOP_LEVEL_KEYS:
        return "capture_metadata"
    return "stable_authoring_state"


def _semantic_subset(document: dict[str, Any]) -> dict[str, Any]:
    return {key: document[key] for key in document.keys() if key in LOADER_TOP_LEVEL_KEYS}


def compare_json_documents(left_text: str, right_text: str) -> DocumentComparison:
    left = loads_no_duplicates(left_text)
    right = loads_no_duplicates(right_text)
    if not isinstance(left, dict) or not isinstance(right, dict):
        raise ValueError("Top-level JSON documents must be objects for state comparison")

    left_flat = dict(_flatten(left))
    right_flat = dict(_flatten(right))
    all_paths = sorted(set(left_flat.keys()) | set(right_flat.keys()))
    differences: list[PathDifference] = []
    for path in all_paths:
        left_value = left_flat.get(path)
        right_value = right_flat.get(path)
        if left_value != right_value:
            differences.append(
                PathDifference(
                    path=path,
                    left=left_value,
                    right=right_value,
                    classification=_classify_path(path),
                )
            )

    semantic_equal = _semantic_subset(left) == _semantic_subset(right)
    return DocumentComparison(raw_equal=left_text == right_text, semantic_equal=semantic_equal, differences=differences)
