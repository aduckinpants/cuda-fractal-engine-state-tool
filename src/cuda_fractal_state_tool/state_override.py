from __future__ import annotations

import copy
import hashlib
import json
import math
import os
import re
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from .agent_bundle import (
    derive_state_override_authoring_surface,
    load_agent_bundle_handoff,
    serialize_state_override_authoring_surface,
    validate_captured_color_pipeline_draft,
)
from .json_utils import loads_strict_no_duplicates


ALLOWED_TOP_LEVEL_DOMAINS = {"params", "view", "color_pipeline_draft"}
_PIPELINE_CHANGE_RE = re.compile(r"^color_pipeline_draft\.lanes\[(\d+)\]")


@dataclass(frozen=True)
class ParsedStateOverride:
    exact_text: str
    exact_utf8: bytes
    sha256: str
    document: dict[str, Any]


@dataclass(frozen=True)
class StateValueChange:
    path: str
    base_value: Any
    merged_value: Any
    conceptual_domain: str


@dataclass(frozen=True)
class StateOverrideMaterialization:
    output_path: Path
    override_text_sha256: str
    base_state_sha256: str
    merged_candidate_sha256: str
    empty_override_byte_exact: bool
    requested_paths: tuple[str, ...]
    changed_paths: tuple[StateValueChange, ...]
    conceptual_domains: tuple[str, ...]
    camera_edits: tuple[str, ...]


@dataclass(frozen=True)
class _PacketOverrideAuthorities:
    state_bytes: bytes
    state: dict[str, Any]
    authoring_surface: dict[str, Any]
    ui_salt_contract: dict[str, Any]


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _load_strict_object(payload: bytes, label: str) -> dict[str, Any]:
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(f"{label} is not valid UTF-8") from exc
    value = loads_strict_no_duplicates(text)
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a JSON object")
    return value


