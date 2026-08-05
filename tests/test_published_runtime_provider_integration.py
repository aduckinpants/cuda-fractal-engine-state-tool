from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from cuda_fractal_state_tool.polynomial_model_provider import (
    ActiveModelCapture,
    CanonicalSampleCapture,
)
from cuda_fractal_state_tool.published_runtime_provider_integration import (
    run_published_runtime_provider_integration,
)
from cuda_fractal_state_tool.runtime_surface import LauncherResolution


class _Client:
    def __init__(self, runtime_executable: Path, *, timeout_seconds: float) -> None:
        self.runtime_executable = runtime_executable
        self.timeout_seconds = timeout_seconds

    def describe(self, **kwargs) -> ActiveModelCapture:
        state_path = kwargs["state_path"]
        state_sha256 = hashlib.sha256(state_path.read_bytes()).hexdigest()
        receipt = {
            "state_binding": {
                "state_json_sha256": state_sha256,
                "runtime_executable_sha256": "a" * 64,
            },
            "provider": {
                "status": "available",
                "provider_id": "polynomial_over_power_escape.v1",
                "provider_version": 1,
            },
            "model": {
                "model_id": "laurent_polynomial_escape_time.v1",
                "real_polynomial_coefficients": [1.0, 0.0, 0.0, 1.0],
                "denominator_power": 1,
            },
        }
        payload = json.dumps(receipt).encode("utf-8")
        return ActiveModelCapture(
            receipt_bytes=payload,
            receipt=receipt,
            runtime_executable_sha256="a" * 64,
            runtime_compatibility={"proof_may_proceed": True},
            command=(str(self.runtime_executable), "--describe-active-fractal-model"),
        )

    def sample(self, **kwargs) -> CanonicalSampleCapture:
        points = tuple(kwargs["points"])
        request = {"request_id": kwargs["request_id"]}
        response = {
            "runtime": {
                "fractal_type": "explaino_rational_escape",
                "backend_used": "cuda",
                "iteration_arithmetic": "float64",
            },
            "samples": [
                {
                    "status": "escaped",
                    "coord_x": point.real,
                    "coord_y": point.imag,
                }
                for point in points
            ],
        }
        return CanonicalSampleCapture(
            request_bytes=b"request",
            request=request,
            response_bytes=b"response",
            response=response,
            command=(str(self.runtime_executable), "--sample-request-stdin"),
        )


class _NonCudaClient(_Client):
    def sample(self, **kwargs) -> CanonicalSampleCapture:
        capture = super().sample(**kwargs)
        capture.response["runtime"]["backend_used"] = "cpu"
        return capture


class _WrongDenominatorClient(_Client):
    def describe(self, **kwargs) -> ActiveModelCapture:
        capture = super().describe(**kwargs)
        capture.receipt["model"]["denominator_power"] = 2
        return capture


