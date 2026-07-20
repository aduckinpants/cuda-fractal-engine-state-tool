from __future__ import annotations

import unittest

from cuda_fractal_state_tool.lane_catalog import (
    RuntimeMetadataShapeUnsupportedError,
    lane_function_known,
    lane_known,
    parse_lane_catalog_payload,
)


class LaneCatalogTests(unittest.TestCase):
    def test_parse_lane_functions_shape(self) -> None:
        catalog = parse_lane_catalog_payload(
            {
                "lane_functions": [
                    {"lane_id": "shape", "function_id": "identity"},
                    {"lane_id": "shape", "function_id": "repeat"},
                    {"lane_id": "palette", "function_id": "cyclic_escape"},
                ]
            }
        )
        self.assertEqual(catalog.shape, "lane_functions")
        self.assertTrue(lane_known(catalog, "shape"))
        self.assertTrue(lane_function_known(catalog, "shape", "identity"))
        self.assertFalse(lane_function_known(catalog, "shape", "unknown"))

    def test_parse_functions_shape(self) -> None:
        catalog = parse_lane_catalog_payload(
            {
                "functions": [
                    {"lane_id": "signal", "id": "root_index"},
                    {"lane_id": "signal", "id": "iteration_count"},
                ]
            }
        )
        self.assertEqual(catalog.shape, "functions")
        self.assertTrue(lane_function_known(catalog, "signal", "iteration_count"))

    def test_parse_color_pipeline_draft_shape(self) -> None:
        catalog = parse_lane_catalog_payload(
            {
                "color_pipeline_draft": {
                    "lanes": [
                        {
                            "lane_id": "grading",
                            "functions": [
                                {"function_id": "basin_default"},
                                {"id": "escape_default"},
                            ],
                        }
                    ]
                }
            }
        )
        self.assertEqual(catalog.shape, "color_pipeline_draft")
        self.assertTrue(lane_function_known(catalog, "grading", "escape_default"))

    def test_unsupported_shape_fails_closed(self) -> None:
        with self.assertRaises(RuntimeMetadataShapeUnsupportedError):
            parse_lane_catalog_payload({"unexpected": {"x": 1}})


if __name__ == "__main__":
    unittest.main()
