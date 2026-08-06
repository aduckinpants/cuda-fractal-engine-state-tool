from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path, PurePosixPath
from typing import Any

from .json_utils import loads_strict_no_duplicates
from .runtime_surface import sha256_file


SCIENTIFIC_RECORD_VERSION = 1
COMMUNICATION_REPORT_VERSION = 1
SUPPORTED_ARTIFACT_ROOTS = frozenset(
    {
        "question_run",
        "state_tool_workspace",
        "finding",
        "packet",
        "proof",
        "sweep",
        "engine_capture",
    }
)
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_CLAIM_ID = re.compile(r"^[a-z][a-z0-9_-]{0,63}$")
_JSON_FENCE = re.compile(r"```([^\r\n`]*)\r?\n(.*?)```", re.DOTALL)


class ScientificConclusion(str, Enum):
    ANSWER_ESTABLISHED = "ANSWER_ESTABLISHED"
    ANSWER_PARTIAL = "ANSWER_PARTIAL"
    QUESTION_UNRESOLVED = "QUESTION_UNRESOLVED"
    CONTRADICTED = "CONTRADICTED"
    NO_SCIENTIFIC_CONCLUSION = "NO_SCIENTIFIC_CONCLUSION"


@dataclass(frozen=True)
class ArtifactRoot:
    name: str
    path: Path
    identity: str


class ArtifactRootRegistry:
    def __init__(self, roots: tuple[ArtifactRoot, ...]) -> None:
        if not roots:
            raise ValueError("Artifact roots must be non-empty")
        self._roots: dict[tuple[str, str], ArtifactRoot] = {}
        for root in roots:
            if root.name not in SUPPORTED_ARTIFACT_ROOTS:
                raise ValueError(f"Unsupported artifact root: {root.name}")
            if not _SHA256.fullmatch(root.identity):
                raise ValueError(f"Artifact root identity is not a SHA-256: {root.name}")
            path = root.path.resolve()
            if not path.is_dir():
                raise ValueError(f"Artifact root directory is unavailable: {path}")
            key = (root.name, root.identity)
            if key in self._roots:
                raise ValueError("Artifact root name and identity pairs must be unique")
            self._roots[key] = ArtifactRoot(root.name, path, root.identity)

    def resolve_and_verify(self, reference: "EvidenceReference") -> Path:
        root = self._roots.get((reference.artifact_root, reference.root_identity))
        if root is None:
            raise ValueError(
                "Evidence reference uses an unregistered or stale root identity: "
                f"{reference.artifact_root}"
            )
        relative = PurePosixPath(reference.relative_path)
        if (
            relative.is_absolute()
            or not relative.parts
            or any(part in {"", ".", ".."} for part in relative.parts)
            or "\\" in reference.relative_path
        ):
            raise ValueError("Evidence reference path must be safe root-relative POSIX text")
        resolved = root.path.joinpath(*relative.parts).resolve()
        if not resolved.is_relative_to(root.path) or not resolved.is_file():
            raise ValueError(f"Evidence reference is missing or escapes its root: {reference.relative_path}")
        if sha256_file(resolved) != reference.sha256:
            raise ValueError(f"Evidence reference hash mismatch: {reference.relative_path}")
        return resolved


def make_evidence_reference(
    *,
    root: ArtifactRoot,
    path: Path,
    artifact_role: str,
    proof_id: str | None = None,
    sweep_id: str | None = None,
    member_index: int | None = None,
) -> EvidenceReference:
    root_path = root.path.resolve()
    exact = path.resolve()
    if not exact.is_file() or not exact.is_relative_to(root_path):
        raise ValueError("Evidence artifact is not a file beneath its declared root")
    relative = exact.relative_to(root_path).as_posix()
    reference = EvidenceReference(
        artifact_role=artifact_role,
        artifact_root=root.name,
        root_identity=root.identity,
        relative_path=relative,
        sha256=sha256_file(exact),
        proof_id=proof_id,
        sweep_id=sweep_id,
        member_index=member_index,
    )
    ArtifactRootRegistry((root,)).resolve_and_verify(reference)
    return reference


