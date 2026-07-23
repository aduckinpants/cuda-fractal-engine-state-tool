from __future__ import annotations

import hashlib
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional

from .async_jobs import JobContext
from .fractal_descriptive_catalog import validate_catalog_bytes
from .fractal_viewport_facts import validate_viewport_facts_bytes
from .json_utils import loads_no_duplicates
from .runtime_surface import (
    build_runtime_command,
    build_runtime_identity,
    resolve_launcher,
    runtime_identity_summary,
    runtime_identity_summary_sha256,
    sha256_file,
)


PACKET_VERSION = 7
BUNDLE_MANIFEST_VERSION = 3
SUPPORTED_PACKET_MANIFEST_VERSIONS = {6: 2, 7: 3}
AUTHORING_SURFACE_VERSION = 2

_SCHEMA_FILENAME = "fractal_binding_surface_v1.ui_schema.json"
_UI_SALT_FILENAME = "color_pipeline_function_library.contract.v1.json"
_PARAMETER_SURFACE_FILENAME = "fractal-parameter-surface.json"
_CATALOG_FILENAME = "fractal-descriptive-catalog.json"
_VIEWPORT_FACTS_FILENAME = "fractal-viewport-facts.json"
_AUTHORING_SURFACE_FILENAME = "state-override-authoring-surface.json"
_PIPELINE_EXAMPLE_FILENAME = "state-override-example-color-pipeline.json"
_STATE_AUTHORING_TRANSPORT_FILENAME = "state-authoring-authorities.md"
_COLOR_PIPELINE_TRANSPORT_FILENAME = "color-pipeline-authority.md"
_FINDING_CONTEXT_TRANSPORT_FILENAME = "finding-context.md"
_WEB_FRAME_FILENAME = "web-agent-frame.png"
_WEB_FRAME_MAX_LONG_EDGE = 2048
_IMAGE_MAX_DECODED_PIXELS = 50_000_000
_IMAGE_MAX_DIMENSION = 16_384


@dataclass(frozen=True)
class AgentBundle:
    packet_version: int
    packet_id: str
    packet_dir: Path
    packet_path: Path
    packet_sha256: str
    manifest_path: Path
    manifest_sha256: str
    finding_id: str
    selected_fractal_type: str
    required_attachments: tuple[str, ...]
    recommended_attachments: tuple[str, ...]
    unavailable_optional_attachments: tuple[str, ...]


@dataclass(frozen=True)
class AgentBundleHandoff:
    packet_version: int
    packet_dir: Path
    packet_text: str
    packet_sha256: str
    required_attachments: tuple[str, ...]
    recommended_attachments: tuple[str, ...]
    unavailable_optional_attachments: tuple[str, ...]


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _json_bytes(value: Any, *, sort_keys: bool = True) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=sort_keys, ensure_ascii=False, allow_nan=False) + "\n").encode(
        "utf-8"
    )


def _write_bytes(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())


def _load_json_object(payload: bytes, label: str) -> dict[str, Any]:
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(f"{label} is not valid UTF-8") from exc
    value = loads_no_duplicates(text)
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a JSON object")
    return value


def load_agent_bundle_handoff(packet_dir: Path) -> AgentBundleHandoff:
    packet_dir = packet_dir.resolve()
    manifest_path = packet_dir / "manifest.json"
    packet_path = packet_dir / "packet.md"
    if not manifest_path.is_file() or not packet_path.is_file():
        raise FileNotFoundError(f"Agent packet directory is incomplete: {packet_dir}")
    manifest = _load_json_object(manifest_path.read_bytes(), "Agent packet manifest")
    packet_version = manifest.get("packet_version")
    expected_manifest_version = SUPPORTED_PACKET_MANIFEST_VERSIONS.get(packet_version)
    if expected_manifest_version is None:
        raise ValueError(f"Unsupported packet version: {packet_version}")
    if manifest.get("bundle_manifest_version") != expected_manifest_version:
        raise ValueError(
            f"Unsupported Packet V{packet_version} manifest version"
        )
    records = manifest.get("files")
    if not isinstance(records, list):
        raise ValueError(f"Packet V{packet_version} manifest has no files array")
    recorded_paths: set[str] = set()
    for record in records:
        if not isinstance(record, dict) or not isinstance(record.get("path"), str):
            raise ValueError(f"Packet V{packet_version} manifest contains an invalid file record")
        record_path = record["path"]
        if Path(record_path).name != record_path or record_path == "manifest.json":
            raise ValueError(f"Packet V{packet_version} manifest contains an unsafe file path: {record_path}")
        if record_path in recorded_paths:
            raise ValueError(f"Packet V{packet_version} manifest repeats file record: {record_path}")
        recorded_paths.add(record_path)
        path = packet_dir / record_path
        if not path.is_file():
            raise FileNotFoundError(f"Packet V{packet_version} attachment is missing: {path}")
        if sha256_file(path) != record.get("sha256") or path.stat().st_size != record.get("size_bytes"):
            raise ValueError(f"Packet V{packet_version} attachment changed after publication: {record_path}")

    actual_paths = {path.name for path in packet_dir.iterdir() if path.is_file() and path.name != "manifest.json"}
    if actual_paths != recorded_paths:
        raise ValueError(f"Packet V{packet_version} directory contents disagree with its manifest")

    def _names(key: str) -> tuple[str, ...]:
        values = manifest.get(key)
        if not isinstance(values, list) or any(not isinstance(item, str) for item in values):
            raise ValueError(f"Packet V{packet_version} manifest {key} must be a string array")
        return tuple(values)

    required = _names("required_attachments")
    recommended = _names("recommended_attachments")
    if set(required) & set(recommended):
        raise ValueError(f"Packet V{packet_version} attachment lists overlap")
    if not set(required + recommended).issubset(recorded_paths):
        raise ValueError(f"Packet V{packet_version} attachment list names are absent from its files manifest")
    by_path = {record["path"]: record for record in records}
    for filename in required:
        if by_path[filename].get("web_handoff") != "required":
            raise ValueError(f"Packet V{packet_version} required attachment classification disagrees for {filename}")
    for filename in recommended:
        if by_path[filename].get("web_handoff") != "recommended":
            raise ValueError(f"Packet V{packet_version} recommended attachment classification disagrees for {filename}")

    packet_bytes = packet_path.read_bytes()
    try:
        packet_text = packet_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(f"Packet V{packet_version} packet.md is not valid UTF-8") from exc
    return AgentBundleHandoff(
        packet_version=packet_version,
        packet_dir=packet_dir,
        packet_text=packet_text,
        packet_sha256=_sha256_bytes(packet_bytes),
        required_attachments=required,
        recommended_attachments=recommended,
        unavailable_optional_attachments=_names("unavailable_optional_attachments"),
    )


def load_existing_agent_bundle(packet_dir: Path) -> AgentBundle:
    """Load one supported immutable packet without refreshing or rewriting it."""
    handoff = load_agent_bundle_handoff(packet_dir)
    manifest_path = handoff.packet_dir / "manifest.json"
    manifest = _load_json_object(manifest_path.read_bytes(), "Agent packet manifest")
    packet_id = manifest.get("packet_id")
    finding_id = manifest.get("finding_id")
    selected = manifest.get("selected_fractal_type")
    if not isinstance(packet_id, str) or packet_id != handoff.packet_dir.name:
        raise ValueError(f"Packet V{handoff.packet_version} packet_id does not match its immutable directory name")
    if not isinstance(finding_id, str) or not finding_id:
        raise ValueError(f"Packet V{handoff.packet_version} manifest has no finding_id")
    if not isinstance(selected, str) or not selected:
        raise ValueError(f"Packet V{handoff.packet_version} manifest has no selected_fractal_type")
    return AgentBundle(
        packet_version=handoff.packet_version,
        packet_id=packet_id,
        packet_dir=handoff.packet_dir,
        packet_path=(handoff.packet_dir / "packet.md").resolve(),
        packet_sha256=handoff.packet_sha256,
        manifest_path=manifest_path.resolve(),
        manifest_sha256=sha256_file(manifest_path),
        finding_id=finding_id,
        selected_fractal_type=selected,
        required_attachments=handoff.required_attachments,
        recommended_attachments=handoff.recommended_attachments,
        unavailable_optional_attachments=handoff.unavailable_optional_attachments,
    )


def copy_agent_packet(packet_dir: Path, clipboard_writer: Callable[[str], None]) -> AgentBundleHandoff:
    handoff = load_agent_bundle_handoff(packet_dir)
    clipboard_writer(handoff.packet_text)
    return handoff


def open_agent_bundle_folder(
    packet_dir: Path,
    opener: Callable[[Path], None] | None = None,
) -> AgentBundleHandoff:
    handoff = load_agent_bundle_handoff(packet_dir)
    if opener is None:
        if not hasattr(os, "startfile"):
            raise RuntimeError("Opening the agent bundle folder is supported only on Windows")
        opener = os.startfile
    opener(handoff.packet_dir)
    return handoff


