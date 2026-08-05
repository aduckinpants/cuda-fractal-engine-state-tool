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
        self.assertIn("Automated Packet V8 route (POC)", source)
        self.assertIn("Automated Session…", source)
        self.assertIn("It never records human acceptance.", source)
        self.assertIn("never human acceptance", source)
        self.assertIn("Run Automated Session", source)
        self.assertIn("automated_model_var", source)
        self.assertIn("automated_reasoning_effort_var", source)
        self.assertIn("credential.identity_dict()", source)
        self.assertIn("fingerprint_sha256[:16]", source)
        self.assertIn("Cancel Automation", source)
        self.assertIn("Open Run Folder", source)
        self.assertIn("Sanitized live event stream", source)
        self.assertIn("Local Scalar Sweep…", source)
        self.assertIn("Run Local Sweep", source)
        self.assertIn("Derived contact sheet (not acceptance)", source)
        self.assertIn("Open Web Review Bundle", source)
        self.assertIn("structurally admissible scalar axes", source)
        self.assertIn("human acceptance: false", source)
        self.assertNotIn('"path": "params.vortex_strength"', source)
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

    def test_automated_budget_projection_is_compact_and_non_authoritative(self) -> None:
        from cuda_fractal_state_tool.user_workflow_app import _automated_budget_text

        self.assertEqual(
            _automated_budget_text(
                {
                    "proven_rounds": 1,
                    "model_responses": 2,
                    "cumulative_input_tokens": 123456,
                    "cumulative_cached_input_tokens": 100000,
                    "cumulative_uncached_input_tokens": 23456,
                    "cumulative_output_tokens": 7890,
                    "cumulative_cache_write_tokens": 4567,
                    "cumulative_calculated_cost_usd": "1.23",
                    "maximum_calculated_cost_usd": "4.00",
                    "last_estimated_call_cost_usd": "1.97",
                    "pricing_policy": {"policy_id": "openai-standard-2026-08-03"},
                    "prompt_cache_policy": "explicit_no_cache",
                }
            ),
            "Rounds 1/2 · Responses 2/6 · Tokens total/cached/uncached/out "
            "123,456/100,000/23,456/7,890 · Cache writes 4,567 · "
            "Calculated USD 1.23/4.00 · Next max 1.97 · "
            "Pricing openai-standard-2026-08-03 · Cache explicit_no_cache",
        )

    def test_automated_event_view_is_compact_and_field_allowlisted(self) -> None:
        from cuda_fractal_state_tool.user_workflow_app import _format_automated_event

        line = _format_automated_event(
            {
                "sequence": 7,
                "event_type": "model_response",
                "payload": {
                    "requested_model": "gpt-5.6",
                    "resolved_model": "gpt-5.6-sol",
                    "input_tokens": 1000,
                    "cached_input_tokens": 800,
                    "uncached_input_tokens": 200,
                    "output_tokens": 50,
                    "latency_seconds": 3.25,
                    "api_key": "must-not-render",
                    "response_text": "must-not-render",
                },
            }
        )
        self.assertIn("MODEL_RESPONSE", line)
        self.assertIn("1,000/800/200/50", line)
        self.assertNotIn("must-not-render", line)

    def test_scalar_sweep_progress_is_compact_and_non_accepting(self) -> None:
        from cuda_fractal_state_tool.user_workflow_app import _format_scalar_sweep_progress

        self.assertEqual(
            _format_scalar_sweep_progress(
                {"event": "MEMBER_STARTED", "index": 2, "value": 0.5}
            ),
            "MEMBER 2  value=0.5  RUNNING",
        )
        completed = _format_scalar_sweep_progress(
            {
                "event": "MEMBER_COMPLETED",
                "index": 2,
                "value": 0.5,
                "status": "REPLAY_PROVEN",
                "proof_id": "proof-2",
            }
        )
        self.assertIn("REPLAY_PROVEN", completed)
        self.assertNotIn("ACCEPTED", completed)

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
