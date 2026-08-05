from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from cuda_fractal_state_tool.agent_bundle import AgentBundle
from cuda_fractal_state_tool.research_results import (
    ResearchResultDisposition,
    ResearchResultService,
)
from cuda_fractal_state_tool.research_run_store import ResearchRunStore
from cuda_fractal_state_tool.scientific_record import ArtifactRoot, ArtifactRootRegistry


def _bundle(root: Path) -> AgentBundle:
    packet = root / "packet"
    packet.mkdir()
    return AgentBundle(
        8,
        "packet-1",
        packet,
        packet / "packet.md",
        "a" * 64,
        packet / "manifest.json",
        "b" * 64,
        "finding-1",
        "explaino_all",
        (),
        (),
        (),
    )


class ResearchResultServiceTests(unittest.TestCase):
    def _fixture(self, root: Path):
        store = ResearchRunStore.create(
            root / "workspace",
            run_id="run-1",
            protocol_snapshot={"schema": "question_research_protocol.v1"},
            initial_packet={"packet_id": "packet-1"},
            research_brief={"sealed": True},
        )
        evidence_root = root / "evidence"
        evidence_root.mkdir()
        evidence = evidence_root / "proof.json"
        evidence.write_text('{"status":"replay_proven"}\n', encoding="utf-8")
        root_id = "c" * 64
        reference = {
            "artifact_role": "proof_receipt",
            "artifact_root": "proof",
            "root_identity": root_id,
            "relative_path": "proof.json",
            "sha256": hashlib.sha256(evidence.read_bytes()).hexdigest(),
            "proof_id": "proof-1",
            "sweep_id": None,
            "member_index": None,
        }
        registry = ArtifactRootRegistry((ArtifactRoot("proof", evidence_root, root_id),))
        value = {
            "scientific_record_version": 1,
            "source": {
                "question_run_id": "run-1",
                "research_brief_sha256": "d" * 64,
                "current_packet_id": "packet-1",
                "current_packet_manifest_sha256": "b" * 64,
                "human_acceptance": False,
            },
            "scientific_conclusion": "ANSWER_ESTABLISHED",
            "answer": "The answer is bounded.",
            "established_claims": [
                {"claim_id": "bounded_answer", "text": "A result was established.", "evidence_references": [reference]}
            ],
            "inferred_claims": [],
            "contradicted_claims": [],
            "unresolved_questions": [],
            "experiment_summaries": [],
            "requested_canonical_emitted_values": [],
            "best_next_experiment": None,
        }
        response = "```json\n" + json.dumps(value) + "\n```"
        return store, registry, response, _bundle(root)

    def test_valid_synthesis_seals_science_and_deterministic_report(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store, registry, response, bundle = self._fixture(Path(temp_dir))
            result = ResearchResultService(store).seal_synthesis(
                response,
                roots=registry,
                research_brief_sha256="d" * 64,
                current_bundle=bundle,
            )
            self.assertEqual(result.disposition, ResearchResultDisposition.COMPLETED)
            self.assertTrue(result.working_report_path.is_file())
            self.assertIn("bounded_answer", result.working_report_path.read_text(encoding="utf-8"))

    def test_invalid_synthesis_has_no_retry_and_no_scientific_claims(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store, registry, _response, bundle = self._fixture(Path(temp_dir))
            result = ResearchResultService(store).seal_synthesis(
                "```json\n{}\n```",
                roots=registry,
                research_brief_sha256="d" * 64,
                current_bundle=bundle,
            )
            self.assertEqual(result.disposition, ResearchResultDisposition.MANUAL_REVIEW_REQUIRED)
            self.assertEqual(result.scientific_record.established_claims, ())
            failure = json.loads(
                (store.run_dir / "synthesis/validation-error.json").read_text(encoding="utf-8")
            )
            self.assertFalse(failure["provider_retry_authorized"])

    def test_failed_required_alternate_report_preserves_science(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store, registry, response, bundle = self._fixture(Path(temp_dir))
            service = ResearchResultService(store)
            result = service.seal_synthesis(
                response,
                roots=registry,
                research_brief_sha256="d" * 64,
                current_bundle=bundle,
            )
            report, disposition = service.seal_alternate_communication(
                "```json\n{}\n```",
                result=result,
                required_deliverable=True,
            )
            self.assertIsNone(report)
            self.assertEqual(disposition, ResearchResultDisposition.MANUAL_REVIEW_REQUIRED)
            self.assertTrue((store.run_dir / "result/scientific-record.json").is_file())
            self.assertTrue((store.run_dir / "result/working-session.md").is_file())

    def test_synthesis_transport_failure_closes_without_fabricated_claims(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store, _registry, _response, bundle = self._fixture(Path(temp_dir))
            result = ResearchResultService(store).seal_synthesis_failure(
                "provider unavailable",
                research_brief_sha256="d" * 64,
                current_bundle=bundle,
            )
            self.assertEqual(result.disposition, ResearchResultDisposition.MANUAL_REVIEW_REQUIRED)
            self.assertEqual(result.scientific_record.established_claims, ())
            self.assertIn(
                "No scientific conclusion",
                result.working_report_path.read_text(encoding="utf-8"),
            )


if __name__ == "__main__":
    unittest.main()
