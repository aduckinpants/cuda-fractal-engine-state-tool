from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .agent_bundle import AgentBundle, load_packet_active_color_pipeline_context
from .openai_transport import TransportResource
from .research_protocol import ResearchBrief, canonical_json_sha256
from .research_run_store import ResearchRunStore
from .research_session import ResearchExecutionEvidence
from .scientific_record import ArtifactRootRegistry, EvidenceReference, ScientificRecord


def _json_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False)
        + "\n"
    ).encode("utf-8")


def _resource(path: Path, *, filename: str, role: str, media_role: str = "file") -> TransportResource:
    payload = path.read_bytes()
    return TransportResource(
        filename=filename,
        role=role,
        media_role=media_role,
        sha256=hashlib.sha256(payload).hexdigest(),
        size_bytes=len(payload),
        local_path=path.resolve(),
        payload=payload,
    )


@dataclass(frozen=True)
class ResearchStageContext:
    prompt: str
    resources: tuple[TransportResource, ...]
    context_path: Path | None = None


def build_planner_context(brief: ResearchBrief, bundle: AgentBundle) -> ResearchStageContext:
    pipeline = load_packet_active_color_pipeline_context(bundle.packet_dir)
    prompt = f"""Investigate the sealed research brief using the attached Packet V8.

Sealed brief:
{json.dumps(brief.to_dict(), indent=2, ensure_ascii=False, allow_nan=False)}

Captured active Color Pipeline:
{pipeline["active_chain_text"]}

Return exactly one planner outcome allowed by question_research_protocol.v1.
The first nonempty line must be exactly `RESEARCH_ACTION: <ACTION>`, with the colon present,
where `<ACTION>` is one of `SINGLE_OVERRIDE`, `SCALAR_SWEEP`, `ANSWER_READY`, or
`UNRESOLVED_REPORT`. Do not write `RESEARCH_ACTION <ACTION>` without the colon.
SINGLE_OVERRIDE uses
these ordered fields: Chosen experiment; Why this experiment; Locked prediction; Observation
channel; Disconfirmation condition; Camera and fixed-state policy; Hostile self-review conclusion.
SCALAR_SWEEP uses: Selected bracket; Why this bracket; Locked trend prediction; Observation
channel; Disconfirmation condition; Fixed-state and camera policy; Hostile self-review conclusion.
For an executable outcome, include exactly one bare JSON payload after those fields.
ANSWER_READY and UNRESOLVED_REPORT contain no JSON. Do not ask a clarification question.
"""
    return ResearchStageContext(prompt=prompt, resources=())


