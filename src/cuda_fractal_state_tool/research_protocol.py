from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from enum import Enum
from typing import Any

from .scalar_sweep import ScalarSweepPlan, parse_scalar_sweep_plan
from .state_override import (
    ParsedStateOverride,
    enumerate_override_leaf_paths,
    parse_state_override,
)


RESEARCH_PROTOCOL_VERSION = 1
ROUND_PLAN_VERSION = 1
SUPPORTED_EXPERIMENT_DOMAINS = frozenset({"params", "view", "color_pipeline_draft"})
SUPPORTED_COMMUNICATION_PROFILES = frozenset({"working_session", "adult_beginner_carl_sagan"})
_SAFE_PATH = re.compile(r"^(params|view)(?:\.[A-Za-z_][A-Za-z0-9_]*)+$")
_JSON_FENCE = re.compile(r"```([^\r\n`]*)\r?\n(.*?)```", re.DOTALL)


class ResearchAction(str, Enum):
    ANSWER_READY = "ANSWER_READY"
    SINGLE_OVERRIDE = "SINGLE_OVERRIDE"
    SCALAR_SWEEP = "SCALAR_SWEEP"
    UNRESOLVED_REPORT = "UNRESOLVED_REPORT"


class ResearchReviewGate(str, Enum):
    COMPLETE_RESEARCH = "COMPLETE_RESEARCH"
    CONTINUE_RETAIN_BASE = "CONTINUE_RETAIN_BASE"
    CONTINUE_PROMOTE_RESULT = "CONTINUE_PROMOTE_RESULT"
    UNRESOLVED = "UNRESOLVED"


class UnresolvedReason(str, Enum):
    BRIEF_INSUFFICIENT = "BRIEF_INSUFFICIENT"
    AUTHORITY_INSUFFICIENT = "AUTHORITY_INSUFFICIENT"
    CAPABILITY_UNAVAILABLE = "CAPABILITY_UNAVAILABLE"
    QUESTION_OUT_OF_SCOPE = "QUESTION_OUT_OF_SCOPE"


@dataclass(frozen=True)
class ResearchResultSelection:
    kind: str
    proof_id: str | None = None
    sweep_id: str | None = None
    member_index: int | None = None

    @classmethod
    def parse(cls, value: str) -> "ResearchResultSelection":
        if value == "none":
            return cls("none")
        parts = value.split(":")
        if len(parts) == 2 and parts[0] == "single" and parts[1]:
            return cls("single", proof_id=parts[1])
        if len(parts) == 3 and parts[0] == "sweep" and parts[1]:
            try:
                index = int(parts[2])
            except ValueError as exc:
                raise ValueError("Sweep result selection has an invalid member index") from exc
            if index < 0:
                raise ValueError("Sweep result selection member index cannot be negative")
            return cls("sweep_member", sweep_id=parts[1], member_index=index)
        raise ValueError("Review selected result must be none, single:<proof_id>, or sweep:<sweep_id>:<index>")


@dataclass(frozen=True)
class ResearchReviewDecision:
    gate: ResearchReviewGate
    source_text: str
    source_response_sha256: str
    prediction_outcome: str
    evidence_assessment: str
    selected_result: ResearchResultSelection
    next_research_step: str
    hostile_self_review_conclusion: str