def _resolve_path(root: Any, dotted_path: str) -> tuple[bool, Any]:
    current = root
    for part in dotted_path.split("."):
        if isinstance(current, dict) and part in current:
            current = current[part]
            continue
        if isinstance(current, list) and part.isdigit():
            index = int(part)
            if 0 <= index < len(current):
                current = current[index]
                continue
        return False, None
    return True, current


def _state_value_for_binding(state: dict[str, Any], binding_path: str) -> tuple[bool, Any]:
    if binding_path == "fractal.view.fractal_type":
        return ("fractal_type" in state, state.get("fractal_type"))
    if binding_path.startswith("fractal.params."):
        return _resolve_path(state.get("params"), binding_path.removeprefix("fractal.params."))
    if binding_path.startswith("fractal.view."):
        return _resolve_path(state.get("view"), binding_path.removeprefix("fractal.view."))
    return False, None


def _visible_in_state(control: dict[str, Any], state: dict[str, Any]) -> bool:
    condition = control.get("visible_if")
    if condition is None:
        return True
    if not isinstance(condition, dict):
        return False
    path = condition.get("path")
    op = condition.get("op")
    if not isinstance(path, str) or not isinstance(op, str):
        return False
    available, current = _state_value_for_binding(state, path)
    if not available:
        return False
    expected = condition.get("value")
    if op == "eq":
        return current == expected
    if op == "neq":
        return current != expected
    if op == "in" and isinstance(expected, str):
        return isinstance(current, str) and current in expected.split(",")
    return False


def _schema_controls(
    schema: dict[str, Any],
) -> tuple[list[tuple[str, dict[str, Any]]], dict[str, dict[str, Any]], dict[str, str]]:
    panels = schema.get("panels")
    if not isinstance(panels, list):
        raise ValueError("Deployed UI schema has no panels array")
    ordered: list[tuple[str, dict[str, Any]]] = []
    indexed: dict[str, dict[str, Any]] = {}
    panel_by_control_id: dict[str, str] = {}
    for panel_index, panel in enumerate(panels):
        if not isinstance(panel, dict) or not isinstance(panel.get("controls"), list):
            raise ValueError(f"Deployed UI schema panel {panel_index} has no controls array")
        panel_id = panel.get("id")
        if not isinstance(panel_id, str) or not panel_id:
            raise ValueError(f"Deployed UI schema panel {panel_index} has no id")
        for control_index, control in enumerate(panel["controls"]):
            if not isinstance(control, dict) or not isinstance(control.get("id"), str):
                raise ValueError(
                    f"Deployed UI schema panel {panel_index} control {control_index} has no id"
                )
            control_id = control["id"]
            if control_id in indexed:
                raise ValueError(f"Deployed UI schema contains duplicate control id: {control_id}")
            ordered.append((panel_id, control))
            indexed[control_id] = control
            panel_by_control_id[control_id] = panel_id
    return ordered, indexed, panel_by_control_id


def _control_entry(
    path: str,
    control: dict[str, Any],
    current_value: Any,
    source_kind: str,
    parameter_surface_sha256: str,
    ui_schema_sha256: str,
    companion_paths: tuple[str, ...] = (),
) -> dict[str, Any]:
    options = control.get("options")
    option_ids: list[str] | None = None
    if isinstance(options, list):
        option_ids = []
        for option in options:
            if not isinstance(option, dict) or not isinstance(option.get("id"), str):
                raise ValueError(f"UI schema control {control.get('id')} has an invalid option")
            option_ids.append(option["id"])
    return {
        "path": path,
        "source_control_id": control["id"],
        "source_kind": source_kind,
        "type": control.get("value_type"),
        "current_value": current_value,
        "minimum": control.get("min"),
        "maximum": control.get("max"),
        "ui_minimum": control.get("ui_min"),
        "ui_maximum": control.get("ui_max"),
        "options": option_ids,
        "companion_paths": list(companion_paths),
        "authority_refs": {
            "parameter_surface_sha256": parameter_surface_sha256,
            "ui_schema_sha256": ui_schema_sha256,
        },
    }


def derive_state_override_authoring_surface(
    state_bytes: bytes,
    parameter_surface_bytes: bytes,
    ui_schema_bytes: bytes,
) -> dict[str, Any]:
    state = _load_json_object(state_bytes, "Copied state.json")
    parameter_surface = _load_json_object(parameter_surface_bytes, "Copied parameter surface")
    ui_schema = _load_json_object(ui_schema_bytes, "Copied UI schema")
    selected = state.get("fractal_type")
    if not isinstance(selected, str) or not selected:
        raise ValueError("Copied state.json has no selected fractal_type")

    parameter_surface_sha256 = _sha256_bytes(parameter_surface_bytes)
    ui_schema_sha256 = _sha256_bytes(ui_schema_bytes)
    ordered_schema_controls, schema_by_id, panel_by_control_id = _schema_controls(ui_schema)
    lanes = parameter_surface.get("lanes")
    if not isinstance(lanes, list):
        raise ValueError("Copied parameter surface has no lanes array")
    selected_lanes = [lane for lane in lanes if isinstance(lane, dict) and lane.get("fractal_id") == selected]
    if len(selected_lanes) != 1:
        raise ValueError(f"Copied parameter surface contains {len(selected_lanes)} lanes for {selected}")
    controls = selected_lanes[0].get("controls")
    if not isinstance(controls, list):
        raise ValueError(f"Copied parameter surface lane {selected} has no controls array")

    entries: list[dict[str, Any]] = []
    emitted_control_ids: set[str] = set()
    selected_surface_control_ids: set[str] = set()
    applicable_count = 0
    for descriptor in controls:
        if not isinstance(descriptor, dict) or not isinstance(descriptor.get("control_id"), str):
            raise ValueError(f"Copied parameter surface lane {selected} has an invalid control")
        applicable_count += 1
        control_id = descriptor["control_id"]
        if control_id in selected_surface_control_ids:
            raise ValueError(f"Copied parameter surface lane {selected} repeats control {control_id}")
        selected_surface_control_ids.add(control_id)
        control = schema_by_id.get(control_id)
        if control is None:
            raise ValueError(f"Applicable control {control_id} is absent from the copied UI schema")
        if panel_by_control_id[control_id] == "color":
            continue
        binding = control.get("binding")
        if not isinstance(binding, dict) or binding.get("kind") != "param":
            continue
        binding_path = binding.get("path")
        if binding_path != descriptor.get("binding_path") or descriptor.get("binding_resolves") is not True:
            continue
        state_io_key = descriptor.get("state_io_key")
        if not isinstance(state_io_key, str) or not state_io_key:
            continue
        if descriptor.get("default_visible") is False and control.get("visible_if") is None:
            continue
        if not _visible_in_state(control, state):
            continue

        if binding_path.startswith("fractal.params."):
            container = state.get("params")
            prefix = "params"
        elif binding_path.startswith("fractal.view."):
            container = state.get("view")
            prefix = "view"
        else:
            continue
        present, current = _resolve_path(container, state_io_key)
        if not present:
            continue
        entries.append(
            _control_entry(
                f"{prefix}.{state_io_key}",
                control,
                current,
                "selected_parameter_surface",
                parameter_surface_sha256,
                ui_schema_sha256,
            )
        )
        emitted_control_ids.add(control_id)

    for panel_id, control in ordered_schema_controls:
        control_id = control["id"]
        if (
            panel_id == "color"
            or control_id in emitted_control_ids
            or control_id in selected_surface_control_ids
            or control.get("visible_if") is not None
        ):
            continue
        binding = control.get("binding")
        if not isinstance(binding, dict) or binding.get("kind") != "param":
            continue
        binding_path = binding.get("path")
        if not isinstance(binding_path, str) or not binding_path.startswith("fractal.params."):
            continue
        suffix = binding_path.removeprefix("fractal.params.")
        present, current = _resolve_path(state.get("params"), suffix)
        if not present:
            continue
        entries.append(
            _control_entry(
                f"params.{suffix}",
                control,
                current,
                "global_ui_schema",
                parameter_surface_sha256,
                ui_schema_sha256,
            )
        )
        emitted_control_ids.add(control_id)

    camera_companions = {
        "center_x": ("view.center_hp_x",),
        "center_y": ("view.center_hp_y",),
        "zoom": ("view.log2_zoom",),
    }
    for control_id, companions in camera_companions.items():
        if control_id in emitted_control_ids:
            continue
        control = schema_by_id.get(control_id)
        if control is None:
            continue
        binding = control.get("binding")
        if not isinstance(binding, dict) or binding.get("kind") != "param":
            continue
        present, current = _resolve_path(state.get("view"), control_id)
        if not present or any(not _resolve_path(state, companion)[0] for companion in companions):
            continue
        entries.append(
            _control_entry(
                f"view.{control_id}",
                control,
                current,
                "camera_ui_schema_with_companion",
                parameter_surface_sha256,
                ui_schema_sha256,
                companions,
            )
        )
        emitted_control_ids.add(control_id)

    seen_paths: set[str] = set()
    for entry in entries:
        if entry["path"] in seen_paths:
            raise ValueError(f"Derived authoring surface contains duplicate path: {entry['path']}")
        seen_paths.add(entry["path"])

    companion_rules = [
        {"path": "view.center_hp_x", "requires_changed_path": "view.center_x"},
        {"path": "view.center_hp_y", "requires_changed_path": "view.center_y"},
        {"path": "view.log2_zoom", "requires_changed_path": "view.zoom"},
    ]
    companion_rules = [
        rule
        for rule in companion_rules
        if rule["requires_changed_path"] in seen_paths and _resolve_path(state, rule["path"])[0]
    ]
    draft = state.get("color_pipeline_draft")
    color_authoring_mode = (
        "color_pipeline_draft_only"
        if isinstance(draft, dict) and isinstance(draft.get("lanes"), list)
        else "unavailable"
    )
    return {
        "surface_version": AUTHORING_SURFACE_VERSION,
        "selected_fractal_type": selected,
        "applicable_control_count": applicable_count,
        "state_override_authorable_control_count": len(entries),
        "authority_refs": {
            "state_sha256": _sha256_bytes(state_bytes),
            "parameter_surface_sha256": parameter_surface_sha256,
            "ui_schema_sha256": ui_schema_sha256,
        },
        "entries": entries,
        "companion_rules": companion_rules,
        "color_authoring": {
            "mode": color_authoring_mode,
            "excluded_ui_panel_id": "color",
            "compatibility_authority": (
                "color_pipeline_function_library.contract.v1.json"
                "#/composition_recipe_contract/compatibility"
            ),
            "engine_materialization_is_final_authority": True,
        },
    }


