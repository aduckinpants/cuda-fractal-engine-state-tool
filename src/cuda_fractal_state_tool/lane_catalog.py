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
class LaneDefinition:
    lane_id: str
    default_function_id: str
    function_ids: tuple[str, ...]


@dataclass(frozen=True)
class LaneCatalog:
    shape: str
    lanes: tuple[LaneDefinition, ...]
    entries: tuple[LaneFunction, ...]


class LaneCatalogError(ValueError):
    pass


class RuntimeMetadataUnavailableError(LaneCatalogError):
    pass


class RuntimeMetadataShapeUnsupportedError(LaneCatalogError):
    pass


class LaneUnknownError(LaneCatalogError):
    pass


class FunctionUnknownError(LaneCatalogError):
    pass


def _non_empty_string(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RuntimeMetadataShapeUnsupportedError(f"Expected non-empty string for {field_name}")
    return value


def parse_ui_salt_contract_payload(payload: Any) -> LaneCatalog:
    if not isinstance(payload, dict):
        raise RuntimeMetadataShapeUnsupportedError("UI-Salt contract root must be an object")
    function_library = payload.get("function_library")
    if not isinstance(function_library, dict):
        raise RuntimeMetadataShapeUnsupportedError("UI-Salt contract is missing function_library")
    lane_payloads = function_library.get("lanes")
    if not isinstance(lane_payloads, list) or not lane_payloads:
        raise RuntimeMetadataShapeUnsupportedError("UI-Salt function_library.lanes must be a non-empty array")

    lanes: list[LaneDefinition] = []
    entries: list[LaneFunction] = []
    seen_lane_ids: set[str] = set()
    for lane_index, lane_payload in enumerate(lane_payloads):
        if not isinstance(lane_payload, dict):
            raise RuntimeMetadataShapeUnsupportedError(
                f"UI-Salt function_library.lanes[{lane_index}] must be an object"
            )
        lane_id = _non_empty_string(lane_payload.get("id"), f"lanes[{lane_index}].id")
        if lane_id in seen_lane_ids:
            raise RuntimeMetadataShapeUnsupportedError(f"Duplicate UI-Salt lane id: {lane_id}")
        seen_lane_ids.add(lane_id)
        default_function_id = _non_empty_string(
            lane_payload.get("default"), f"lanes[{lane_index}].default"
        )
        function_payloads = lane_payload.get("functions")
        if not isinstance(function_payloads, list) or not function_payloads:
            raise RuntimeMetadataShapeUnsupportedError(
                f"UI-Salt lane {lane_id} must contain a non-empty functions array"
            )
        function_ids: list[str] = []
        seen_function_ids: set[str] = set()
        for function_index, function_payload in enumerate(function_payloads):
            if not isinstance(function_payload, dict):
                raise RuntimeMetadataShapeUnsupportedError(
                    f"UI-Salt lane {lane_id} function[{function_index}] must be an object"
                )
            function_id = _non_empty_string(
                function_payload.get("id"), f"lane {lane_id} function[{function_index}].id"
            )
            if function_id in seen_function_ids:
                raise RuntimeMetadataShapeUnsupportedError(
                    f"Duplicate UI-Salt function id in lane {lane_id}: {function_id}"
                )
            seen_function_ids.add(function_id)
            function_ids.append(function_id)
            entries.append(LaneFunction(lane_id=lane_id, function_id=function_id))
        if default_function_id not in seen_function_ids:
            raise RuntimeMetadataShapeUnsupportedError(
                f"UI-Salt lane {lane_id} default is not present in functions: {default_function_id}"
            )
        lanes.append(
            LaneDefinition(
                lane_id=lane_id,
                default_function_id=default_function_id,
                function_ids=tuple(function_ids),
            )
        )

    return LaneCatalog(shape="ui_salt_function_library_v1", lanes=tuple(lanes), entries=tuple(entries))


def load_lane_catalog_from_ui_salt_contract(contract_path: Path) -> LaneCatalog:
    path = contract_path.resolve()
    if not path.exists():
        raise RuntimeMetadataUnavailableError(f"UI-Salt contract file not found: {path}")
    payload = loads_no_duplicates(path.read_text(encoding="utf-8"))
    return parse_ui_salt_contract_payload(payload)


def lane_known(catalog: LaneCatalog, lane_id: str) -> bool:
    return any(lane.lane_id == lane_id for lane in catalog.lanes)


def lane_function_known(catalog: LaneCatalog, lane_id: str, function_id: str) -> bool:
    return any(
        lane.lane_id == lane_id and function_id in lane.function_ids
        for lane in catalog.lanes
    )


def validate_lane_function_reference(catalog: LaneCatalog, lane_id: str, function_id: str) -> None:
    if not lane_known(catalog, lane_id):
        raise LaneUnknownError(f"lane_unknown: {lane_id}")
    if not lane_function_known(catalog, lane_id, function_id):
        raise FunctionUnknownError(f"function_unknown: lane={lane_id} function={function_id}")


def ordered_selection_actions(catalog: LaneCatalog, selections: dict[str, str]) -> tuple[str, ...]:
    unknown_lanes = sorted(set(selections) - {lane.lane_id for lane in catalog.lanes})
    if unknown_lanes:
        raise LaneUnknownError(f"lane_unknown: {unknown_lanes[0]}")
    actions: list[str] = []
    for lane in catalog.lanes:
        function_id = selections.get(lane.lane_id)
        if function_id is None:
            continue
        validate_lane_function_reference(catalog, lane.lane_id, function_id)
        actions.append(f"select_function:{lane.lane_id}:0:{function_id}")
    return tuple(actions)
