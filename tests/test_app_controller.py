from __future__ import annotations

import inspect
import unittest
from pathlib import Path

import cuda_fractal_state_tool.app as app_entry


class ActiveApplicationSurfaceTests(unittest.TestCase):
    def test_app_module_is_only_a_compatibility_entry_point(self) -> None:
        source = inspect.getsource(app_entry)
        self.assertIn("user_workflow_app", source)
        self.assertNotIn("Phase1Controller", source)
        self.assertNotIn("Notebook", source)
        self.assertFalse(hasattr(app_entry, "Phase1Controller"))
        self.assertFalse(hasattr(app_entry, "Phase1App"))

    def test_active_application_has_no_proposal_or_repair_surface(self) -> None:
        from cuda_fractal_state_tool import user_workflow_app

        source = inspect.getsource(user_workflow_app)
        self.assertIn("Incoming State Override JSON", source)
        self.assertIn("Accept Candidate", source)
        self.assertIn("Revision Needed", source)
        self.assertIn("review_surface_seen", source)
        self.assertIn("Candidate visual delta", source)
        self.assertIn("IDENTICAL decoded pixels", source)
        self.assertIn("PIXELS IDENTICAL TO BASE", source)
        self.assertNotIn("proposal_v1", source)
        self.assertNotIn("Repair Packet", source)
        self.assertNotIn("execute_bound_proof", source)

    def test_proposal_era_modules_are_absent_from_active_package(self) -> None:
        package_dir = Path(inspect.getfile(app_entry)).parent
        retired = {
            "proposal.py",
            "proposal_cli.py",
            "materializer.py",
            "state_workflow.py",
            "workflow_cli.py",
            "finding_workflow.py",
            "finding_workflow_cli.py",
            "prompt_session_cli.py",
            "user_proof.py",
            "lane_catalog.py",
            "lane_catalog_cli.py",
        }
        self.assertEqual(retired & {path.name for path in package_dir.glob("*.py")}, set())


if __name__ == "__main__":
    unittest.main()