def serialize_state_override_authoring_surface(surface: dict[str, Any]) -> bytes:
    return _json_bytes(surface)


def _contract_function_index(contract: dict[str, Any]) -> tuple[list[str], dict[tuple[str, str], dict[str, Any]]]:
    library = contract.get("function_library")
    if not isinstance(library, dict) or not isinstance(library.get("lanes"), list):
        raise ValueError("Copied UI-Salt contract has no function_library.lanes array")
    lane_order: list[str] = []
    functions: dict[tuple[str, str], dict[str, Any]] = {}
    for lane in library["lanes"]:
        if not isinstance(lane, dict) or not isinstance(lane.get("id"), str):
            raise ValueError("Copied UI-Salt contract contains an invalid lane")
        lane_id = lane["id"]
        if lane_id in lane_order:
            raise ValueError(f"Copied UI-Salt contract repeats lane {lane_id}")
        lane_order.append(lane_id)
        function_items = lane.get("functions")
        if not isinstance(function_items, list):
            raise ValueError(f"Copied UI-Salt lane {lane_id} has no functions array")
        for function in function_items:
            if not isinstance(function, dict) or not isinstance(function.get("id"), str):
                raise ValueError(f"Copied UI-Salt lane {lane_id} contains an invalid function")
            key = (lane_id, function["id"])
            if key in functions:
                raise ValueError(f"Copied UI-Salt contract repeats function {lane_id}/{function['id']}")
            functions[key] = function
    return lane_order, functions


def _validate_color_pipeline_compatibility_authority(contract: dict[str, Any]) -> None:
    recipe_contract = contract.get("composition_recipe_contract")
    if not isinstance(recipe_contract, dict):
        raise ValueError("Copied UI-Salt contract has no composition_recipe_contract object")
    compatibility = recipe_contract.get("compatibility")
    if not isinstance(compatibility, list) or not compatibility:
        raise ValueError(
            "Copied UI-Salt contract has no composition_recipe_contract.compatibility rows"
        )
    for index, row in enumerate(compatibility):
        if not isinstance(row, dict) or any(
            not isinstance(row.get(field), str) or not row[field]
            for field in ("source", "palette", "grading")
        ):
            raise ValueError(f"Copied UI-Salt compatibility row {index} is invalid")


def validate_captured_color_pipeline_draft(state: dict[str, Any], contract: dict[str, Any]) -> dict[str, Any] | None:
    draft = state.get("color_pipeline_draft")
    if draft is None:
        return None
    if not isinstance(draft, dict) or not isinstance(draft.get("lanes"), list):
        raise ValueError("Copied state color_pipeline_draft must contain a lanes array")
    next_row_id = draft.get("next_row_id")
    if isinstance(next_row_id, bool) or not isinstance(next_row_id, int) or next_row_id < 1:
        raise ValueError("Copied state color_pipeline_draft has an invalid next_row_id")
    lane_order, functions = _contract_function_index(contract)
    captured_lane_ids: list[str] = []
    captured_row_ids: set[int] = set()
    for lane_index, lane in enumerate(draft["lanes"]):
        if (
            not isinstance(lane, dict)
            or not isinstance(lane.get("lane_id"), str)
            or not isinstance(lane.get("label"), str)
            or not lane["label"]
        ):
            raise ValueError(f"Captured Color Pipeline lane {lane_index} is invalid")
        lane_id = lane["lane_id"]
        captured_lane_ids.append(lane_id)
        rows = lane.get("rows")
        if not isinstance(rows, list):
            raise ValueError(f"Captured Color Pipeline lane {lane_id} has no rows array")
        for row_index, row in enumerate(rows):
            if (
                not isinstance(row, dict)
                or not isinstance(row.get("function_id"), str)
                or isinstance(row.get("ui_row_id"), bool)
                or not isinstance(row.get("ui_row_id"), int)
                or not isinstance(row.get("enabled"), bool)
            ):
                raise ValueError(f"Captured Color Pipeline row {lane_id}[{row_index}] is invalid")
            ui_row_id = row["ui_row_id"]
            if ui_row_id in captured_row_ids:
                raise ValueError(f"Captured Color Pipeline repeats ui_row_id {ui_row_id}")
            captured_row_ids.add(ui_row_id)
            function = functions.get((lane_id, row["function_id"]))
            if function is None:
                raise ValueError(
                    f"Captured Color Pipeline function is absent from copied contract: {lane_id}/{row['function_id']}"
                )
            declared = function.get("params", [])
            if not isinstance(declared, list):
                raise ValueError(f"Copied contract function {lane_id}/{row['function_id']} has invalid params")
            values = row.get("parameter_values", [])
            if not isinstance(values, list):
                raise ValueError(f"Captured Color Pipeline row {lane_id}[{row_index}] has invalid parameter_values")
            declared_paths = [item.get("path") if isinstance(item, dict) else None for item in declared]
            captured_paths = [item.get("path") if isinstance(item, dict) else None for item in values]
            if captured_paths != declared_paths:
                raise ValueError(
                    f"Captured Color Pipeline parameters do not follow copied contract order for "
                    f"{lane_id}/{row['function_id']}"
                )
            if len(set(captured_paths)) != len(captured_paths):
                raise ValueError(
                    f"Captured Color Pipeline parameters repeat a path for {lane_id}/{row['function_id']}"
                )
            for parameter, captured in zip(declared, values, strict=True):
                if not isinstance(parameter, dict) or not isinstance(captured, dict):
                    raise ValueError(
                        f"Captured Color Pipeline parameter is invalid for {lane_id}/{row['function_id']}"
                    )
                declared_type = parameter.get("type")
                if captured.get("type") != declared_type:
                    raise ValueError(
                        f"Captured Color Pipeline parameter {captured.get('path')} has a type that disagrees "
                        f"with the copied contract"
                    )
                if declared_type in {"float", "int"}:
                    if set(captured) != {"path", "type", "number_value"}:
                        raise ValueError(
                            f"Captured Color Pipeline parameter {captured.get('path')} has the wrong numeric carrier"
                        )
                    number = captured["number_value"]
                    if isinstance(number, bool) or not isinstance(number, (int, float)) or not math.isfinite(number):
                        raise ValueError(
                            f"Captured Color Pipeline parameter {captured.get('path')} is not finite numeric data"
                        )
                    if declared_type == "int" and not isinstance(number, int):
                        raise ValueError(
                            f"Captured Color Pipeline parameter {captured.get('path')} is not an integer"
                        )
                    minimum = parameter.get("min")
                    maximum = parameter.get("max")
                    if isinstance(minimum, (int, float)) and number < minimum:
                        raise ValueError(
                            f"Captured Color Pipeline parameter {captured.get('path')} is below the copied range"
                        )
                    if isinstance(maximum, (int, float)) and number > maximum:
                        raise ValueError(
                            f"Captured Color Pipeline parameter {captured.get('path')} is above the copied range"
                        )
                elif declared_type == "enum":
                    if set(captured) != {"path", "type", "enum_value"}:
                        raise ValueError(
                            f"Captured Color Pipeline parameter {captured.get('path')} has the wrong enum carrier"
                        )
                    options = parameter.get("options")
                    if not isinstance(options, list) or captured["enum_value"] not in options:
                        raise ValueError(
                            f"Captured Color Pipeline parameter {captured.get('path')} is outside copied enum options"
                        )
                else:
                    raise ValueError(
                        f"Copied contract parameter {captured.get('path')} has unsupported type {declared_type}"
                    )
    if captured_lane_ids != lane_order:
        raise ValueError("Captured Color Pipeline lane order does not match copied UI-Salt contract")
    if captured_row_ids and next_row_id <= max(captured_row_ids):
        raise ValueError("Captured Color Pipeline next_row_id does not advance beyond existing rows")
    return draft


