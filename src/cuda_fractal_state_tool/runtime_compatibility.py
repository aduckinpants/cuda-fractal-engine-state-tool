from __future__ import annotations

import os
from collections.abc import Mapping
from typing import Any


RUNTIME_COMPATIBILITY_ENV = "CUDA_FRACTAL_STATE_TOOL_RUNTIME_COMPATIBILITY"
RUNTIME_COMPATIBILITY_MODES = ("development", "strict")


def resolve_runtime_compatibility_mode(
    explicit: str | None,
    environ: Mapping[str, str] | None = None,
) -> str:
    source = os.environ if environ is None else environ
    value = explicit if explicit is not None else source.get(RUNTIME_COMPATIBILITY_ENV, "development")
    normalized = value.strip().lower()
    if normalized not in RUNTIME_COMPATIBILITY_MODES:
        raise ValueError("Runtime compatibility mode must be development or strict")
    return normalized


def runtime_identity_differences(
    packet_identity: Any,
    current_identity: Any,
) -> tuple[dict[str, Any], ...]:
    differences: list[dict[str, Any]] = []

    def walk(packet_value: Any, current_value: Any, path: str) -> None:
        if isinstance(packet_value, dict) and isinstance(current_value, dict):
            for key in sorted(set(packet_value) | set(current_value)):
                child = f"{path}.{key}" if path else key
                if key not in packet_value:
                    differences.append(
                        {"path": child, "packet_value": None, "current_value": current_value[key]}
                    )
                elif key not in current_value:
                    differences.append(
                        {"path": child, "packet_value": packet_value[key], "current_value": None}
                    )
                else:
                    walk(packet_value[key], current_value[key], child)
            return
        if isinstance(packet_value, list) and isinstance(current_value, list):
            for index in range(max(len(packet_value), len(current_value))):
                child = f"{path}[{index}]"
                if index >= len(packet_value):
                    differences.append(
                        {"path": child, "packet_value": None, "current_value": current_value[index]}
                    )
                elif index >= len(current_value):
                    differences.append(
                        {"path": child, "packet_value": packet_value[index], "current_value": None}
                    )
                else:
                    walk(packet_value[index], current_value[index], child)
            return
        if packet_value != current_value:
            differences.append(
                {
                    "path": path or "$",
                    "packet_value": packet_value,
                    "current_value": current_value,
                }
            )

    walk(packet_identity, current_identity, "")
    return tuple(differences)


def assess_runtime_compatibility(
    packet_identity: dict[str, Any],
    current_identity: dict[str, Any],
    mode: str,
) -> dict[str, Any]:
    resolved_mode = resolve_runtime_compatibility_mode(mode, {})
    differences = runtime_identity_differences(packet_identity, current_identity)
    drift_detected = bool(differences)
    if not drift_detected:
        disposition = "identity_match"
        proof_may_proceed = True
    elif resolved_mode == "development":
        disposition = "warning_attempt_current_runtime"
        proof_may_proceed = True
    else:
        disposition = "warning_strict_stop_before_materialization"
        proof_may_proceed = False
    return {
        "mode": resolved_mode,
        "drift_detected": drift_detected,
        "proof_may_proceed": proof_may_proceed,
        "disposition": disposition,
        "differences": list(differences),
    }
