from __future__ import annotations

import unittest

from cuda_fractal_state_tool.fractal_parameter_authority import build_parameter_projection


def _descriptor() -> dict:
    return {
        "version": 1,
        "lanes": [
            {
                "fractal_id": "explaino_all",
                "controls": [
                    {
                        "control_id": "explaino_seed",
                        "owner_lane": "explaino_all",
                        "binding_path": "fractal.params.explaino_seed",
                        "state_io_key": "explaino_seed",
                        "binding_resolves": True,
                        "default_visible": True,
                        "visibility_surface_id": "default",
                    },
                    {
                        "control_id": "explaino_root_0_x",
                        "owner_lane": "explaino_all",
                        "binding_path": "fractal.params.explaino_roots.0.x",
                        "state_io_key": "explaino_roots.0.x",
                        "binding_resolves": True,
                        "default_visible": False,
                        "visibility_surface_id": "explaino_roots_custom",
                    },
                ],
            },
            {
                "fractal_id": "multibrot",
                "controls": [
                    {
                        "control_id": "multibrot_power",
                        "binding_path": "fractal.params.multibrot_power_float",
                        "state_io_key": "multibrot_power_float",
                        "binding_resolves": True,
                    }
                ],
            },
        ],
    }


def _schema() -> dict:
    return {
        "schema_version": 1,
        "panels": [
            {
                "id": "fractal",
                "controls": [
                    {
                        "id": "explaino_seed",
                        "type": "slider_double",
                        "label": "Explaino Seed",
                        "help": "Primary Explaino seed control.",
                        "ui_min": -10.0,
                        "ui_max": 10.0,
                        "step": 0.001,
                        "binding": {"kind": "param", "path": "fractal.params.explaino_seed"},
                        "visible_if": {
                            "op": "in",
                            "path": "fractal.view.fractal_type",
                            "value": "explaino,explaino_all",
                        },
                    },
                    {
                        "id": "explaino_root_0_x",
                        "type": "drag_float",
                        "label": "Root 1 X",
                        "binding": {"kind": "param", "path": "fractal.params.explaino_roots.0.x"},
                        "visible_if": {
                            "op": "eq",
                            "path": "fractal.params.explaino_root_authority",
                            "value": "custom",
                        },
                    },
                    {
                        "id": "multibrot_power",
                        "type": "slider_float",
                        "label": "Multibrot Power",
                        "binding": {"kind": "param", "path": "fractal.params.multibrot_power_float"},
                    },
                ],
            }
        ],
    }


class FractalParameterAuthorityTests(unittest.TestCase):
    def test_selected_lane_excludes_other_family_controls_and_merges_properties(self) -> None:
        projection = build_parameter_projection(
            "explaino_all",
            {
                "params": {
                    "explaino_seed": 1,
                    "explaino_roots": [{"x": -0.5, "y": 0.2}],
                    "multibrot_power_float": 3.0,
                }
            },
            {"active_fractal_controls": {"explaino_seed": 38}},
            _descriptor(),
            _schema(),
        )
        self.assertEqual([item["control_id"] for item in projection["controls"]], ["explaino_seed", "explaino_root_0_x"])
        self.assertNotIn("multibrot_power", {item["control_id"] for item in projection["controls"]})
        seed = projection["controls"][0]
        self.assertEqual(seed["current_value"], 38)
        self.assertEqual(seed["current_value_source"], "fractal-state.json.active_fractal_controls")
        self.assertEqual(seed["schema_properties"]["help"], "Primary Explaino seed control.")
        self.assertEqual(seed["schema_properties"]["ui_max"], 10.0)
        root = projection["controls"][1]
        self.assertEqual(root["current_value"], -0.5)
        self.assertEqual(root["current_value_source"], "state.json.params")
        self.assertFalse(root["descriptor_properties"]["default_visible"])
        self.assertEqual(root["schema_properties"]["visible_if"]["value"], "custom")

    def test_missing_selected_lane_fails_closed(self) -> None:
        with self.assertRaisesRegex(ValueError, "0 lanes"):
            build_parameter_projection("julia", {"params": {}}, None, _descriptor(), _schema())

    def test_unresolved_binding_fails_closed(self) -> None:
        descriptor = _descriptor()
        descriptor["lanes"][0]["controls"][0]["binding_resolves"] = False
        with self.assertRaisesRegex(ValueError, "no resolved binding"):
            build_parameter_projection("explaino_all", {"params": {}}, None, descriptor, _schema())

    def test_descriptor_schema_binding_mismatch_fails_closed(self) -> None:
        schema = _schema()
        schema["panels"][0]["controls"][0]["binding"]["path"] = "fractal.params.other"
        with self.assertRaisesRegex(ValueError, "binding mismatch"):
            build_parameter_projection("explaino_all", {"params": {}}, None, _descriptor(), schema)


if __name__ == "__main__":
    unittest.main()