def build_review_context(
    *,
    run_store: ResearchRunStore,
    brief: ResearchBrief,
    bundle: AgentBundle,
    evidence: ResearchExecutionEvidence,
) -> ResearchStageContext:
    attempt = evidence.attempt_number
    attempt_dir = run_store.run_dir / "attempts" / f"{attempt:03d}"
    round_plan_path = attempt_dir / "round-plan.json"
    execution_ref_path = attempt_dir / "execution-ref.json"
    round_plan_bytes = round_plan_path.read_bytes()
    execution_bytes = execution_ref_path.read_bytes()
    pipeline = load_packet_active_color_pipeline_context(bundle.packet_dir)
    context = {
        "research_review_context_version": 1,
        "attempt_number": attempt,
        "research_brief": brief.to_dict(),
        "research_brief_sha256": canonical_json_sha256(brief.to_dict()),
        "current_packet": {
            "packet_id": bundle.packet_id,
            "manifest_sha256": bundle.manifest_sha256,
            "finding_id": bundle.finding_id,
        },
        "captured_active_color_pipeline": pipeline,
        "round_plan": json.loads(round_plan_bytes.decode("utf-8")),
        "round_plan_file_sha256": hashlib.sha256(round_plan_bytes).hexdigest(),
        "execution": json.loads(execution_bytes.decode("utf-8")),
        "execution_file_sha256": hashlib.sha256(execution_bytes).hexdigest(),
        "authority_note": (
            "This is a fresh review context. The round plan locks the prediction before evidence; "
            "Packet V8 and proof/sweep artifacts remain domain authority."
        ),
    }
    context_path = run_store.write_evidence_once_bytes(
        f"attempts/{attempt:03d}/review-context.json", _json_bytes(context)
    )
    resources: list[TransportResource] = [
        _resource(context_path, filename="research-review-context.json", role="research_review_context")
    ]
    if evidence.proof is not None:
        proof = evidence.proof
        resources.append(
            _resource(
                proof.receipt_path,
                filename="candidate-proof-receipt.json",
                role="state_override_proof_receipt",
            )
        )
        if proof.candidate_display_path is not None:
            resources.append(
                _resource(
                    proof.candidate_display_path,
                    filename="candidate-display.png",
                    role="proof_candidate_display",
                    media_role="vision",
                )
            )
    elif evidence.sweep is not None and evidence.sweep.web_review_dir is not None:
        web = evidence.sweep.web_review_dir
        resources.extend(
            (
                _resource(
                    web / "sweep-review.md",
                    filename="sweep-review.md",
                    role="scalar_sweep_review",
                ),
                _resource(
                    web / "sweep-evidence.json",
                    filename="sweep-evidence.json",
                    role="scalar_sweep_evidence",
                ),
                _resource(
                    web / "contact-sheet.png",
                    filename="sweep-contact-sheet.png",
                    role="scalar_sweep_contact_sheet",
                    media_role="vision",
                ),
            )
        )
    prompt = """Review this completed experiment in a fresh context.
Bind every conclusion to the attached exact round plan and result evidence. Compare the locked
prediction with what the evidence establishes, including failure or no-effect evidence.
The first nonempty line must be exactly `RESEARCH_GATE: <GATE>`, with the colon present, where
`<GATE>` is one of `COMPLETE_RESEARCH`, `CONTINUE_RETAIN_BASE`,
`CONTINUE_PROMOTE_RESULT`, or `UNRESOLVED`. Then return exactly these five labeled fields in
this order: `Prediction outcome:`, `Evidence assessment:`, `Selected result:`,
`Next research step:`, and `Hostile self-review conclusion:`. Use `Selected result: none`
unless `CONTINUE_PROMOTE_RESULT` nominates one exact `single:<proof_id>` or
`sweep:<sweep_id>:<member_index>`. Return plain text only: no JSON object and no code fence.
Promotion requires one exact replay-proven result identity; replay proof alone never implies it.
"""
    return ResearchStageContext(prompt, tuple(resources), context_path)


