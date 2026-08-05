from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from cuda_fractal_state_tool.agent_bundle import AgentBundle
from cuda_fractal_state_tool.openai_transport import DispatchAuthorizationRejected
from cuda_fractal_state_tool.research_protocol import ResearchBrief
from cuda_fractal_state_tool.research_results import ResearchResultDisposition, ResearchResultService
from cuda_fractal_state_tool.research_run_store import ResearchRunStore
from cuda_fractal_state_tool.research_runner import ResearchSessionRunner
from cuda_fractal_state_tool.research_session import (
    ResearchRouteServices,
    ResearchSessionController,
    ResearchSessionState,
)


class _Transport:
    def __init__(self) -> None:
        self.closed = False

    def close_owned_files(self, **kwargs):
        self.closed = True


class _Provider:
    def __init__(self) -> None:
        self.run_store = None
        self.transport = _Transport()
        self.stages = []

    def dispatch(self, *, stage, additional_resources=(), **kwargs):
        self.stages.append(stage.value)
        if stage.value == "planner":
            return SimpleNamespace(
                output_text="""RESEARCH_ACTION: ANSWER_READY

Proposed answer: The packet already supports a bounded answer.
Evidence basis: The exact packet state and engine context.
Uncertainty: No causal experiment was run.
Hostile self-review conclusion: Synthesis must ground any claim in packet evidence.
"""
            )
        if stage.value == "synthesis":
            context_resource = next(
                item for item in additional_resources if item.role == "research_synthesis_context"
            )
            context = json.loads(context_resource.payload.decode("utf-8"))
            reference = context["allowed_evidence_references"][0]
            value = {
                "scientific_record_version": 1,
                "source": {
                    "question_run_id": context["question_run_id"],
                    "research_brief_sha256": context["research_brief_sha256"],
                    "current_packet_id": context["current_research_base"]["packet_id"],
                    "current_packet_manifest_sha256": context["current_research_base"]["manifest_sha256"],
                    "human_acceptance": False,
                },
                "scientific_conclusion": "ANSWER_PARTIAL",
                "answer": "The packet supports a bounded provisional answer.",
                "established_claims": [
                    {
                        "claim_id": "packet_fact",
                        "text": "The exact packet is the current research base.",
                        "evidence_references": [reference],
                    }
                ],
                "inferred_claims": [],
                "contradicted_claims": [],
                "unresolved_questions": ["No causal experiment was run."],
                "experiment_summaries": [],
                "requested_canonical_emitted_values": [],
                "best_next_experiment": None,
            }
            return SimpleNamespace(output_text="```json\n" + json.dumps(value) + "\n```")
        raise AssertionError(stage)


