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


if __name__ == "__main__":
    unittest.main()
