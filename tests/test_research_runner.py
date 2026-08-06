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
from cuda_fractal_state_tool.research_protocol import ResearchAction, ResearchBrief
from cuda_fractal_state_tool.research_results import ResearchResultDisposition, ResearchResultService
from cuda_fractal_state_tool.research_run_store import ResearchRunStore
from cuda_fractal_state_tool.research_runner import ResearchSessionRunner
from cuda_fractal_state_tool.research_session import (
    ResearchExecutionEvidence,
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
    def test_sweep_proof_values_are_compacted_for_synthesis(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            workspace = root / "workspace"
            packet = root / "packet"
            proof_dir = root / "proof"
            packet.mkdir()
            proof_dir.mkdir()
            (packet / "packet.md").write_text("# Packet\n", encoding="utf-8")
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
            store = ResearchRunStore.create(
                workspace,
                run_id="run-values",
                protocol_snapshot={"schema": "question_research_protocol.v1"},
                initial_packet={
                    "packet_id": bundle.packet_id,
                    "manifest_sha256": bundle.manifest_sha256,
                    "finding_id": bundle.finding_id,
                },
                research_brief={},
            )
            receipt_path = proof_dir / "receipt.json"
            receipt_path.write_text(
                json.dumps(
                    {
                        "requested_value_receipts": [
                            {
                                "path": "params.epsilon",
                                "requested_value": 1e-8,
                                "engine_emitted_value": 9.99999993922529e-9,
                            }
                        ]
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            receipt_sha = hashlib.sha256(receipt_path.read_bytes()).hexdigest()
            proof = SimpleNamespace(
                proof_id="proof-1",
                receipt_path=receipt_path,
                receipt_sha256=receipt_sha,
            )
            second_receipt_path = proof_dir / "receipt-2.json"
            second_receipt_path.write_bytes(receipt_path.read_bytes())
            second_receipt_sha = hashlib.sha256(
                second_receipt_path.read_bytes()
            ).hexdigest()
            second_proof = SimpleNamespace(
                proof_id="proof-2",
                receipt_path=second_receipt_path,
                receipt_sha256=second_receipt_sha,
            )
            members = (
                SimpleNamespace(index=0, proof_result=proof),
                SimpleNamespace(index=1, proof_result=second_proof),
            )
            sweep = SimpleNamespace(sweep_id="sweep-1", members=members)
            controller = SimpleNamespace(
                run_store=store,
                execution_history=(SimpleNamespace(proof=None, sweep=sweep),),
            )
            provider = SimpleNamespace(run_store=store, transport=_Transport())
            runner = ResearchSessionRunner(
                controller=controller,
                provider=provider,
                results=ResearchResultService(store),
            )

            evidence_path = runner._seal_requested_value_evidence()
            self.assertIsNotNone(evidence_path)
            value = json.loads(evidence_path.read_text(encoding="utf-8"))
            self.assertEqual(len(value["requested_value_receipts"]), 1)
            receipt = value["requested_value_receipts"][0]
            self.assertEqual(receipt["requested_value"], 1e-8)
            self.assertEqual(receipt["engine_emitted_value"], 9.99999993922529e-9)
            self.assertEqual(receipt["canonical_value_status"], "unavailable")
            self.assertEqual(receipt["sources"][0]["proof_receipt_sha256"], receipt_sha)
            self.assertEqual(len(receipt["sources"]), 2)
            self.assertEqual(receipt["sources"][1]["proof_receipt_sha256"], second_receipt_sha)

    def test_authority_drift_is_a_terminal_execution_blocker(self) -> None:
        evidence = ResearchExecutionEvidence(
            attempt_number=1,
            action=ResearchAction.SCALAR_SWEEP,
            round_plan_sha256="a" * 64,
            sweep=SimpleNamespace(disposition="AUTHORITY_DRIFT"),
        )
        reason = ResearchSessionRunner._execution_blocker(evidence)
        self.assertIsNotNone(reason)
        self.assertIn("no review", reason)

        complete = ResearchExecutionEvidence(
            attempt_number=1,
            action=ResearchAction.SCALAR_SWEEP,
            round_plan_sha256="b" * 64,
            sweep=SimpleNamespace(disposition="COMPLETE"),
        )
        self.assertIsNone(ResearchSessionRunner._execution_blocker(complete))

    def test_authority_drift_skips_review_and_synthesis(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            packet = root / "packet"
            packet.mkdir()
            (packet / "packet.md").write_text("# Packet\n", encoding="utf-8")
            (packet / "manifest.json").write_text(
                '{"packet_version":8}\n', encoding="utf-8"
            )
            manifest_sha = hashlib.sha256(
                (packet / "manifest.json").read_bytes()
            ).hexdigest()
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
                    "question": "How does epsilon change the field?",
                    "attention_context": "Use exact evidence.",
                    "user_hypotheses": [],
                    "experiment_permissions": {
                        "domains": ["params"],
                        "allowed_paths": ["params.epsilon"],
                        "allow_scalar_sweep": True,
                    },
                    "fixed_conditions": {"notes": []},
                    "useful_answer": {"kind": "bounded", "details": "Report honestly."},
                    "maximum_experiment_rounds": 1,
                    "communication_profile": "working_session",
                    "hard_dollar_budget": "1",
                }
            )
            store = ResearchRunStore.create(
                root / "workspace",
                run_id="run-drift",
                protocol_snapshot={"schema": "question_research_protocol.v1"},
                initial_packet={
                    "packet_id": bundle.packet_id,
                    "manifest_sha256": bundle.manifest_sha256,
                    "finding_id": bundle.finding_id,
                },
                research_brief=brief.to_dict(),
            )
            sweep = SimpleNamespace(
                sweep_id="sweep-drift",
                disposition="AUTHORITY_DRIFT",
                members=(),
                web_review_dir=None,
            )
            services = ResearchRouteServices(
                validate_single=lambda *args: None,
                execute_single=lambda *args: None,
                validate_sweep=lambda *args: SimpleNamespace(),
                execute_sweep=lambda *args: sweep,
                promote=lambda *args: None,
            )
            controller = ResearchSessionController(
                brief=brief,
                run_store=store,
                initial_bundle=bundle,
                services=services,
            )

            class DriftProvider:
                def __init__(self):
                    self.run_store = store
                    self.transport = _Transport()
                    self.stages = []

                def dispatch(self, *, stage, **_kwargs):
                    self.stages.append(stage.value)
                    if stage.value != "planner":
                        raise AssertionError(stage)
                    return SimpleNamespace(
                        output_text="""RESEARCH_ACTION: SCALAR_SWEEP

Selected bracket: Vary epsilon across a bounded bracket.
Why this bracket: It tests one authorized scalar path.
Locked trend prediction: The visible boundary will move monotonically.
Observation channel: Compare the fixed-camera frames.
Disconfirmation condition: Non-monotone or absent movement.
Fixed-state and camera policy: Keep every other state path fixed.
Hostile self-review conclusion: Runtime drift invalidates continuation.

```json
{"sweep_version":1,"axis":{"path":"params.epsilon","values":[1e-7,5e-7,1e-6]},"member_failure_policy":"continue_independent"}
```
"""
                    )

            provider = DriftProvider()
            with patch(
                "cuda_fractal_state_tool.research_context.load_packet_active_color_pipeline_context",
                return_value={"active_chain_text": "Phase Orbit -> Phase Wheel"},
            ):
                result = ResearchSessionRunner(
                    controller=controller,
                    provider=provider,
                    results=ResearchResultService(store),
                ).run()
            self.assertEqual(provider.stages, ["planner"])
            self.assertEqual(result.controller_disposition, "AUTHORITY_DRIFT")
            self.assertEqual(
                result.disposition, ResearchResultDisposition.MANUAL_REVIEW_REQUIRED
            )
            self.assertTrue(provider.transport.closed)
            closeout = json.loads(
                (store.run_dir / "result/controller-closeout.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertFalse(closeout["provider_retry_authorized"])

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
