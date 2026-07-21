from __future__ import annotations

import inspect
import unittest

import cuda_fractal_state_tool.app as app_entry


class ActiveApplicationSurfaceTests(unittest.TestCase):
    def test_app_module_is_only_a_compatibility_entry_point(self) -> None:
        source = inspect.getsource(app_entry)
        self.assertIn("user_workflow_app", source)
        self.assertNotIn("Phase1Controller", source)
        self.assertNotIn("Notebook", source)
        self.assertFalse(hasattr(app_entry, "Phase1Controller"))
        self.assertFalse(hasattr(app_entry, "Phase1App"))


if __name__ == "__main__":
    unittest.main()