@dataclass(frozen=True)
class ExperimentPermissions:
    domains: tuple[str, ...]
    allowed_paths: tuple[str, ...] | None
    allow_scalar_sweep: bool

    @classmethod
    def from_dict(cls, value: Any) -> "ExperimentPermissions":
        if not isinstance(value, dict) or set(value) != {
            "domains",
            "allowed_paths",
            "allow_scalar_sweep",
        }:
            raise ValueError("Experiment permissions have an invalid shape")
        raw_domains = value["domains"]
        if (
            not isinstance(raw_domains, list)
            or any(not isinstance(item, str) for item in raw_domains)
            or len(raw_domains) != len(set(raw_domains))
            or any(item not in SUPPORTED_EXPERIMENT_DOMAINS for item in raw_domains)
        ):
            raise ValueError("Experiment permission domains are invalid")
        raw_paths = value["allowed_paths"]
        allowed_paths: tuple[str, ...] | None
        if raw_paths is None:
            allowed_paths = None
        elif (
            not isinstance(raw_paths, list)
            or any(not isinstance(item, str) for item in raw_paths)
            or len(raw_paths) != len(set(raw_paths))
        ):
            raise ValueError("Experiment allowed_paths must be null or a unique string array")
        else:
            for path in raw_paths:
                if path == "color_pipeline_draft":
                    domain = path
                elif _SAFE_PATH.fullmatch(path):
                    domain = path.split(".", 1)[0]
                else:
                    raise ValueError(f"Experiment allowed path is invalid: {path}")
                if domain not in raw_domains:
                    raise ValueError(f"Experiment allowed path is outside permitted domains: {path}")
            allowed_paths = tuple(raw_paths)
        if not isinstance(value["allow_scalar_sweep"], bool):
            raise ValueError("allow_scalar_sweep must be boolean")
        return cls(tuple(raw_domains), allowed_paths, value["allow_scalar_sweep"])

    def authorizes_path(self, path: str) -> bool:
        domain = path.split(".", 1)[0].split("[", 1)[0]
        if domain not in self.domains:
            return False
        if self.allowed_paths is None:
            return True
        for allowed in self.allowed_paths:
            if path == allowed:
                return True
            if allowed == "color_pipeline_draft" and (
                path.startswith("color_pipeline_draft.")
                or path.startswith("color_pipeline_draft[")
            ):
                return True
        return False


@dataclass(frozen=True)
class ResearchBrief:
    question: str
    attention_context: str
    user_hypotheses: tuple[str, ...]
    experiment_permissions: ExperimentPermissions
    fixed_condition_notes: tuple[str, ...]
    useful_answer_kind: str
    useful_answer_details: str
    maximum_experiment_rounds: int
    communication_profile: str
    hard_dollar_budget: Decimal

    @classmethod
    def from_dict(cls, value: Any) -> "ResearchBrief":
        expected = {
            "question",
            "attention_context",
            "user_hypotheses",
            "experiment_permissions",
            "fixed_conditions",
            "useful_answer",
            "maximum_experiment_rounds",
            "communication_profile",
            "hard_dollar_budget",
        }
        if not isinstance(value, dict) or set(value) != expected:
            raise ValueError("Research brief has an invalid shape")

        def required_text(name: str) -> str:
            text = value[name]
            if not isinstance(text, str) or not text.strip():
                raise ValueError(f"Research brief {name} is required")
            return text.strip()

        hypotheses = value["user_hypotheses"]
        if not isinstance(hypotheses, list) or any(
            not isinstance(item, str) or not item.strip() for item in hypotheses
        ):
            raise ValueError("Research brief hypotheses must be non-empty strings")
        fixed = value["fixed_conditions"]
        if not isinstance(fixed, dict) or set(fixed) != {"notes"}:
            raise ValueError("Research brief fixed_conditions has an invalid shape")
        notes = fixed["notes"]
        if not isinstance(notes, list) or any(
            not isinstance(item, str) or not item.strip() for item in notes
        ):
            raise ValueError("Research brief fixed-condition notes must be non-empty strings")
        useful = value["useful_answer"]
        if not isinstance(useful, dict) or set(useful) != {"kind", "details"}:
            raise ValueError("Research brief useful_answer has an invalid shape")
        if any(not isinstance(useful[key], str) or not useful[key].strip() for key in useful):
            raise ValueError("Research brief useful-answer values are required")
        rounds = value["maximum_experiment_rounds"]
        if isinstance(rounds, bool) or not isinstance(rounds, int) or not 0 <= rounds <= 2:
            raise ValueError("maximum_experiment_rounds must be an integer from zero through two")
        profile = value["communication_profile"]
        if profile not in SUPPORTED_COMMUNICATION_PROFILES:
            raise ValueError("Research brief communication profile is unsupported")
        try:
            budget = Decimal(str(value["hard_dollar_budget"]))
        except (InvalidOperation, ValueError) as exc:
            raise ValueError("Research brief hard dollar budget is invalid") from exc
        if not budget.is_finite() or budget < 0:
            raise ValueError("Research brief hard dollar budget must be finite and non-negative")
        return cls(
            question=required_text("question"),
            attention_context=required_text("attention_context"),
            user_hypotheses=tuple(item.strip() for item in hypotheses),
            experiment_permissions=ExperimentPermissions.from_dict(
                value["experiment_permissions"]
            ),
            fixed_condition_notes=tuple(item.strip() for item in notes),
            useful_answer_kind=useful["kind"].strip(),
            useful_answer_details=useful["details"].strip(),
            maximum_experiment_rounds=rounds,
            communication_profile=profile,
            hard_dollar_budget=budget,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "question": self.question,
            "attention_context": self.attention_context,
            "user_hypotheses": list(self.user_hypotheses),
            "experiment_permissions": {
                "domains": list(self.experiment_permissions.domains),
                "allowed_paths": (
                    None
                    if self.experiment_permissions.allowed_paths is None
                    else list(self.experiment_permissions.allowed_paths)
                ),
                "allow_scalar_sweep": self.experiment_permissions.allow_scalar_sweep,
            },
            "fixed_conditions": {"notes": list(self.fixed_condition_notes)},
            "useful_answer": {
                "kind": self.useful_answer_kind,
                "details": self.useful_answer_details,
            },
            "maximum_experiment_rounds": self.maximum_experiment_rounds,
            "communication_profile": self.communication_profile,
            "hard_dollar_budget": format(self.hard_dollar_budget, "f"),
        }


