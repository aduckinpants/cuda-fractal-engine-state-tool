from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from cuda_fractal_state_tool.agent_bundle import AgentBundle
from cuda_fractal_state_tool.research_context import (
    build_planner_context,
    build_review_context,
    build_synthesis_context,
    seal_prior_round_ledger,
    seal_communication_context,
)
from cuda_fractal_state_tool.research_protocol import ResearchBrief
from cuda_fractal_state_tool.research_run_store import ResearchRunStore
from cuda_fractal_state_tool.research_session import ResearchExecutionEvidence
from cuda_fractal_state_tool.research_protocol import ResearchAction
from cuda_fractal_state_tool.scientific_record import (
    ArtifactRoot,
    ArtifactRootRegistry,
    EvidenceReference,
    ScientificConclusion,
    ScientificRecord,
)


def _brief():
    return ResearchBrief.from_dict(
        {
            "question": "What changes?",
            "attention_context": "Inspect the circle.",
            "user_hypotheses": [],
            "experiment_permissions": {
                "domains": ["params"],
                "allowed_paths": ["params.epsilon"],
                "allow_scalar_sweep": True,
            },
            "fixed_conditions": {"notes": ["Keep the camera fixed."]},
            "useful_answer": {"kind": "bounded", "details": "Report evidence."},
            "maximum_experiment_rounds": 1,
            "communication_profile": "working_session",
            "hard_dollar_budget": "0",
        }
    )


def _bundle(root: Path) -> AgentBundle:
    packet = root / "packet"
    packet.mkdir()
    return AgentBundle(
        packet_version=8,
        packet_id="packet-1",
        packet_dir=packet,
        packet_path=packet / "packet.md",
        packet_sha256="1" * 64,
        manifest_path=packet / "manifest.json",
        manifest_sha256="2" * 64,
        finding_id="finding-1",
        selected_fractal_type="explaino_all",
        required_attachments=(),
        recommended_attachments=(),
        unavailable_optional_attachments=(),
    )


