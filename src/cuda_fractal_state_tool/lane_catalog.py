from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .json_utils import loads_no_duplicates


@dataclass(frozen=True)
class LaneFunction:
    lane_id: str
    function_id: str


@dataclass(frozen=True)
class LaneCatalog:
    shape: str
    entries: tuple[LaneFunction, ...]


class LaneCatalogError(ValueError):
    pass


class RuntimeMetadataUnavailableError(LaneCatalogError):
    pass


class RuntimeMetadataShapeUnsupportedError(LaneCatalogError):
    pass


def _ensure_str(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RuntimeMetadataShapeUnsupportedError(f"Expected non-empty string for {field_name}")
    return value


def _collect_from_lane_functions(payload: Any) -> list[LaneFunction]:
    if not isinstance(payload, list):
        raise RuntimeMetadataShapeUnsupportedError("Expected list payload for lane/function metadata")
    entries: list[LaneFunction] = []
    for item in payload:
        if not isinstance(item, dict):
            raise RuntimeMetadataShapeUnsupportedError("Expected object entries in lane/function metadata list")
        lane_id = _ensure_str(item.get("lane_id"), "lane_id")
        function_id = _ensure_str(item.get("function_id"), "function_id")
        entries.append(LaneFunction(lane_id=lane_id, function_id=function_id))
    return entries


def _collect_from_functions(payload: Any) -> list[LaneFunction]:
    if not isinstance(payload, list):
        raise RuntimeMetadataShapeUnsupportedError("Expected list payload for functions metadata")
    entries: list[LaneFunction] = []
    for item in payload:
        if not isinstance(item, dict):
            raise RuntimeMetadataShapeUnsupportedError("Expected object entries in functions metadata list")
        lane_id = _ensure_str(item.get("lane_id"), "lane_id")
        function_id = _ensure_str(item.get("id"), "id")
        entries.append(LaneFunction(lane_id=lane_id, function_id=function_id))
    return entries


def _collect_from_color_pipeline_draft(payload: Any) -> list[LaneFunction]:
    if not isinstance(payload, dict):
        raise RuntimeMetadataShapeUnsupportedError("Expected object payload for color_pipeline_draft metadata")
    lanes = payload.get("lanes")
    if not isinstance(lanes, list):
        raise RuntimeMetadataShapeUnsupportedError("Expected lanes list in color_pipeline_draft metadata")

    entries: list[LaneFunction] = []
    for lane in lanes:
        if not isinstance(lane, dict):
            raise RuntimeMetadataShapeUnsupportedError("Expected lane object in color_pipeline_draft metadata")
        lane_id = _ensure_str(lane.get("lane_id"), "lane_id")
        functions = lane.get("functions")
        if not isinstance(functions, list):
            raise RuntimeMetadataShapeUnsupportedError("Expected functions list for lane in color_pipeline_draft metadata")
        for function in functions:
            if isinstance(function, str):
                function_id = _ensure_str(function, "function")
            elif isinstance(function, dict):
                function_id = _ensure_str(function.get("function_id") or function.get("id"), "function_id")
            else:
                raise RuntimeMetadataShapeUnsupportedError("Expected string/object function entries")
            entries.append(LaneFunction(lane_id=lane_id, function_id=function_id))
    return entries


def parse_lane_catalog_payload(describe_functions_payload: Any) -> LaneCatalog:
    shape = ""
    entries: list[LaneFunction]

    if isinstance(describe_functions_payload, dict) and "lane_functions" in describe_functions_payload:
        shape = "lane_functions"
        entries = _collect_from_lane_functions(describe_functions_payload["lane_functions"])
    elif isinstance(describe_functions_payload, dict) and "functions" in describe_functions_payload:
        shape = "functions"
        entries = _collect_from_functions(describe_functions_payload["functions"])
    elif isinstance(describe_functions_payload, dict) and "color_pipeline_draft" in describe_functions_payload:
        shape = "color_pipeline_draft"
        entries = _collect_from_color_pipeline_draft(describe_functions_payload["color_pipeline_draft"])
    elif isinstance(describe_functions_payload, list):
        shape = "lane_functions"
        entries = _collect_from_lane_functions(describe_functions_payload)
    else:
        raise RuntimeMetadataShapeUnsupportedError("No supported lane/function metadata shape found")

    deduped = sorted({(item.lane_id, item.function_id) for item in entries})
    if not deduped:
        raise RuntimeMetadataShapeUnsupportedError("No lane/function entries were found")

    return LaneCatalog(shape=shape, entries=tuple(LaneFunction(lane_id=lane_id, function_id=function_id) for lane_id, function_id in deduped))


def load_lane_catalog_from_describe_functions(describe_functions_path: Path) -> LaneCatalog:
    path = describe_functions_path.resolve()
    if not path.exists():
        raise RuntimeMetadataUnavailableError(f"describe-functions file not found: {path}")
    payload = loads_no_duplicates(path.read_text(encoding="utf-8"))
    return parse_lane_catalog_payload(payload)


def lane_known(catalog: LaneCatalog, lane_id: str) -> bool:
    return any(entry.lane_id == lane_id for entry in catalog.entries)


def lane_function_known(catalog: LaneCatalog, lane_id: str, function_id: str) -> bool:
    return any(entry.lane_id == lane_id and entry.function_id == function_id for entry in catalog.entries)