@dataclass(frozen=True)
class PlannerDecision:
    action: ResearchAction
    source_text: str
    source_response_sha256: str
    fields: dict[str, str]
    payload_text: str | None
    payload_sha256: str | None
    unresolved_reason: UnresolvedReason | None = None


_EXECUTABLE_HEADINGS = {
    ResearchAction.SINGLE_OVERRIDE: (
        "Chosen experiment",
        "Why this experiment",
        "Locked prediction",
        "Observation channel",
        "Disconfirmation condition",
        "Camera and fixed-state policy",
        "Hostile self-review conclusion",
    ),
    ResearchAction.SCALAR_SWEEP: (
        "Selected bracket",
        "Why this bracket",
        "Locked trend prediction",
        "Observation channel",
        "Disconfirmation condition",
        "Fixed-state and camera policy",
        "Hostile self-review conclusion",
    ),
}


def _sections_before_fence(text: str, headings: tuple[str, ...]) -> dict[str, str]:
    prefix = text.split("```", 1)[0]
    lines = prefix.splitlines()
    nonempty = [index for index, line in enumerate(lines) if line.strip()]
    if not nonempty:
        raise ValueError("Planner response is empty")
    cursor = nonempty[0] + 1
    fields: dict[str, str] = {}
    for position, heading in enumerate(headings):
        while cursor < len(lines) and not lines[cursor].strip():
            cursor += 1
        if cursor >= len(lines) or not lines[cursor].strip().startswith(f"{heading}:"):
            raise ValueError(f"Planner response is missing ordered field: {heading}")
        line = lines[cursor].strip()
        if line.split(":", 1)[0] != heading:
            raise ValueError(f"Planner response field label changed: {heading}")
        content = [line.split(":", 1)[1].strip()]
        cursor += 1
        next_heading = headings[position + 1] if position + 1 < len(headings) else None
        while cursor < len(lines):
            stripped = lines[cursor].strip()
            if next_heading is not None and stripped.startswith(f"{next_heading}:"):
                break
            if stripped:
                content.append(stripped)
            cursor += 1
        joined = "\n".join(item for item in content if item)
        if not joined:
            raise ValueError(f"Planner response field is empty: {heading}")
        fields[heading] = joined
    if any(line.strip() for line in lines[cursor:]):
        raise ValueError("Planner response contains text outside the locked fields")
    return fields


