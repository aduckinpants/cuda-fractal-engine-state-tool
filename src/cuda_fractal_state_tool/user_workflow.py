from __future__ import annotations

import hashlib
import json
import os
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from .async_jobs import JobContext
from .finding_workspace import ImportResult, SourceCaptureImporter
from .fractal_parameter_authority import capture_fractal_parameter_authority
from .json_utils import loads_no_duplicates
from .lane_catalog import load_lane_catalog_from_ui_salt_contract
from .preview_service import PreviewResult
from .proposal import ALLOWED_COLOR_TRIPLETS, parse_proposal_v1
from .runtime_surface import DEFAULT_RUNTIME_CMD, build_runtime_identity, resolve_launcher, sha256_file


CAPABILITY_PROFILE = "finding-color-first-row-v1"
PACKET_VERSION = 4


class SessionState(str, Enum):
    EMPTY = "EMPTY"
    FINDING_READY = "FINDING_READY"
    PACKET_READY = "PACKET_READY"
    PROPOSAL_DIRTY = "PROPOSAL_DIRTY"
    PROVING = "PROVING"
    PROVEN = "PROVEN"
    REJECTED = "REJECTED"


@dataclass(frozen=True)
class FindingContext:
    import_result: ImportResult
    workspace_root: Path
    workspace_manifest: dict[str, Any]
    authoring_base_state_path: Path
    review_fractal_state_path: Optional[Path]
    review_fractal_state_sha256: Optional[str]
    primary_frame_path: Optional[Path]
    summary_text: str

    @property
    def finding_id(self) -> str:
        return self.import_result.finding_id

    @property
    def authoring_base_sha256(self) -> str:
        return self.import_result.authoring_base_state_sha256


@dataclass(frozen=True)
class PacketContext:
    packet_id: str
    packet_sha256: str
    capability_profile: str
    packet_text: str
    packet_path: Path
    manifest_path: Path
    runtime_identity_sha256: str
    ui_salt_contract_sha256: str
    parameter_surface_sha256: str


@dataclass
class UserWorkflowSession:
    generation: int = 0
    state: SessionState = SessionState.EMPTY
    finding: Optional[FindingContext] = None
    packet: Optional[PacketContext] = None
    preview: Optional[PreviewResult] = None
    proposal_text: str = ""
    proof_result: Any = None
    status_text: str = "Choose a captured finding to begin."

    def begin_finding_change(self) -> int:
        self.generation += 1
        retained_proposal = self.proposal_text
        self.finding = None
        self.packet = None
        self.preview = None
        self.proof_result = None
        self.state = SessionState.EMPTY
        self.status_text = "Loading finding…"
        if retained_proposal:
            self.status_text = "Loading finding; existing proposal will require a new packet binding."
        return self.generation

    def accept_finding(self, finding: FindingContext) -> None:
        self.finding = finding
        self.packet = None
        self.preview = None
        self.proof_result = None
        self.state = SessionState.PROPOSAL_DIRTY if self.proposal_text.strip() else SessionState.FINDING_READY
        self.status_text = "Finding ready. Building its agent exploration packet…"

    def accept_preview(self, preview: PreviewResult) -> None:
        self.preview = preview

    def accept_packet(self, packet: PacketContext) -> None:
        self.packet = packet
        self.proof_result = None
        self.state = SessionState.PROPOSAL_DIRTY if self.proposal_text.strip() else SessionState.PACKET_READY
        self.status_text = "Exact intake packet ready to copy."

    def set_proposal_text(self, proposal_text: str) -> None:
        if proposal_text == self.proposal_text:
            return
        self.proposal_text = proposal_text
        self.proof_result = None
        if proposal_text.strip() and self.finding is not None:
            self.state = SessionState.PROPOSAL_DIRTY
            self.status_text = "Proposal changed. Validate and replay-prove this exact text against the active packet."
        elif self.packet is not None:
            self.state = SessionState.PACKET_READY
            self.status_text = "Exact intake packet ready to copy."
        elif self.finding is not None:
            self.state = SessionState.FINDING_READY
            self.status_text = "Finding ready. Building its agent exploration packet…"
        else:
            self.state = SessionState.EMPTY
            self.status_text = "Choose a captured finding to begin."

    def begin_proof(self) -> None:
        if self.finding is None or self.packet is None or not self.proposal_text.strip():
            raise ValueError("A finding, exact packet, and proposal are required before proof")
        self.proof_result = None
        self.state = SessionState.PROVING
        self.status_text = "Validating exact binding and proving through the CUDA engine…"

    def accept_proof_result(self, result: Any) -> None:
        self.proof_result = result
        if getattr(result, "status", None) == "proven":
            self.state = SessionState.PROVEN
            self.status_text = "Exact proposal binding proven and candidate launch-ready."
        else:
            self.state = SessionState.REJECTED
            self.status_text = "Proposal rejected. Review the proof status and copy the repair packet."

    def reset(self) -> None:
        self.generation += 1
        self.state = SessionState.EMPTY
        self.finding = None
        self.packet = None
        self.preview = None
        self.proposal_text = ""
        self.proof_result = None
        self.status_text = "Session reset. Durable findings, packets, and preview caches were preserved."