@dataclass(frozen=True)
class EvidenceReference:
    artifact_role: str
    artifact_root: str
    root_identity: str
    relative_path: str
    sha256: str
    proof_id: str | None
    sweep_id: str | None
    member_index: int | None

    @classmethod
    def from_dict(cls, value: Any) -> "EvidenceReference":
        expected = {
            "artifact_role",
            "artifact_root",
            "root_identity",
            "relative_path",
            "sha256",
            "proof_id",
            "sweep_id",
            "member_index",
        }
        if not isinstance(value, dict) or set(value) != expected:
            raise ValueError("Evidence reference has an invalid shape")
        for key in ("artifact_role", "artifact_root", "root_identity", "relative_path", "sha256"):
            if not isinstance(value[key], str) or not value[key]:
                raise ValueError(f"Evidence reference {key} is required")
        if value["artifact_root"] not in SUPPORTED_ARTIFACT_ROOTS:
            raise ValueError("Evidence reference uses an unsupported root")
        if not _SHA256.fullmatch(value["root_identity"]) or not _SHA256.fullmatch(value["sha256"]):
            raise ValueError("Evidence reference identities must be lowercase SHA-256 values")
        for key in ("proof_id", "sweep_id"):
            if value[key] is not None and (not isinstance(value[key], str) or not value[key]):
                raise ValueError(f"Evidence reference {key} must be null or non-empty text")
        member = value["member_index"]
        if member is not None and (isinstance(member, bool) or not isinstance(member, int) or member < 0):
            raise ValueError("Evidence reference member_index must be null or non-negative")
        return cls(**value)

    def to_dict(self) -> dict[str, Any]:
        return {
            "artifact_role": self.artifact_role,
            "artifact_root": self.artifact_root,
            "root_identity": self.root_identity,
            "relative_path": self.relative_path,
            "sha256": self.sha256,
            "proof_id": self.proof_id,
            "sweep_id": self.sweep_id,
            "member_index": self.member_index,
        }


@dataclass(frozen=True)
class ScientificClaim:
    claim_id: str
    text: str
    evidence_references: tuple[EvidenceReference, ...]


@dataclass(frozen=True)
class ScientificRecord:
    exact_text: str
    sha256: str
    value: dict[str, Any]
    conclusion: ScientificConclusion
    established_claims: tuple[ScientificClaim, ...]
    inferred_claims: tuple[ScientificClaim, ...]
    contradicted_claims: tuple[ScientificClaim, ...]


def _one_json_document(response_text: str, *, label: str) -> tuple[str, dict[str, Any]]:
    fences = _JSON_FENCE.findall(response_text)
    if len(fences) != 1 or response_text.count("```") != 2:
        raise ValueError(f"{label} must contain exactly one fenced JSON block")
    language, payload = fences[0]
    if language.strip().lower() != "json":
        raise ValueError(f"{label} fenced block must use the json language tag")
    if (
        response_text[: response_text.find("```")].strip()
        or response_text[response_text.rfind("```") + 3 :].strip()
    ):
        raise ValueError(f"{label} must not contain prose outside its JSON block")
    parsed = loads_strict_no_duplicates(payload)
    if not isinstance(parsed, dict):
        raise ValueError(f"{label} JSON must be an object")
    return payload, parsed


def _text(value: Any, label: str, *, nullable: bool = False) -> str | None:
    if nullable and value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be non-empty text")
    return value.strip()


def _string_array(value: Any, label: str) -> tuple[str, ...]:
    if not isinstance(value, list) or any(
        not isinstance(item, str) or not item.strip() for item in value
    ):
        raise ValueError(f"{label} must be an array of non-empty strings")
    return tuple(item.strip() for item in value)


def _claims(
    value: Any,
    label: str,
    roots: ArtifactRootRegistry,
) -> tuple[ScientificClaim, ...]:
    if not isinstance(value, list):
        raise ValueError(f"{label} must be an array")
    claims: list[ScientificClaim] = []
    for item in value:
        if not isinstance(item, dict) or set(item) != {
            "claim_id",
            "text",
            "evidence_references",
        }:
            raise ValueError(f"{label} contains an invalid claim")
        claim_id = item["claim_id"]
        text = item["text"]
        if not isinstance(claim_id, str) or not _CLAIM_ID.fullmatch(claim_id):
            raise ValueError(f"{label} contains an invalid claim_id")
        if not isinstance(text, str) or not text.strip():
            raise ValueError(f"{label} contains empty claim text")
        refs_raw = item["evidence_references"]
        if not isinstance(refs_raw, list) or not refs_raw:
            raise ValueError(f"{label} claims require at least one evidence reference")
        refs = tuple(EvidenceReference.from_dict(ref) for ref in refs_raw)
        for ref in refs:
            roots.resolve_and_verify(ref)
        claims.append(ScientificClaim(claim_id, text.strip(), refs))
    return tuple(claims)