def _single_json_payload(text: str) -> str:
    fences = _JSON_FENCE.findall(text)
    if len(fences) != 1 or text.count("```") != 2:
        raise ValueError("Executable planner response must contain exactly one fenced code block")
    language, payload = fences[0]
    if language.strip().lower() != "json":
        raise ValueError("Executable planner response code block must use the json language tag")
    return payload


def parse_planner_response(text: str) -> PlannerDecision:
    try:
        exact = text.encode("utf-8")
    except UnicodeError as exc:
        raise ValueError("Planner response is not UTF-8 encodable") from exc
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines or not lines[0].startswith("RESEARCH_ACTION: "):
        raise ValueError("Planner response must begin with RESEARCH_ACTION")
    try:
        action = ResearchAction(lines[0].split(":", 1)[1].strip())
    except ValueError as exc:
        raise ValueError("Planner response has an unsupported RESEARCH_ACTION") from exc
    payload_text: str | None = None
    payload_sha256: str | None = None
    unresolved: UnresolvedReason | None = None
    if action in _EXECUTABLE_HEADINGS:
        fields = _sections_before_fence(text, _EXECUTABLE_HEADINGS[action])
        payload_text = _single_json_payload(text)
        payload_sha256 = hashlib.sha256(payload_text.encode("utf-8")).hexdigest()
        if action is ResearchAction.SINGLE_OVERRIDE:
            parse_state_override(payload_text)
        else:
            parse_scalar_sweep_plan(payload_text)
    elif action is ResearchAction.ANSWER_READY:
        if "```" in text:
            raise ValueError("ANSWER_READY must not contain a code block")
        fields = _sections_before_fence(
            text,
            (
                "Proposed answer",
                "Evidence basis",
                "Uncertainty",
                "Hostile self-review conclusion",
            ),
        )
    else:
        if "```" in text:
            raise ValueError("UNRESOLVED_REPORT must not contain a code block")
        fields = _sections_before_fence(
            text,
            (
                "Unresolved reason",
                "What is missing",
                "Why current authority cannot answer",
                "Best next step",
                "Hostile self-review conclusion",
            ),
        )
        try:
            unresolved = UnresolvedReason(fields["Unresolved reason"])
        except ValueError as exc:
            raise ValueError("Planner unresolved reason is unsupported") from exc
    return PlannerDecision(
        action=action,
        source_text=text,
        source_response_sha256=hashlib.sha256(exact).hexdigest(),
        fields=fields,
        payload_text=payload_text,
        payload_sha256=payload_sha256,
        unresolved_reason=unresolved,
    )


def parse_review_response(text: str) -> ResearchReviewDecision:
    try:
        exact = text.encode("utf-8")
    except UnicodeError as exc:
        raise ValueError("Review response is not UTF-8 encodable") from exc
    if "```" in text:
        raise ValueError("Research review response must not contain a code block")
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines or not lines[0].startswith("RESEARCH_GATE: "):
        raise ValueError("Review response must begin with RESEARCH_GATE")
    try:
        gate = ResearchReviewGate(lines[0].split(":", 1)[1].strip())
    except ValueError as exc:
        raise ValueError("Review response has an unsupported RESEARCH_GATE") from exc
    fields = _sections_before_fence(
        text,
        (
            "Prediction outcome",
            "Evidence assessment",
            "Selected result",
            "Next research step",
            "Hostile self-review conclusion",
        ),
    )
    selection = ResearchResultSelection.parse(fields["Selected result"])
    if gate is ResearchReviewGate.CONTINUE_PROMOTE_RESULT:
        if selection.kind == "none":
            raise ValueError("CONTINUE_PROMOTE_RESULT requires one exact selected result")
    elif selection.kind != "none":
        raise ValueError(f"{gate.value} must use Selected result: none")
    return ResearchReviewDecision(
        gate=gate,
        source_text=text,
        source_response_sha256=hashlib.sha256(exact).hexdigest(),
        prediction_outcome=fields["Prediction outcome"],
        evidence_assessment=fields["Evidence assessment"],
        selected_result=selection,
        next_research_step=fields["Next research step"],
        hostile_self_review_conclusion=fields["Hostile self-review conclusion"],
    )