class ResearchContextTests(unittest.TestCase):
    def _store(self, root: Path):
        return ResearchRunStore.create(
            root / "workspace",
            run_id="run-1",
            protocol_snapshot={"schema": "question_research_protocol.v1"},
            initial_packet={"packet_id": "packet-1"},
            research_brief=_brief().to_dict(),
        )

    def test_review_context_is_fresh_compact_and_carries_exact_result(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            store = self._store(root)
            bundle = _bundle(root)
            attempt = store.run_dir / "attempts/001"
            attempt.mkdir()
            (attempt / "round-plan.json").write_text(
                '{"prediction":"grows","round_plan_canonicalization_version":1}\n',
                encoding="utf-8",
            )
            (attempt / "execution-ref.json").write_text('{"proof":{"status":"replay_proven"}}\n', encoding="utf-8")
            proof_dir = root / "proof"
            proof_dir.mkdir()
            receipt = proof_dir / "receipt.json"
            receipt.write_text('{"status":"replay_proven"}\n', encoding="utf-8")
            display = proof_dir / "candidate-display.png"
            display.write_bytes(b"png")
            evidence = ResearchExecutionEvidence(
                attempt_number=1,
                action=ResearchAction.SINGLE_OVERRIDE,
                round_plan_contract_sha256="3" * 64,
                proof=SimpleNamespace(
                    proof_id="proof-1",
                    status="replay_proven",
                    receipt_path=receipt,
                    candidate_display_path=display,
                ),
            )
            with patch(
                "cuda_fractal_state_tool.research_context.load_packet_active_color_pipeline_context",
                return_value={"active_chain_text": "Phase Orbit -> Phase Wheel"},
            ):
                context = build_review_context(
                    run_store=store,
                    brief=_brief(),
                    bundle=bundle,
                    evidence=evidence,
                )
            self.assertEqual(
                [item.role for item in context.resources],
                ["research_review_context", "state_override_proof_receipt", "proof_candidate_display"],
            )
            self.assertEqual(context.resources[-1].media_role, "vision")
            self.assertIn("fresh context", context.prompt)
            self.assertIn("RESEARCH_GATE: <GATE>", context.prompt)
            self.assertIn("with the colon present", context.prompt)
            self.assertIn("Return plain text only: no JSON object", context.prompt)
            self.assertIn("Selected result: none", context.prompt)
            self.assertIn("CENSORED_OUT_OF_FRAME", context.prompt)
            document = json.loads(context.context_path.read_text(encoding="utf-8"))
            self.assertEqual(
                document["round_plan_identity"]["round_plan_contract_sha256"],
                "3" * 64,
            )

    def test_planner_context_requires_literal_colon_bearing_action_header(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            bundle = _bundle(root)
            with patch(
                "cuda_fractal_state_tool.research_context.load_packet_active_color_pipeline_context",
                return_value={"active_chain_text": "Phase Orbit -> Phase Wheel"},
            ):
                context = build_planner_context(_brief(), bundle)
            self.assertIn("RESEARCH_ACTION: <ACTION>", context.prompt)
            self.assertIn("with the colon present", context.prompt)
            self.assertIn("Do not write `RESEARCH_ACTION <ACTION>`", context.prompt)

    def test_second_planner_receives_immutable_prior_round_ledger(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            store = self._store(root)
            bundle = _bundle(root)
            attempt = store.run_dir / "attempts/001"
            attempt.mkdir()
            (attempt / "round-plan.json").write_text(
                '{"action":"SCALAR_SWEEP","prediction":"grows"}\n',
                encoding="utf-8",
            )
            (attempt / "payload.json").write_text(
                '{"sweep_version":1,"axis":{"path":"params.epsilon",'
                '"values":[1e-7,1e-6,1e-5]},'
                '"member_failure_policy":"continue_independent"}\n',
                encoding="utf-8",
            )
            (attempt / "execution-ref.json").write_text(
                '{"sweep":{"sweep_id":"sweep-1"}}\n', encoding="utf-8"
            )
            (attempt / "review-decision.json").write_text(
                '{"gate":"CONTINUE_RETAIN_BASE",'
                '"next_action_class":"STATE_EXPERIMENT",'
                '"next_research_step":"refine locally"}\n',
                encoding="utf-8",
            )
            ledger_path = seal_prior_round_ledger(
                run_store=store,
                bundle=bundle,
                packet_lineage=[{"packet_id": bundle.packet_id}],
                attempts_consumed=1,
                maximum_experiment_rounds=2,
                spent_cost_usd="0.08",
                hard_budget_usd="0.30",
            )
            self.assertIsNotNone(ledger_path)
            ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
            self.assertEqual(
                ledger["tested_scalar_values"]["params.epsilon"],
                [1e-7, 1e-6, 1e-5],
            )
            self.assertEqual(ledger["attempts_remaining"], 1)
            with patch(
                "cuda_fractal_state_tool.research_context.load_packet_active_color_pipeline_context",
                return_value={"active_chain_text": "Phase Orbit -> Phase Wheel"},
            ):
                context = build_planner_context(
                    _brief(), bundle, prior_round_ledger_path=ledger_path
                )
            self.assertEqual(context.resources[0].role, "prior_round_ledger")
            self.assertIn("continuation, not a blind restart", context.prompt)
            self.assertIn("dense bracket", context.prompt)

    def test_synthesis_context_embeds_run_history_and_hash_bound_inventory(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            store = self._store(root)
            bundle = _bundle(root)
            attempt = store.run_dir / "attempts/001"
            attempt.mkdir()
            (attempt / "round-plan.json").write_text('{"prediction":"grows"}\n', encoding="utf-8")
            evidence_path = root / "evidence" / "receipt.json"
            evidence_path.parent.mkdir()
            evidence_path.write_text('{"status":"replay_proven"}\n', encoding="utf-8")
            root_id = "4" * 64
            artifact_root = ArtifactRoot("proof", evidence_path.parent, root_id)
            reference = EvidenceReference(
                artifact_role="proof_receipt",
                artifact_root="proof",
                root_identity=root_id,
                relative_path="receipt.json",
                sha256=hashlib.sha256(evidence_path.read_bytes()).hexdigest(),
                proof_id="proof-1",
                sweep_id=None,
                member_index=None,
            )
            with patch(
                "cuda_fractal_state_tool.research_context.load_packet_active_color_pipeline_context",
                return_value={"active_chain_text": "Phase Orbit -> Phase Wheel"},
            ):
                context = build_synthesis_context(
                    run_store=store,
                    brief=_brief(),
                    current_bundle=bundle,
                    packet_lineage=[{"packet_id": "packet-1"}],
                    evidence_references=(reference,),
                    roots=ArtifactRootRegistry((artifact_root,)),
                )
            document = json.loads(context.context_path.read_text(encoding="utf-8"))
            self.assertEqual(document["attempts"][0]["round_plan"]["prediction"], "grows")
            self.assertEqual(
                document["captured_active_color_pipeline"]["active_chain_text"],
                "Phase Orbit -> Phase Wheel",
            )
            self.assertEqual(len(context.resources), 2)
            self.assertEqual(context.resources[1].role, "proof_receipt")
            self.assertIn("answer is one", context.prompt)
            self.assertIn("unresolved_questions is an array of strings", context.prompt)
            self.assertIn("same path may appear more than once", context.prompt)
            self.assertIn("exactly `available` or `unavailable`", context.prompt)

    def test_communication_context_contains_only_sealed_science(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            store = self._store(root)
            value = {
                "scientific_record_version": 1,
                "source": {},
                "scientific_conclusion": "QUESTION_UNRESOLVED",
                "answer": "Unresolved.",
                "established_claims": [],
                "inferred_claims": [],
                "contradicted_claims": [],
                "unresolved_questions": ["More evidence is needed."],
                "experiment_summaries": [],
                "requested_canonical_emitted_values": [],
                "confidence_and_limitations": {
                    "confidence": "LOW",
                    "limitations": ["More evidence is needed."],
                },
                "best_next_experiment": None,
            }
            exact = json.dumps(value)
            record = ScientificRecord(
                exact_text=exact,
                sha256=hashlib.sha256(exact.encode()).hexdigest(),
                value=value,
                conclusion=ScientificConclusion.QUESTION_UNRESOLVED,
                established_claims=(),
                inferred_claims=(),
                contradicted_claims=(),
            )
            context = seal_communication_context(run_store=store, record=record)
            self.assertEqual(len(context.resources), 1)
            self.assertEqual(context.resources[0].role, "sealed_scientific_record")


if __name__ == "__main__":
    unittest.main()