def build_synthesis_context(
    *,
    run_store: ResearchRunStore,
    brief: ResearchBrief,
    current_bundle: AgentBundle,
    packet_lineage: list[dict[str, Any]],
    evidence_references: tuple[EvidenceReference, ...],
    roots: ArtifactRootRegistry,
    terminal_planner_decision: dict[str, Any] | None = None,
) -> ResearchStageContext:
    attempts: list[dict[str, Any]] = []
    attempts_dir = run_store.run_dir / "attempts"
    for attempt_dir in sorted(path for path in attempts_dir.iterdir() if path.is_dir()):
        record: dict[str, Any] = {"attempt": attempt_dir.name}
        for filename, key in (
            ("round-plan.json", "round_plan"),
            ("execution-ref.json", "execution"),
            ("review-decision.json", "review"),
        ):
            path = attempt_dir / filename
            if path.is_file():
                record[key] = json.loads(path.read_text(encoding="utf-8"))
                record[f"{key}_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
        attempts.append(record)
    pipeline = load_packet_active_color_pipeline_context(current_bundle.packet_dir)
    context = {
        "research_synthesis_context_version": 1,
        "question_run_id": run_store.run_dir.name,
        "research_brief": brief.to_dict(),
        "research_brief_sha256": canonical_json_sha256(brief.to_dict()),
        "current_research_base": {
            "packet_id": current_bundle.packet_id,
            "manifest_sha256": current_bundle.manifest_sha256,
            "finding_id": current_bundle.finding_id,
            "promotion_kind": "automated_research_promotion"
            if len(packet_lineage) > 1
            else "captured_finding_base",
            "replay_proven": len(packet_lineage) > 1,
            "human_acceptance": False,
            "launched": False,
        },
        "packet_lineage": packet_lineage,
        "captured_active_color_pipeline": pipeline,
        "attempts": attempts,
        "terminal_planner_decision": terminal_planner_decision,
        "allowed_evidence_references": [item.to_dict() for item in evidence_references],
        "scientific_record_contract": {
            "scientific_record_version": 1,
            "source": {
                "question_run_id": run_store.run_dir.name,
                "research_brief_sha256": canonical_json_sha256(brief.to_dict()),
                "current_packet_id": current_bundle.packet_id,
                "current_packet_manifest_sha256": current_bundle.manifest_sha256,
                "human_acceptance": False,
            },
            "scientific_conclusion_options": [
                "ANSWER_ESTABLISHED",
                "ANSWER_PARTIAL",
                "QUESTION_UNRESOLVED",
                "CONTRADICTED",
                "NO_SCIENTIFIC_CONCLUSION",
            ],
            "claim_fields": ["claim_id", "text", "evidence_references"],
            "experiment_summary_fields": [
                "attempt_number",
                "action",
                "prediction",
                "prediction_outcome",
                "evidence_references",
            ],
            "value_receipt_fields": [
                "path",
                "requested_value",
                "canonical_value_status",
                "canonical_value",
                "emitted_value",
                "evidence_references",
            ],
            "wire_shape_rules": {
                "answer": "non-empty string",
                "claims": (
                    "arrays of objects with exactly claim_id, text, and evidence_references"
                ),
                "unresolved_questions": "array of non-empty strings, not objects",
                "requested_canonical_emitted_values": (
                    "one object per distinct requested/emitted pair; a sweep path may repeat "
                    "for different values"
                ),
                "canonical_value_status": "exactly available or unavailable",
                "unavailable_canonical_value": "null",
                "best_next_experiment": "non-empty string or null",
                "evidence_references": (
                    "copy exact objects from allowed_evidence_references; never invent or edit"
                ),
            },
            "top_level_fields": [
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
            ],
        },
        "authority_note": (
            "Only listed hash-verified references may ground claims. A provisional ANSWER_READY "
            "planner response is proposed text, not scientific evidence."
        ),
    }
    context_path = run_store.write_evidence_once_bytes(
        "synthesis/synthesis-context.json", _json_bytes(context)
    )
    resources = [
        _resource(context_path, filename="research-synthesis-context.json", role="research_synthesis_context")
    ]
    for index, reference in enumerate(evidence_references):
        path = roots.resolve_and_verify(reference)
        suffix = path.suffix.lower()
        resources.append(
            _resource(
                path,
                filename=f"evidence-{index:03d}{suffix or '.bin'}",
                role=reference.artifact_role,
                media_role="vision" if suffix in {".png", ".jpg", ".jpeg"} else "file",
            )
        )
    prompt = """Produce the audience-neutral scientific record for this bounded run.
Return exactly one fenced JSON object and no prose outside it. Follow the exact top-level fields,
field types, and wire_shape_rules in scientific_record_contract. In particular: answer is one
string; unresolved_questions is an array of strings; each claim is exactly {claim_id, text,
evidence_references}; and best_next_experiment is a string or null. Copy evidence-reference
objects byte-for-field from allowed_evidence_references instead of inventing identities.
The source object must copy all five declared source fields exactly, including
`human_acceptance: false`.

For requested_canonical_emitted_values, emit one item for every distinct requested/emitted value
pair supported by an existing receipt. The same path may appear more than once for different sweep
values. canonical_value_status is exactly `available` or `unavailable`; use `unavailable` and null
when no existing normalization receipt provides a canonical value.

Use scientific_record_version 1 and the exact source identities from the synthesis context.
Separate established, inferred, contradicted, and unresolved material. CONTRADICTED applies only
when the question's principal proposition was contradicted. Keep the record concise enough to
complete: use the shortest sufficient evidence set for each item and do not repeat explanatory
prose across sections. Do not infer science from replay success or image hashes alone and do not
record human acceptance.
"""
    return ResearchStageContext(prompt, tuple(resources), context_path)


_COMMUNICATION_PROMPT = """Render the attached sealed scientific record for an adult beginner in a
Carl-Sagan-like concept-first register: clear, curious, accurate, and never overstated. Return
exactly one fenced JSON object for communication_report_version 1 with the exact fields profile,
source_scientific_record_sha256, covered_claim_ids, and report_markdown. Use profile
adult_beginner_carl_sagan. Preserve every established and contradicted claim and list their stable
claim IDs in covered_claim_ids. Do not add science.
"""


def seal_communication_context(
    *,
    run_store: ResearchRunStore,
    record: ScientificRecord,
) -> ResearchStageContext:
    payload = _json_bytes(record.value)
    path = run_store.write_evidence_once_bytes(
        "communication/scientific-record.json", payload
    )
    resource = _resource(path, filename="scientific-record.json", role="sealed_scientific_record")
    return ResearchStageContext(_COMMUNICATION_PROMPT, (resource,), path)