def parse_state_override(text: str) -> ParsedStateOverride:
    try:
        exact_utf8 = text.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise ValueError("State override text cannot be encoded as UTF-8") from exc
    try:
        value = loads_strict_no_duplicates(text)
    except (json.JSONDecodeError, ValueError) as exc:
        raise ValueError(f"State override is not strict JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError("State override must be one JSON object")
    unknown = sorted(set(value) - ALLOWED_TOP_LEVEL_DOMAINS)
    if unknown:
        raise ValueError(f"State override contains unsupported top-level domains: {unknown}")
    for domain, domain_value in value.items():
        if not isinstance(domain_value, dict):
            raise ValueError(f"State override {domain} must be an object")
    _reject_nulls_and_nonfinite(value)
    return ParsedStateOverride(
        exact_text=text,
        exact_utf8=exact_utf8,
        sha256=_sha256_bytes(exact_utf8),
        document=value,
    )


def _reject_nulls_and_nonfinite(value: Any, path: str = "$") -> None:
    if value is None:
        raise ValueError(f"State override contains null at {path}")
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError(f"State override contains a non-finite number at {path}")
    if isinstance(value, dict):
        for key, item in value.items():
            _reject_nulls_and_nonfinite(item, f"{path}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _reject_nulls_and_nonfinite(item, f"{path}[{index}]")


def _required_packet_bytes(packet_dir: Path, filename: str) -> bytes:
    path = packet_dir / filename
    if not path.is_file():
        raise FileNotFoundError(f"Packet V6 authority is missing: {path}")
    return path.read_bytes()


def _load_packet_authorities(
    packet_dir: Path,
    expected_manifest_sha256: str | None,
) -> _PacketOverrideAuthorities:
    packet_dir = packet_dir.resolve()
    load_agent_bundle_handoff(packet_dir)
    manifest_path = packet_dir / "manifest.json"
    manifest_bytes = manifest_path.read_bytes()
    manifest_sha256 = _sha256_bytes(manifest_bytes)
    if expected_manifest_sha256 is not None and manifest_sha256 != expected_manifest_sha256:
        raise ValueError("Packet V6 manifest hash does not match the bound session")
    manifest = _load_strict_object(manifest_bytes, "Packet V6 manifest.json")
    records = manifest.get("files")
    if not isinstance(records, list):
        raise ValueError("Packet V6 manifest has no files array")
    record_by_path = {
        record.get("path"): record
        for record in records
        if isinstance(record, dict) and isinstance(record.get("path"), str)
    }

    def captured_bytes(filename: str) -> bytes:
        payload = _required_packet_bytes(packet_dir, filename)
        record = record_by_path.get(filename)
        if (
            not isinstance(record, dict)
            or record.get("sha256") != _sha256_bytes(payload)
            or record.get("size_bytes") != len(payload)
        ):
            raise ValueError(f"Packet V6 authority bytes disagree with manifest.json: {filename}")
        return payload

    state_bytes = captured_bytes("state.json")
    parameter_surface_bytes = captured_bytes("fractal-parameter-surface.json")
    ui_schema_bytes = captured_bytes("fractal_binding_surface_v1.ui_schema.json")
    ui_salt_bytes = captured_bytes("color_pipeline_function_library.contract.v1.json")
    bundled_surface_bytes = captured_bytes("state-override-authoring-surface.json")

    state = _load_strict_object(state_bytes, "Packet V6 state.json")
    bundled_surface = _load_strict_object(
        bundled_surface_bytes,
        "Packet V6 state-override-authoring-surface.json",
    )
    regenerated_surface = derive_state_override_authoring_surface(
        state_bytes,
        parameter_surface_bytes,
        ui_schema_bytes,
    )
    regenerated_bytes = serialize_state_override_authoring_surface(regenerated_surface)
    if bundled_surface_bytes != regenerated_bytes or bundled_surface != regenerated_surface:
        raise ValueError("Packet V6 authoring surface does not match its copied authority bytes")
    ui_salt_contract = _load_strict_object(ui_salt_bytes, "Packet V6 UI-Salt contract")
    if manifest_path.read_bytes() != manifest_bytes:
        raise ValueError("Packet V6 manifest changed while loading override authorities")
    load_agent_bundle_handoff(packet_dir)
    return _PacketOverrideAuthorities(
        state_bytes=state_bytes,
        state=state,
        authoring_surface=bundled_surface,
        ui_salt_contract=ui_salt_contract,
    )


def _resolve_path(root: Any, dotted_path: str) -> tuple[bool, Any]:
    current = root
    for part in dotted_path.split("."):
        if not isinstance(current, dict) or part not in current:
            return False, None
        current = current[part]
    return True, current


def _walk_leaves(value: Any, prefix: str) -> Iterable[tuple[str, Any]]:
    if isinstance(value, dict):
        for key, item in value.items():
            child = f"{prefix}.{key}" if prefix else key
            yield from _walk_leaves(item, child)
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            yield from _walk_leaves(item, f"{prefix}[{index}]")
        return
    yield prefix, value


def _validate_existing_object_shape(override: dict[str, Any], base: dict[str, Any], prefix: str) -> None:
    for key, value in override.items():
        path = f"{prefix}.{key}" if prefix else key
        if key not in base:
            raise ValueError(f"State override path is absent from the base state: {path}")
        base_value = base[key]
        if isinstance(value, dict):
            if not isinstance(base_value, dict):
                raise ValueError(f"State override object conflicts with scalar base path: {path}")
            _validate_existing_object_shape(value, base_value, path)


def _authoring_entries(surface: dict[str, Any]) -> dict[str, dict[str, Any]]:
    entries = surface.get("entries")
    if not isinstance(entries, list):
        raise ValueError("Packet V6 authoring surface has no entries array")
    indexed: dict[str, dict[str, Any]] = {}
    for entry in entries:
        if not isinstance(entry, dict) or not isinstance(entry.get("path"), str):
            raise ValueError("Packet V6 authoring surface contains an invalid entry")
        path = entry["path"]
        if path in indexed:
            raise ValueError(f"Packet V6 authoring surface repeats path: {path}")
        indexed[path] = entry
    return indexed


def _validate_value_against_entry(path: str, value: Any, entry: dict[str, Any]) -> None:
    value_type = entry.get("type")
    if value_type in {"float", "double"}:
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError(f"State override {path} must be a finite number")
    elif value_type == "int":
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"State override {path} must be an integer")
    elif value_type == "bool":
        if not isinstance(value, bool):
            raise ValueError(f"State override {path} must be a boolean")
    elif value_type == "enum":
        options = entry.get("options")
        if not isinstance(value, str) or not isinstance(options, list) or value not in options:
            raise ValueError(f"State override {path} must use a declared enum option")
    else:
        raise ValueError(f"State override {path} has unsupported deployed value type: {value_type}")

    if isinstance(value, (int, float)) and not isinstance(value, bool):
        minimum = entry.get("minimum")
        maximum = entry.get("maximum")
        if isinstance(minimum, (int, float)) and value < minimum:
            raise ValueError(f"State override {path} is below the deployed minimum {minimum}")
        if isinstance(maximum, (int, float)) and value > maximum:
            raise ValueError(f"State override {path} is above the deployed maximum {maximum}")


def _validate_params_and_view(
    override: dict[str, Any],
    base: dict[str, Any],
    surface: dict[str, Any],
) -> tuple[str, ...]:
    indexed = _authoring_entries(surface)
    requested_paths: set[str] = set()
    for domain in ("params", "view"):
        domain_override = override.get(domain)
        if domain_override is None:
            continue
        domain_base = base.get(domain)
        if not isinstance(domain_base, dict):
            raise ValueError(f"Base state has no authorable {domain} object")
        _validate_existing_object_shape(domain_override, domain_base, domain)
        for path, value in _walk_leaves(domain_override, domain):
            requested_paths.add(path)
            entry = indexed.get(path)
            if entry is not None:
                _validate_value_against_entry(path, value, entry)

    rules = surface.get("companion_rules")
    if not isinstance(rules, list):
        raise ValueError("Packet V6 authoring surface has no companion_rules array")
    companion_paths: set[str] = set()
    camera_edits: list[str] = []
    for rule in rules:
        if (
            not isinstance(rule, dict)
            or not isinstance(rule.get("path"), str)
            or not isinstance(rule.get("requires_changed_path"), str)
        ):
            raise ValueError("Packet V6 authoring surface contains an invalid companion rule")
        companion = rule["path"]
        ordinary = rule["requires_changed_path"]
        companion_paths.add(companion)
        ordinary_present = ordinary in requested_paths
        companion_present = companion in requested_paths
        if ordinary_present != companion_present:
            raise ValueError(f"Camera edit must include both {ordinary} and {companion}")
        if ordinary_present:
            camera_edits.append(ordinary)

    for path, value in _walk_leaves(override.get("view", {}), "view"):
        if path in indexed:
            continue
        if path not in companion_paths:
            raise ValueError(f"State override path is not state-authorable: {path}")
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError(f"Camera companion {path} must be a finite number")
        present, base_value = _resolve_path(base, path)
        if not present or isinstance(base_value, bool) or not isinstance(base_value, (int, float)):
            raise ValueError(f"Camera companion {path} disagrees with the serialized base type")

    for path, value in _walk_leaves(override.get("params", {}), "params"):
        if path not in indexed:
            raise ValueError(f"State override path is not state-authorable: {path}")
        _validate_value_against_entry(path, value, indexed[path])
    zoom_present, zoom_value = _resolve_path(override, "view.zoom")
    if zoom_present and zoom_value <= 0:
        raise ValueError("State override view.zoom must be positive")
    return tuple(camera_edits)


def _validate_and_order_pipeline_lanes(
    override_value: dict[str, Any],
    base: dict[str, Any],
    contract: dict[str, Any],
) -> list[dict[str, Any]]:
    if set(override_value) != {"lanes"} or not isinstance(override_value.get("lanes"), list):
        raise ValueError("color_pipeline_draft override must contain only a complete lanes array")
    base_draft = base.get("color_pipeline_draft")
    if not isinstance(base_draft, dict):
        raise ValueError("Base state has no complete color_pipeline_draft")
    validate_captured_color_pipeline_draft(base, contract)
    base_lanes = base_draft.get("lanes")
    override_lanes = override_value["lanes"]
    if not isinstance(base_lanes, list) or len(override_lanes) != len(base_lanes):
        raise ValueError("Color Pipeline lane count must match the captured draft")

    ordered_lanes: list[dict[str, Any]] = []
    for lane_index, (base_lane, override_lane) in enumerate(zip(base_lanes, override_lanes, strict=True)):
        if not isinstance(base_lane, dict) or not isinstance(override_lane, dict):
            raise ValueError(f"Color Pipeline lane {lane_index} must remain an object")
        if set(override_lane) != set(base_lane):
            raise ValueError(f"Color Pipeline lane {lane_index} fields must match the captured topology")
        for key in base_lane:
            if key != "rows" and override_lane[key] != base_lane[key]:
                raise ValueError(f"Color Pipeline lane {lane_index}.{key} is topology and cannot change")
        base_rows = base_lane.get("rows")
        override_rows = override_lane.get("rows")
        if not isinstance(base_rows, list) or not isinstance(override_rows, list) or len(override_rows) != len(base_rows):
            raise ValueError(f"Color Pipeline row count must match captured lane {base_lane.get('lane_id')}")

        ordered_rows: list[dict[str, Any]] = []
        for row_index, (base_row, override_row) in enumerate(zip(base_rows, override_rows, strict=True)):
            if not isinstance(base_row, dict) or not isinstance(override_row, dict):
                raise ValueError(f"Color Pipeline row {lane_index}[{row_index}] must remain an object")
            if set(override_row) != set(base_row):
                raise ValueError(f"Color Pipeline row {lane_index}[{row_index}] fields must match captured topology")
            for key in base_row:
                if key not in {"function_id", "parameter_values"} and override_row[key] != base_row[key]:
                    raise ValueError(
                        f"Color Pipeline row {lane_index}[{row_index}].{key} is topology and cannot change"
                    )
            ordered_row = {key: copy.deepcopy(override_row[key]) for key in base_row}
            ordered_rows.append(ordered_row)
        ordered_lane = {
            key: ordered_rows if key == "rows" else copy.deepcopy(override_lane[key])
            for key in base_lane
        }
        ordered_lanes.append(ordered_lane)

    candidate = copy.deepcopy(base)
    candidate["color_pipeline_draft"]["lanes"] = ordered_lanes
    validate_captured_color_pipeline_draft(candidate, contract)
    return ordered_lanes


def _deep_merge_existing(target: dict[str, Any], override: dict[str, Any]) -> None:
    for key, value in override.items():
        if isinstance(value, dict):
            current = target[key]
            if not isinstance(current, dict):
                raise ValueError(f"Cannot merge object into scalar state key: {key}")
            _deep_merge_existing(current, value)
        else:
            target[key] = copy.deepcopy(value)


def _diff_values(left: Any, right: Any, prefix: str = "") -> Iterable[tuple[str, Any, Any]]:
    if isinstance(left, dict) and isinstance(right, dict):
        for key in left:
            child = f"{prefix}.{key}" if prefix else key
            yield from _diff_values(left[key], right[key], child)
        return
    if isinstance(left, list) and isinstance(right, list) and len(left) == len(right):
        for index, (left_item, right_item) in enumerate(zip(left, right, strict=True)):
            yield from _diff_values(left_item, right_item, f"{prefix}[{index}]")
        return
    if left != right:
        yield prefix, left, right


def _conceptual_domain(path: str, merged: dict[str, Any]) -> str:
    if path.startswith("params."):
        return path.split(".", 2)[0] + "." + path.split(".", 2)[1]
    if path.startswith("view.center_x") or path.startswith("view.center_hp_x"):
        return "view.center_x"
    if path.startswith("view.center_y") or path.startswith("view.center_hp_y"):
        return "view.center_y"
    if path.startswith("view.zoom") or path.startswith("view.log2_zoom"):
        return "view.zoom"
    match = _PIPELINE_CHANGE_RE.match(path)
    if match:
        lane_index = int(match.group(1))
        lanes = merged.get("color_pipeline_draft", {}).get("lanes", [])
        if 0 <= lane_index < len(lanes) and isinstance(lanes[lane_index], dict):
            return f"color_pipeline_draft.{lanes[lane_index].get('lane_id', lane_index)}"
        return "color_pipeline_draft"
    return path.split(".", 1)[0]


def _atomic_write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(f".{path.name}.tmp.{uuid.uuid4().hex}")
    try:
        with temp_path.open("xb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(str(temp_path), str(path))
    finally:
        if temp_path.exists():
            temp_path.unlink()


def materialize_state_override(
    packet_dir: Path,
    override_text: str,
    output_path: Path,
    *,
    expected_manifest_sha256: str | None = None,
) -> StateOverrideMaterialization:
    packet_dir = packet_dir.resolve()
    output_path = output_path.resolve()
    authorities = _load_packet_authorities(packet_dir, expected_manifest_sha256)
    try:
        output_path.relative_to(packet_dir)
    except ValueError:
        pass
    else:
        raise ValueError("Merged candidate output must not write inside the immutable Packet V6 directory")
    parsed = parse_state_override(override_text)
    base = authorities.state
    override = parsed.document

    camera_edits = _validate_params_and_view(override, base, authorities.authoring_surface)
    merged = copy.deepcopy(base)
    for domain in ("params", "view"):
        domain_override = override.get(domain)
        if domain_override is not None:
            _deep_merge_existing(merged[domain], domain_override)
    if "color_pipeline_draft" in override:
        ordered_lanes = _validate_and_order_pipeline_lanes(
            override["color_pipeline_draft"],
            base,
            authorities.ui_salt_contract,
        )
        merged["color_pipeline_draft"]["lanes"] = ordered_lanes

    if not override:
        candidate_bytes = authorities.state_bytes
        empty_override_byte_exact = True
    else:
        candidate_bytes = (
            json.dumps(merged, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
        ).encode("utf-8")
        empty_override_byte_exact = False
    _atomic_write(output_path, candidate_bytes)

    changes: list[StateValueChange] = []
    domains: list[str] = []
    for path, left, right in _diff_values(base, merged):
        domain = _conceptual_domain(path, merged)
        if domain not in domains:
            domains.append(domain)
        changes.append(
            StateValueChange(
                path=path,
                base_value=left,
                merged_value=right,
                conceptual_domain=domain,
            )
        )
    requested_paths = tuple(path for domain, value in override.items() for path, _ in _walk_leaves(value, domain))
    return StateOverrideMaterialization(
        output_path=output_path,
        override_text_sha256=parsed.sha256,
        base_state_sha256=_sha256_bytes(authorities.state_bytes),
        merged_candidate_sha256=_sha256_bytes(candidate_bytes),
        empty_override_byte_exact=empty_override_byte_exact,
        requested_paths=requested_paths,
        changed_paths=tuple(changes),
        conceptual_domains=tuple(domains),
        camera_edits=camera_edits,
    )
