from __future__ import annotations

import unittest

from cuda_fractal_state_tool.runtime_compatibility import (
    assess_runtime_compatibility,
    resolve_runtime_compatibility_mode,
    runtime_identity_differences,
)


class RuntimeCompatibilityTests(unittest.TestCase):
    def test_mode_resolution_uses_explicit_then_environment_then_development_default(self) -> None:
        self.assertEqual(resolve_runtime_compatibility_mode(None, {}), "development")
        self.assertEqual(
            resolve_runtime_compatibility_mode(
                None,
                {"CUDA_FRACTAL_STATE_TOOL_RUNTIME_COMPATIBILITY": "strict"},
            ),
            "strict",
        )
        self.assertEqual(
            resolve_runtime_compatibility_mode(
                "development",
                {"CUDA_FRACTAL_STATE_TOOL_RUNTIME_COMPATIBILITY": "strict"},
            ),
            "development",
        )
        with self.assertRaisesRegex(ValueError, "development or strict"):
            resolve_runtime_compatibility_mode("permissive", {})

    def test_field_level_differences_are_stable_and_explicit(self) -> None:
        packet = {"executable": {"sha256": "a", "size": 10}, "schema": "one"}
        current = {"executable": {"sha256": "b", "size": 10}, "contract": "new"}
        self.assertEqual(
            runtime_identity_differences(packet, current),
            (
                {"path": "contract", "packet_value": None, "current_value": "new"},
                {
                    "path": "executable.sha256",
                    "packet_value": "a",
                    "current_value": "b",
                },
                {"path": "schema", "packet_value": "one", "current_value": None},
            ),
        )

    def test_assessment_warns_and_attempts_in_development_but_stops_in_strict(self) -> None:
        packet = {"resolved_executable_sha256": "a"}
        current = {"resolved_executable_sha256": "b"}
        development = assess_runtime_compatibility(packet, current, "development")
        self.assertTrue(development["drift_detected"])
        self.assertTrue(development["proof_may_proceed"])
        self.assertEqual(development["disposition"], "warning_attempt_current_runtime")
        strict = assess_runtime_compatibility(packet, current, "strict")
        self.assertTrue(strict["drift_detected"])
        self.assertFalse(strict["proof_may_proceed"])
        self.assertEqual(strict["disposition"], "warning_strict_stop_before_materialization")


if __name__ == "__main__":
    unittest.main()