class PublishedRuntimeProviderIntegrationTests(unittest.TestCase):
    def test_orchestration_writes_a_machine_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            runtime_cmd = root / "fractal_ui.cmd"
            runtime_exe = root / "fractal_ui.exe"
            state = root / "state.json"
            output = root / "proof.json"
            runtime_cmd.write_text("@echo off\n", encoding="utf-8")
            runtime_exe.write_bytes(b"runtime")
            state.write_text(
                json.dumps(
                    {
                        "fractal_type": "explaino_rational_escape",
                        "params": {
                            "explaino_rational_escape_denominator_power": 1
                        },
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            launcher = LauncherResolution(
                runtime_cmd_path=str(runtime_cmd),
                launcher_directory=str(root),
                active_file_path=str(root / "fractal_ui_active.txt"),
                active_entry="fractal_ui.exe",
                resolved_executable_path=str(runtime_exe),
                repo_root_hint=None,
                runtime_schema_path=None,
                ui_salt_contract_path=None,
            )
            provider_result = {
                "features": {"critical_points": [{}, {}], "fixed_points": [{}]}
            }
            with (
                patch(
                    "cuda_fractal_state_tool.published_runtime_provider_integration.resolve_launcher",
                    return_value=launcher,
                ),
                patch(
                    "cuda_fractal_state_tool.published_runtime_provider_integration.build_runtime_identity",
                    return_value={"resolved_executable_sha256": "a" * 64},
                ),
                patch(
                    "cuda_fractal_state_tool.published_runtime_provider_integration.ActiveModelRuntimeClient",
                    _Client,
                ),
                patch(
                    "cuda_fractal_state_tool.published_runtime_provider_integration.PolynomialOverPowerEscapeProvider.derive",
                    return_value=provider_result,
                ),
            ):
                result = run_published_runtime_provider_integration(
                    runtime_cmd=runtime_cmd,
                    state_json=state,
                    out_json=output,
                )

            self.assertTrue(result["ok"])
            self.assertEqual(result["active_model"]["provider_id"], "polynomial_over_power_escape.v1")
            self.assertEqual(result["active_model"]["critical_point_count"], 2)
            self.assertEqual(result["canonical_sample"]["sample_count"], 2)
            self.assertEqual(json.loads(output.read_text(encoding="utf-8")), result)

    def test_non_cuda_response_fails_the_dedicated_rail(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            runtime_cmd = root / "fractal_ui.cmd"
            runtime_exe = root / "fractal_ui.exe"
            state = root / "state.json"
            runtime_cmd.write_text("@echo off\n", encoding="utf-8")
            runtime_exe.write_bytes(b"runtime")
            state.write_text(
                '{"fractal_type":"explaino_rational_escape",'
                '"params":{"explaino_rational_escape_denominator_power":1}}\n',
                encoding="utf-8",
            )
            launcher = LauncherResolution(
                runtime_cmd_path=str(runtime_cmd),
                launcher_directory=str(root),
                active_file_path=str(root / "fractal_ui_active.txt"),
                active_entry="fractal_ui.exe",
                resolved_executable_path=str(runtime_exe),
                repo_root_hint=None,
                runtime_schema_path=None,
                ui_salt_contract_path=None,
            )
            with (
                patch(
                    "cuda_fractal_state_tool.published_runtime_provider_integration.resolve_launcher",
                    return_value=launcher,
                ),
                patch(
                    "cuda_fractal_state_tool.published_runtime_provider_integration.build_runtime_identity",
                    return_value={"resolved_executable_sha256": "a" * 64},
                ),
                patch(
                    "cuda_fractal_state_tool.published_runtime_provider_integration.ActiveModelRuntimeClient",
                    _NonCudaClient,
                ),
                patch(
                    "cuda_fractal_state_tool.published_runtime_provider_integration.PolynomialOverPowerEscapeProvider.derive",
                    return_value={
                        "features": {"critical_points": [], "fixed_points": []}
                    },
                ),
                self.assertRaisesRegex(ValueError, "did not use CUDA"),
            ):
                run_published_runtime_provider_integration(
                    runtime_cmd=runtime_cmd,
                    state_json=state,
                    out_json=root / "proof.json",
                )

    def test_model_denominator_must_match_the_exact_state(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            runtime_cmd = root / "fractal_ui.cmd"
            runtime_exe = root / "fractal_ui.exe"
            state = root / "state.json"
            runtime_cmd.write_text("@echo off\n", encoding="utf-8")
            runtime_exe.write_bytes(b"runtime")
            state.write_text(
                '{"fractal_type":"explaino_rational_escape",'
                '"params":{"explaino_rational_escape_denominator_power":1}}\n',
                encoding="utf-8",
            )
            launcher = LauncherResolution(
                runtime_cmd_path=str(runtime_cmd),
                launcher_directory=str(root),
                active_file_path=str(root / "fractal_ui_active.txt"),
                active_entry="fractal_ui.exe",
                resolved_executable_path=str(runtime_exe),
                repo_root_hint=None,
                runtime_schema_path=None,
                ui_salt_contract_path=None,
            )
            with (
                patch(
                    "cuda_fractal_state_tool.published_runtime_provider_integration.resolve_launcher",
                    return_value=launcher,
                ),
                patch(
                    "cuda_fractal_state_tool.published_runtime_provider_integration.build_runtime_identity",
                    return_value={"resolved_executable_sha256": "a" * 64},
                ),
                patch(
                    "cuda_fractal_state_tool.published_runtime_provider_integration.ActiveModelRuntimeClient",
                    _WrongDenominatorClient,
                ),
                patch(
                    "cuda_fractal_state_tool.published_runtime_provider_integration.PolynomialOverPowerEscapeProvider.derive",
                    return_value={
                        "features": {"critical_points": [], "fixed_points": []}
                    },
                ),
                self.assertRaisesRegex(ValueError, "denominator disagrees"),
            ):
                run_published_runtime_provider_integration(
                    runtime_cmd=runtime_cmd,
                    state_json=state,
                    out_json=root / "proof.json",
                )

    def test_wrong_selector_fails_before_runtime_invocation(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            runtime_cmd = root / "fractal_ui.cmd"
            state = root / "state.json"
            runtime_cmd.write_text("@echo off\n", encoding="utf-8")
            state.write_text('{"fractal_type":"mandelbrot"}\n', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "must select explaino_rational_escape"):
                run_published_runtime_provider_integration(
                    runtime_cmd=runtime_cmd,
                    state_json=state,
                    out_json=root / "proof.json",
                )

    def test_duplicate_state_keys_fail_before_runtime_invocation(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            runtime_cmd = root / "fractal_ui.cmd"
            state = root / "state.json"
            runtime_cmd.write_text("@echo off\n", encoding="utf-8")
            state.write_text(
                '{"fractal_type":"explaino_rational_escape",'
                '"fractal_type":"explaino_rational_escape",'
                '"params":{"explaino_rational_escape_denominator_power":1}}\n',
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "duplicate keys"):
                run_published_runtime_provider_integration(
                    runtime_cmd=runtime_cmd,
                    state_json=state,
                    out_json=root / "proof.json",
                )

    def test_missing_inputs_and_nonfinite_points_fail_instead_of_skipping(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            with self.assertRaises(FileNotFoundError):
                run_published_runtime_provider_integration(
                    runtime_cmd=root / "missing.cmd",
                    state_json=root / "missing.json",
                    out_json=root / "proof.json",
                )

            runtime_cmd = root / "fractal_ui.cmd"
            state = root / "state.json"
            runtime_cmd.write_text("@echo off\n", encoding="utf-8")
            state.write_text(
                '{"fractal_type":"explaino_rational_escape",'
                '"params":{"explaino_rational_escape_denominator_power":1}}\n',
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "coordinates must be finite"):
                run_published_runtime_provider_integration(
                    runtime_cmd=runtime_cmd,
                    state_json=state,
                    out_json=root / "proof.json",
                    sample_points=(complex(float("nan"), 0.0),),
                )


if __name__ == "__main__":
    unittest.main()