def _reference_array(
    value: Any,
    label: str,
    roots: ArtifactRootRegistry,
) -> tuple[EvidenceReference, ...]:
    if not isinstance(value, list) or not value:
        raise ValueError(f"{label} requires at least one evidence reference")
    references = tuple(EvidenceReference.from_dict(item) for item in value)
    for reference in references:
        roots.resolve_and_verify(reference)
    return references


def _validate_experiment_summaries(value: Any, roots: ArtifactRootRegistry) -> None:
    if not isinstance(value, list):
        raise ValueError("experiment_summaries must be an array")
    seen: set[int] = set()
    for item in value:
        if not isinstance(item, dict) or set(item) != {
            "attempt_number",
            "action",
            "prediction",
            "prediction_outcome",
            "evidence_references",
        }:
            raise ValueError("experiment_summaries contains an invalid item")
        attempt = item["attempt_number"]
        if isinstance(attempt, bool) or not isinstance(attempt, int) or attempt < 1 or attempt > 2:
            raise ValueError("experiment_summaries attempt_number must be one or two")
        if attempt in seen:
            raise ValueError("experiment_summaries attempt numbers must be unique")
        seen.add(attempt)
        for key in ("action", "prediction", "prediction_outcome"):
            _text(item[key], f"experiment_summaries.{key}")
        _reference_array(item["evidence_references"], "experiment_summaries", roots)


def _validate_value_receipts(value: Any, roots: ArtifactRootRegistry) -> None:
    if not isinstance(value, list):
        raise ValueError("requested_canonical_emitted_values must be an array")
    seen: set[str] = set()
    for item in value:
        if not isinstance(item, dict) or set(item) != {
            "path",
            "requested_value",
            "canonical_value_status",
            "canonical_value",
            "emitted_value",
            "evidence_references",
        }:
            raise ValueError("requested_canonical_emitted_values contains an invalid item")
        path = item["path"]
        if not isinstance(path, str) or not path:
            raise ValueError("requested/canonical/emitted paths must be non-empty text")
        identity = json.dumps(
            {
                "path": path,
                "requested_value": item["requested_value"],
                "canonical_value_status": item["canonical_value_status"],
                "canonical_value": item["canonical_value"],
                "emitted_value": item["emitted_value"],
            },
            sort_keys=True,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
        )
        if identity in seen:
            raise ValueError("requested/canonical/emitted values contain a duplicate item")
        seen.add(identity)
        status = item["canonical_value_status"]
        if status not in {"available", "unavailable"}:
            raise ValueError("canonical_value_status must be available or unavailable")
        if status == "unavailable" and item["canonical_value"] is not None:
            raise ValueError("Unavailable canonical values must be null")
        if status == "available" and item["canonical_value"] is None:
            raise ValueError("Available canonical values must be present")
        references = _reference_array(
            item["evidence_references"],
            "requested_canonical_emitted_values",
            roots,
        )
        matching_receipts: list[dict[str, Any]] = []
        for reference in references:
            path_ref = roots.resolve_and_verify(reference)
            if path_ref.suffix.lower() != ".json":
                continue
            try:
                document = loads_strict_no_duplicates(path_ref.read_text(encoding="utf-8"))
            except (OSError, UnicodeError, ValueError):
                continue
            if not isinstance(document, dict):
                continue
            receipts = document.get("requested_value_receipts")
            if isinstance(receipts, dict):
                receipts = [receipts]
            if isinstance(receipts, list):
                matching_receipts.extend(
                    receipt
                    for receipt in receipts
                    if isinstance(receipt, dict) and receipt.get("path") == path
                )
        if not any(
            receipt.get("requested_value") == item["requested_value"]
            and receipt.get("engine_emitted_value") == item["emitted_value"]
            for receipt in matching_receipts
        ):
            raise ValueError(
                f"Requested/emitted values have no matching existing proof receipt: {path}"
            )
        if status == "available" and not any(
            "canonical_value" in receipt
            and receipt["canonical_value"] == item["canonical_value"]
            for receipt in matching_receipts
        ):
            raise ValueError(
                f"Canonical value is not available from an existing receipt: {path}"
            )


