from __future__ import annotations

import json
import unittest

from cuda_fractal_state_tool.fractal_viewport_facts import validate_viewport_facts_bytes


def _bytes(value: object) -> bytes:
    return (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def _fixture() -> dict:
    return {
        "schema_version": 1,
        "mapping_id": "cuda_fractal_renderer_pixel_center_v1",
        "selected_fractal_type": "mcmullen",
        "render": {"width": 4096, "height": 2560, "aspect_ratio": 1.6},
        "camera": {
            "center_hp_x": 0.667,
            "center_hp_y": -0.044,
            "log2_zoom": 6.6,
            "resolved_zoom": 97.0,
            "rotation_degrees": 0.0,
        },
        "local_frame": {
            "half_width": 0.032,
            "half_height": 0.02,
            "full_width": 0.064,
            "full_height": 0.04,
        },
        "complex_pixel_basis": {
            "x_step": {"real": 0.00001, "imag": 0.0},
            "y_step": {"real": 0.0, "imag": 0.00001},
            "units_per_pixel_x": 0.00001,
            "units_per_pixel_y": 0.00001,
        },
        "continuous_edge_corners": [
            {"real": 0.63, "imag": -0.06},
            {"real": 0.70, "imag": -0.06},
            {"real": 0.70, "imag": -0.02},
            {"real": 0.63, "imag": -0.02},
        ],
        "pixel_center_corners": [
            {"real": 0.631, "imag": -0.059},
            {"real": 0.699, "imag": -0.059},
            {"real": 0.699, "imag": -0.021},
            {"real": 0.631, "imag": -0.021},
        ],
        "axis_aligned_complex_bounds": {
            "minimum": {"real": 0.63, "imag": -0.06},
            "maximum": {"real": 0.70, "imag": -0.02},
        },
        "fit_model": {
            "forward_mapping": "engine mapping",
            "pixel_normalization": "engine normalization",
            "inverse_fit": "engine inverse fit",
            "point_preparation": "engine point preparation",
        },
    }


class FractalViewportFactsTests(unittest.TestCase):
    def test_accepts_engine_v1_without_recomputing_camera_mapping(self) -> None:
        value = validate_viewport_facts_bytes(
            _bytes(_fixture()),
            expected_selector="mcmullen",
            expected_width=4096,
            expected_height=2560,
        )
        self.assertEqual(value["mapping_id"], "cuda_fractal_renderer_pixel_center_v1")
        self.assertEqual(value["local_frame"]["full_width"], 0.064)

    def test_rejects_wrong_identity_nonfinite_values_and_malformed_geometry(self) -> None:
        wrong = _fixture()
        wrong["selected_fractal_type"] = "newton"
        with self.assertRaisesRegex(ValueError, "selected selector"):
            validate_viewport_facts_bytes(
                _bytes(wrong), expected_selector="mcmullen", expected_width=4096, expected_height=2560
            )

        nonfinite = _fixture()
        nonfinite["local_frame"]["full_width"] = float("nan")
        with self.assertRaisesRegex(ValueError, "finite"):
            validate_viewport_facts_bytes(
                _bytes(nonfinite), expected_selector="mcmullen", expected_width=4096, expected_height=2560
            )

        malformed = _fixture()
        malformed["pixel_center_corners"] = malformed["pixel_center_corners"][:3]
        with self.assertRaisesRegex(ValueError, "four complex points"):
            validate_viewport_facts_bytes(
                _bytes(malformed), expected_selector="mcmullen", expected_width=4096, expected_height=2560
            )

    def test_rejects_duplicate_json_keys(self) -> None:
        duplicate = b'{"schema_version":1,"schema_version":1}\n'
        with self.assertRaisesRegex(ValueError, "duplicate"):
            validate_viewport_facts_bytes(
                duplicate, expected_selector="mcmullen", expected_width=4096, expected_height=2560
            )

    def test_rejects_undeclared_v1_fields_instead_of_silently_broadening_authority(self) -> None:
        extra = _fixture()
        extra["agent_camera_hint"] = {"zoom_out": 2.0}
        with self.assertRaisesRegex(ValueError, "undeclared fields"):
            validate_viewport_facts_bytes(
                _bytes(extra), expected_selector="mcmullen", expected_width=4096, expected_height=2560
            )


if __name__ == "__main__":
    unittest.main()
