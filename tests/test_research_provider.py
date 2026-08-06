from __future__ import annotations

import hashlib
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

from cuda_fractal_state_tool.model_profile import ModelProfileV1
from cuda_fractal_state_tool.openai_transport import (
    PacketV8ResponsesTransport,
    PromptCachePolicy,
    ProviderFile,
    ProviderResponse,
    ProviderTransportError,
    TransportCancelled,
    TransportResource,
)
from cuda_fractal_state_tool.pricing_policy import load_pricing_policy
from cuda_fractal_state_tool.research_cost import ResearchCostController, ResearchProviderStage
from cuda_fractal_state_tool.research_provider import ResearchProviderDispatcher
from cuda_fractal_state_tool.research_run_store import ResearchRunStore


class _Provider:
    def __init__(self) -> None:
        self.requests = []
        self.count_requests = []
        self.deleted = []
        self.generated = 0

    def upload_file(self, filename, payload):
        return ProviderFile(f"file-{filename}", filename)

    def count_input_tokens(self, request, *, timeout_seconds):
        self.count_requests.append(request)
        return 1_000

    def create_response(self, request, *, timeout_seconds):
        self.requests.append(request)
        self.generated += 1
        return ProviderResponse(
            id=f"response-{self.generated}",
            model="gpt-5.6-luna",
            status="completed",
            output_text="bounded response",
            usage={
                "input_tokens": 1_000,
                "cached_input_tokens": 0,
                "cache_write_tokens": 0,
                "output_tokens": 100,
            },
            raw={"id": f"response-{self.generated}"},
        )

    def delete_file(self, file_id):
        self.deleted.append(file_id)


