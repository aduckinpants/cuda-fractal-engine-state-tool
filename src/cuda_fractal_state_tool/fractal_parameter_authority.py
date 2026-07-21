from __future__ import annotations

import hashlib
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from .async_jobs import JobContext
from .json_utils import loads_no_duplicates
from .runtime_surface import build_runtime_command, resolve_launcher, sha256_file


@dataclass(frozen=True)
class FractalParameterAuthority:
    parameter_surface_text: str
    parameter_surface_sha256: str
    runtime_schema_sha256: str
    projection: dict[str, Any]


def _load_object(text: str, label: str) -> dict[str, Any]:
    value = loads_no_duplicates(text)
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a JSON object")
    return value


def _resolve_value(root: Any, dotted_path: str) -> tuple[bool, Any]:
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


def _schema_control_index(schema: dict[str, Any]) -> dict[str, dict[str, Any]]:
    panels = schema.get("panels")
    if not isinstance(panels, list):
        raise ValueError("Runtime UI schema has no panels array")
    index: dict[str, dict[str, Any]] = {}
    duplicates: set[str] = set()
    for panel in panels:
        if not isinstance(panel, dict):
            raise ValueError("Runtime UI schema panel must be an object")
        controls = panel.get("controls")
        if not isinstance(controls, list):
            raise ValueError("Runtime UI schema panel has no controls array")
        for control in controls:
            if not isinstance(control, dict) or not isinstance(control.get("id"), str):
                raise ValueError("Runtime UI schema control is missing its id")
            control_id = control["id"]
            if control_id in index:
                duplicates.add(control_id)
            index[control_id] = control
    if duplicates:
        raise ValueError(f"Runtime UI schema has duplicate control ids: {', '.join(sorted(duplicates))}")
    return index


def build_parameter_projection(
    fractal_id: str,
    state: dict[str, Any],
    review_state: Optional[dict[str, Any]],
    parameter_surface: dict[str, Any],
    runtime_schema: dict[str, Any],
) -> dict[str, Any]:
    lanes = parameter_surface.get("lanes")
    if not isinstance(lanes, list):
        raise ValueError("Engine parameter-surface descriptor has no lanes array")
    matches = [lane for lane in lanes if isinstance(lane, dict) and lane.get("fractal_id") == fractal_id]
    if len(matches) != 1:
        raise ValueError(f"Engine parameter-surface descriptor has {len(matches)} lanes for {fractal_id}")
    controls = matches[0].get("controls")
    if not isinstance(controls, list):
        raise ValueError(f"Engine parameter-surface lane {fractal_id} has no controls array")

    schema_controls = _schema_control_index(runtime_schema)
    params = state.get("params") if isinstance(state.get("params"), dict) else {}
    review_controls: dict[str, Any] = {}
    if isinstance(review_state, dict) and isinstance(review_state.get("active_fractal_controls"), dict):
        review_controls = review_state["active_fractal_controls"]

    projected: list[dict[str, Any]] = []
    seen: set[str] = set()
    for descriptor in controls:
        if not isinstance(descriptor, dict) or not isinstance(descriptor.get("control_id"), str):
            raise ValueError(f"Engine parameter-surface lane {fractal_id} contains an invalid control")
        control_id = descriptor["control_id"]
        if control_id in seen:
            raise ValueError(f"Engine parameter-surface lane {fractal_id} repeats control {control_id}")
        seen.add(control_id)
        if descriptor.get("binding_resolves") is not True:
            raise ValueError(f"Engine parameter-surface control {control_id} has no resolved binding")
        schema_control = schema_controls.get(control_id)
        if schema_control is None:
            raise ValueError(f"Engine parameter-surface control {control_id} is absent from the runtime UI schema")
        schema_binding = schema_control.get("binding")
        if not isinstance(schema_binding, dict) or schema_binding.get("path") != descriptor.get("binding_path"):
            raise ValueError(f"Engine descriptor/schema binding mismatch for control {control_id}")

        state_io_key = descriptor.get("state_io_key")
        current_available = False
        current_value = None
        current_source = "unavailable"
        if isinstance(state_io_key, str) and state_io_key:
            current_available, current_value = _resolve_value(review_controls, state_io_key)
            if current_available:
                current_source = "fractal-state.json.active_fractal_controls"
            else:
                current_available, current_value = _resolve_value(params, state_io_key)
                if current_available:
                    current_source = "state.json.params"

        projected.append(
            {
                "control_id": control_id,
                "binding_path": descriptor.get("binding_path"),
                "state_io_key": state_io_key,
                "current_value_available": current_available,
                "current_value": current_value,
                "current_value_source": current_source,
                "descriptor_properties": {
                    key: value
                    for key, value in descriptor.items()
                    if key not in {"control_id", "binding_path", "state_io_key"}
                },
                "schema_properties": {
                    key: value
                    for key, value in schema_control.items()
                    if key not in {"id", "binding"}
                },
            }
        )

    return {
        "projection_version": 1,
        "fractal_id": fractal_id,
        "parameter_surface_version": parameter_surface.get("version"),
        "runtime_schema_version": runtime_schema.get("schema_version"),
        "controls": projected,
    }


def capture_fractal_parameter_authority(
    runtime_cmd_path: Path,
    fractal_id: str,
    state: dict[str, Any],
    review_state: Optional[dict[str, Any]],
    job: Optional[JobContext] = None,
    timeout_seconds: float = 30.0,
) -> FractalParameterAuthority:
    runtime_cmd_path = runtime_cmd_path.resolve()
    resolution = resolve_launcher(runtime_cmd_path)
    if not resolution.runtime_schema_path:
        raise ValueError("Published runtime has no deployed fractal UI schema")
    schema_path = Path(resolution.runtime_schema_path).resolve()
    schema_text = schema_path.read_bytes().decode("utf-8")
    runtime_schema = _load_object(schema_text, "Runtime fractal UI schema")

    with tempfile.TemporaryDirectory(prefix="fractal-parameter-authority-") as temp_dir:
        output_path = Path(temp_dir) / "parameter-surface.json"
        command = build_runtime_command(
            runtime_cmd_path,
            "--describe-parameter-surface-json",
            str(output_path.resolve()),
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
                    text=True,
                    capture_output=True,
                    timeout=timeout_seconds,
                    check=False,
                )
                exit_code = completed.returncode
                timed_out = False
                detail = completed.stderr.strip() or completed.stdout.strip()
            except subprocess.TimeoutExpired as exc:
                raise ValueError("Engine parameter-surface descriptor timed out") from exc
        if timed_out or exit_code != 0 or not output_path.is_file():
            suffix = f": {detail}" if detail else ""
            raise ValueError(f"Engine parameter-surface descriptor failed{suffix}")
        parameter_surface_bytes = output_path.read_bytes()

    parameter_surface_text = parameter_surface_bytes.decode("utf-8")
    parameter_surface = _load_object(parameter_surface_text, "Engine parameter-surface descriptor")
    projection = build_parameter_projection(
        fractal_id,
        state,
        review_state,
        parameter_surface,
        runtime_schema,
    )
    return FractalParameterAuthority(
        parameter_surface_text=parameter_surface_text,
        parameter_surface_sha256=hashlib.sha256(parameter_surface_bytes).hexdigest(),
        runtime_schema_sha256=sha256_file(schema_path),
        projection=projection,
    )