def _capture_export(
    runtime_cmd_path: Path,
    flag: str,
    filename: str,
    job: Optional[JobContext],
    timeout_seconds: float,
    temp_root: Path,
    *extra_args: str,
) -> bytes:
    with tempfile.TemporaryDirectory(prefix=".agent-bundle-export-", dir=temp_root) as temp_dir:
        output_path = Path(temp_dir) / filename
        command = build_runtime_command(
            runtime_cmd_path,
            flag,
            str(output_path.resolve()),
            *extra_args,
        )
        if job is not None:
            result = job.run_process(command, runtime_cmd_path.parent, timeout_seconds=timeout_seconds)
            exit_code = result.exit_code
            timed_out = result.timed_out
            detail = result.stderr.strip() or result.stdout.strip()
        else:
            try:
                completed = subprocess.run(
                    command,
                    cwd=str(runtime_cmd_path.parent),
                    capture_output=True,
                    text=True,
                    timeout=timeout_seconds,
                    check=False,
                )
            except subprocess.TimeoutExpired as exc:
                raise ValueError(f"Runtime export {flag} timed out") from exc
            exit_code = completed.returncode
            timed_out = False
            detail = completed.stderr.strip() or completed.stdout.strip()
        if timed_out or exit_code != 0 or not output_path.is_file():
            suffix = f": {detail}" if detail else ""
            raise ValueError(f"Runtime export {flag} failed{suffix}")
        return output_path.read_bytes()