def parse_scientific_record_response(
    response_text: str,
    *,
    roots: ArtifactRootRegistry,
    expected_question_run_id: str,
    expected_research_brief_sha256: str,
    expected_current_packet_id: str,
    expected_current_packet_manifest_sha256: str,
) -> ScientificRecord:
    payload, value = _one_json_document(response_text, label="Scientific-record response")
    expected = {
        "scientific_record_version",
        "source",
        "scientific_conclusion",
        "answer",
        "established_claims",
        "inferred_claims",
        "contradicted_claims",
        "unresolved_questions",
        "experiment_summaries",
        "requested_canonical_emitted_values",
        "best_next_experiment",
    }
    if set(value) != expected or value["scientific_record_version"] != SCIENTIFIC_RECORD_VERSION:
        raise ValueError("Scientific record fields or version are invalid")
    source = value["source"]
    source_expected = {
        "question_run_id",
        "research_brief_sha256",
        "current_packet_id",
        "current_packet_manifest_sha256",
        "human_acceptance",
    }
    if not isinstance(source, dict) or set(source) != source_expected:
        raise ValueError("Scientific record source has an invalid shape")
    if source != {
        "question_run_id": expected_question_run_id,
        "research_brief_sha256": expected_research_brief_sha256,
        "current_packet_id": expected_current_packet_id,
        "current_packet_manifest_sha256": expected_current_packet_manifest_sha256,
        "human_acceptance": False,
    }:
        raise ValueError("Scientific record source disagrees with current run authority")
    try:
        conclusion = ScientificConclusion(value["scientific_conclusion"])
    except (TypeError, ValueError) as exc:
        raise ValueError("Scientific record conclusion is unsupported") from exc
    _text(value["answer"], "Scientific record answer")
    established = _claims(value["established_claims"], "established_claims", roots)
    inferred = _claims(value["inferred_claims"], "inferred_claims", roots)
    contradicted = _claims(value["contradicted_claims"], "contradicted_claims", roots)
    all_claims = (*established, *inferred, *contradicted)
    claim_ids = [claim.claim_id for claim in all_claims]
    if len(claim_ids) != len(set(claim_ids)):
        raise ValueError("Scientific record claim IDs must be globally unique")
    _string_array(value["unresolved_questions"], "unresolved_questions")
    _validate_experiment_summaries(value["experiment_summaries"], roots)
    _validate_value_receipts(value["requested_canonical_emitted_values"], roots)
    _text(value["best_next_experiment"], "best_next_experiment", nullable=True)
    if conclusion is ScientificConclusion.CONTRADICTED and not contradicted:
        raise ValueError("CONTRADICTED requires a contradicted principal claim")
    if conclusion is ScientificConclusion.NO_SCIENTIFIC_CONCLUSION and all_claims:
        raise ValueError("NO_SCIENTIFIC_CONCLUSION cannot assert scientific claims")
    return ScientificRecord(
        exact_text=payload,
        sha256=hashlib.sha256(payload.encode("utf-8")).hexdigest(),
        value=value,
        conclusion=conclusion,
        established_claims=established,
        inferred_claims=inferred,
        contradicted_claims=contradicted,
    )


def no_scientific_conclusion_record(
    *,
    question_run_id: str,
    research_brief_sha256: str,
    current_packet_id: str,
    current_packet_manifest_sha256: str,
    reason: str,
) -> dict[str, Any]:
    return {
        "scientific_record_version": SCIENTIFIC_RECORD_VERSION,
        "source": {
            "question_run_id": question_run_id,
            "research_brief_sha256": research_brief_sha256,
            "current_packet_id": current_packet_id,
            "current_packet_manifest_sha256": current_packet_manifest_sha256,
            "human_acceptance": False,
        },
        "scientific_conclusion": ScientificConclusion.NO_SCIENTIFIC_CONCLUSION.value,
        "answer": "No scientific conclusion was sealed because final synthesis failed validation.",
        "established_claims": [],
        "inferred_claims": [],
        "contradicted_claims": [],
        "unresolved_questions": [reason],
        "experiment_summaries": [],
        "requested_canonical_emitted_values": [],
        "best_next_experiment": None,
    }


