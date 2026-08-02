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
        self.assertIn("NO-OP OVERRIDE — EXACT BASE REPLAY", source)
        self.assertIn("Merged input is byte-identical to the authoritative base state", source)
        self.assertIn("Acknowledge Base Replay", source)
        self.assertIn("User explicitly acknowledged exact base replay.", source)
        self.assertIn("Capture or Agent Packet folder", source)
        self.assertIn("result.candidate_display_path", source)
        self.assertIn("decoded RGBA pixels match the engine candidate", source)
        self.assertIn("load_existing_packet_context", source)
        self.assertIn("without refresh", source)
        self.assertIn("Runtime compatibility", source)
        self.assertIn("RUNTIME DRIFT WARNING", source)
        self.assertIn("Primary handoff remains drag-all", source)
        self.assertNotIn("--packet-dir", source)
        self.assertNotIn("proposal_v1", source)
        self.assertNotIn("Repair Packet", source)
        self.assertNotIn("execute_bound_proof", source)

    def test_noop_proof_uses_explicit_base_replay_presentation(self) -> None:
        from types import SimpleNamespace

        from cuda_fractal_state_tool.user_workflow_app import (
            _candidate_accept_action_label,
            _candidate_preview_pixel_note,
            _is_exact_base_replay,
        )

        noop = SimpleNamespace(empty_override_byte_exact=True)
        ordinary = SimpleNamespace(empty_override_byte_exact=False)
        legacy = SimpleNamespace()
        self.assertTrue(_is_exact_base_replay(noop))
        self.assertFalse(_is_exact_base_replay(ordinary))
        self.assertFalse(_is_exact_base_replay(legacy))
        self.assertEqual(_candidate_accept_action_label(noop), "Acknowledge Base Replay")
        self.assertEqual(_candidate_accept_action_label(ordinary), "Accept Candidate")
        self.assertEqual(
            _candidate_preview_pixel_note(noop, {"decoded_equal": True}),
            " | EXACT BASE REPLAY | PIXELS IDENTICAL TO BASE",
        )
        self.assertEqual(
            _candidate_preview_pixel_note(noop, {"decoded_equal": False}),
            " | EXACT BASE REPLAY | PIXELS DIFFER FROM CAPTURED BASE",
        )
        self.assertEqual(
            _candidate_preview_pixel_note(noop, None),
            " | EXACT BASE REPLAY | base-frame comparison unavailable",
        )
        self.assertEqual(
            _candidate_preview_pixel_note(ordinary, {"decoded_equal": True}),
            " | PIXELS IDENTICAL TO BASE",
        )

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
