from __future__ import annotations

import cmath
import hashlib
import io
import json
import math
import os
import subprocess
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from PIL import Image, ImageDraw, ImageFont, __version__ as PILLOW_VERSION

from .json_utils import loads_no_duplicates
from .runtime_compatibility import assess_runtime_compatibility, resolve_runtime_compatibility_mode


MODEL_ID = "laurent_polynomial_escape_time.v1"
PROVIDER_ID = "polynomial_over_power_escape.v1"
PROVIDER_VERSION = 1
ANNOTATION_SCHEMA_VERSION = 1
ANNOTATION_BUILDER_VERSION = 2
ANNOTATION_RENDERER_VERSION = 2


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(65536):
            digest.update(chunk)
    return digest.hexdigest()


def _finite_number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
        raise ValueError(f"{label} must be finite numeric data")
    return float(value)


def _object(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be an object")
    return value


def _complex_json(value: complex) -> dict[str, float]:
    real = 0.0 if abs(value.real) < 5e-16 else float(value.real)
    imag = 0.0 if abs(value.imag) < 5e-16 else float(value.imag)
    return {"real": real, "imag": imag}


def _poly_eval(coefficients: list[complex], value: complex) -> complex:
    result = 0j
    for coefficient in reversed(coefficients):
        result = result * value + coefficient
    return result


def _poly_derivative(coefficients: list[complex]) -> list[complex]:
    return [index * coefficient for index, coefficient in enumerate(coefficients)][1:]


def _trim(coefficients: list[complex]) -> list[complex]:
    result = list(coefficients)
    scale = max((abs(value) for value in result), default=0.0)
    tolerance = max(scale * 1e-15, 1e-30)
    while len(result) > 1 and abs(result[-1]) <= tolerance:
        result.pop()
    return result


def _polynomial_roots(coefficients: list[complex]) -> list[complex]:
    coefficients = _trim(coefficients)
    degree = len(coefficients) - 1
    if degree < 1:
        return []
    leading = coefficients[-1]
    monic = [value / leading for value in coefficients]
    if degree == 1:
        return [-monic[0]]
    radius = 1.0 + max(abs(value) for value in monic[:-1])
    roots = [
        radius * cmath.exp(2j * math.pi * (index + 0.371) / degree)
        for index in range(degree)
    ]
    converged = False
    for _ in range(2000):
        next_roots: list[complex] = []
        largest_delta = 0.0
        for index, root in enumerate(roots):
            denominator = 1 + 0j
            for other_index, other in enumerate(roots):
                if index != other_index:
                    denominator *= root - other
            if abs(denominator) < 1e-30:
                root += complex(1e-12 * (index + 1), -1e-12 * (index + 1))
                denominator = 1 + 0j
                for other_index, other in enumerate(roots):
                    if index != other_index:
                        denominator *= root - other
            delta = _poly_eval(monic, root) / denominator
            updated = root - delta
            next_roots.append(updated)
            largest_delta = max(largest_delta, abs(delta))
        roots = next_roots
        if largest_delta <= 2e-14:
            converged = True
            break
    if not converged:
        raise ValueError("Deterministic polynomial root solve did not converge")
    derivative = _poly_derivative(coefficients)
    polished: list[complex] = []
    for root in roots:
        for _ in range(12):
            slope = _poly_eval(derivative, root)
            if abs(slope) < 1e-30:
                break
            correction = _poly_eval(coefficients, root) / slope
            root -= correction
            if abs(correction) <= 2e-15:
                break
        residual = abs(_poly_eval(coefficients, root))
        scale = max(1.0, sum(abs(coefficient) * max(1.0, abs(root) ** index) for index, coefficient in enumerate(coefficients)))
        if residual > 2e-11 * scale:
            raise ValueError(f"Polynomial root residual exceeds the bounded solver tolerance: {residual}")
        polished.append(complex(0.0 if abs(root.real) < 5e-15 else root.real, 0.0 if abs(root.imag) < 5e-15 else root.imag))
    polished.sort(key=lambda value: (round(value.real, 14), round(value.imag, 14)))
    return polished


def validate_active_model_receipt(
    payload: bytes,
    *,
    expected_state_sha256: str,
    expected_runtime_sha256: str,
    expected_selector: str,
) -> dict[str, Any]:
    try:
        value = loads_no_duplicates(payload.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise ValueError(f"Active-model receipt is invalid UTF-8 JSON or contains duplicate keys: {exc}") from exc
    receipt = _object(value, "Active-model receipt")
    if receipt.get("schema_version") != 1:
        raise ValueError("Unsupported active-model receipt schema version")
    binding = _object(receipt.get("state_binding"), "Active-model state binding")
    if binding.get("state_json_sha256") != expected_state_sha256:
        raise ValueError("Active-model receipt state hash disagrees with the exact Packet V8 state")
    if binding.get("runtime_executable_sha256") != expected_runtime_sha256:
        raise ValueError("Active-model receipt runtime hash disagrees with the invoked executable")
    if receipt.get("selected_fractal_type") != expected_selector or receipt.get(
        "resolved_runtime_fractal_type"
    ) != expected_selector:
        raise ValueError("Active-model receipt selector disagrees with Packet V8")
    provider = _object(receipt.get("provider"), "Active-model provider")
    status = provider.get("status")
    if status not in {"available", "unavailable"}:
        raise ValueError("Active-model provider status is invalid")
    if status == "unavailable":
        if not isinstance(provider.get("unavailable_reason"), str) or not provider["unavailable_reason"]:
            raise ValueError("Unavailable active-model receipt has no reason")
        if receipt.get("model") is not None:
            raise ValueError("Unavailable active-model receipt unexpectedly contains a model")
        return receipt
    if provider.get("provider_id") != PROVIDER_ID or provider.get("provider_version") != PROVIDER_VERSION:
        raise ValueError("Active-model receipt names an unsupported provider identity")
    numeric = _object(receipt.get("numeric_authority"), "Active-model numeric authority")
    if numeric.get("resolved_backend") not in {"float32", "float64", "mixed"}:
        raise ValueError("Active-model receipt has no supported resolved numeric backend")
    evaluation = _object(receipt.get("evaluation_authority"), "Active-model evaluation authority")
    if evaluation.get("evaluation_surface") != "fractal.sample":
        raise ValueError("Active-model receipt does not name fractal.sample as evaluation authority")
    if evaluation.get("state_binding_required") is not True or evaluation.get("runtime_binding_required") is not True:
        raise ValueError("Active-model receipt does not require exact state and runtime binding")
    model = _object(receipt.get("model"), "Active-model model")
    if model.get("model_id") != MODEL_ID:
        raise ValueError("Active-model receipt names an unsupported model identity")
    if model.get("coefficient_order") != "ascending_power":
        raise ValueError("Active-model polynomial coefficient order is unsupported")
    coefficients = model.get("real_polynomial_coefficients")
    if not isinstance(coefficients, list) or not 2 <= len(coefficients) <= 32:
        raise ValueError("Active-model polynomial coefficients are invalid")
    for index, coefficient in enumerate(coefficients):
        _finite_number(coefficient, f"Active-model coefficient {index}")
    denominator_power = model.get("denominator_power")
    if isinstance(denominator_power, bool) or not isinstance(denominator_power, int) or not 1 <= denominator_power <= 32:
        raise ValueError("Active-model denominator power is invalid")
    _finite_number(model.get("pole_threshold_abs2"), "Active-model pole threshold")
    _finite_number(model.get("escape_radius_abs2"), "Active-model escape radius")
    participating = receipt.get("participating_state")
    if not isinstance(participating, list):
        raise ValueError("Active-model participating state is invalid")
    by_path: dict[str, Any] = {}
    for record in participating:
        record = _object(record, "Active-model participating state record")
        path = record.get("path")
        if not isinstance(path, str) or not path or path in by_path:
            raise ValueError("Active-model participating state has a missing or duplicate path")
        by_path[path] = record.get("value")
    if _finite_number(by_path.get("params.explaino_warp_strength"), "ExplainO warp strength") != 0.0:
        raise ValueError("Polynomial-over-power provider requires zero ExplainO warp")
    if by_path.get("params.poly_coeffs") != coefficients:
        raise ValueError("Active-model coefficients disagree with participating state")
    if by_path.get("params.explaino_rational_escape_denominator_power") != denominator_power:
        raise ValueError("Active-model denominator power disagrees with participating state")
    return receipt


@dataclass(frozen=True)
class ActiveModelCapture:
    receipt_bytes: bytes
    receipt: dict[str, Any]
    runtime_executable_sha256: str
    runtime_compatibility: dict[str, Any]
    command: tuple[str, ...]


@dataclass(frozen=True)
class CanonicalSampleCapture:
    request_bytes: bytes
    request: dict[str, Any]
    response_bytes: bytes
    response: dict[str, Any]
    command: tuple[str, ...]


class ActiveModelRuntimeClient:
    def __init__(self, runtime_executable: Path, *, timeout_seconds: float = 30.0) -> None:
        self.runtime_executable = runtime_executable.resolve()
        if not self.runtime_executable.is_file():
            raise FileNotFoundError(f"Published runtime executable is missing: {self.runtime_executable}")
        if not math.isfinite(timeout_seconds) or timeout_seconds <= 0.0:
            raise ValueError("Active-model runtime timeout must be positive and finite")
        self.timeout_seconds = float(timeout_seconds)

    def describe(
        self,
        *,
        state_path: Path,
        expected_selector: str,
        packet_runtime_identity: dict[str, Any],
        compatibility_mode: str | None,
    ) -> ActiveModelCapture:
        state_path = state_path.resolve()
        state_before = state_path.read_bytes()
        state_sha256 = _sha256(state_before)
        runtime_sha256 = _sha256_file(self.runtime_executable)
        packet_executable_sha256 = packet_runtime_identity.get("resolved_executable_sha256")
        compatibility = assess_runtime_compatibility(
            {"resolved_executable_sha256": packet_executable_sha256},
            {"resolved_executable_sha256": runtime_sha256},
            resolve_runtime_compatibility_mode(compatibility_mode),
        )
        if compatibility["proof_may_proceed"] is not True:
            raise ValueError("Strict runtime compatibility stops active-model enrichment before invocation")
        command = (
            str(self.runtime_executable),
            "--load-state-json",
            str(state_path),
            "--describe-active-fractal-model",
        )
        completed = subprocess.run(
            command,
            cwd=str(self.runtime_executable.parent),
            capture_output=True,
            timeout=self.timeout_seconds,
            check=False,
        )
        if completed.returncode != 0:
            diagnostic = completed.stderr.decode("utf-8", errors="replace").strip()
            raise RuntimeError(f"Active-model runtime invocation failed ({completed.returncode}): {diagnostic}")
        if completed.stderr:
            raise RuntimeError("Active-model runtime emitted unexpected stderr diagnostics")
        if state_path.read_bytes() != state_before:
            raise ValueError("Exact Packet V8 state changed during active-model capture")
        if _sha256_file(self.runtime_executable) != runtime_sha256:
            raise ValueError("Published runtime executable changed during active-model capture")
        receipt = validate_active_model_receipt(
            completed.stdout,
            expected_state_sha256=state_sha256,
            expected_runtime_sha256=runtime_sha256,
            expected_selector=expected_selector,
        )
        return ActiveModelCapture(
            receipt_bytes=completed.stdout,
            receipt=receipt,
            runtime_executable_sha256=runtime_sha256,
            runtime_compatibility=compatibility,
            command=command,
        )

    def sample(
        self,
        *,
        state_path: Path,
        points: Iterable[complex],
        request_id: str,
        active_model: ActiveModelCapture,
    ) -> CanonicalSampleCapture:
        state_path = state_path.resolve()
        state_before = state_path.read_bytes()
        if _sha256(state_before) != active_model.receipt["state_binding"]["state_json_sha256"]:
            raise ValueError("Canonical sample state changed after active-model capture")
        if _sha256_file(self.runtime_executable) != active_model.runtime_executable_sha256:
            raise ValueError("Canonical sample runtime changed after active-model capture")
        request = build_sample_request(state_path=state_path, points=points, request_id=request_id)
        request_bytes = json.dumps(
            request,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
        command = (
            str(self.runtime_executable),
            "--sample-request-stdin",
            "--sample-response-stdout",
        )
        completed = subprocess.run(
            command,
            cwd=str(self.runtime_executable.parent),
            input=request_bytes,
            capture_output=True,
            timeout=self.timeout_seconds,
            check=False,
        )
        if completed.returncode != 0:
            diagnostic = (completed.stderr or completed.stdout).decode("utf-8", errors="replace").strip()
            raise RuntimeError(f"Canonical fractal.sample invocation failed ({completed.returncode}): {diagnostic}")
        if completed.stderr:
            raise RuntimeError("Canonical fractal.sample emitted unexpected stderr diagnostics")
        try:
            response_value = loads_no_duplicates(completed.stdout.decode("utf-8"))
        except (UnicodeDecodeError, ValueError) as exc:
            raise ValueError(f"Canonical sample response is invalid JSON or contains duplicate keys: {exc}") from exc
        response = _object(response_value, "Canonical sample response")
        validate_sample_response(response, request=request, active_model_receipt=active_model.receipt)
        if state_path.read_bytes() != state_before:
            raise ValueError("Exact Packet V8 state changed during canonical sampling")
        if _sha256_file(self.runtime_executable) != active_model.runtime_executable_sha256:
            raise ValueError("Published runtime executable changed during canonical sampling")
        return CanonicalSampleCapture(
            request_bytes=request_bytes,
            request=request,
            response_bytes=completed.stdout,
            response=response,
            command=command,
        )


class PolynomialOverPowerEscapeProvider:
    provider_id = PROVIDER_ID
    provider_version = PROVIDER_VERSION
    supported_model_ids = (MODEL_ID,)

    def derive(self, receipt: dict[str, Any]) -> dict[str, Any]:
        provider = _object(receipt.get("provider"), "Active-model provider")
        if provider.get("status") != "available" or provider.get("provider_id") != self.provider_id:
            raise ValueError("Polynomial-over-power provider received an unavailable or foreign receipt")
        model = _object(receipt.get("model"), "Active-model model")
        if model.get("model_id") != MODEL_ID:
            raise ValueError("Polynomial-over-power provider received an unsupported model")
        coefficients = [complex(_finite_number(value, "Polynomial coefficient"), 0.0) for value in model["real_polynomial_coefficients"]]
        denominator_power = model["denominator_power"]
        if isinstance(denominator_power, bool) or not isinstance(denominator_power, int):
            raise ValueError("Polynomial-over-power denominator power is invalid")

        critical_equation = [(index - denominator_power) * coefficient for index, coefficient in enumerate(coefficients)]
        critical_roots = _polynomial_roots(critical_equation)
        critical_points = []
        for index, point in enumerate(critical_roots, start=1):
            if abs(point) < 1e-15:
                continue
            value = _poly_eval(coefficients, point) / (point ** denominator_power)
            critical_points.append(
                {
                    "feature_id": f"critical-{index}",
                    "point": _complex_json(point),
                    "critical_value": _complex_json(value),
                    "equation_residual": abs(_poly_eval(critical_equation, point)),
                    "epistemic_status": "numerical_solution_of_exact_derived_equation",
                }
            )

        fixed_equation = list(coefficients)
        while len(fixed_equation) <= denominator_power + 1:
            fixed_equation.append(0j)
        fixed_equation[denominator_power + 1] -= 1.0
        fixed_points = []
        for index, point in enumerate(_polynomial_roots(fixed_equation), start=1):
            if abs(point) < 1e-15:
                continue
            numerator = _poly_eval(critical_equation, point)
            multiplier = numerator / (point ** (denominator_power + 1))
            fixed_points.append(
                {
                    "feature_id": f"fixed-{index}",
                    "point": _complex_json(point),
                    "multiplier": _complex_json(multiplier),
                    "multiplier_abs": abs(multiplier),
                    "equation_residual": abs(_poly_eval(fixed_equation, point)),
                    "epistemic_status": "numerical_solution_of_exact_derived_equation",
                }
            )

        singular_points = []
        for index, record in enumerate(model.get("structural_singular_points", []), start=1):
            record = _object(record, "Structural singular point")
            singular_points.append(
                {
                    "feature_id": f"singular-{index}",
                    "point": {
                        "real": _finite_number(record.get("real"), "Structural singular real coordinate"),
                        "imag": _finite_number(record.get("imag"), "Structural singular imaginary coordinate"),
                    },
                    "kind": record.get("kind"),
                    "epistemic_status": "exact_symbolic_derivation",
                }
            )
        return {
            "schema_version": 1,
            "status": "available",
            "provider_id": self.provider_id,
            "provider_version": self.provider_version,
            "model_id": MODEL_ID,
            "equations": {
                "recurrence": "F(z) = P(z) / z^d",
                "critical_points": "z P'(z) - d P(z) = 0",
                "fixed_points": "P(z) - z^(d+1) = 0",
            },
            "features": {
                "critical_points": critical_points,
                "fixed_points": fixed_points,
                "structural_singular_points": singular_points,
            },
        }


def project_complex_to_viewport(point: complex, viewport: dict[str, Any]) -> dict[str, Any]:
    render = _object(viewport.get("render"), "Viewport render")
    width = render.get("width")
    height = render.get("height")
    if isinstance(width, bool) or not isinstance(width, int) or width < 1:
        raise ValueError("Viewport width is invalid")
    if isinstance(height, bool) or not isinstance(height, int) or height < 1:
        raise ValueError("Viewport height is invalid")
    camera = _object(viewport.get("camera"), "Viewport camera")
    center = complex(
        _finite_number(camera.get("center_hp_x"), "Viewport center X"),
        _finite_number(camera.get("center_hp_y"), "Viewport center Y"),
    )
    basis = _object(viewport.get("complex_pixel_basis"), "Viewport pixel basis")
    x_record = _object(basis.get("x_step"), "Viewport X basis")
    y_record = _object(basis.get("y_step"), "Viewport Y basis")
    x_step = complex(
        _finite_number(x_record.get("real"), "Viewport X basis real"),
        _finite_number(x_record.get("imag"), "Viewport X basis imag"),
    )
    y_step = complex(
        _finite_number(y_record.get("real"), "Viewport Y basis real"),
        _finite_number(y_record.get("imag"), "Viewport Y basis imag"),
    )
    determinant = x_step.real * y_step.imag - y_step.real * x_step.imag
    if abs(determinant) < 1e-30:
        raise ValueError("Viewport pixel basis is singular")
    delta = point - center
    x_offset = (delta.real * y_step.imag - y_step.real * delta.imag) / determinant
    y_offset = (x_step.real * delta.imag - delta.real * x_step.imag) / determinant
    pixel_x = (width - 1) / 2.0 + x_offset
    pixel_y = (height - 1) / 2.0 + y_offset
    return {
        "mapping_id": viewport.get("mapping_id"),
        "pixel_x": pixel_x,
        "pixel_y": pixel_y,
        "contained": 0.0 <= pixel_x < width and 0.0 <= pixel_y < height,
        "source_width": width,
        "source_height": height,
    }


def build_annotation_set(provider_result: dict[str, Any], viewport: dict[str, Any]) -> dict[str, Any]:
    annotations = []
    groups = (
        ("critical_points", "critical_point", "critical point (F'(z)=0)"),
        ("fixed_points", "fixed_point", "fixed point (F(z)=z)"),
        ("structural_singular_points", "structural_singular_point", "structural pole (z=0)"),
    )
    features = _object(provider_result.get("features"), "Provider features")
    for group_name, kind, label_prefix in groups:
        records = features.get(group_name)
        if not isinstance(records, list):
            raise ValueError(f"Provider feature group {group_name} is invalid")
        for record in records:
            record = _object(record, f"Provider feature {kind}")
            point_record = _object(record.get("point"), f"Provider feature {kind} point")
            point = complex(
                _finite_number(point_record.get("real"), f"{kind} real coordinate"),
                _finite_number(point_record.get("imag"), f"{kind} imaginary coordinate"),
            )
            annotations.append(
                {
                    "annotation_id": record.get("feature_id"),
                    "feature_kind": kind,
                    "point": _complex_json(point),
                    "viewport": project_complex_to_viewport(point, viewport),
                    "label": label_prefix,
                    "epistemic_status": record.get("epistemic_status"),
                }
            )
    camera = _object(viewport.get("camera"), "Viewport camera")
    center = complex(
        _finite_number(camera.get("center_hp_x"), "Viewport center X"),
        _finite_number(camera.get("center_hp_y"), "Viewport center Y"),
    )
    nearest = min(
        annotations,
        key=lambda item: abs(complex(item["point"]["real"], item["point"]["imag"]) - center),
    )
    nearest_distance = abs(
        complex(nearest["point"]["real"], nearest["point"]["imag"]) - center
    )
    return {
        "schema_version": ANNOTATION_SCHEMA_VERSION,
        "builder_version": ANNOTATION_BUILDER_VERSION,
        "provider_id": provider_result.get("provider_id"),
        "provider_version": provider_result.get("provider_version"),
        "viewport_mapping_id": viewport.get("mapping_id"),
        "nearest_to_camera_center": {
            "annotation_id": nearest["annotation_id"],
            "distance_complex_units": nearest_distance,
            "distance_pixels": math.hypot(
                nearest["viewport"]["pixel_x"] - (nearest["viewport"]["source_width"] - 1) / 2.0,
                nearest["viewport"]["pixel_y"] - (nearest["viewport"]["source_height"] - 1) / 2.0,
            ),
            "epistemic_status": "comparison_derived_result",
        },
        "annotations": annotations,
    }


def build_sample_request(
    *,
    state_path: Path,
    points: Iterable[complex],
    request_id: str,
) -> dict[str, Any]:
    point_list = tuple(points)
    if not point_list:
        raise ValueError("Canonical model evaluation requires at least one point")
    return {
        "request_version": 1,
        "request_id": request_id,
        "function_id": "fractal.sample",
        "mode": "point_set",
        "base_state": {"load_state_json": str(state_path.resolve())},
        "points": [{"x": _finite_number(point.real, "Evaluation point real"), "y": _finite_number(point.imag, "Evaluation point imag")} for point in point_list],
        "metrics": ["iterations", "status", "final_z", "final_abs2", "residual", "root_index"],
    }


def validate_sample_response(
    response: dict[str, Any],
    *,
    request: dict[str, Any],
    active_model_receipt: dict[str, Any],
) -> dict[str, Any]:
    if response.get("response_version") != 1 or response.get("request_id") != request.get("request_id"):
        raise ValueError("Canonical sample response identity disagrees with its request")
    if response.get("function_id") != "fractal.sample" or response.get("ok") is not True:
        raise ValueError(f"Canonical fractal.sample request failed: {response.get('error')}")
    runtime = _object(response.get("runtime"), "Canonical sample runtime")
    if runtime.get("backend_used") != "cuda":
        raise ValueError("Canonical sample response did not use the CUDA backend")
    if runtime.get("fractal_type") != active_model_receipt.get("resolved_runtime_fractal_type"):
        raise ValueError("Canonical sample response fractal identity disagrees with active-model receipt")
    numeric = _object(active_model_receipt.get("numeric_authority"), "Active-model numeric authority")
    if runtime.get("iteration_arithmetic") != numeric.get("resolved_backend"):
        raise ValueError("Canonical sample response numeric backend disagrees with active-model receipt")
    samples = response.get("samples")
    request_points = request.get("points")
    if not isinstance(samples, list) or not isinstance(request_points, list) or len(samples) != len(request_points):
        raise ValueError("Canonical sample response point count disagrees with its request")
    for index, (sample, point) in enumerate(zip(samples, request_points, strict=True)):
        sample = _object(sample, f"Canonical sample {index}")
        if not math.isclose(_finite_number(sample.get("coord_x"), "Sample X"), point["x"], rel_tol=0.0, abs_tol=1e-14) or not math.isclose(
            _finite_number(sample.get("coord_y"), "Sample Y"), point["y"], rel_tol=0.0, abs_tol=1e-14
        ):
            raise ValueError("Canonical sample response coordinates disagree with its request")
    return response


def render_annotations(
    source_path: Path,
    output_path: Path,
    annotation_set: dict[str, Any],
    *,
    source_viewport_width: int,
    source_viewport_height: int,
) -> dict[str, Any]:
    source_bytes = source_path.read_bytes()
    with Image.open(io.BytesIO(source_bytes)) as opened:
        opened.load()
        image = opened.convert("RGBA")
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default()
    rendered_ids: list[str] = []
    for record in annotation_set.get("annotations", []):
        viewport = _object(record.get("viewport"), "Annotation viewport")
        if viewport.get("contained") is not True:
            continue
        x = (float(viewport["pixel_x"]) + 0.5) * image.width / source_viewport_width - 0.5
        y = (float(viewport["pixel_y"]) + 0.5) * image.height / source_viewport_height - 0.5
        radius = 9
        color = (255, 255, 255, 255)
        outline = (0, 0, 0, 255)
        draw.ellipse((x - radius, y - radius, x + radius, y + radius), outline=outline, width=5)
        draw.ellipse((x - radius, y - radius, x + radius, y + radius), outline=color, width=2)
        draw.line((x - radius - 6, y, x + radius + 6, y), fill=outline, width=5)
        draw.line((x, y - radius - 6, x, y + radius + 6), fill=outline, width=5)
        draw.line((x - radius - 6, y, x + radius + 6, y), fill=color, width=2)
        draw.line((x, y - radius - 6, x, y + radius + 6), fill=color, width=2)
        label = str(record.get("label", "feature"))
        label_x = min(image.width - 1, x + radius + 8)
        label_y = max(0.0, y - radius - 3)
        box = draw.textbbox((label_x, label_y), label, font=font)
        padded = (box[0] - 3, box[1] - 2, box[2] + 3, box[3] + 2)
        draw.rectangle(padded, fill=(0, 0, 0, 220))
        draw.text((label_x, label_y), label, fill=color, font=font)
        rendered_ids.append(str(record.get("annotation_id")))
    buffer = io.BytesIO()
    image.save(buffer, format="PNG", compress_level=9, optimize=False)
    output_bytes = buffer.getvalue()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = output_path.with_name(f".{output_path.name}.{uuid.uuid4().hex}.tmp")
    try:
        with temporary.open("xb") as handle:
            handle.write(output_bytes)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, output_path)
    finally:
        if temporary.exists():
            temporary.unlink()
    return {
        "schema_version": 1,
        "renderer_version": ANNOTATION_RENDERER_VERSION,
        "pillow_version": PILLOW_VERSION,
        "input_image_sha256": _sha256(source_bytes),
        "input_width": image.width,
        "input_height": image.height,
        "source_viewport_width": source_viewport_width,
        "source_viewport_height": source_viewport_height,
        "transform": "pixel_center_scale_no_crop",
        "annotation_ids": rendered_ids,
        "style_profile": "bounded_crosshair_label_v2",
        "output_png_sha256": _sha256(output_bytes),
        "output_width": image.width,
        "output_height": image.height,
    }
