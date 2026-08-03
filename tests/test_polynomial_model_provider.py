from __future__ import annotations

import hashlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from cuda_fractal_state_tool.polynomial_model_provider import (
    PolynomialOverPowerEscapeProvider,
    build_annotation_set,
    build_sample_request,
    project_complex_to_viewport,
    render_annotations,
    validate_active_model_receipt,
    validate_sample_response,
)


STATE_BYTES = b'{"fractal_type":"explaino_rational_escape"}\n'
RUNTIME_SHA256 = "5" * 64


def _receipt() -> dict[str, object]:
    return {
        "schema_version": 1,
        "state_binding": {
            "state_json_sha256": hashlib.sha256(STATE_BYTES).hexdigest(),
            "runtime_executable_sha256": RUNTIME_SHA256,
        },
        "selected_fractal_type": "explaino_rational_escape",
        "resolved_runtime_fractal_type": "explaino_rational_escape",
        "provider": {
            "status": "available",
            "provider_id": "polynomial_over_power_escape.v1",
            "provider_version": 1,
            "unavailable_reason": None,
        },
        "numeric_authority": {
            "requested_sample_tier": "standard",
            "resolved_backend": "float64",
            "iteration_strategy": "direct",
        },
        "evaluation_authority": {
            "evaluation_surface": "fractal.sample",
            "state_binding_required": True,
            "runtime_binding_required": True,
        },
        "participating_state": [
            {"path": "view.fractal_type", "value": "explaino_rational_escape"},
            {"path": "render.sample_tier", "value": "standard"},
            {
                "path": "params.poly_coeffs",
                "value": [
                    0.69175207614898682,
                    -1.4607863426208496,
                    2.0896022319793701,
                    -1.035009503364563,
                    1.0,
                ],
            },
            {"path": "params.explaino_rational_escape_denominator_power", "value": 3},
            {"path": "params.explaino_warp_strength", "value": 0.0},
            {"path": "params.max_iter", "value": 1200},
        ],
        "model": {
            "model_id": "laurent_polynomial_escape_time.v1",
            "recurrence_id": "z_next_equals_real_polynomial_degree4_over_z_power",
            "coefficient_order": "ascending_power",
            "real_polynomial_coefficients": [
                0.69175207614898682,
                -1.4607863426208496,
                2.0896022319793701,
                -1.035009503364563,
                1.0,
            ],
            "denominator_power": 3,
            "max_iterations": 1200,
            "pole_threshold_abs2": 1e-30,
            "escape_radius_abs2": 10000.0,
            "termination_kinds": ["pole", "escaped_radius", "nonfinite", "max_iterations"],
            "structural_singular_points": [
                {"real": 0.0, "imag": 0.0, "kind": "denominator_zero"}
            ],
        },
    }


def _viewport() -> dict[str, object]:
    return {
        "mapping_id": "cuda_fractal_renderer_pixel_center_v1",
        "render": {"width": 4096, "height": 2559, "aspect_ratio": 4096 / 2559},
        "camera": {
            "center_hp_x": 0.46716576441518648,
            "center_hp_y": -0.85863281063104113,
            "log2_zoom": 9.51071886458249,
            "resolved_zoom": 729.4770926887894,
            "rotation_degrees": 0.0,
        },
        "local_frame": {
            "half_width": 0.004388418115601859,
            "half_height": 0.002741689931109657,
            "full_width": 0.008776836231203717,
            "full_height": 0.005483379862219314,
        },
        "complex_pixel_basis": {
            "x_step": {"real": 2.14278228300872e-6, "imag": 0.0},
            "y_step": {"real": 0.0, "imag": 2.14278228300872e-6},
            "units_per_pixel_x": 2.14278228300872e-6,
            "units_per_pixel_y": 2.14278228300872e-6,
        },
        "continuous_edge_corners": [],
        "pixel_center_corners": [],
        "axis_aligned_complex_bounds": {
            "minimum": {"real": 0.4627773462995846, "imag": -0.8613745005621508},
            "maximum": {"real": 0.47155418253078835, "imag": -0.8558911206999315},
        },
        "fit_model": {},
    }


