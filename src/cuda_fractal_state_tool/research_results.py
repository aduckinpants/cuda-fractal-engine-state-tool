from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from .agent_bundle import AgentBundle
from .research_run_store import ResearchRunStore
from .scientific_record import (
    ArtifactRootRegistry,
    CommunicationReport,
    ScientificConclusion,
    ScientificRecord,
    communication_coverage_receipt,
    no_scientific_conclusion_record,
    parse_communication_report_response,
    parse_scientific_record_response,
    render_working_session_report,
)


class ResearchResultDisposition(str, Enum):
    COMPLETED = "COMPLETED"
    MANUAL_REVIEW_REQUIRED = "MANUAL_REVIEW_REQUIRED"


@dataclass(frozen=True)
class SealedResearchResult:
    scientific_record: ScientificRecord
    disposition: ResearchResultDisposition
    working_report_path: Path
    synthesis_validation_error: str | None


def _json_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False)
        + "\n"
    ).encode("utf-8")


def _record_from_fallback(value: dict[str, Any]) -> ScientificRecord:
    payload = _json_bytes(value).decode("utf-8")
    return ScientificRecord(
        exact_text=payload,
        sha256=hashlib.sha256(payload.encode("utf-8")).hexdigest(),
        value=value,
        conclusion=ScientificConclusion.NO_SCIENTIFIC_CONCLUSION,
        established_claims=(),
        inferred_claims=(),
        contradicted_claims=(),
    )


