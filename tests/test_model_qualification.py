from __future__ import annotations

import tempfile
import unittest
import json
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

from cuda_fractal_state_tool.automated_protocol import ControllerDisposition, SessionBudgets
from cuda_fractal_state_tool.enrichment_disclosure import DisclosureProfile
from cuda_fractal_state_tool.model_profile import ModelProfileV1
from cuda_fractal_state_tool.model_qualification import (
    AUTOMATIC_GATE_IDS,
    QualificationCaseV1,
    QualificationRole,
    RecordedResponsesTransport,
    RecordedTurn,
    create_qualification_run_store,
    count_qualification_author_input,
    load_qualification_case,
    run_qualification_case,
)
from cuda_fractal_state_tool.pricing_policy import load_pricing_policy
from cuda_fractal_state_tool.openai_transport import TransportInputCountResult

from tests.test_automated_session import (
    VALID_OVERRIDE_RESPONSE,
    ServiceHarness,
    _bundle,
)


class ModelProfileTests(unittest.TestCase):
    def test_profile_identity_is_deterministic_and_effort_sensitive(self) -> None:
        policy = load_pricing_policy()
        high = ModelProfileV1(
            model="gpt-5.6-luna",
            reasoning_effort="high",
            pricing_tier=policy.service_tier,
        )
        medium = ModelProfileV1(
            model="gpt-5.6-luna",
            reasoning_effort="medium",
            pricing_tier=policy.service_tier,
        )
        high.validate(policy)
        medium.validate(policy)
        self.assertEqual(high.sha256, high.sha256)
        self.assertNotEqual(high.sha256, medium.sha256)

    def test_profile_rejects_unpriced_model_and_unsupported_cache_mode(self) -> None:
        policy = load_pricing_policy()
        with self.assertRaisesRegex(ValueError, "no model match"):
            ModelProfileV1(model="unknown", pricing_tier=policy.service_tier).validate(policy)

    def test_tracked_rubric_names_the_exact_implemented_automatic_gates(self) -> None:
        root = Path(__file__).resolve().parents[1]
        rubric = json.loads(
            (root / "docs" / "v9_economic_qualification_rubric.v1.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(tuple(rubric["automatic_gates"]), AUTOMATIC_GATE_IDS)


class QualificationHarnessTests(unittest.TestCase):
    def _case(self, root: Path, bundle) -> QualificationCaseV1:
        policy = load_pricing_policy()
        profile = ModelProfileV1(
            model="gpt-5.6-luna",
            reasoning_effort="high",
            pricing_tier=policy.service_tier,
        )
        budgets = SessionBudgets(
            maximum_proven_rounds=1,
            maximum_model_responses=2,
            maximum_cumulative_input_tokens=1_000,
            maximum_cumulative_output_tokens=500,
            maximum_input_tokens_per_response=500,
            maximum_output_tokens_per_response=100,
            maximum_review_output_tokens_per_response=50,
            maximum_correction_output_tokens_per_response=50,
            maximum_calculated_cost_usd=Decimal("0.50"),
        )
        return QualificationCaseV1(
            role=QualificationRole.HARD_CALIBRATOR,
            packet_dir=bundle.packet_dir,
            packet_id=bundle.packet_id,
            packet_manifest_sha256=bundle.manifest_sha256,
            finding_id=bundle.finding_id,
            selected_fractal_type=bundle.selected_fractal_type,
            disclosure_profile=DisclosureProfile.BLIND,
            expected_analysis_id=None,
            model_profile=profile,
            budgets=budgets,
            pricing_policy_identity=policy.identity_dict(),
            pricing_policy_sha256=policy.sha256,
        )

    def test_recorded_response_route_exercises_controller_and_hard_gates_offline(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            initial = _bundle(root, "packet-base", "finding-base", "base")
            derived = _bundle(root, "packet-derived", "finding-derived", "derived")
            services = ServiceHarness(root, initial, [derived])
            case = self._case(root, initial)
            store = create_qualification_run_store(
                workspace_root=root / "workspace",
                run_id="qualification-offline",
                case=case,
            )
            transport = RecordedResponsesTransport(
                (
                    RecordedTurn(
                        output_text=VALID_OVERRIDE_RESPONSE,
                        input_tokens=100,
                        output_tokens=20,
                        resolved_model="gpt-5.6-luna",
                        response_id="recorded-author",
                    ),
                    RecordedTurn(
                        output_text="Result matched.\nGATE_DECISION: SESSION_PASS\n",
                        input_tokens=120,
                        output_tokens=15,
                        resolved_model="gpt-5.6-luna",
                        response_id="recorded-review",
                    ),
                )
            )
            result, receipt = run_qualification_case(
                case=case,
                bundle=initial,
                transport=transport,
                run_store=store,
                services=services.services(),
                pricing_policy=load_pricing_policy(),
            )

            self.assertEqual(result.disposition, ControllerDisposition.SESSION_PASSED)
            self.assertTrue(receipt.passed)
            self.assertTrue(
                (store.run_dir / "qualification" / "automatic-gates.json").is_file()
            )
            responses = [
                event for event in store.read_events() if event["event_type"] == "model_response"
            ]
            self.assertEqual(
                [event["payload"]["reasoning_effort"] for event in responses],
                ["high", "high"],
            )
            self.assertTrue(
                all(
                    event["payload"]["model_profile"]["sha256"]
                    == case.model_profile.sha256
                    for event in responses
                )
            )

    def test_count_only_route_uses_controller_context_and_never_sends_a_turn(self) -> None:
        class CountOnlyTransport:
            def __init__(self) -> None:
                self.count_calls = []
                self.send_calls = 0

            def count_turn_input(self, **kwargs):
                self.count_calls.append(kwargs)
                store = kwargs["run_store"]
                request = store.write_evidence_json(
                    "transport/count-author-0001/request.json",
                    {"count_only": True},
                )
                count = store.write_evidence_json(
                    "transport/count-author-0001/input-token-count.json",
                    {"input_tokens": 200},
                )
                return TransportInputCountResult(
                    input_tokens=200,
                    requested_model=kwargs["model"],
                    reasoning_effort=kwargs["reasoning_effort"],
                    model_profile_sha256=kwargs["model_profile_sha256"],
                    maximum_output_tokens=kwargs["max_output_tokens"],
                    prompt_cache_policy=kwargs["prompt_cache_policy"].value,
                    request_evidence_path=request,
                    count_evidence_path=count,
                )

            def send_turn(self, **kwargs):
                self.send_calls += 1
                raise AssertionError("Count-only qualification must not generate a response")

            def close_owned_files(self, **kwargs):
                kwargs["run_store"].write_evidence_json(
                    "transport/provider-file-cleanup.json",
                    {"cleanup_complete": True, "remaining_provider_file_ids": []},
                )

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            initial = _bundle(root, "packet-base", "finding-base", "base")
            services = ServiceHarness(root, initial, [])
            case = self._case(root, initial)
            store = create_qualification_run_store(
                workspace_root=root / "workspace",
                run_id="qualification-count-only",
                case=case,
            )
            transport = CountOnlyTransport()
            count, receipt = count_qualification_author_input(
                case=case,
                bundle=initial,
                transport=transport,
                run_store=store,
                services=services.services(),
                pricing_policy=load_pricing_policy(),
            )
            self.assertEqual(count.transport_count.input_tokens, 200)
            self.assertTrue(receipt.within_case_budget)
            self.assertEqual(transport.send_calls, 0)
            self.assertEqual(len(transport.count_calls), 1)
            self.assertEqual(
                transport.count_calls[0]["model_profile_sha256"],
                case.model_profile.sha256,
            )
            self.assertFalse(
                any(event["event_type"] == "model_response" for event in store.read_events())
            )

    def test_case_rejects_stale_packet_binding_and_campaign_overrun(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            initial = _bundle(root, "packet-base", "finding-base", "base")
            case = self._case(root, initial)
            changed = _bundle(root, "packet-changed", "finding-base", "changed")
            with self.assertRaisesRegex(ValueError, "packet authority changed"):
                case.validate_bundle(changed)
            with self.assertRaisesRegex(ValueError, "campaign ceiling"):
                QualificationCaseV1(
                    **{
                        **case.__dict__,
                        "budgets": SessionBudgets(
                            maximum_proven_rounds=1,
                            maximum_model_responses=2,
                            maximum_calculated_cost_usd=Decimal("8.01"),
                        ),
                    }
                )

    def test_serialized_case_reloads_only_against_exact_current_authority(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            initial = _bundle(root, "packet-base", "finding-base", "base")
            case = self._case(root, initial)
            case_path = root / "case.json"
            case_path.write_text(
                json.dumps(case.identity_dict(), indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            with patch(
                "cuda_fractal_state_tool.model_qualification.load_existing_agent_bundle",
                return_value=initial,
            ):
                loaded = load_qualification_case(
                    case_path,
                    packet_dir=initial.packet_dir,
                    pricing_policy=load_pricing_policy(),
                )
            self.assertEqual(loaded.sha256, case.sha256)
            changed = _bundle(root, "packet-changed", "finding-base", "changed")
            with patch(
                "cuda_fractal_state_tool.model_qualification.load_existing_agent_bundle",
                return_value=changed,
            ):
                with self.assertRaisesRegex(ValueError, "identity or current authority"):
                    load_qualification_case(
                        case_path,
                        packet_dir=changed.packet_dir,
                        pricing_policy=load_pricing_policy(),
                    )


if __name__ == "__main__":
    unittest.main()
