from __future__ import annotations

import unittest

from cuda_fractal_state_tool.state_compare import compare_json_documents


LEFT = """
{
  "state_version": 3,
  "fractal_type": "newton",
  "view": {"center_x": 0},
  "params": {"max_iter": 10},
  "render": {"width": 10},
  "stats": {"last_render_ms": 1.0}
}
"""

RIGHT = """
{
  "state_version": 3,
  "fractal_type": "newton",
  "view": {"center_x": 0},
  "params": {"max_iter": 10},
  "render": {"width": 10},
  "stats": {"last_render_ms": 2.0}
}
"""


class StateCompareTests(unittest.TestCase):
    def test_stats_difference_is_volatile_but_semantically_equal(self) -> None:
        result = compare_json_documents(LEFT, RIGHT)
        self.assertFalse(result.raw_equal)
        self.assertTrue(result.semantic_equal)
        self.assertEqual(result.differences[0].classification, "volatile_diagnostic_data")


if __name__ == "__main__":
    unittest.main()