class ResearchResultService:
    def __init__(self, run_store: ResearchRunStore) -> None:
        self.run_store = run_store

    def seal_synthesis(
        self,
        response_text: str,
        *,
        roots: ArtifactRootRegistry,
        research_brief_sha256: str,
        current_bundle: AgentBundle,
    ) -> SealedResearchResult:
        self.run_store.write_evidence_once_bytes(
            "synthesis/response.txt", response_text.encode("utf-8")
        )
        error: str | None = None
        try:
            record = parse_scientific_record_response(
                response_text,
                roots=roots,
                expected_question_run_id=self.run_store.run_dir.name,
                expected_research_brief_sha256=research_brief_sha256,
                expected_current_packet_id=current_bundle.packet_id,
                expected_current_packet_manifest_sha256=current_bundle.manifest_sha256,
            )
            disposition = ResearchResultDisposition.COMPLETED
            record_bytes = record.exact_text.encode("utf-8")
        except Exception as exc:
            error = str(exc)
            fallback = no_scientific_conclusion_record(
                question_run_id=self.run_store.run_dir.name,
                research_brief_sha256=research_brief_sha256,
                current_packet_id=current_bundle.packet_id,
                current_packet_manifest_sha256=current_bundle.manifest_sha256,
                reason=error,
            )
            record = _record_from_fallback(fallback)
            disposition = ResearchResultDisposition.MANUAL_REVIEW_REQUIRED
            record_bytes = record.exact_text.encode("utf-8")
            self.run_store.write_evidence_once_json(
                "synthesis/validation-error.json",
                {
                    "error": error,
                    "provider_retry_authorized": False,
                    "fallback_scientific_conclusion": "NO_SCIENTIFIC_CONCLUSION",
                },
            )
        self.run_store.write_evidence_once_bytes(
            "result/scientific-record.json", record_bytes
        )
        report = render_working_session_report(record).encode("utf-8")
        working_path = self.run_store.write_evidence_once_bytes(
            "result/working-session.md", report
        )
        self._write_disposition(
            disposition,
            record=record,
            communication_status="not_requested",
            error=error,
        )
        return SealedResearchResult(record, disposition, working_path, error)

    def seal_synthesis_failure(
        self,
        error: str,
        *,
        research_brief_sha256: str,
        current_bundle: AgentBundle,
    ) -> SealedResearchResult:
        fallback = no_scientific_conclusion_record(
            question_run_id=self.run_store.run_dir.name,
            research_brief_sha256=research_brief_sha256,
            current_packet_id=current_bundle.packet_id,
            current_packet_manifest_sha256=current_bundle.manifest_sha256,
            reason=error,
        )
        record = _record_from_fallback(fallback)
        self.run_store.write_evidence_once_json(
            "synthesis/validation-error.json",
            {
                "error": error,
                "provider_retry_authorized": False,
                "provider_response_available": False,
                "fallback_scientific_conclusion": "NO_SCIENTIFIC_CONCLUSION",
            },
        )
        self.run_store.write_evidence_once_bytes(
            "result/scientific-record.json", record.exact_text.encode("utf-8")
        )
        working_path = self.run_store.write_evidence_once_bytes(
            "result/working-session.md",
            render_working_session_report(record).encode("utf-8"),
        )
        disposition = ResearchResultDisposition.MANUAL_REVIEW_REQUIRED
        self._write_disposition(
            disposition,
            record=record,
            communication_status="not_requested",
            error=error,
        )
        return SealedResearchResult(record, disposition, working_path, error)

    def seal_alternate_communication(
        self,
        response_text: str,
        *,
        result: SealedResearchResult,
        required_deliverable: bool,
    ) -> tuple[CommunicationReport | None, ResearchResultDisposition]:
        self.run_store.write_evidence_once_bytes(
            "communication/response.txt", response_text.encode("utf-8")
        )
        try:
            report = parse_communication_report_response(
                response_text,
                record=result.scientific_record,
            )
        except Exception as exc:
            disposition = (
                ResearchResultDisposition.MANUAL_REVIEW_REQUIRED
                if required_deliverable
                else result.disposition
            )
            self.run_store.write_evidence_once_json(
                "communication/failure.json",
                {
                    "error": str(exc),
                    "provider_retry_authorized": False,
                    "scientific_record_remains_valid": True,
                    "working_session_report_remains_available": True,
                    "required_deliverable": required_deliverable,
                },
            )
            self._write_disposition(
                disposition,
                record=result.scientific_record,
                communication_status="failed",
                error=str(exc),
                replace=True,
            )
            return None, disposition

        appendix = [
            "",
            "## Claim coverage appendix",
            "",
        ]
        claims = (
            *result.scientific_record.established_claims,
            *result.scientific_record.inferred_claims,
            *result.scientific_record.contradicted_claims,
        )
        appendix.extend(f"- `{claim.claim_id}` — {claim.text}" for claim in claims)
        rendered = report.report_markdown.rstrip() + "\n" + "\n".join(appendix) + "\n"
        self.run_store.write_evidence_once_bytes(
            "result/adult-beginner-carl-sagan.md", rendered.encode("utf-8")
        )
        self.run_store.write_evidence_once_json(
            "communication/coverage.json",
            communication_coverage_receipt(report, result.scientific_record),
        )
        self._write_disposition(
            result.disposition,
            record=result.scientific_record,
            communication_status="complete",
            error=None,
            replace=True,
        )
        return report, result.disposition

    def seal_communication_failure(
        self,
        error: str,
        *,
        result: SealedResearchResult,
        required_deliverable: bool,
    ) -> ResearchResultDisposition:
        disposition = (
            ResearchResultDisposition.MANUAL_REVIEW_REQUIRED
            if required_deliverable
            else result.disposition
        )
        self.run_store.write_evidence_once_json(
            "communication/failure.json",
            {
                "error": error,
                "provider_retry_authorized": False,
                "provider_response_available": False,
                "scientific_record_remains_valid": True,
                "working_session_report_remains_available": True,
                "required_deliverable": required_deliverable,
            },
        )
        self._write_disposition(
            disposition,
            record=result.scientific_record,
            communication_status="failed",
            error=error,
            replace=True,
        )
        return disposition

    def _write_disposition(
        self,
        disposition: ResearchResultDisposition,
        *,
        record: ScientificRecord,
        communication_status: str,
        error: str | None,
        replace: bool = False,
    ) -> None:
        value = {
            "controller_disposition": disposition.value,
            "scientific_conclusion": record.conclusion.value,
            "scientific_record_sha256": record.sha256,
            "working_session_status": "rendered",
            "alternate_communication_status": communication_status,
            # Retained as a compatibility alias for the pre-repair result reader.
            "communication_status": communication_status,
            "error": error,
            "human_acceptance": False,
        }
        relative = "result/disposition.json"
        if replace:
            self.run_store.write_evidence_json(relative, value)
        else:
            self.run_store.write_evidence_once_json(relative, value)
