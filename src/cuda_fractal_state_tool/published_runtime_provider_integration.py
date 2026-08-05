from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Sequence

from .json_utils import loads_no_duplicates
from .polynomial_model_provider import (
    ActiveModelRuntimeClient,
    PolynomialOverPowerEscapeProvider,
)
from .runtime_surface import build_runtime_identity, resolve_launcher


EXPECTED_SELECTOR = "explaino_rational_escape"


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _finite_complex(real: float, imag: float) -> complex:
    if not math.isfinite(real) or not math.isfinite(imag):
        raise ValueError("Integration sample coordinates must be finite")
    return complex(real, imag)


def run_published_runtime_provider_integration(
    *,
    runtime_cmd: Path,
    state_json: Path,
    out_json: Path,
    timeout_seconds: float = 60.0,
    sample_points: Sequence[complex] = (complex(0.25, -0.5), complex(0.0, 0.0)),
) -> dict[str, Any]:
    runtime_cmd = runtime_cmd.resolve()
    state_json = state_json.resolve()
    out_json = out_json.resolve()
    if not runtime_cmd.is_file():
        raise FileNotFoundError(f"Published runtime launcher is missing: {runtime_cmd}")
    if not state_json.is_file():
        raise FileNotFoundError(f"Integration state is missing: {state_json}")
    if not math.isfinite(timeout_seconds) or timeout_seconds <= 0.0:
        raise ValueError("Integration timeout must be positive and finite")
    if not sample_points:
        raise ValueError("Integration requires at least one sample point")
    points = tuple(_finite_complex(point.real, point.imag) for point in sample_points)

    state_bytes = state_json.read_bytes()
    try:
        state = loads_no_duplicates(state_bytes.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise ValueError(
            f"Integration state is not valid JSON or contains duplicate keys: {exc}"
        ) from exc
    if not isinstance(state, dict):
        raise ValueError("Integration state root must be an object")
    selector = state.get("fractal_type")
    if selector != EXPECTED_SELECTOR:
        raise ValueError(
            f"Integration state must select {EXPECTED_SELECTOR}, got {selector!r}"
        )
    params = state.get("params")
    if not isinstance(params, dict):
        raise ValueError("Integration state params must be an object")
    expected_denominator_power = params.get(
        "explaino_rational_escape_denominator_power"
    )
    if (
        isinstance(expected_denominator_power, bool)
        or not isinstance(expected_denominator_power, int)
    ):
        raise ValueError("Integration state denominator power must be an integer")

    launcher = resolve_launcher(runtime_cmd)
    if not launcher.resolved_executable_path:
        raise FileNotFoundError(
            "Published runtime launcher does not resolve an active executable"
        )
    runtime_executable = Path(launcher.resolved_executable_path).resolve()
    if not runtime_executable.is_file():
        raise FileNotFoundError(
            f"Published runtime executable is missing: {runtime_executable}"
        )
    runtime_identity = build_runtime_identity(runtime_cmd, runtime_cmd.parent)
    runtime_sha256 = runtime_identity.get("resolved_executable_sha256")
    if not isinstance(runtime_sha256, str) or len(runtime_sha256) != 64:
        raise ValueError("Published runtime identity lacks an executable SHA-256")

    client = ActiveModelRuntimeClient(
        runtime_executable,
        timeout_seconds=timeout_seconds,
    )
    active_model = client.describe(
        state_path=state_json,
        expected_selector=EXPECTED_SELECTOR,
        packet_runtime_identity={"resolved_executable_sha256": runtime_sha256},
        compatibility_mode="strict",
    )
    provider_result = PolynomialOverPowerEscapeProvider().derive(active_model.receipt)
    sample = client.sample(
        state_path=state_json,
        points=points,
        request_id="published-runtime-provider-integration-v1",
        active_model=active_model,
    )

    receipt = active_model.receipt
    provider = receipt["provider"]
    model = receipt["model"]
    response_runtime = sample.response["runtime"]
    samples = sample.response["samples"]
    if provider.get("provider_id") != "polynomial_over_power_escape.v1":
        raise ValueError("Published runtime returned the wrong active-model provider")
    if model.get("model_id") != "laurent_polynomial_escape_time.v1":
        raise ValueError("Published runtime returned the wrong active model")
    if model.get("denominator_power") != expected_denominator_power:
        raise ValueError(
            "Published runtime active-model denominator disagrees with the exact state"
        )
    if response_runtime.get("fractal_type") != EXPECTED_SELECTOR:
        raise ValueError("Canonical sample response selected the wrong fractal")
    if response_runtime.get("backend_used") != "cuda":
        raise ValueError("Canonical sample response did not use CUDA")
    if response_runtime.get("iteration_arithmetic") != "float64":
        raise ValueError("Integration state did not resolve to float64 iteration arithmetic")
    if not isinstance(samples, list) or len(samples) != len(points):
        raise ValueError("Canonical sample response count disagrees with the request")

    result = {
        "schema_id": "cuda_fractal_state_tool.published_runtime_provider_integration.v1",
        "ok": True,
        "runtime": {
            "launcher": str(runtime_cmd),
            "executable": str(runtime_executable),
            "executable_sha256": runtime_sha256,
            "backend_used": response_runtime.get("backend_used"),
            "iteration_arithmetic": response_runtime.get("iteration_arithmetic"),
        },
        "state": {
            "path": str(state_json),
            "sha256": _sha256(state_bytes),
            "selector": selector,
            "denominator_power": expected_denominator_power,
        },
        "active_model": {
            "provider_id": provider.get("provider_id"),
            "provider_version": provider.get("provider_version"),
            "model_id": model.get("model_id"),
            "denominator_power": model.get("denominator_power"),
            "critical_point_count": len(provider_result["features"]["critical_points"]),
            "fixed_point_count": len(provider_result["features"]["fixed_points"]),
            "receipt_sha256": _sha256(active_model.receipt_bytes),
        },
        "canonical_sample": {
            "request_id": sample.request["request_id"],
            "request_sha256": _sha256(sample.request_bytes),
            "response_sha256": _sha256(sample.response_bytes),
            "sample_count": len(samples),
            "statuses": [item.get("status") for item in samples],
            "coordinates": [
                {"real": item.get("coord_x"), "imag": item.get("coord_y")}
                for item in samples
            ],
        },
        "commands": {
            "describe": list(active_model.command),
            "sample": list(sample.command),
        },
    }
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(
        json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False)
        + "\n",
        encoding="utf-8",
    )
    return result


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run the state-tool polynomial provider directly against a published CUDA "
            "fractal runtime. Missing runtime/state inputs are failures, not skips."
        )
    )
    parser.add_argument("--runtime-cmd", type=Path, required=True)
    parser.add_argument("--state-json", type=Path, required=True)
    parser.add_argument("--out-json", type=Path, required=True)
    parser.add_argument("--timeout-seconds", type=float, default=60.0)
    parser.add_argument(
        "--sample-point",
        nargs=2,
        type=float,
        action="append",
        metavar=("REAL", "IMAG"),
        help="Complex sample point; may be repeated.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    points = (
        tuple(_finite_complex(real, imag) for real, imag in args.sample_point)
        if args.sample_point
        else (complex(0.25, -0.5), complex(0.0, 0.0))
    )
    result = run_published_runtime_provider_integration(
        runtime_cmd=args.runtime_cmd,
        state_json=args.state_json,
        out_json=args.out_json,
        timeout_seconds=args.timeout_seconds,
        sample_points=points,
    )
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