class ResearchProviderDispatcherTests(unittest.TestCase):
    def _fixture(self, root: Path, budget: str):
        workspace = root / "workspace"
        store = ResearchRunStore.create(
            workspace,
            run_id="run-1",
            protocol_snapshot={"schema": "question_research_protocol.v1"},
            initial_packet={"packet_id": "packet-1"},
            research_brief={"sealed": True},
        )
        profile = ModelProfileV1(
            model="gpt-5.6-luna",
            reasoning_effort="high",
            pricing_tier="standard",
            prompt_cache_policy=PromptCachePolicy.EXPLICIT_NO_CACHE,
        )
        cost = ResearchCostController(
            pricing_policy=load_pricing_policy(),
            model_profile=profile,
            hard_budget_usd=Decimal(budget),
        )
        provider = _Provider()
        transport = PacketV8ResponsesTransport(provider)
        dispatcher = ResearchProviderDispatcher(
            transport=transport,
            run_store=store,
            cost=cost,
            model_profile=profile,
            minimum_generation_spacing_seconds=0,
        )
        payload = b'{"context":"exact"}\n'
        path = root / "context.json"
        path.write_bytes(payload)
        resource = TransportResource(
            filename="context.json",
            role="research_context",
            media_role="file",
            sha256=hashlib.sha256(payload).hexdigest(),
            size_bytes=len(payload),
            local_path=path,
            payload=payload,
        )
        return dispatcher, provider, transport, resource

    def test_every_stage_dispatch_is_a_fresh_provider_context(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            dispatcher, provider, transport, resource = self._fixture(Path(temp_dir), "10")
            dispatcher.dispatch(
                stage=ResearchProviderStage.REVIEW,
                turn_id="review-1",
                prompt="Review exact evidence.",
                packet_dir=None,
                additional_resources=(resource,),
            )
            dispatcher.dispatch(
                stage=ResearchProviderStage.SYNTHESIS,
                turn_id="synthesis-1",
                prompt="Synthesize exact evidence.",
                packet_dir=None,
                additional_resources=(resource,),
            )
            self.assertEqual(len(provider.requests), 2)
            self.assertTrue(all("previous_response_id" not in request for request in provider.requests))
            self.assertGreater(dispatcher.cost.spent_cost_usd, 0)
            transport.close_owned_files(run_store=dispatcher.run_store)

    def test_count_only_reports_exact_first_call_and_never_generates(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            dispatcher, provider, _transport, resource = self._fixture(Path(temp_dir), "0")
            gate = dispatcher.count_only(
                stage=ResearchProviderStage.PLANNER,
                turn_id="planner-count",
                prompt="Plan one experiment.",
                packet_dir=None,
                additional_resources=(resource,),
                planner_may_execute=True,
                correction_available=True,
                experiment_attempts_remaining=2,
            )
            self.assertEqual(gate.count.input_tokens, 1_000)
            self.assertFalse(gate.budget.authorized)
            self.assertEqual(provider.generated, 0)
            self.assertGreater(Decimal(gate.conservative_adaptive_ceiling_usd), 0)

    def test_completed_durable_response_is_recovered_without_new_provider_request(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            dispatcher, provider, _transport, resource = self._fixture(root, "10")
            first = dispatcher.dispatch(
                stage=ResearchProviderStage.SYNTHESIS,
                turn_id="synthesis-1",
                prompt="Synthesize exact evidence.",
                packet_dir=None,
                additional_resources=(resource,),
            )
            self.assertEqual(provider.generated, 1)

            recovered_dispatcher, recovered_provider, _transport, _resource = self._fixture(
                root / "second", "10"
            )
            recovered_dispatcher.run_store = dispatcher.run_store
            recovered = recovered_dispatcher.dispatch(
                stage=ResearchProviderStage.SYNTHESIS,
                turn_id="synthesis-1",
                prompt="This prompt must not be transmitted.",
                packet_dir=None,
            )

            self.assertEqual(recovered.response_id, first.response_id)
            self.assertEqual(recovered.output_text, first.output_text)
            self.assertEqual(recovered_provider.generated, 0)
            self.assertEqual(recovered_provider.requests, [])
            recovered_event = next(
                event
                for event in dispatcher.run_store.read_events()
                if event["event_type"] == "research_provider_response_recovered"
            )
            self.assertFalse(recovered_event["payload"]["provider_request_dispatched"])
            self.assertTrue(recovered_event["payload"]["durable_response_recovered"])
            self.assertNotIn("provider_redispatch", recovered_event["payload"])

    def test_negative_generation_spacing_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            dispatcher, _provider, transport, _resource = self._fixture(Path(temp_dir), "10")
            with self.assertRaisesRegex(ValueError, "spacing cannot be negative"):
                ResearchProviderDispatcher(
                    transport=transport,
                    run_store=dispatcher.run_store,
                    cost=dispatcher.cost,
                    model_profile=dispatcher.model_profile,
                    minimum_generation_spacing_seconds=-1,
                )

    def test_generation_spacing_is_cancellable_before_provider_dispatch(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            dispatcher, provider, _transport, resource = self._fixture(Path(temp_dir), "10")
            dispatcher.minimum_generation_spacing_seconds = 65
            dispatcher.dispatch(
                stage=ResearchProviderStage.REVIEW,
                turn_id="review-1",
                prompt="Review exact evidence.",
                packet_dir=None,
                additional_resources=(resource,),
            )
            cancellation_checks = 0

            def cancel_during_pacing() -> bool:
                nonlocal cancellation_checks
                cancellation_checks += 1
                return cancellation_checks >= 4

            dispatcher.cancelled = cancel_during_pacing

            with self.assertRaisesRegex(TransportCancelled, "pre-dispatch pacing"):
                dispatcher.dispatch(
                    stage=ResearchProviderStage.PLANNER,
                    turn_id="planner-2",
                    prompt="Plan a measured follow-up.",
                    packet_dir=None,
                    additional_resources=(resource,),
                )

            self.assertEqual(provider.generated, 1)
            self.assertEqual(len(provider.requests), 1)
            pacing = [
                event
                for event in dispatcher.run_store.read_events()
                if event["event_type"] == "research_provider_pacing"
            ]
            self.assertEqual(len(pacing), 1)
            self.assertEqual(pacing[0]["payload"]["turn_id"], "planner-2")
            self.assertFalse(pacing[0]["payload"]["provider_dispatch_started"])

    def test_incomplete_response_cost_is_recorded_and_redispatch_is_forbidden(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            dispatcher, provider, _transport, resource = self._fixture(Path(temp_dir), "10")

            def incomplete_response(request, *, timeout_seconds):
                provider.requests.append(request)
                provider.generated += 1
                return ProviderResponse(
                    id="response-incomplete",
                    model="gpt-5.6-luna",
                    status="incomplete",
                    output_text="partial",
                    usage={
                        "input_tokens": 1_000,
                        "cached_input_tokens": 0,
                        "cache_write_tokens": 0,
                        "output_tokens": 8_000,
                    },
                    raw={
                        "id": "response-incomplete",
                        "status": "incomplete",
                        "incomplete_details": {"reason": "max_output_tokens"},
                    },
                )

            provider.create_response = incomplete_response
            with self.assertRaises(ProviderTransportError):
                dispatcher.dispatch(
                    stage=ResearchProviderStage.SYNTHESIS,
                    turn_id="synthesis-incomplete",
                    prompt="Synthesize exact evidence.",
                    packet_dir=None,
                    additional_resources=(resource,),
                )
            self.assertGreater(dispatcher.cost.spent_cost_usd, 0)
            self.assertTrue(
                (
                    dispatcher.run_store.run_dir
                    / "cost/synthesis-incomplete-incomplete-actual.json"
                ).is_file()
            )
            self.assertTrue(
                any(
                    event["event_type"] == "research_provider_incomplete_response"
                    for event in dispatcher.run_store.read_events()
                )
            )
            with self.assertRaisesRegex(RuntimeError, "forbids redispatch"):
                dispatcher.dispatch(
                    stage=ResearchProviderStage.SYNTHESIS,
                    turn_id="synthesis-incomplete",
                    prompt="Do not resend.",
                    packet_dir=None,
                    additional_resources=(resource,),
                )
            self.assertEqual(provider.generated, 1)


if __name__ == "__main__":
    unittest.main()