class PolynomialModelProviderTests(unittest.TestCase):
    def test_receipt_validation_is_exactly_state_and_runtime_bound(self) -> None:
        validated = validate_active_model_receipt(
            json.dumps(_receipt()).encode("utf-8"),
            expected_state_sha256=hashlib.sha256(STATE_BYTES).hexdigest(),
            expected_runtime_sha256=RUNTIME_SHA256,
            expected_selector="explaino_rational_escape",
        )
        self.assertEqual(validated["model"]["model_id"], "laurent_polynomial_escape_time.v1")
        changed = _receipt()
        changed["state_binding"]["state_json_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "state hash"):
            validate_active_model_receipt(
                json.dumps(changed).encode("utf-8"),
                expected_state_sha256=hashlib.sha256(STATE_BYTES).hexdigest(),
                expected_runtime_sha256=RUNTIME_SHA256,
                expected_selector="explaino_rational_escape",
            )

    def test_unavailable_receipt_is_valid_authority_without_a_fallback_model(self) -> None:
        receipt = _receipt()
        receipt["provider"] = {
            "status": "unavailable",
            "provider_id": None,
            "provider_version": None,
            "unavailable_reason": "nonzero_warp_unsupported",
        }
        receipt["model"] = None
        validated = validate_active_model_receipt(
            json.dumps(receipt).encode("utf-8"),
            expected_state_sha256=hashlib.sha256(STATE_BYTES).hexdigest(),
            expected_runtime_sha256=RUNTIME_SHA256,
            expected_selector="explaino_rational_escape",
        )
        self.assertEqual(validated["provider"]["status"], "unavailable")
        self.assertIsNone(validated["model"])

    def test_unavailable_receipt_may_report_a_normalized_runtime_selector(self) -> None:
        receipt = _receipt()
        receipt["selected_fractal_type"] = "explaino_all"
        receipt["resolved_runtime_fractal_type"] = "explaino"
        receipt["provider"] = {
            "status": "unavailable",
            "provider_id": None,
            "provider_version": None,
            "unavailable_reason": "unsupported_fractal_type",
        }
        receipt["model"] = None
        validated = validate_active_model_receipt(
            json.dumps(receipt).encode("utf-8"),
            expected_state_sha256=hashlib.sha256(STATE_BYTES).hexdigest(),
            expected_runtime_sha256=RUNTIME_SHA256,
            expected_selector="explaino_all",
        )
        self.assertEqual(validated["selected_fractal_type"], "explaino_all")
        self.assertEqual(validated["resolved_runtime_fractal_type"], "explaino")

        receipt["selected_fractal_type"] = "explaino_fold"
        with self.assertRaisesRegex(ValueError, "selector disagrees"):
            validate_active_model_receipt(
                json.dumps(receipt).encode("utf-8"),
                expected_state_sha256=hashlib.sha256(STATE_BYTES).hexdigest(),
                expected_runtime_sha256=RUNTIME_SHA256,
                expected_selector="explaino_all",
            )

    def test_available_receipt_requires_exact_resolved_selector(self) -> None:
        receipt = _receipt()
        receipt["resolved_runtime_fractal_type"] = "explaino"
        with self.assertRaisesRegex(ValueError, "resolved selector"):
            validate_active_model_receipt(
                json.dumps(receipt).encode("utf-8"),
                expected_state_sha256=hashlib.sha256(STATE_BYTES).hexdigest(),
                expected_runtime_sha256=RUNTIME_SHA256,
                expected_selector="explaino_rational_escape",
            )

    def test_provider_derives_critical_and_fixed_points_with_small_residuals(self) -> None:
        result = PolynomialOverPowerEscapeProvider().derive(_receipt())
        critical = result["features"]["critical_points"]
        self.assertEqual(len(critical), 4)
        expected = complex(0.467055157863372, -0.858583585204410)
        nearest = min(critical, key=lambda item: abs(complex(item["point"]["real"], item["point"]["imag"]) - expected))
        self.assertLess(
            abs(complex(nearest["point"]["real"], nearest["point"]["imag"]) - expected),
            1e-10,
        )
        self.assertLess(nearest["equation_residual"], 1e-10)
        self.assertTrue(result["features"]["fixed_points"])
        self.assertTrue(
            all(item["equation_residual"] < 1e-9 for item in result["features"]["fixed_points"])
        )
        self.assertEqual(result["features"]["structural_singular_points"][0]["point"], {"real": 0.0, "imag": 0.0})

    def test_projection_uses_exported_pixel_basis_and_hits_expected_fixture_location(self) -> None:
        projected = project_complex_to_viewport(
            complex(0.467055157863372, -0.858583585204410),
            _viewport(),
        )
        self.assertTrue(projected["contained"])
        self.assertAlmostEqual(projected["pixel_x"], 1995.88, delta=0.1)
        self.assertAlmostEqual(projected["pixel_y"], 1301.97, delta=0.1)

    def test_sample_request_loads_exact_base_state_and_response_must_match_receipt(self) -> None:
        request = build_sample_request(
            state_path=Path(r"C:\exact\state.json"),
            points=(complex(0.25, -0.5),),
            request_id="request-one",
        )
        self.assertEqual(request["base_state"], {"load_state_json": r"C:\exact\state.json"})
        self.assertNotIn("overrides", request)
        response = {
            "response_version": 1,
            "request_id": "request-one",
            "function_id": "fractal.sample",
            "ok": True,
            "runtime": {
                "fractal_type": "explaino_rational_escape",
                "backend_used": "cuda",
                "iteration_arithmetic": "float64",
            },
            "samples": [{"coord_x": 0.25, "coord_y": -0.5, "status": "bounded"}],
            "error": None,
        }
        validated = validate_sample_response(response, request=request, active_model_receipt=_receipt())
        self.assertEqual(validated["samples"][0]["status"], "bounded")
        response["runtime"]["iteration_arithmetic"] = "float32"
        with self.assertRaisesRegex(ValueError, "numeric backend"):
            validate_sample_response(response, request=request, active_model_receipt=_receipt())

    def test_annotation_records_and_render_receipt_are_separate_and_deterministic(self) -> None:
        provider_result = PolynomialOverPowerEscapeProvider().derive(_receipt())
        annotation_set = build_annotation_set(provider_result, _viewport())
        contained = [item for item in annotation_set["annotations"] if item["viewport"]["contained"]]
        self.assertTrue(any(item["feature_kind"] == "critical_point" for item in contained))
        self.assertEqual(annotation_set["nearest_to_camera_center"]["annotation_id"], "critical-2")
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "web-agent-frame.png"
            Image.new("RGBA", (2048, 1280), (10, 20, 30, 255)).save(source, format="PNG")
            first = render_annotations(
                source,
                root / "annotated-a.png",
                annotation_set,
                source_viewport_width=4096,
                source_viewport_height=2559,
            )
            second = render_annotations(
                source,
                root / "annotated-b.png",
                annotation_set,
                source_viewport_width=4096,
                source_viewport_height=2559,
            )
            self.assertEqual(first["output_png_sha256"], second["output_png_sha256"])
            self.assertEqual((root / "annotated-a.png").read_bytes(), (root / "annotated-b.png").read_bytes())
            self.assertNotIn("output_png_sha256", annotation_set)
            decoded = Image.open(io.BytesIO((root / "annotated-a.png").read_bytes()))
            self.assertEqual(decoded.size, (2048, 1280))


if __name__ == "__main__":
    unittest.main()
