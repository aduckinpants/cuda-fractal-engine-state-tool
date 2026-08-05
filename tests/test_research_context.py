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
    build_review_context,
    build_synthesis_context,
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
            (attempt / "round-plan.json").write_text('{"prediction":"grows"}\n', encoding="utf-8")
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
                round_plan_sha256="3" * 64,
                proof=SimpleNamespace(
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