def authorize_single_override(
    decision: PlannerDecision, permissions: ExperimentPermissions
) -> ParsedStateOverride:
    if decision.action is not ResearchAction.SINGLE_OVERRIDE or decision.payload_text is None:
        raise ValueError("Planner decision is not a single override")
    override = parse_state_override(decision.payload_text)
    paths = enumerate_override_leaf_paths(override)
    if not paths:
        raise ValueError("UNINTENDED_NO_EFFECT")
    denied = [path for path in paths if not permissions.authorizes_path(path)]
    if denied:
        raise ValueError("Override contains paths outside research permission: " + ", ".join(denied))
    return override


def authorize_scalar_sweep(
    decision: PlannerDecision, permissions: ExperimentPermissions
) -> ScalarSweepPlan:
    if decision.action is not ResearchAction.SCALAR_SWEEP or decision.payload_text is None:
        raise ValueError("Planner decision is not a scalar sweep")
    if not permissions.allow_scalar_sweep:
        raise ValueError("Research brief does not permit a scalar sweep")
    plan = parse_scalar_sweep_plan(decision.payload_text)
    if not permissions.authorizes_path(plan.axis_path):
        raise ValueError(f"Sweep axis is outside research permission: {plan.axis_path}")
    return plan


def round_plan_document(decision: PlannerDecision, *, attempt_number: int) -> dict[str, Any]:
    if decision.action not in {ResearchAction.SINGLE_OVERRIDE, ResearchAction.SCALAR_SWEEP}:
        raise ValueError("Only executable planner decisions have round plans")
    if isinstance(attempt_number, bool) or not isinstance(attempt_number, int) or attempt_number < 1:
        raise ValueError("Round-plan attempt number must be positive")
    prediction_field = (
        "Locked prediction"
        if decision.action is ResearchAction.SINGLE_OVERRIDE
        else "Locked trend prediction"
    )
    camera_field = (
        "Camera and fixed-state policy"
        if decision.action is ResearchAction.SINGLE_OVERRIDE
        else "Fixed-state and camera policy"
    )
    if decision.payload_sha256 is None:
        raise ValueError("Executable planner decision has no payload identity")
    return {
        "round_plan_version": ROUND_PLAN_VERSION,
        "attempt_number": attempt_number,
        "action": decision.action.value,
        "experiment": decision.fields[
            "Chosen experiment"
            if decision.action is ResearchAction.SINGLE_OVERRIDE
            else "Selected bracket"
        ],
        "rationale": decision.fields[
            "Why this experiment"
            if decision.action is ResearchAction.SINGLE_OVERRIDE
            else "Why this bracket"
        ],
        "prediction": decision.fields[prediction_field],
        "observation_channel": decision.fields["Observation channel"],
        "disconfirmation_condition": decision.fields["Disconfirmation condition"],
        "camera_policy": decision.fields[camera_field],
        "hostile_self_review_conclusion": decision.fields["Hostile self-review conclusion"],
        "payload_sha256": decision.payload_sha256,
        "source_response_sha256": decision.source_response_sha256,
    }


def canonical_json_sha256(value: Any) -> str:
    payload = (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
        + "\n"
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()
