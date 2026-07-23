from __future__ import annotations

import math
from typing import Any

from .json_utils import loads_no_duplicates


SCHEMA_VERSION = 1
MAPPING_ID = "cuda_fractal_renderer_pixel_center_v1"


def _object(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"Viewport facts {label} must be an object")
    return value


def _exact_keys(value: dict[str, Any], expected: set[str], label: str) -> None:
    actual = set(value)
    missing = sorted(expected - actual)
    extra = sorted(actual - expected)
    if missing:
        raise ValueError(f"Viewport facts {label} is missing fields: {', '.join(missing)}")
    if extra:
        raise ValueError(f"Viewport facts {label} contains undeclared fields: {', '.join(extra)}")


def _finite(value: Any, label: str, *, positive: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
        raise ValueError(f"Viewport facts {label} must be finite numeric data")
    result = float(value)
    if positive and result <= 0.0:
        raise ValueError(f"Viewport facts {label} must be positive")
    return result


def _point(value: Any, label: str) -> None:
    point = _object(value, label)
    _exact_keys(point, {"real", "imag"}, label)
    _finite(point.get("real"), f"{label}.real")
    _finite(point.get("imag"), f"{label}.imag")


def _four_points(value: Any, label: str) -> None:
    if not isinstance(value, list) or len(value) != 4:
        raise ValueError(f"Viewport facts {label} must contain four complex points")
    for index, point in enumerate(value):
        _point(point, f"{label}[{index}]")


def validate_viewport_facts_bytes(
    payload: bytes,
    *,
    expected_selector: str,
    expected_width: int,
    expected_height: int,
) -> dict[str, Any]:
    """Validate engine identity and structure without reimplementing its camera mapping."""
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("Viewport facts are not valid UTF-8") from exc
    try:
        value = loads_no_duplicates(text)
    except ValueError as exc:
        raise ValueError(f"Viewport facts JSON is invalid or contains a duplicate key: {exc}") from exc
    root = _object(value, "root")
    _exact_keys(
        root,
        {
            "schema_version",
            "mapping_id",
            "selected_fractal_type",
            "render",
            "camera",
            "local_frame",
            "complex_pixel_basis",
            "continuous_edge_corners",
            "pixel_center_corners",
            "axis_aligned_complex_bounds",
            "fit_model",
        },
        "root",
    )
    if root.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(f"Unsupported viewport facts schema version: {root.get('schema_version')}")
    if root.get("mapping_id") != MAPPING_ID:
        raise ValueError(f"Unsupported viewport facts mapping identity: {root.get('mapping_id')}")
    if root.get("selected_fractal_type") != expected_selector:
        raise ValueError("Viewport facts selected selector disagrees with copied state.json")

    render = _object(root.get("render"), "render")
    _exact_keys(render, {"width", "height", "aspect_ratio"}, "render")
    if render.get("width") != expected_width or render.get("height") != expected_height:
        raise ValueError("Viewport facts render dimensions disagree with copied state.json")
    _finite(render.get("aspect_ratio"), "render.aspect_ratio", positive=True)

    camera = _object(root.get("camera"), "camera")
    _exact_keys(
        camera,
        {"center_hp_x", "center_hp_y", "log2_zoom", "resolved_zoom", "rotation_degrees"},
        "camera",
    )
    for field in ("center_hp_x", "center_hp_y", "log2_zoom", "rotation_degrees"):
        _finite(camera.get(field), f"camera.{field}")
    _finite(camera.get("resolved_zoom"), "camera.resolved_zoom", positive=True)

    local_frame = _object(root.get("local_frame"), "local_frame")
    _exact_keys(
        local_frame,
        {"half_width", "half_height", "full_width", "full_height"},
        "local_frame",
    )
    for field in ("half_width", "half_height", "full_width", "full_height"):
        _finite(local_frame.get(field), f"local_frame.{field}", positive=True)

    basis = _object(root.get("complex_pixel_basis"), "complex_pixel_basis")
    _exact_keys(
        basis,
        {"x_step", "y_step", "units_per_pixel_x", "units_per_pixel_y"},
        "complex_pixel_basis",
    )
    _point(basis.get("x_step"), "complex_pixel_basis.x_step")
    _point(basis.get("y_step"), "complex_pixel_basis.y_step")
    _finite(basis.get("units_per_pixel_x"), "complex_pixel_basis.units_per_pixel_x", positive=True)
    _finite(basis.get("units_per_pixel_y"), "complex_pixel_basis.units_per_pixel_y", positive=True)

    _four_points(root.get("continuous_edge_corners"), "continuous_edge_corners")
    _four_points(root.get("pixel_center_corners"), "pixel_center_corners")
    bounds = _object(root.get("axis_aligned_complex_bounds"), "axis_aligned_complex_bounds")
    _exact_keys(bounds, {"minimum", "maximum"}, "axis_aligned_complex_bounds")
    _point(bounds.get("minimum"), "axis_aligned_complex_bounds.minimum")
    _point(bounds.get("maximum"), "axis_aligned_complex_bounds.maximum")

    fit_model = _object(root.get("fit_model"), "fit_model")
    _exact_keys(
        fit_model,
        {"forward_mapping", "pixel_normalization", "inverse_fit", "point_preparation"},
        "fit_model",
    )
    for field in ("forward_mapping", "pixel_normalization", "inverse_fit", "point_preparation"):
        if not isinstance(fit_model.get(field), str) or not fit_model[field].strip():
            raise ValueError(f"Viewport facts fit_model.{field} must be nonempty text")
    return root
