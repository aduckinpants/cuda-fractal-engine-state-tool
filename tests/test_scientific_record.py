from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from cuda_fractal_state_tool.scientific_record import (
    ArtifactRoot,
    ArtifactRootRegistry,
    ScientificConclusion,
    communication_coverage_receipt,
    no_scientific_conclusion_record,
    parse_communication_report_response,
    parse_scientific_record_response,
    render_working_session_report,
)


def _sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


class ScientificRecordTests(unittest.TestCase):
    def _fixture(self, root: Path):
        run = root / "run"
        run.mkdir()
        evidence = b'{"status":"replay_proven"}\n'
        (run / "proof.json").write_bytes(evidence)
        root_id = "a" * 64
        registry = ArtifactRootRegistry((ArtifactRoot("question_run", run, root_id),))
        reference = {
            "artifact_role": "proof_receipt",
            "artifact_root": "question_run",
            "root_identity": root_id,
            "relative_path": "proof.json",
            "sha256": _sha(evidence),
            "proof_id": "proof-1",
            "sweep_id": None,
            "member_index": None,
        }
        record = {
            "scientific_record_version": 1,
            "source": {
                "question_run_id": "run-1",
                "research_brief_sha256": "b" * 64,
                "current_packet_id": "packet-1",
                "current_packet_manifest_sha256": "c" * 64,
                "human_acceptance": False,
            },
            "scientific_conclusion": "ANSWER_ESTABLISHED",
            "answer": "The bounded evidence supports the answer.",
            "established_claims": [
                {
                    "claim_id": "radius_growth",
                    "text": "The radius grew.",
                    "evidence_references": [reference],
                }
            ],
            "inferred_claims": [],
            "contradicted_claims": [],
            "unresolved_questions": [],
            "experiment_summaries": [],
            "requested_canonical_emitted_values": [],
            "best_next_experiment": None,
        }
        response = "```json\n" + json.dumps(record) + "\n```\n"
        return registry, record, response

    def _parse(self, registry, response):
        return parse_scientific_record_response(
            response,
            roots=registry,
            expected_question_run_id="run-1",
            expected_research_brief_sha256="b" * 64,
            expected_current_packet_id="packet-1",
            expected_current_packet_manifest_sha256="c" * 64,
        )

    def test_valid_record_resolves_hash_bound_evidence_and_renders(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            registry, _value, response = self._fixture(Path(temp_dir))
            record = self._parse(registry, response)
            self.assertEqual(record.conclusion, ScientificConclusion.ANSWER_ESTABLISHED)
            rendered = render_working_session_report(record)
            self.assertIn("radius_growth", rendered)
            self.assertIn(record.sha256, rendered)

    def test_stale_or_traversing_evidence_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            registry, value, _response = self._fixture(Path(temp_dir))
            value["established_claims"][0]["evidence_references"][0]["relative_path"] = "../proof.json"
            response = "```json\n" + json.dumps(value) + "\n```"
            with self.assertRaisesRegex(ValueError, "safe root-relative"):
                self._parse(registry, response)

    def test_duplicate_json_keys_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            registry, _value, _response = self._fixture(Path(temp_dir))
            with self.assertRaises(ValueError):
                self._parse(
                    registry,
                    '```json\n{"scientific_record_version":1,"scientific_record_version":1}\n```',
                )

    def test_no_conclusion_fallback_cannot_claim_science(self) -> None:
        value = no_scientific_conclusion_record(
            question_run_id="run-1",
            research_brief_sha256="b" * 64,
            current_packet_id="packet-1",
            current_packet_manifest_sha256="c" * 64,
            reason="Synthesis response was ungrounded.",
        )
        self.assertEqual(value["scientific_conclusion"], "NO_SCIENTIFIC_CONCLUSION")
        self.assertEqual(value["established_claims"], [])

    def test_alternate_report_requires_established_claim_coverage(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            registry, _value, response = self._fixture(Path(temp_dir))
            record = self._parse(registry, response)
            candidate = {
                "communication_report_version": 1,
                "profile": "adult_beginner_carl_sagan",
                "source_scientific_record_sha256": record.sha256,
                "covered_claim_ids": [],
                "report_markdown": "A friendly explanation.",
            }
            with self.assertRaisesRegex(ValueError, "coverage"):
                parse_communication_report_response(
                    "```json\n" + json.dumps(candidate) + "\n```",
                    record=record,
                )
            candidate["covered_claim_ids"] = ["radius_growth"]
            report = parse_communication_report_response(
                "```json\n" + json.dumps(candidate) + "\n```",
                record=record,
            )
            self.assertTrue(
                communication_coverage_receipt(report, record)["coverage_complete"]
            )


if __name__ == "__main__":
    unittest.main()
