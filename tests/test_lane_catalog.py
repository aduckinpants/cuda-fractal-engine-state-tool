from __future__ import annotations

import unittest

from cuda_fractal_state_tool.lane_catalog import (
    FunctionUnknownError,
    LaneUnknownError,
    RuntimeMetadataShapeUnsupportedError,
    lane_function_known,
    lane_known,
    ordered_selection_actions,
    parse_ui_salt_contract_payload,
    validate_lane_function_reference,
)


def contract_payload() -> dict:
    return {
        "function_library": {
            "lanes": [
                {
                    "id": "source",
                    "default": "root_index",
                    "functions": [{"id": "root_index"}],
                },
                {
                    "id": "shape",
                    "default": "identity",
                    "functions": [{"id": "identity"}, {"id": "repeat"}],
                },
            ]
        }
    }


class LaneCatalogTests(unittest.TestCase):
    def test_parses_only_compiled_ui_salt_shape_and_preserves_order(self) -> None:
        catalog = parse_ui_salt_contract_payload(contract_payload())
        self.assertEqual(catalog.shape, "ui_salt_function_library_v1")
        self.assertEqual([lane.lane_id for lane in catalog.lanes], ["source", "shape"])
        self.assertEqual(catalog.lanes[1].default_function_id, "identity")
        self.assertTrue(lane_known(catalog, "shape"))
        self.assertTrue(lane_function_known(catalog, "shape", "repeat"))

    def test_rejects_callable_registry_instead_of_inventing_lane_metadata(self) -> None:
        with self.assertRaises(RuntimeMetadataShapeUnsupportedError):
            parse_ui_salt_contract_payload(
                {"functions": [{"id": "fractal.sample"}, {"id": "generic.sample"}]}
            )

    def test_rejects_duplicate_lanes_functions_and_missing_default(self) -> None:
        duplicate_lane = contract_payload()
        duplicate_lane["function_library"]["lanes"].append(
            {"id": "shape", "default": "identity", "functions": [{"id": "identity"}]}
        )
        with self.assertRaises(RuntimeMetadataShapeUnsupportedError):
            parse_ui_salt_contract_payload(duplicate_lane)

        duplicate_function = contract_payload()
        duplicate_function["function_library"]["lanes"][1]["functions"].append({"id": "repeat"})
        with self.assertRaises(RuntimeMetadataShapeUnsupportedError):
            parse_ui_salt_contract_payload(duplicate_function)

        missing_default = contract_payload()
        missing_default["function_library"]["lanes"][1]["default"] = "missing"
        with self.assertRaises(RuntimeMetadataShapeUnsupportedError):
            parse_ui_salt_contract_payload(missing_default)

    def test_validation_and_actions_fail_closed_and_use_contract_order(self) -> None:
        catalog = parse_ui_salt_contract_payload(contract_payload())
        with self.assertRaises(LaneUnknownError):
            validate_lane_function_reference(catalog, "grading", "neutral_finish")
        with self.assertRaises(FunctionUnknownError):
            validate_lane_function_reference(catalog, "shape", "mirror_repeat")
        self.assertEqual(
            ordered_selection_actions(catalog, {"shape": "repeat", "source": "root_index"}),
            (
                "select_function:source:0:root_index",
                "select_function:shape:0:repeat",
            ),
        )


if __name__ == "__main__":
    unittest.main()