def _load_object(path: Path, label: str) -> dict[str, Any]:
    payload = loads_no_duplicates(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{label} must be a JSON object: {path}")
    return payload


def _resolve_artifact(finding_dir: Path, workspace_path: Any, label: str) -> Optional[Path]:
    if workspace_path is None:
        return None
    if not isinstance(workspace_path, str) or not workspace_path:
        raise ValueError(f"Finding manifest {label} path must be a non-empty string or null")
    resolved = (finding_dir / workspace_path).resolve()
    try:
        resolved.relative_to(finding_dir.resolve())
    except ValueError as exc:
        raise ValueError(f"Finding manifest {label} escapes the finding directory") from exc
    if not resolved.is_file():
        raise FileNotFoundError(f"Finding manifest {label} does not exist: {resolved}")
    return resolved


def load_finding_context(source_capture_path: Path, workspace_root: Path) -> FindingContext:
    importer = SourceCaptureImporter(workspace_root)
    import_result = importer.import_capture(source_capture_path)
    manifest = _load_object(import_result.workspace_manifest_path, "Finding workspace manifest")
    finding_dir = import_result.finding_dir.resolve()
    authoring_base = manifest.get("authoring_base")
    if not isinstance(authoring_base, dict):
        raise ValueError("Finding workspace manifest is missing authoring_base")
    state_path = _resolve_artifact(finding_dir, authoring_base.get("state_path"), "authoring base")
    if state_path is None:
        raise ValueError("Finding workspace manifest is missing authoring base state path")
    observed_state_sha256 = sha256_file(state_path)
    if observed_state_sha256 != import_result.authoring_base_state_sha256:
        raise ValueError("Imported authoring base hash changed after workspace import")

    source_artifacts = manifest.get("source_artifacts")
    if not isinstance(source_artifacts, dict):
        raise ValueError("Finding workspace manifest is missing source_artifacts")
    frame_entry = source_artifacts.get("primary_frame")
    frame_path = None
    if isinstance(frame_entry, dict):
        frame_path = _resolve_artifact(finding_dir, frame_entry.get("workspace_path"), "primary frame")

    review_entry = source_artifacts.get("review_fractal_state")
    review_path = None
    review_sha256 = None
    if isinstance(review_entry, dict):
        review_path = _resolve_artifact(
            finding_dir,
            review_entry.get("workspace_path"),
            "review-focused fractal state",
        )
        expected_review_sha256 = review_entry.get("sha256")
        if review_path is not None:
            review_sha256 = sha256_file(review_path)
            if expected_review_sha256 != review_sha256:
                raise ValueError("Review-focused fractal-state.json hash changed after workspace import")
            review_state = _load_object(review_path, "Review-focused fractal state")
            if review_state.get("schema_id") != "viewer.finding_fractal_state.v1":
                raise ValueError("Unsupported review-focused fractal-state.json schema_id")

    state = _load_object(state_path, "Authoring base state")
    render = state.get("render") if isinstance(state.get("render"), dict) else {}
    params = state.get("params") if isinstance(state.get("params"), dict) else {}
    summary_lines = [
        f"Finding ID: {import_result.finding_id}",
        f"Authoring base SHA-256: {import_result.authoring_base_state_sha256}",
        f"Fractal family: {state.get('fractal_type', 'unknown')}",
        f"Render: {render.get('width', '?')} × {render.get('height', '?')} | device {render.get('device_id', '?')}",
        f"Iterations: {params.get('max_iter', '?')} | auto: {(state.get('view') or {}).get('auto_max_iter', '?') if isinstance(state.get('view'), dict) else '?'}",
        f"Color: {params.get('color_signal', '?')} → {params.get('color_shape', '?')} → {params.get('color_palette', '?')} → {params.get('color_grading', '?')}",
        f"Frame: {frame_path.name if frame_path else 'not present'}",
        f"Review sidecar: {'viewer.finding_fractal_state.v1' if review_path else 'not present'}",
        f"Workspace index: {'updated' if import_result.workspace_index_updated else 'imported; index update failed'}",
    ]
    return FindingContext(
        import_result=import_result,
        workspace_root=workspace_root.resolve(),
        workspace_manifest=manifest,
        authoring_base_state_path=state_path,
        review_fractal_state_path=review_path,
        review_fractal_state_sha256=review_sha256,
        primary_frame_path=frame_path,
        summary_text="\n".join(summary_lines),
    )


def _canonical_sha256(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(f"{path.name}.tmp.{uuid.uuid4().hex}")
    with temp_path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(str(temp_path), str(path))


def _proposal_example(finding: FindingContext, overrides: dict[str, Any]) -> str:
    text = json.dumps(
        {
            "proposal_version": 1,
            "base_state": {
                "finding_id": finding.finding_id,
                "sha256": finding.authoring_base_sha256,
            },
            "overrides": overrides,
        },
        indent=2,
        ensure_ascii=False,
    )
    parse_proposal_v1(text, finding.finding_id, finding.authoring_base_sha256)
    return text


def _contract_authoring_lines(contract_path: Path, lane_ids: tuple[str, ...]) -> list[str]:
    payload = _load_object(contract_path, "Deployed UI-Salt contract")
    library = payload.get("function_library")
    lanes = library.get("lanes") if isinstance(library, dict) else None
    if not isinstance(lanes, list):
        raise ValueError("Deployed UI-Salt contract is missing function_library.lanes")

    by_id: dict[str, dict[str, Any]] = {}
    for lane in lanes:
        if isinstance(lane, dict) and isinstance(lane.get("id"), str):
            by_id[lane["id"]] = lane

    lines = [
        "The pipeline runs in this order: source -> shape -> palette -> grading.",
        "This capability profile may select row 0 only, at most once per shipped lane.",
        "Parameters, extra rows, recipes, and graph restructuring are not accepted.",
    ]
    for lane_id in lane_ids:
        lane = by_id.get(lane_id)
        if lane is None:
            raise ValueError(f"Deployed UI-Salt contract is missing lane: {lane_id}")
        label = lane.get("label")
        default = lane.get("default")
        functions = lane.get("functions")
        if not isinstance(label, str) or not label.strip():
            raise ValueError(f"Deployed UI-Salt lane {lane_id} has no authoritative label")
        if not isinstance(default, str) or not default.strip():
            raise ValueError(f"Deployed UI-Salt lane {lane_id} has no default function")
        if not isinstance(functions, list) or not functions:
            raise ValueError(f"Deployed UI-Salt lane {lane_id} has no functions")
        lines.extend(("", f"{label} lane (`{lane_id}`; contract default `{default}`)"))
        for function in functions:
            if not isinstance(function, dict):
                raise ValueError(f"Deployed UI-Salt lane {lane_id} contains an invalid function")
            function_id = function.get("id")
            function_label = function.get("label")
            description = function.get("description")
            if not isinstance(function_id, str) or not function_id.strip():
                raise ValueError(f"Deployed UI-Salt lane {lane_id} contains a function without an id")
            if not isinstance(function_label, str) or not function_label.strip():
                raise ValueError(f"Deployed UI-Salt function {lane_id}/{function_id} has no label")
            if not isinstance(description, str) or not description.strip():
                raise ValueError(f"Deployed UI-Salt function {lane_id}/{function_id} has no description")
            lines.append(f"- `{function_id}` ({function_label}): {description}")
    return lines


def _serialized_draft_lines(state: dict[str, Any]) -> list[str]:
    draft = state.get("color_pipeline_draft")
    if not isinstance(draft, dict):
        return [
            "No explicit `color_pipeline_draft` is serialized in this capture.",
            "On load, the engine rebuilds its live Color Pipeline model from the serialized fractal and parameter state.",
        ]
    lanes = draft.get("lanes")
    if not isinstance(lanes, list):
        raise ValueError("Serialized color_pipeline_draft.lanes must be an array")
    lines = ["The capture serializes these row-0 selections:"]
    for lane in lanes:
        if not isinstance(lane, dict):
            raise ValueError("Serialized color_pipeline_draft lane must be an object")
        lane_id = lane.get("lane_id")
        rows = lane.get("rows")
        if not isinstance(lane_id, str) or not isinstance(rows, list) or not rows:
            raise ValueError("Serialized color_pipeline_draft lane is missing its id or rows")
        row = rows[0]
        if not isinstance(row, dict) or not isinstance(row.get("function_id"), str):
            raise ValueError(f"Serialized Color Pipeline lane {lane_id} has no valid row 0")
        lines.append(f"- `{lane_id}` row 0: `{row['function_id']}`")
    return lines


def build_finding_intake_packet(
    finding: FindingContext,
    runtime_cmd_path: Path = DEFAULT_RUNTIME_CMD,
    job: Optional[JobContext] = None,
) -> PacketContext:
    runtime_cmd_path = runtime_cmd_path.resolve()
    runtime_identity = build_runtime_identity(runtime_cmd_path, runtime_cmd_path.parent)
    resolution = resolve_launcher(runtime_cmd_path)
    if not resolution.ui_salt_contract_path:
        raise ValueError("Published runtime has no deployed UI-Salt contract")
    contract_path = Path(resolution.ui_salt_contract_path)
    catalog = load_lane_catalog_from_ui_salt_contract(contract_path)
    contract_sha256 = sha256_file(contract_path)
    state_text = finding.authoring_base_state_path.read_bytes().decode("utf-8")
    state = loads_no_duplicates(state_text)
    if not isinstance(state, dict):
        raise ValueError("Authoritative finding state.json must be an object")
    if sha256_file(finding.authoring_base_state_path) != finding.authoring_base_sha256:
        raise ValueError("Authoritative finding state.json changed before packet generation")
    review_state_text = None
    review_state = None
    if finding.review_fractal_state_path is not None:
        review_state_text = finding.review_fractal_state_path.read_bytes().decode("utf-8")
        observed_review_sha256 = sha256_file(finding.review_fractal_state_path)
        if observed_review_sha256 != finding.review_fractal_state_sha256:
            raise ValueError("Review-focused fractal-state.json changed before packet generation")
        review_state = loads_no_duplicates(review_state_text)
        if not isinstance(review_state, dict):
            raise ValueError("Review-focused fractal-state.json must be an object")
    fractal_id = state.get("fractal_type")
    if not isinstance(fractal_id, str) or not fractal_id:
        raise ValueError("Authoritative finding state has no fractal_type")
    parameter_authority = capture_fractal_parameter_authority(
        runtime_cmd_path,
        fractal_id,
        state,
        review_state,
        job=job,
    )
    parameter_projection_text = json.dumps(
        parameter_authority.projection,
        indent=2,
        sort_keys=True,
        ensure_ascii=False,
    )
    runtime_summary = {
        "launcher_sha256": runtime_identity.get("launcher_sha256"),
        "resolved_executable_sha256": runtime_identity.get("resolved_executable_sha256"),
        "resolved_executable_file_version": runtime_identity.get("resolved_executable_file_version"),
        "runtime_schema_sha256": runtime_identity.get("runtime_schema_sha256"),
        "source_schema_sha256": runtime_identity.get("source_schema_sha256"),
        "ui_salt_contract_sha256": contract_sha256,
    }
    runtime_identity_sha256 = _canonical_sha256(runtime_summary)
    packet_id = str(uuid.uuid4())
    lane_ids = tuple(lane.lane_id for lane in catalog.lanes)
    authoring_lines = _contract_authoring_lines(contract_path, lane_ids)
    render = state.get("render") if isinstance(state.get("render"), dict) else {}
    params = state.get("params") if isinstance(state.get("params"), dict) else {}
    view = state.get("view") if isinstance(state.get("view"), dict) else {}
    current_max_iter = params.get("max_iter")
    if not isinstance(current_max_iter, int) or isinstance(current_max_iter, bool) or current_max_iter < 1:
        raise ValueError("Authoritative finding state has no valid params.max_iter")
    shape_lane = next((lane for lane in catalog.lanes if lane.lane_id == "shape"), None)
    if shape_lane is None or not shape_lane.function_ids:
        raise ValueError("Deployed UI-Salt contract has no Shape lane functions")
    current_shape = params.get("color_shape")
    example_shape = next(
        (function_id for function_id in shape_lane.function_ids if function_id != current_shape),
        shape_lane.function_ids[0],
    )
    max_iter_example = _proposal_example(finding, {"params.max_iter": current_max_iter + 100})
    lane_example = _proposal_example(
        finding,
        {"color_pipeline_draft": {"lanes": [{"lane_id": "shape", "function_id": example_shape}]}},
    )
    combined_example = _proposal_example(
        finding,
        {
            "params.max_iter": current_max_iter + 100,
            "color_pipeline_draft": {"lanes": [{"lane_id": "shape", "function_id": example_shape}]},
        },
    )
    allowed_triplet_lines = [
        f"- `{signal}` + `{palette}` + `{grading}`"
        for signal, palette, grading in sorted(ALLOWED_COLOR_TRIPLETS)
    ]
    draft_lines = _serialized_draft_lines(state)
    packet_text = "\n".join(
        [
            "# CUDA Fractal Finding — Agent Exploration Packet",
            "",
            "## Behavioral contract — read first",
            "",
            "- This interaction is exploration-first. Discuss the finding before turning it into configuration work.",
            "- Evidence order: attached frame for visual observations; engine-generated parameter projection for",
            "  applicability and parameter properties; `fractal-state.json` for capture-time review values and Color",
            "  Pipeline context; `state.json` for the exact replay base. Engine help or proven comparisons are needed",
            "  for causal claims.",
            "- Do not emit proposal JSON for questions, observations, requests for ideas/options, or exploratory prompts",
            "  such as 'What would you try?', 'Show me a good alternative', or 'Could root proximity help?'. Discuss",
            "  those normally and ask what direction the user wants to take.",
            "- Emit a proposal only when the user explicitly asks to make/generate/return one, asks to apply/try/do a",
            "  specific change, or unambiguously accepts a specific immediately preceding change ('Let's do that').",
            "- If proposal intent is ambiguous, ask one concise clarification question and emit no JSON.",
            "- When triggered, give a short rationale followed by exactly one fenced `json` block containing one object",
            "  whose `proposal_version` is `1`. Do not use `proposal_v1` as the fence language. Do not return a complete",
            "  `state.json`.",
            "- Applicability, co-occurrence, symmetry among values, and suggestive parameter names are not causal proof.",
            "  Keep relationships hypothetical unless engine help text or a proven comparison supports them.",
            "",
            "## What this session is for",
            "",
            "You are helping the user explore the attached CUDA fractal render.",
            "Begin with a curiosity-driven discussion rather than treating this as a form-filling task.",
            "Look at the attached frame and the exact serialized state together. Surface anything mathematically",
            "interesting that is actually visible or state-grounded: symmetry, repetition, self-similar structure,",
            "basin or boundary behavior, unusually sensitive regions, and relationships between the fractal family,",
            "view, iteration settings, and Color Pipeline. Mention noteworthy settings in plain language and explain",
            "what they may be contributing, while clearly separating serialized facts, visual observations, and",
            "tentative interpretation. Do not invent mathematical claims that the frame or state cannot support.",
            "Offer a few promising things to inspect or wonder about and ask questions that help the user choose",
            "where to look next. Discuss interesting regions and possible changes normally with the user; a proposal",
            "is optional until the user wants to try a concrete change.",
            "You may suggest parameter and Color Pipeline directions during that discussion. Follow the behavioral",
            "contract above for the exact transition from discussion to proposal output.",
            "The desktop tool applies the bounded proposal to the exact captured state below and proves the result",
            "through the CUDA engine's existing state loader, Color Pipeline action seam, and action-free replay.",
            "",
            "Attach the finding frame to this conversation separately; the image is not embedded in this text packet.",
            "",
            "## Authoritative evidence appendix",
            "",
            "The remaining sections provide audit and execution authority. They do not change the behavioral contract.",
            "",
            "## State interpretation warning — read this before discussing the math",
            "",
            "`state.json` is the engine's complete replay authority. It intentionally serializes a broad shared",
            "parameter model, including defaults, compatibility mirrors, derived values, and fields owned by other",
            "fractal families. A field's presence in `state.json` does not prove that it affects this render.",
            "",
            "The engine-generated applicable-parameter projection below is the authority for which fractal controls",
            f"belong to `{fractal_id}`. It is produced for this packet from the published runtime's parameter-surface",
            "descriptor and deployed UI schema. Use only controls listed in that projection when discussing fractal",
            "parameters; do not infer applicability from names or from unrelated values in the broad replay state.",
            "Each projected control includes its current value when resolvable, binding/state key, label, help text,",
            "type, defaults, ranges, step, animation/validation metadata, and exact visibility condition.",
            "",
            "`default_visible: false` or a non-default `visibility_surface_id` marks a conditionally applicable control;",
            "read its exact `visible_if` schema property before treating it as active in the captured configuration.",
            "The sibling `fractal-state.json` remains the preferred review source for capture-time values, derived",
            "runtime receipts, and Color Pipeline state. It is not replay input and does not replace the generated",
            "applicability projection.",
            "",
            "Applicability is still not counterfactual sensitivity proof. A correctly applicable control can be inert",
            "under its current value, mode, gate, authority choice, or downstream pipeline selection. Do not translate",
            "a suggestive identifier into undocumented mathematics; describe causal influence only when engine help",
            "text, current gating metadata, or a proven comparison supports it.",
            "A relationship among applicable values—such as conjugate roots, real coefficients, or matching defaults—",
            "may be worth exploring but must remain a hypothesis about the visible frame until that relationship is",
            "documented by the engine or isolated by a comparison.",
            "",
            "Phrase conclusions at the right confidence level:",
            "- serialized fact: the field or sidecar reports a value;",
            "- visual observation: a feature is visible in the attached frame;",
            "- grounded inference: engine metadata or proven behavior supports a relationship;",
            "- hypothesis: an interesting possibility to test, not a claim about what caused this frame.",
            "",
            "## Engine-generated applicable fractal parameters",
            "",
            f"- selected fractal: `{fractal_id}`",
            f"- parameter-surface SHA-256: `{parameter_authority.parameter_surface_sha256}`",
            f"- deployed UI-schema SHA-256: `{parameter_authority.runtime_schema_sha256}`",
            "",
            "```json",
            parameter_projection_text,
            "```",
            "",
            "## Current finding",
            "",
            f"- Fractal family: `{state.get('fractal_type', 'unknown')}`",
            f"- Render: `{render.get('width', '?')} × {render.get('height', '?')}` on device `{render.get('device_id', '?')}`",
            f"- Iterations: `{current_max_iter}`",
            f"- Automatic iteration adjustment: `{view.get('auto_max_iter', 'not serialized')}`",
            f"- Serialized color tuple: `{params.get('color_signal', '?')} -> {params.get('color_shape', '?')} -> {params.get('color_palette', '?')} -> {params.get('color_grading', '?')}`",
            "",
            "### Serialized Color Pipeline state",
            "",
            *draft_lines,
            "",
            "## Exact authoritative engine state",
            "",
            "The JSON below is the exact UTF-8 `state.json` captured by the engine and bound by this packet.",
            "It is the base state, not a proposal and not a Python reconstruction.",
            "",
            "```json",
            state_text.rstrip("\r\n"),
            "```",
            "",
            "## Exact review-focused active-state sidecar",
            "",
            *(
                [
                    "This is the exact engine-captured `fractal-state.json`. It is review guidance, not replay input,",
                    "and must be interpreted with the limitations above.",
                    "",
                    "```json",
                    review_state_text.rstrip("\r\n"),
                    "```",
                ]
                if review_state_text is not None
                else [
                    "No `fractal-state.json` accompanied this capture. Applicability cannot be inferred from the broad",
                    "replay state alone; keep parameter-to-image explanations tentative unless separately grounded.",
                ]
            ),
            "",
            "## What a proposal may change",
            "",
            f"- `params.max_iter`: positive integer; current value `{current_max_iter}`.",
            f"- `params.color_shape`: `identity` or `repeat`; current value `{params.get('color_shape', '?')}`.",
            "- `params.color_signal`, `params.color_palette`, and `params.color_grading`: all three must be supplied together as one replay-proven tuple.",
            "- `color_pipeline_draft.lanes`: one optional `{lane_id, function_id}` row-0 selection per shipped lane.",
            "- Scalar overrides are applied to the captured base before Color Pipeline row-0 selection actions.",
            "",
            "Replay-proven scalar color tuples (the engine still rejects tuples incompatible with this fractal family):",
            *allowed_triplet_lines,
            "",
            "## Color Pipeline functions",
            "",
            *authoring_lines,
            "",
            "## Exact proposal schema",
            "",
            "Return the JSON object inside one code block. The desktop proposal editor receives the JSON itself.",
            "`base_state.finding_id` and `base_state.sha256` must remain exactly as shown.",
            "`overrides` may contain only the bounded paths described above.",
            "",
            "### Example A — iteration change",
            "```json",
            max_iter_example,
            "```",
            "",
            "### Example B — one Color Pipeline row-0 selection",
            "```json",
            lane_example,
            "```",
            "",
            "### Example C — combined scalar and Color Pipeline change",
            "```json",
            combined_example,
            "```",
            "",
            "These examples were generated and accepted by the same `proposal_v1` parser used by the desktop tool.",
            "",
            "## Exact machine binding and provenance",
            "",
            f"- packet_version: `{PACKET_VERSION}`",
            f"- packet_id: `{packet_id}`",
            f"- capability_profile: `{CAPABILITY_PROFILE}`",
            f"- finding_id: `{finding.finding_id}`",
            f"- authoring_base_sha256: `{finding.authoring_base_sha256}`",
            f"- review_fractal_state_sha256: `{finding.review_fractal_state_sha256 or 'not-present'}`",
            f"- runtime_identity_sha256: `{runtime_identity_sha256}`",
            f"- ui_salt_contract_sha256: `{contract_sha256}`",
            f"- parameter_surface_sha256: `{parameter_authority.parameter_surface_sha256}`",
            "",
            "The exact copied packet payload is hashed and retained by the desktop tool. A later proof request must",
            "bind this packet, this base state, this runtime and contract identity, and the exact pasted proposal text.",
        ]
    )
    packet_sha256 = hashlib.sha256(packet_text.encode("utf-8")).hexdigest()
    packet_dir = finding.import_result.finding_dir / "packets" / packet_id
    packet_path = packet_dir / "packet.txt"
    manifest_path = packet_dir / "manifest.json"
    manifest = {
        "packet_version": PACKET_VERSION,
        "packet_id": packet_id,
        "packet_sha256": packet_sha256,
        "capability_profile": CAPABILITY_PROFILE,
        "finding_id": finding.finding_id,
        "authoring_base_sha256": finding.authoring_base_sha256,
        "review_fractal_state_sha256": finding.review_fractal_state_sha256,
        "runtime_identity": runtime_summary,
        "runtime_identity_sha256": runtime_identity_sha256,
        "ui_salt_contract_sha256": contract_sha256,
        "parameter_surface_sha256": parameter_authority.parameter_surface_sha256,
        "parameter_surface_path": "parameter-surface.json",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "packet_path": "packet.txt",
    }
    _atomic_write_text(packet_path, packet_text)
    _atomic_write_text(packet_dir / "parameter-surface.json", parameter_authority.parameter_surface_text)
    _atomic_write_text(manifest_path, json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return PacketContext(
        packet_id=packet_id,
        packet_sha256=packet_sha256,
        capability_profile=CAPABILITY_PROFILE,
        packet_text=packet_text,
        packet_path=packet_path.resolve(),
        manifest_path=manifest_path.resolve(),
        runtime_identity_sha256=runtime_identity_sha256,
        ui_salt_contract_sha256=contract_sha256,
        parameter_surface_sha256=parameter_authority.parameter_surface_sha256,
    )