def _create_web_frame_derivative(
    stage_dir: Path,
    frame_filename: str,
    job: Optional[JobContext],
    timeout_seconds: float,
) -> dict[str, Any]:
    source_path = (stage_dir / frame_filename).resolve()
    output_path = (stage_dir / _WEB_FRAME_FILENAME).resolve()
    command = [
        sys.executable,
        "-m",
        "cuda_fractal_state_tool.preview_worker",
        "--source",
        str(source_path),
        "--out",
        str(output_path),
        "--max-width",
        str(_WEB_FRAME_MAX_LONG_EDGE),
        "--max-height",
        str(_WEB_FRAME_MAX_LONG_EDGE),
        "--max-pixels",
        str(_IMAGE_MAX_DECODED_PIXELS),
        "--max-dimension",
        str(_IMAGE_MAX_DIMENSION),
    ]
    if job is not None:
        result = job.run_process(command, cwd=stage_dir, timeout_seconds=timeout_seconds)
        exit_code = result.exit_code
        timed_out = result.timed_out
        stdout = result.stdout
        stderr = result.stderr
    else:
        try:
            completed = subprocess.run(
                command,
                cwd=str(stage_dir),
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise ValueError("Web-agent frame derivative generation timed out") from exc
        exit_code = completed.returncode
        timed_out = False
        stdout = completed.stdout
        stderr = completed.stderr
    if timed_out or exit_code != 0 or not output_path.is_file():
        detail = stderr.strip() or stdout.strip()
        suffix = f": {detail}" if detail else ""
        raise ValueError(f"Web-agent frame derivative generation failed{suffix}")
    try:
        worker_result = json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise ValueError("Web-agent frame worker returned invalid JSON") from exc
    if not isinstance(worker_result, dict) or worker_result.get("status") != "ok":
        raise ValueError("Web-agent frame worker returned an invalid result")
    if worker_result.get("upscaled") is not False:
        raise ValueError("Web-agent frame worker violated the no-upscaling contract")
    if max(int(worker_result["preview_width"]), int(worker_result["preview_height"])) > _WEB_FRAME_MAX_LONG_EDGE:
        raise ValueError("Web-agent frame worker exceeded the maximum long edge")
    return {
        "status": "discussion_derivative_not_full_resolution_authority",
        "source_path": frame_filename,
        "source_sha256": sha256_file(source_path),
        "source_size_bytes": source_path.stat().st_size,
        "source_format": worker_result["source_format"],
        "source_width": int(worker_result["source_width"]),
        "source_height": int(worker_result["source_height"]),
        "derivative_path": _WEB_FRAME_FILENAME,
        "derivative_sha256": sha256_file(output_path),
        "derivative_size_bytes": output_path.stat().st_size,
        "derivative_width": int(worker_result["preview_width"]),
        "derivative_height": int(worker_result["preview_height"]),
        "upscaled": False,
        "resampling": worker_result["resampling"],
        "pixel_mode": worker_result["pixel_mode"],
        "orientation_handling": worker_result["orientation_handling"],
        "policy": {
            "maximum_long_edge": _WEB_FRAME_MAX_LONG_EDGE,
            "maximum_decoded_pixels": _IMAGE_MAX_DECODED_PIXELS,
            "maximum_dimension": _IMAGE_MAX_DIMENSION,
            "timeout_seconds": timeout_seconds,
        },
    }


def _artifact_path(finding_dir: Path, manifest: dict[str, Any], key: str) -> Path | None:
    artifacts = manifest.get("source_artifacts")
    item = artifacts.get(key) if isinstance(artifacts, dict) else None
    relative = item.get("workspace_path") if isinstance(item, dict) else None
    if not isinstance(relative, str) or not relative:
        return None
    candidate = (finding_dir / relative).resolve()
    try:
        candidate.relative_to(finding_dir.resolve())
    except ValueError as exc:
        raise ValueError(f"Workspace artifact {key} escapes the finding directory") from exc
    if not candidate.is_file():
        raise FileNotFoundError(f"Workspace artifact {key} is missing: {candidate}")
    return candidate


def _selected_description_lines(entry: dict[str, Any]) -> list[str]:
    if entry.get("description_status") != "reviewed":
        return [
            "No reviewed engine-owned mathematical background is available for this selector.",
            "Do not substitute historical or model-invented prose.",
        ]
    description = entry["description"]
    return [
        f"- Math summary: {description['math_summary']}",
        f"- Recurrence or field model: {description['recurrence_or_field_model']}",
        f"- State order: {description['state_order']}",
        f"- Termination or classification: {description['termination_or_classification']}",
        f"- Interpretation notes: {description['interpretation_notes']}",
    ]


def _markdown_fence(payload: str) -> str:
    longest = 0
    current = 0
    for character in payload:
        if character == "`":
            current += 1
            longest = max(longest, current)
        else:
            current = 0
    return "`" * max(3, longest + 1)


def _embedded_text_artifact(
    filename: str,
    role: str,
    payload: bytes,
    *,
    language: str,
) -> str:
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(f"Web transport source {filename} is not valid UTF-8") from exc
    fence = _markdown_fence(text)
    separator = "" if text.endswith(("\n", "\r")) else "\n"
    return (
        f"## `{filename}`\n\n"
        f"- Role: {role}\n"
        f"- Exact neighboring-file size: `{len(payload)}` bytes\n"
        f"- Exact neighboring-file SHA-256: `{_sha256_bytes(payload)}`\n\n"
        f"{fence}{language}\n{text}{separator}{fence}\n"
    )


def _pipeline_topology_index(state: dict[str, Any]) -> dict[str, Any]:
    draft = state.get("color_pipeline_draft")
    if not isinstance(draft, dict) or not isinstance(draft.get("lanes"), list):
        return {
            "status": "unavailable",
            "reason": "captured state has no complete color_pipeline_draft",
        }
    lanes: list[dict[str, Any]] = []
    for lane in draft["lanes"]:
        rows = lane.get("rows", []) if isinstance(lane, dict) else []
        lanes.append(
            {
                "lane_id": lane.get("lane_id"),
                "label": lane.get("label"),
                "rows": [
                    {
                        "ui_row_id": row.get("ui_row_id"),
                        "enabled": row.get("enabled"),
                        "function_id": row.get("function_id"),
                        "parameter_paths": [
                            value.get("path")
                            for value in row.get("parameter_values", [])
                            if isinstance(value, dict)
                        ],
                    }
                    for row in rows
                    if isinstance(row, dict)
                ],
            }
        )
    return {
        "status": "available",
        "role": "mechanical_navigation_index_not_authority",
        "next_row_id": draft.get("next_row_id"),
        "lanes": lanes,
    }


def _build_transport_views(
    stage_dir: Path,
    state: dict[str, Any],
    selected_entry: dict[str, Any],
    unavailable: list[str],
    *,
    has_pipeline_example: bool,
) -> dict[str, bytes]:
    state_authoring_sections = [
        "# State Authoring Authorities\n\n"
        "This file is a deterministic web-transport view. Each exact section is "
        "bound to an immutable neighboring local authority by byte size and SHA-256. "
        "The individual JSON files remain the proof and validation authority.\n",
        _embedded_text_artifact(
            _PARAMETER_SURFACE_FILENAME,
            "complete runtime-selected applicability authority",
            (stage_dir / _PARAMETER_SURFACE_FILENAME).read_bytes(),
            language="json",
        ),
        _embedded_text_artifact(
            _SCHEMA_FILENAME,
            "deployed UI control and state-binding authority",
            (stage_dir / _SCHEMA_FILENAME).read_bytes(),
            language="json",
        ),
        _embedded_text_artifact(
            _AUTHORING_SURFACE_FILENAME,
            "finding-specific mechanically derived state-override index",
            (stage_dir / _AUTHORING_SURFACE_FILENAME).read_bytes(),
            language="json",
        ),
    ]

    topology_bytes = _json_bytes(_pipeline_topology_index(state))
    pipeline_sections = [
        "# Color Pipeline Authority\n\n"
        "This file is a deterministic web-transport view. The complete UI-Salt "
        "contract below owns function and parameter validity. The topology index "
        "is navigation help derived from the exact captured state; it grants no "
        "additional authority.\n",
        _embedded_text_artifact(
            _UI_SALT_FILENAME,
            "complete deployed Color Pipeline function and compatibility authority",
            (stage_dir / _UI_SALT_FILENAME).read_bytes(),
            language="json",
        ),
        _embedded_text_artifact(
            "current-color-pipeline-topology-index.json",
            "mechanical navigation index derived from exact staged state.json",
            topology_bytes,
            language="json",
        ),
    ]
    if has_pipeline_example:
        pipeline_sections.append(
            _embedded_text_artifact(
                _PIPELINE_EXAMPLE_FILENAME,
                "complete unchanged whole-array structural editing example",
                (stage_dir / _PIPELINE_EXAMPLE_FILENAME).read_bytes(),
                language="json",
            )
        )
    else:
        pipeline_sections.append(
            "## Pipeline structural example unavailable\n\n"
            "The captured state contains no complete `color_pipeline_draft`; "
            "Color Pipeline override authoring is unavailable for this packet.\n"
        )

    catalog_bytes = (stage_dir / _CATALOG_FILENAME).read_bytes()
    selected_entry_bytes = _json_bytes(
        {
            "source_catalog_sha256": _sha256_bytes(catalog_bytes),
            "selected_entry": selected_entry,
        }
    )
    context_sections = [
        "# Finding Context\n\n"
        "This file consolidates optional human context and the selected engine-owned "
        "description. Exact replay and authoring authority remain in the separately "
        "attached state files and authority documents.\n",
        _embedded_text_artifact(
            "selected-fractal-description.json",
            "selected entry projected from the complete neighboring descriptive catalog",
            selected_entry_bytes,
            language="json",
        ),
    ]
    if (stage_dir / "finding.json").is_file():
        context_sections.append(
            _embedded_text_artifact(
                "finding.json",
                "capture manifest context",
                (stage_dir / "finding.json").read_bytes(),
                language="json",
            )
        )
    else:
        context_sections.append("## `finding.json` unavailable\n\nNo capture manifest was present.\n")
    if (stage_dir / "field-notes.md").is_file():
        context_sections.append(
            _embedded_text_artifact(
                "field-notes.md",
                "user-authored context",
                (stage_dir / "field-notes.md").read_bytes(),
                language="markdown",
            )
        )
    else:
        context_sections.append("## `field-notes.md` unavailable\n\nNo field notes were present.\n")
    if unavailable:
        context_sections.append(
            "## Other unavailable optional artifacts\n\n"
            + "\n".join(f"- `{name}`" for name in unavailable)
            + "\n"
        )

    return {
        _STATE_AUTHORING_TRANSPORT_FILENAME: "\n".join(state_authoring_sections).encode("utf-8"),
        _COLOR_PIPELINE_TRANSPORT_FILENAME: "\n".join(pipeline_sections).encode("utf-8"),
        _FINDING_CONTEXT_TRANSPORT_FILENAME: "\n".join(context_sections).encode("utf-8"),
    }


def _packet_markdown(
    packet_id: str,
    finding_id: str,
    state: dict[str, Any],
    selected_entry: dict[str, Any],
    viewport_facts: dict[str, Any],
    authoring_surface: dict[str, Any],
    required: list[str],
    recommended: list[str],
    unavailable: list[str],
    file_hashes: dict[str, str],
    has_pipeline_example: bool,
    web_frame_derivative: dict[str, Any] | None,
) -> str:
    fractal_type = state["fractal_type"]
    params = state.get("params") if isinstance(state.get("params"), dict) else {}
    render = state.get("render") if isinstance(state.get("render"), dict) else {}
    authorable_paths = [entry["path"] for entry in authoring_surface["entries"]]
    viewport_camera = viewport_facts["camera"]
    viewport_frame = viewport_facts["local_frame"]
    viewport_basis = viewport_facts["complex_pixel_basis"]
    draft = state.get("color_pipeline_draft")
    pipeline_summary: list[str] = []
    if isinstance(draft, dict) and isinstance(draft.get("lanes"), list):
        for lane in draft["lanes"]:
            rows = lane.get("rows", []) if isinstance(lane, dict) else []
            functions = [row.get("function_id", "?") for row in rows if isinstance(row, dict)]
            pipeline_summary.append(f"- `{lane.get('lane_id', '?')}`: {', '.join(functions) or '(no rows)'}")
    else:
        pipeline_summary.append("- No complete `color_pipeline_draft` is present in this capture.")

    attachment_lines = [f"- `{name}` — SHA-256 `{file_hashes[name]}`" for name in required]
    context_lines = [f"- `{name}` — SHA-256 `{file_hashes[name]}`" for name in recommended]
    unavailable_lines = [f"- `{name}`" for name in unavailable]
    if web_frame_derivative is None:
        web_frame_lines = [
            "No captured frame was available, so this packet has no web discussion image.",
        ]
    else:
        web_frame_lines = [
            f"`{_WEB_FRAME_FILENAME}` is a bounded discussion derivative of "
            f"`{web_frame_derivative['source_path']}`.",
            f"- Source: `{web_frame_derivative['source_width']} × {web_frame_derivative['source_height']}`; "
            f"SHA-256 `{web_frame_derivative['source_sha256']}`",
            f"- Derivative: `{web_frame_derivative['derivative_width']} × "
            f"{web_frame_derivative['derivative_height']}`; "
            f"SHA-256 `{web_frame_derivative['derivative_sha256']}`",
            f"- Resampling: `{web_frame_derivative['resampling']}`; upscaled: `false`",
            "Use it for visual discussion, not as full-resolution pixel authority. Exact color counts,",
            "pixel frequencies, and other resolution-sensitive measurements describe this derivative only",
            "unless the full source frame is separately supplied and explicitly identified.",
        ]
    example_note = (
        f"A complete unchanged structural template is embedded in `{_COLOR_PIPELINE_TRANSPORT_FILENAME}` "
        f"and retained locally as `{_PIPELINE_EXAMPLE_FILENAME}`. "
        "It demonstrates the required whole-array replacement shape; it is not a recommended visual change. "
        "When you change a function, return the complete parameter list for the new function in exact deployed-contract order."
        if has_pipeline_example
        else "This capture has no complete serialized pipeline draft, so Color Pipeline state override authoring is unavailable."
    )
    color_authoring_guidance = (
        [
            "This packet's color authoring is Color-Pipeline-only. Do not return flat `params` color controls from",
            "`state.json` or the UI schema: those fields are replay/compatibility mirrors and are not independently",
            "state-override-authorable. Return `color_pipeline_draft` with the complete `lanes` array from the embedded",
            "structural template, preserving lane/row topology, IDs, labels, ordering, enablement, and row counts.",
            f"Functions and complete parameter lists may change only as allowed by `{_COLOR_PIPELINE_TRANSPORT_FILENAME}`.",
            "Function IDs are not freely composable. For function changes, consult",
            "`composition_recipe_contract.compatibility` in that contract and use a supported Source/Palette pair",
            "with its matching grading. A parameter-only edit to current functions preserves the captured recipe.",
            "Contract-valid drafts outside a runtime-supported recipe can still fail closed during engine proof.",
            "During proof, the published runtime applies that loaded draft through the engine-owned lowering operation;",
            "replay then uses the complete engine-emitted state without that operation.",
        ]
        if has_pipeline_example
        else [
            "Color authoring is unavailable for this packet because no complete serialized Color Pipeline draft exists.",
            "Do not return flat `params` color controls from `state.json` or the UI schema; they are not an accepted",
            "state-overlay authority.",
        ]
    )

    return "\n".join(
        [
            "# CUDA Fractal Finding — Agent Exploration Packet V7",
            "",
            "## Behavioral contract — read first",
            "",
            "- Begin with curiosity-driven discussion of the finding. Do not turn exploratory questions into configuration output.",
            "- Evidence order: frame observations; engine-owned fractal background; state-override authoring surface;",
            "  review sidecar; exact replay state; then proven comparisons.",
            "- A field's presence in broad `state.json` does not prove applicability, activity, or visible contribution.",
            "- Applicable controls are relevant to the live fractal. State-override-authorable controls are the smaller",
            "  set that mechanically maps to fields present in this capture. Only the attached authoring surface grants",
            "  ordinary state-override authority.",
            "- Continuous signals do not establish basins; serialized root symmetry does not establish visible symmetry;",
            "  nonzero values do not prove visible contribution; global statistics cannot be spatially localized; and one",
            "  frame does not prove exact self-similarity.",
            "- Use engine help no more broadly than its words. Separate serialized facts, visual observations, grounded",
            "  inferences, and hypotheses.",
            "",
            "## Experiment executability and observability — read before recommending a state change",
            "",
            "- Curiosity-driven discussion may include three kinds of next step: `state-authorable`, `analysis-only`,",
            "  or `requires unavailable capability`. Before presenting a recommendation as an executable state",
            "  experiment, classify it. Analysis, measurement, comparison, overlays, probes, annotations, diagnostics,",
            "  and automation are not state-authorable unless an exact attached authoring path implements them.",
            "- A state-authorable experiment must describe one candidate state and map to at least one authorized leaf change",
            f"  in the embedded `state-override-authoring-surface.json` section of `{_STATE_AUTHORING_TRANSPORT_FILENAME}`.",
            "  User acceptance of analysis-only or unavailable work does not",
            "  create state authority. At the output trigger, if that mapping fails, ask one clarification question and",
            "  return no preflight or JSON; do not silently substitute a camera, dynamics, or color experiment.",
            "- Before choosing a state experiment, identify the active rendered signal or exported diagnostic that can",
            "  observe its intended effect. If none can, choose an observable experiment, explicitly label a user-requested negative control",
            "  and its limited interpretation, or ask one clarification question. A semantic classification change",
            "  ignored by the active signal must not be presented as a visual test of the hidden class.",
            "- An empty override is an explicit exact-base-replay operation. Return `{}` only when the user explicitly",
            "  requests unchanged-state replay or verification; never use it as a refusal, ambiguity fallback, capability signal,",
            "  or substitute for an unrepresentable experiment. If no authorized leaf change implements the selected",
            "  experiment, ask one clarification question instead.",
            "",
            "## Dynamics and viewport continuity — read before any non-color override",
            "",
            "This rule applies to every fractal selector, not only one family:",
            "",
            "- A color-only change preserves the exact camera unless the user separately asks to reframe.",
            "- For every non-color dynamics change at meaningful zoom, state one camera intent in prose:",
            "  `same_window_comparison`, `feature_tracking`, or `transition_survey`. Camera intent is explanation,",
            "  not a JSON field.",
            "- Small numerical changes do not establish small visual changes. At high zoom, a small parameter change",
            "  can move, split, merge, remove, or reorganize the visible subject far outside the current frame.",
            "- Feature tracking requires an estimated before/after location. Recenter only for a uniquely continued",
            "  feature. For a split, merge, disappearance, or ambiguity, frame the complete branch set or transition",
            "  neighborhood rather than claiming one unchanged object.",
            "- Before retaining the current camera, compare the predicted subject or transition region with the exact",
            "  viewport bounds. `same_window_comparison` is valid only when the relevant subject is predicted to intersect the exact retained viewport,",
            "  or when the user explicitly chooses a fixed-window control",
            "  intentionally expected to lose the subject. Disclose that expected disappearance before returning JSON.",
            "- If the subject is predicted outside the frame, provide a grounded tracking or survey camera, ask for",
            "  direction, or first obtain explicit agreement to the disappearance control. A claimed `feature_tracking`",
            "  or `transition_survey` reframe must have matching complete companion-paired `view` changes in the JSON.",
            "- Whenever attached authority and transparent mathematics permit it, report the predicted subject location",
            "  or transition set, the exact retained viewport bounds, and the containment result. Otherwise state that",
            "  containment cannot be established and choose clarification or an honest survey frame.",
            "- Use `fractal-viewport-facts.json` for the exact renderer mapping, aspect ratio, spans, pixel basis,",
            "  corners, bounds, and inverse-fit equation. Do not invent a universal zoom formula.",
            "- If the feature location cannot be derived from attached engine authority and transparent mathematics,",
            "  say so. Preserve a comparison window or choose an honestly wider survey frame; do not fabricate precision.",
            "",
            "Current engine viewport facts:",
            f"- Mapping: `{viewport_facts['mapping_id']}`",
            f"- High-precision center: `({viewport_camera['center_hp_x']}, {viewport_camera['center_hp_y']})`",
            f"- `log2_zoom`: `{viewport_camera['log2_zoom']}`; resolved zoom: `{viewport_camera['resolved_zoom']}`",
            f"- Complex frame size: `{viewport_frame['full_width']} × {viewport_frame['full_height']}`",
            f"- Complex units per pixel: X `{viewport_basis['units_per_pixel_x']}`, Y `{viewport_basis['units_per_pixel_y']}`",
            "",
            "## Output trigger and contract",
            "",
            "Discuss ideas normally until the user explicitly asks to make, apply, or return a concrete change, or",
            "unambiguously accepts one specific immediately preceding change. One override represents one state and one",
            "coherent experiment. Generic assent is ambiguous after multiple numbered experiments, alternatives, a",
            "multi-value sweep, unresolved camera choices, or more than one candidate state. Ask one concise clarification",
            "question unless the user explicitly delegates the selection. A sweep cannot be encoded as one override;",
            "select its exact single member before returning JSON.",
            "Ambiguity exception: when the selected experiment is ambiguous, return exactly one clarification question",
            "with no decision-preflight sections and no JSON. The five-section preflight plus one JSON block applies only",
            "after one coherent candidate state has been selected.",
            "",
            "When triggered, provide a concise visible decision preflight using these exact labels:",
            "",
            "- `Chosen experiment`: identify the one state and experiment being implemented.",
            "- `Why this override`: connect every changed path to that experiment.",
            "- `Expected effect, observation channel, and uncertainty`: state the expected result, the exact active",
            "  rendered signal or exported diagnostic that can observe it, the expected information gain, and the",
            "  largest uncertainty.",
            "- `Camera intent and viewport check`: name the intent, compare the subject with the exact bounds, and state",
            "  whether the subject should remain visible. For a color-only change, say that the exact camera is preserved",
            "  and return no `view` paths unless the user separately requested reframing.",
            "- `Hostile self-review conclusion`: report the strongest plausible failure and whether ambiguity, path",
            "  authority, narrative/JSON alignment, displacement, split/merge/disappearance, blank framing, and accidental",
            "  compression of multiple states into one have been resolved. Keep this to a brief audit conclusion, for",
            "  example: `Rejected the unchanged camera because the predicted transition set lies outside the retained",
            "  bounds; selected a transition-survey reframe.`",
            "",
            "Do not provide private chain-of-thought; report only the concise auditable conclusions above. Every JSON change",
            "must be explained, and every promised mutation must appear in JSON. After the preflight, return exactly one",
            "fenced `json` block containing one sparse state-shaped object and no other code block. Include only",
            "properties to change. Do not return a complete state, IDs, hashes, capability profiles, actions,",
            "or receipt metadata. Objects merge recursively; scalars replace; arrays replace completely. `null`, duplicates,",
            "unknown paths, absent paths, and read-only fields are rejected.",
            "For view changes, return each ordinary value and its required serialized companion in the same override:",
            "`center_x` with `center_hp_x`, `center_y` with `center_hp_y`, and `zoom` with `log2_zoom`.",
            "Use the JSON types shown in `state.json`; do not return a companion by itself.",
            *color_authoring_guidance,
            "",
            "### State Override Example",
            "",
            "This illustrates the wire shape only. It is authorized for this finding only if the exact path appears in",
            "`state-override-authoring-surface.json`.",
            "",
            "```json",
            "{",
            '  "params": {',
            '    "explaino_damping": 0.9',
            "  }",
            "}",
            "```",
            "",
            example_note,
            "",
            "## Selected fractal — engine-owned mathematical background",
            "",
            *_selected_description_lines(selected_entry),
            "",
            "## Current finding",
            "",
            f"- Finding ID: `{finding_id}`",
            f"- Selected fractal: `{fractal_type}`",
            f"- Render: `{render.get('width', '?')} × {render.get('height', '?')}` on device `{render.get('device_id', '?')}`",
            f"- Iterations: `{params.get('max_iter', '?')}`",
            f"- Serialized flat color tuple: `{params.get('color_signal', '?')} -> {params.get('color_shape', '?')} -> "
            f"{params.get('color_palette', '?')} -> {params.get('color_grading', '?')}`",
            "",
            "### Serialized Color Pipeline",
            "",
            *pipeline_summary,
            "",
            "### Web discussion image",
            "",
            *web_frame_lines,
            "",
            "### State-override-authorable paths",
            "",
            *([f"- `{path}`" for path in authorable_paths] or ["- No ordinary state paths resolved for this capture."]),
            "",
            "The complete types, ranges, options, current values, source control IDs, and authority hashes are embedded in",
            f"`{_STATE_AUTHORING_TRANSPORT_FILENAME}`. The complete local JSON authorities remain in this immutable packet.",
            "",
            "## Required authority attachments",
            "",
            *attachment_lines,
            "",
            "## Web-session handoff",
            "",
            "1. Paste this exact `packet.md` text into the fresh session.",
            "2. Open this packet's bundle folder.",
            "3. Attach every file under Required authority attachments, preserving its filename.",
            "4. Confirm the session can identify every required authority before relying on its analysis.",
            "",
            "## Recommended context attachments",
            "",
            *(context_lines or ["- None present."]),
            "",
            "## Optional attachments unavailable in this capture",
            "",
            *(unavailable_lines or ["- None."]),
            "",
            "Copying this Markdown does not transport those files. Attach them from the packet directory before relying on them.",
            "",
            "## Authority ownership",
            "",
            "- `state.json`: exact complete replay base.",
            "- `fractal-state.json`: capture-time review projection and derived receipts, when present.",
            "- `fractal-viewport-facts.json`: engine-owned exact camera geometry and inverse-fit authority.",
            f"- `{_STATE_AUTHORING_TRANSPORT_FILENAME}`: exact embedded parameter surface, UI schema, and finding-specific authoring index.",
            f"- `{_COLOR_PIPELINE_TRANSPORT_FILENAME}`: exact embedded UI-Salt contract and current pipeline editing context.",
            f"- `{_FINDING_CONTEXT_TRANSPORT_FILENAME}`: finding manifest, field notes, and selected engine-owned description.",
            f"- `{_WEB_FRAME_FILENAME}`: bounded PNG discussion derivative with explicit source and resampling provenance.",
            "- The exact captured source frame remains local immutable visual evidence and is not silently replaced.",
            "- The individual JSON and context files remain local immutable proof authorities even when they are not web uploads.",
            "",
            f"Packet ID: `{packet_id}`",
            "",
        ]
    )


def build_agent_bundle(
    finding_dir: Path,
    runtime_cmd_path: Path,
    job: Optional[JobContext] = None,
    timeout_seconds: float = 30.0,
) -> AgentBundle:
    finding_dir = finding_dir.resolve()
    runtime_cmd_path = runtime_cmd_path.resolve()
    workspace_manifest_path = finding_dir / "workspace.json"
    if not workspace_manifest_path.is_file():
        raise FileNotFoundError(f"Finding workspace manifest is missing: {workspace_manifest_path}")
    workspace_manifest = _load_json_object(workspace_manifest_path.read_bytes(), "Finding workspace manifest")
    finding_id = workspace_manifest.get("finding_id")
    if not isinstance(finding_id, str) or not finding_id:
        raise ValueError("Finding workspace manifest has no finding_id")

    source_paths: dict[str, Path] = {}
    state_path = _artifact_path(finding_dir, workspace_manifest, "state")
    if state_path is None:
        raise ValueError("Finding workspace manifest has no authoring state")
    source_paths["state.json"] = state_path
    optional_sources = {
        "fractal-state.json": "review_fractal_state",
        _VIEWPORT_FACTS_FILENAME: "fractal_viewport_facts",
        "finding.json": "finding_manifest",
        "field-notes.md": "field_notes",
    }
    for filename, key in optional_sources.items():
        path = _artifact_path(finding_dir, workspace_manifest, key)
        if path is None and filename == "field-notes.md":
            discovered = finding_dir / "source" / filename
            path = discovered.resolve() if discovered.is_file() else None
        if path is not None:
            source_paths[filename] = path
    frame_path = _artifact_path(finding_dir, workspace_manifest, "primary_frame")
    frame_filename: str | None = None
    if frame_path is not None:
        frame_filename = f"frame{frame_path.suffix.lower()}"
        source_paths[frame_filename] = frame_path

    resolution = resolve_launcher(runtime_cmd_path)
    if not resolution.runtime_schema_path or not resolution.ui_salt_contract_path:
        raise ValueError("Published runtime is missing the deployed UI schema or UI-Salt contract")
    runtime_identity_before = build_runtime_identity(runtime_cmd_path, runtime_cmd_path.parent)
    schema_source = Path(resolution.runtime_schema_path).resolve()
    contract_source = Path(resolution.ui_salt_contract_path).resolve()
    packet_id = str(uuid.uuid4())
    packets_dir = finding_dir / "packets"
    packets_dir.mkdir(parents=True, exist_ok=True)
    stage_dir = packets_dir / f".packet-v7-{packet_id}.tmp"
    final_dir = packets_dir / packet_id
    if stage_dir.exists() or final_dir.exists():
        raise FileExistsError(f"Packet identity collision: {packet_id}")
    stage_dir.mkdir()
    try:
        parameter_surface_bytes = _capture_export(
            runtime_cmd_path,
            "--describe-parameter-surface-json",
            _PARAMETER_SURFACE_FILENAME,
            job,
            timeout_seconds,
            packets_dir,
        )
        catalog_bytes = _capture_export(
            runtime_cmd_path,
            "--describe-fractal-catalog-json",
            _CATALOG_FILENAME,
            job,
            timeout_seconds,
            packets_dir,
        )
        staged_source_hashes: dict[str, str] = {}
        for filename, source_path in source_paths.items():
            payload = source_path.read_bytes()
            _write_bytes(stage_dir / filename, payload)
            staged_source_hashes[filename] = _sha256_bytes(payload)
        _write_bytes(stage_dir / _SCHEMA_FILENAME, schema_source.read_bytes())
        _write_bytes(stage_dir / _UI_SALT_FILENAME, contract_source.read_bytes())
        _write_bytes(stage_dir / _PARAMETER_SURFACE_FILENAME, parameter_surface_bytes)
        _write_bytes(stage_dir / _CATALOG_FILENAME, catalog_bytes)

        state_bytes = (stage_dir / "state.json").read_bytes()
        schema_bytes = (stage_dir / _SCHEMA_FILENAME).read_bytes()
        contract_bytes = (stage_dir / _UI_SALT_FILENAME).read_bytes()
        copied_parameter_surface_bytes = (stage_dir / _PARAMETER_SURFACE_FILENAME).read_bytes()
        copied_catalog_bytes = (stage_dir / _CATALOG_FILENAME).read_bytes()
        state = _load_json_object(state_bytes, "Copied state.json")
        contract = _load_json_object(contract_bytes, "Copied UI-Salt contract")
        selected = state.get("fractal_type")
        if not isinstance(selected, str) or not selected:
            raise ValueError("Copied state.json has no selected fractal_type")
        render = state.get("render")
        if not isinstance(render, dict):
            raise ValueError("Copied state.json has no render object")
        width = render.get("width")
        height = render.get("height")
        if (
            isinstance(width, bool)
            or not isinstance(width, int)
            or width <= 0
            or isinstance(height, bool)
            or not isinstance(height, int)
            or height <= 0
        ):
            raise ValueError("Copied state.json has invalid render dimensions")

        runtime_viewport_bytes = _capture_export(
            runtime_cmd_path,
            "--describe-viewport-facts-json",
            _VIEWPORT_FACTS_FILENAME,
            job,
            timeout_seconds,
            packets_dir,
            "--load-state-json",
            str((stage_dir / "state.json").resolve()),
        )
        if _VIEWPORT_FACTS_FILENAME in source_paths:
            copied_viewport_bytes = (stage_dir / _VIEWPORT_FACTS_FILENAME).read_bytes()
            if copied_viewport_bytes != runtime_viewport_bytes:
                raise ValueError(
                    "Captured finding viewport facts disagree with the current runtime export "
                    "for the exact copied state"
                )
            viewport_facts_origin = "captured_finding_sidecar_verified_against_runtime"
        else:
            copied_viewport_bytes = runtime_viewport_bytes
            _write_bytes(stage_dir / _VIEWPORT_FACTS_FILENAME, copied_viewport_bytes)
            viewport_facts_origin = "runtime_export_from_copied_state"
        viewport_facts = validate_viewport_facts_bytes(
            copied_viewport_bytes,
            expected_selector=selected,
            expected_width=width,
            expected_height=height,
        )
        catalog_by_selector = validate_catalog_bytes(copied_catalog_bytes)
        selected_entry = catalog_by_selector.get(selected)
        if selected_entry is None:
            raise ValueError(f"Copied descriptive catalog has no selected selector: {selected}")

        authoring_surface = derive_state_override_authoring_surface(
            state_bytes,
            copied_parameter_surface_bytes,
            schema_bytes,
        )
        authoring_surface_bytes = serialize_state_override_authoring_surface(authoring_surface)
        _write_bytes(stage_dir / _AUTHORING_SURFACE_FILENAME, authoring_surface_bytes)
        loaded_surface = _load_json_object(authoring_surface_bytes, "Derived authoring surface")
        refs = loaded_surface.get("authority_refs")
        expected_refs = {
            "state_sha256": _sha256_bytes(state_bytes),
            "parameter_surface_sha256": _sha256_bytes(copied_parameter_surface_bytes),
            "ui_schema_sha256": _sha256_bytes(schema_bytes),
        }
        if refs != expected_refs:
            raise ValueError("Derived authoring surface authority_refs do not match neighboring bundle files")

        draft = validate_captured_color_pipeline_draft(state, contract)
        has_pipeline_example = draft is not None
        if draft is not None:
            _validate_color_pipeline_compatibility_authority(contract)
            example_bytes = _json_bytes({"color_pipeline_draft": {"lanes": draft["lanes"]}}, sort_keys=False)
            _write_bytes(stage_dir / _PIPELINE_EXAMPLE_FILENAME, example_bytes)

        web_frame_derivative = (
            _create_web_frame_derivative(stage_dir, frame_filename, job, timeout_seconds)
            if frame_filename is not None
            else None
        )
        unavailable = [
            name
            for name in ("fractal-state.json", "finding.json", "field-notes.md", "frame")
            if (name == "frame" and frame_filename is None)
            or (name != "frame" and name not in source_paths)
        ]
        transport_views = _build_transport_views(
            stage_dir,
            state,
            selected_entry,
            unavailable,
            has_pipeline_example=has_pipeline_example,
        )
        for filename, payload in transport_views.items():
            _write_bytes(stage_dir / filename, payload)

        required = [
            "state.json",
            *(["fractal-state.json"] if "fractal-state.json" in source_paths else []),
            _VIEWPORT_FACTS_FILENAME,
            _STATE_AUTHORING_TRANSPORT_FILENAME,
            _COLOR_PIPELINE_TRANSPORT_FILENAME,
            _FINDING_CONTEXT_TRANSPORT_FILENAME,
            *([_WEB_FRAME_FILENAME] if web_frame_derivative else []),
        ]
        recommended: list[str] = []
        hash_names = required + recommended
        file_hashes = {name: sha256_file(stage_dir / name) for name in hash_names}
        packet_text = _packet_markdown(
            packet_id,
            finding_id,
            state,
            selected_entry,
            viewport_facts,
            authoring_surface,
            required,
            recommended,
            unavailable,
            file_hashes,
            has_pipeline_example,
            web_frame_derivative,
        )
        packet_bytes = packet_text.encode("utf-8")
        _write_bytes(stage_dir / "packet.md", packet_bytes)

        file_records: list[dict[str, Any]] = []
        roles = {
            "packet.md": "behavior_and_authority_index",
            "state.json": "complete_replay_base",
            "fractal-state.json": "capture_review_projection",
            "finding.json": "capture_manifest_context",
            "field-notes.md": "user_context",
            _SCHEMA_FILENAME: "deployed_ui_control_authority",
            _UI_SALT_FILENAME: "deployed_color_pipeline_authority",
            _PARAMETER_SURFACE_FILENAME: "runtime_parameter_applicability_authority",
            _CATALOG_FILENAME: "runtime_fractal_description_authority",
            _VIEWPORT_FACTS_FILENAME: "runtime_viewport_geometry_authority",
            _AUTHORING_SURFACE_FILENAME: "finding_specific_state_override_index",
            _PIPELINE_EXAMPLE_FILENAME: "captured_pipeline_whole_array_example",
            _STATE_AUTHORING_TRANSPORT_FILENAME: "consolidated_state_authoring_transport_view",
            _COLOR_PIPELINE_TRANSPORT_FILENAME: "consolidated_color_pipeline_transport_view",
            _FINDING_CONTEXT_TRANSPORT_FILENAME: "consolidated_finding_context_transport_view",
        }
        if frame_filename:
            roles[frame_filename] = "captured_visual_evidence"
        if web_frame_derivative:
            roles[_WEB_FRAME_FILENAME] = "web_discussion_derivative"
        for path in sorted(item for item in stage_dir.iterdir() if item.is_file()):
            file_records.append(
                {
                    "path": path.name,
                    "role": roles[path.name],
                    "sha256": sha256_file(path),
                    "size_bytes": path.stat().st_size,
                    "web_handoff": (
                        "required"
                        if path.name in required
                        else "recommended"
                        if path.name in recommended
                        else "index"
                        if path.name == "packet.md"
                        else "generated_helper"
                        if path.name == _PIPELINE_EXAMPLE_FILENAME
                        else "local_authority"
                    ),
                }
            )

        runtime_summary = runtime_identity_summary(runtime_identity_before)
        manifest = {
            "bundle_manifest_version": BUNDLE_MANIFEST_VERSION,
            "packet_version": PACKET_VERSION,
            "packet_id": packet_id,
            "finding_id": finding_id,
            "selected_fractal_type": selected,
            "selected_fractal_description_status": selected_entry["description_status"],
            "viewport_facts_origin": viewport_facts_origin,
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "runtime_identity": runtime_summary,
            "runtime_identity_sha256": runtime_identity_summary_sha256(runtime_summary),
            "authority_identities": {
                "state_sha256": _sha256_bytes(state_bytes),
                "parameter_surface_sha256": _sha256_bytes(copied_parameter_surface_bytes),
                "ui_schema_sha256": _sha256_bytes(schema_bytes),
                "ui_salt_contract_sha256": _sha256_bytes(contract_bytes),
                "fractal_descriptive_catalog_sha256": _sha256_bytes(copied_catalog_bytes),
                "fractal_viewport_facts_sha256": _sha256_bytes(copied_viewport_bytes),
                "state_override_authoring_surface_sha256": _sha256_bytes(authoring_surface_bytes),
            },
            "web_frame_derivative": web_frame_derivative,
            "required_attachments": required,
            "recommended_attachments": recommended,
            "unavailable_optional_attachments": unavailable,
            "files": file_records,
        }
        _write_bytes(stage_dir / "manifest.json", _json_bytes(manifest))

        parameter_surface_after = _capture_export(
            runtime_cmd_path,
            "--describe-parameter-surface-json",
            _PARAMETER_SURFACE_FILENAME,
            job,
            timeout_seconds,
            packets_dir,
        )
        catalog_after = _capture_export(
            runtime_cmd_path,
            "--describe-fractal-catalog-json",
            _CATALOG_FILENAME,
            job,
            timeout_seconds,
            packets_dir,
        )
        viewport_after = _capture_export(
            runtime_cmd_path,
            "--describe-viewport-facts-json",
            _VIEWPORT_FACTS_FILENAME,
            job,
            timeout_seconds,
            packets_dir,
            "--load-state-json",
            str((stage_dir / "state.json").resolve()),
        )
        runtime_identity_after = build_runtime_identity(runtime_cmd_path, runtime_cmd_path.parent)
        if parameter_surface_after != copied_parameter_surface_bytes:
            raise ValueError("Runtime parameter-surface export changed during packet construction")
        if catalog_after != copied_catalog_bytes:
            raise ValueError("Runtime descriptive-catalog export changed during packet construction")
        if viewport_after != copied_viewport_bytes:
            raise ValueError("Runtime viewport-facts export changed during packet construction")
        if runtime_identity_summary(runtime_identity_after) != runtime_summary:
            raise ValueError("Published runtime identity changed during packet construction")
        if sha256_file(schema_source) != _sha256_bytes(schema_bytes):
            raise ValueError("Deployed UI schema changed during packet construction")
        if sha256_file(contract_source) != _sha256_bytes(contract_bytes):
            raise ValueError("Deployed UI-Salt contract changed during packet construction")
        for filename, source_path in source_paths.items():
            if sha256_file(source_path) != staged_source_hashes[filename]:
                raise ValueError(f"Finding source changed during packet construction: {filename}")

        load_agent_bundle_handoff(stage_dir)

        os.replace(str(stage_dir), str(final_dir))
    except Exception:
        shutil.rmtree(stage_dir, ignore_errors=True)
        raise

    packet_path = final_dir / "packet.md"
    manifest_path = final_dir / "manifest.json"
    return AgentBundle(
        packet_version=PACKET_VERSION,
        packet_id=packet_id,
        packet_dir=final_dir.resolve(),
        packet_path=packet_path.resolve(),
        packet_sha256=sha256_file(packet_path),
        manifest_path=manifest_path.resolve(),
        manifest_sha256=sha256_file(manifest_path),
        finding_id=finding_id,
        selected_fractal_type=selected,
        required_attachments=tuple(required),
        recommended_attachments=tuple(recommended),
        unavailable_optional_attachments=tuple(unavailable),
    )