class ResearchSessionRunnerTests(unittest.TestCase):
    def test_answer_ready_routes_through_fresh_synthesis_and_cleanup(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            packet = root / "packet"
            packet.mkdir()
            (packet / "packet.md").write_text("# Packet\n", encoding="utf-8")
            (packet / "state.json").write_text('{"fractal_type":"explaino_all"}\n', encoding="utf-8")
            (packet / "manifest.json").write_text('{"packet_version":8}\n', encoding="utf-8")
            manifest_sha = hashlib.sha256((packet / "manifest.json").read_bytes()).hexdigest()
            bundle = AgentBundle(
                8,
                "packet-1",
                packet,
                packet / "packet.md",
                hashlib.sha256((packet / "packet.md").read_bytes()).hexdigest(),
                packet / "manifest.json",
                manifest_sha,
                "finding-1",
                "explaino_all",
                (),
                (),
                (),
            )
            brief = ResearchBrief.from_dict(
                {
                    "question": "What is present?",
                    "attention_context": "Use the packet.",
                    "user_hypotheses": [],
                    "experiment_permissions": {
                        "domains": [],
                        "allowed_paths": [],
                        "allow_scalar_sweep": False,
                    },
                    "fixed_conditions": {"notes": []},
                    "useful_answer": {"kind": "bounded", "details": "Report facts."},
                    "maximum_experiment_rounds": 0,
                    "communication_profile": "working_session",
                    "hard_dollar_budget": "1",
                }
            )
            store = ResearchRunStore.create(
                root / "workspace",
                run_id="run-1",
                protocol_snapshot={"schema": "question_research_protocol.v1"},
                initial_packet={
                    "packet_id": bundle.packet_id,
                    "manifest_sha256": bundle.manifest_sha256,
                    "finding_id": bundle.finding_id,
                },
                research_brief=brief.to_dict(),
            )
            services = ResearchRouteServices(
                validate_single=lambda *args: None,
                execute_single=lambda *args: None,
                validate_sweep=lambda *args: None,
                execute_sweep=lambda *args: None,
                promote=lambda *args: None,
            )
            controller = ResearchSessionController(
                brief=brief,
                run_store=store,
                initial_bundle=bundle,
                services=services,
            )
            provider = _Provider()
            provider.run_store = store
            with patch(
                "cuda_fractal_state_tool.research_context.load_packet_active_color_pipeline_context",
                return_value={"active_chain_text": "Phase Orbit -> Phase Wheel"},
            ):
                result = ResearchSessionRunner(
                    controller=controller,
                    provider=provider,
                    results=ResearchResultService(store),
                ).run()
            self.assertEqual(result.disposition, ResearchResultDisposition.COMPLETED)
            self.assertEqual(provider.stages, ["planner", "synthesis"])
            self.assertEqual(result.attempts_consumed, 0)
            self.assertEqual(result.controller_disposition, "COMPLETED")
            self.assertTrue(provider.transport.closed)
            self.assertTrue((store.run_dir / "result/working-session.md").is_file())

    def test_budget_refusal_closes_without_experiment_or_provider_retry(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            packet = root / "packet"
            packet.mkdir()
            (packet / "packet.md").write_text("# Packet\n", encoding="utf-8")
            (packet / "manifest.json").write_text('{"packet_version":8}\n', encoding="utf-8")
            manifest_sha = hashlib.sha256((packet / "manifest.json").read_bytes()).hexdigest()
            bundle = AgentBundle(
                8, "packet-1", packet, packet / "packet.md",
                hashlib.sha256((packet / "packet.md").read_bytes()).hexdigest(),
                packet / "manifest.json", manifest_sha, "finding-1", "explaino_all",
                (), (), (),
            )
            brief = ResearchBrief.from_dict(
                {
                    "question": "What changes?",
                    "attention_context": "Use exact evidence.",
                    "user_hypotheses": [],
                    "experiment_permissions": {
                        "domains": [], "allowed_paths": [], "allow_scalar_sweep": False,
                    },
                    "fixed_conditions": {"notes": []},
                    "useful_answer": {"kind": "bounded", "details": "Report honestly."},
                    "maximum_experiment_rounds": 0,
                    "communication_profile": "working_session",
                    "hard_dollar_budget": "0",
                }
            )
            store = ResearchRunStore.create(
                root / "workspace",
                run_id="run-budget",
                protocol_snapshot={"schema": "question_research_protocol.v1"},
                initial_packet={
                    "packet_id": bundle.packet_id,
                    "manifest_sha256": bundle.manifest_sha256,
                    "finding_id": bundle.finding_id,
                },
                research_brief=brief.to_dict(),
            )
            controller = SimpleNamespace(
                brief=brief,
                run_store=store,
                current_bundle=bundle,
                state=ResearchSessionState.PLANNING,
                attempts_consumed=0,
                correction_used=False,
                execution_history=[],
            )

            class BudgetProvider:
                def __init__(self):
                    self.run_store = store
                    self.transport = _Transport()
                    self.calls = 0

                def dispatch(self, **_kwargs):
                    self.calls += 1
                    raise DispatchAuthorizationRejected("insufficient exact budget")

            provider = BudgetProvider()
            with patch(
                "cuda_fractal_state_tool.research_runner.build_planner_context",
                return_value=SimpleNamespace(prompt="planner", resources=()),
            ):
                result = ResearchSessionRunner(
                    controller=controller,
                    provider=provider,
                    results=ResearchResultService(store),
                ).run()
            self.assertEqual(provider.calls, 1)
            self.assertEqual(result.attempts_consumed, 0)
            self.assertEqual(result.controller_disposition, "BUDGET_EXHAUSTED")
            self.assertEqual(result.disposition, ResearchResultDisposition.MANUAL_REVIEW_REQUIRED)
            self.assertTrue(provider.transport.closed)
            closeout = json.loads(
                (store.run_dir / "result/controller-closeout.json").read_text(encoding="utf-8")
            )
            self.assertEqual(closeout["controller_disposition"], "BUDGET_EXHAUSTED")
            self.assertFalse(closeout["provider_retry_authorized"])


if __name__ == "__main__":
    unittest.main()
