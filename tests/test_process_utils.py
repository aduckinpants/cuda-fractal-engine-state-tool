from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

from cuda_fractal_state_tool.process_utils import process_exists, run_command


class ProcessUtilsTests(unittest.TestCase):
    def test_timeout_kills_spawned_child_tree(self) -> None:
        fixture = Path(__file__).parent / "fixtures" / "spawn_child_tree.py"
        result = run_command([sys.executable, str(fixture)], cwd=fixture.parent, timeout_seconds=1.0)
        self.assertTrue(result.timed_out)
        self.assertFalse(process_exists(result.pid))
        match = re.search(r"child_pid=(\d+)", result.stdout)
        self.assertIsNotNone(match)
        if match:
            self.assertFalse(process_exists(int(match.group(1))))


if __name__ == "__main__":
    unittest.main()