def render_working_session_report(record: ScientificRecord) -> str:
    value = record.value
    lines = [
        "# Research Session Result",
        "",
        f"Conclusion: `{record.conclusion.value}`",
        "",
        "## Answer",
        "",
        value["answer"],
    ]
    sections = (
        ("Established claims", record.established_claims),
        ("Inferences", record.inferred_claims),
        ("Contradicted claims", record.contradicted_claims),
    )
    for title, claims in sections:
        lines.extend(["", f"## {title}", ""])
        if claims:
            lines.extend(f"- `{claim.claim_id}` — {claim.text}" for claim in claims)
        else:
            lines.append("- None.")
    lines.extend(["", "## Unresolved questions", ""])
    unresolved = value["unresolved_questions"]
    if unresolved:
        lines.extend(f"- {item}" for item in unresolved)
    else:
        lines.append("- None.")
    lines.extend(["", "## Experiments", ""])
    experiments = value["experiment_summaries"]
    if experiments:
        for experiment in experiments:
            lines.extend(
                [
                    f"### Attempt {experiment['attempt_number']} — {experiment['action']}",
                    "",
                    f"- Locked prediction: {experiment['prediction']}",
                    f"- Outcome: {experiment['prediction_outcome']}",
                ]
            )
    else:
        lines.append("- No local experiment was executed.")
    lines.extend(["", "## Requested, canonical, and emitted values", ""])
    receipts = value["requested_canonical_emitted_values"]
    if receipts:
        lines.extend(
            [
                "| Path | Requested | Canonical | Emitted |",
                "|---|---|---|---|",
            ]
        )
        for receipt in receipts:
            canonical = (
                json.dumps(receipt["canonical_value"], ensure_ascii=False)
                if receipt["canonical_value_status"] == "available"
                else "unavailable"
            )
            lines.append(
                "| `{}` | `{}` | `{}` | `{}` |".format(
                    receipt["path"],
                    json.dumps(receipt["requested_value"], ensure_ascii=False),
                    canonical,
                    json.dumps(receipt["emitted_value"], ensure_ascii=False),
                )
            )
    else:
        lines.append("- No value-change receipt was sealed.")
    lines.extend(["", "## Best next experiment", ""])
    lines.append(value["best_next_experiment"] or "None required by the sealed record.")
    lines.extend(
        [
            "",
            "## Authority boundary",
            "",
            "This report is derived from the sealed scientific record. Replay proof is not human acceptance.",
            f"Scientific record SHA-256: `{record.sha256}`",
            "",
        ]
    )
    return "\n".join(lines)


@dataclass(frozen=True)
class CommunicationReport:
    exact_text: str
    sha256: str
    profile: str
    report_markdown: str
    covered_claim_ids: tuple[str, ...]


def parse_communication_report_response(
    response_text: str,
    *,
    record: ScientificRecord,
    expected_profile: str = "adult_beginner_carl_sagan",
) -> CommunicationReport:
    payload, value = _one_json_document(response_text, label="Communication-report response")
    expected = {
        "communication_report_version",
        "profile",
        "source_scientific_record_sha256",
        "covered_claim_ids",
        "report_markdown",
    }
    if set(value) != expected or value["communication_report_version"] != COMMUNICATION_REPORT_VERSION:
        raise ValueError("Communication report fields or version are invalid")
    if (
        value["profile"] != expected_profile
        or value["source_scientific_record_sha256"] != record.sha256
    ):
        raise ValueError("Communication report disagrees with its source science or profile")
    covered = _string_array(value["covered_claim_ids"], "covered_claim_ids")
    if len(covered) != len(set(covered)):
        raise ValueError("Communication report covered_claim_ids are duplicated")
    known = {
        claim.claim_id
        for claim in (
            *record.established_claims,
            *record.inferred_claims,
            *record.contradicted_claims,
        )
    }
    required = {
        claim.claim_id
        for claim in (*record.established_claims, *record.contradicted_claims)
    }
    if not set(covered).issubset(known) or not required.issubset(set(covered)):
        raise ValueError("Communication report claim coverage is incomplete or unknown")
    markdown = _text(value["report_markdown"], "Communication report markdown")
    return CommunicationReport(
        exact_text=payload,
        sha256=hashlib.sha256(payload.encode("utf-8")).hexdigest(),
        profile=expected_profile,
        report_markdown=markdown,
        covered_claim_ids=covered,
    )


def communication_coverage_receipt(
    report: CommunicationReport,
    record: ScientificRecord,
) -> dict[str, Any]:
    required = sorted(
        claim.claim_id
        for claim in (*record.established_claims, *record.contradicted_claims)
    )
    return {
        "communication_coverage_version": 1,
        "scientific_record_sha256": record.sha256,
        "communication_report_sha256": report.sha256,
        "required_claim_ids": required,
        "covered_claim_ids": list(report.covered_claim_ids),
        "coverage_complete": set(required).issubset(set(report.covered_claim_ids)),
    }
