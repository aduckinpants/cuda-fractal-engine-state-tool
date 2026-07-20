from __future__ import annotations

import unittest

from cuda_fractal_state_tool.json_utils import DuplicateKeyError, loads_no_duplicates


class JsonUtilsTests(unittest.TestCase):
    def test_loads_no_duplicates_accepts_unique_keys(self) -> None:
        value = loads_no_duplicates('{"a": 1, "b": {"c": 2}}')
        self.assertEqual(value["b"]["c"], 2)

    def test_loads_no_duplicates_rejects_top_level_duplicates(self) -> None:
        with self.assertRaises(DuplicateKeyError):
            loads_no_duplicates('{"a": 1, "a": 2}')

    def test_loads_no_duplicates_rejects_nested_duplicates(self) -> None:
        with self.assertRaises(DuplicateKeyError):
            loads_no_duplicates('{"a": {"b": 1, "b": 2}}')


if __name__ == "__main__":
    unittest.main()
