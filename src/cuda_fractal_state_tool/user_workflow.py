from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from .agent_bundle import AgentBundle, load_existing_agent_bundle
from .finding_workspace import FINDINGS_INDEX_FILENAME, ImportResult, SourceCaptureImporter
from .json_utils import loads_no_duplicates
from .preview_service import PreviewResult
from .runtime_surface import sha256_file
from .state_override_proof import StateOverrideProofResult


class SessionState(str, Enum):
    EMPTY = "EMPTY"
    FINDING_READY = "FINDING_READY"
    PACKET_READY = "PACKET_READY"
    OVERRIDE_DIRTY = "OVERRIDE DIRTY"
    PROVING = "PROVING"
    OVERRIDE_ACCEPTED = "OVERRIDE ACCEPTED"
    REPLAY_PROVEN = "REPLAY PROVEN"
    VISUAL_REVIEW_PENDING = "VISUAL REVIEW PENDING"
    USER_ACCEPTED = "USER ACCEPTED"
    REVISION_NEEDED = "REVISION NEEDED"
    LAUNCH_READY = "LAUNCH READY"
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
class ExistingPacketContext:
    finding: FindingContext
    bundle: AgentBundle


@dataclass
class UserWorkflowSession:
    generation: int = 0
    state: SessionState = SessionState.EMPTY
    finding: Optional[FindingContext] = None
    bundle: Optional[AgentBundle] = None
    preview: Optional[PreviewResult] = None
    override_text: str = ""
    proof_result: Optional[StateOverrideProofResult] = None
    candidate_preview: Optional[PreviewResult] = None
    review_decision: Optional[str] = None
    status_text: str = "Choose a captured finding to begin."

    def _unproven_state(self) -> SessionState:
        if self.override_text.strip() and self.bundle is not None:
            return SessionState.OVERRIDE_DIRTY
        if self.bundle is not None:
            return SessionState.PACKET_READY
        if self.finding is not None:
            return SessionState.FINDING_READY
        return SessionState.EMPTY

    def _invalidate_proof(self) -> None:
        self.proof_result = None
        self.candidate_preview = None
        self.review_decision = None

    def begin_finding_change(self) -> int:
        self.generation += 1
        self.finding = None
        self.bundle = None
        self.preview = None
        self._invalidate_proof()
        self.state = SessionState.EMPTY
        self.status_text = (
            "Loading finding; retained override text will require a new exact bundle binding."
            if self.override_text.strip()
            else "Loading finding…"
        )
        return self.generation

    def accept_finding(self, finding: FindingContext) -> None:
        self.finding = finding
        self.bundle = None
        self.preview = None
        self._invalidate_proof()
        self.state = SessionState.FINDING_READY
        self.status_text = "Finding ready. Building its exact Agent Bundle V8…"

    def accept_preview(self, preview: PreviewResult) -> None:
        self.preview = preview

    def accept_bundle(self, bundle: AgentBundle) -> None:
        self.bundle = bundle
        self._invalidate_proof()
        self.state = self._unproven_state()
        self.status_text = (
            "Exact Agent Bundle V8 ready; retained override text is dirty against this new binding."
            if self.override_text.strip()
            else "Exact Agent Bundle V8 ready for drag-all handoff."
        )

    def set_override_text(self, override_text: str) -> None:
        if override_text == self.override_text:
            return
        self.override_text = override_text
        self._invalidate_proof()
        self.state = self._unproven_state()
        if override_text.strip() and self.bundle is not None:
            self.status_text = "State override changed. Validate and replay-prove this exact text."
        elif self.bundle is not None:
            self.status_text = "Exact Agent Bundle V8 ready; paste a sparse state override when desired."
        elif self.finding is not None:
            self.status_text = "Finding ready. Building its exact Agent Bundle V8…"
        else:
            self.status_text = "Choose a captured finding to begin."

    def begin_proof(self) -> None:
        if self.finding is None or self.bundle is None or not self.override_text.strip():
            raise ValueError("A finding, exact Agent Bundle, and state override are required before proof")
        self._invalidate_proof()
        self.state = SessionState.PROVING
        self.status_text = "Validating the sparse override and proving the complete merged state through the engine…"

    def accept_proof_result(self, result: StateOverrideProofResult) -> None:
        self.proof_result = result
        self.review_decision = None
        if result.status == "replay_proven":
            self.state = SessionState.VISUAL_REVIEW_PENDING
            self.status_text = (
                "Exact base replay proven. Review it and explicitly acknowledge the unchanged-state replay."
                if getattr(result, "empty_override_byte_exact", False)
                else "Override accepted and replay proven. Review the candidate frame before launch."
            )
        else:
            self.state = SessionState.REJECTED
            self.status_text = "State override rejected. Review the preserved proof error."

    def accept_candidate_preview(self, preview: PreviewResult) -> None:
        self.candidate_preview = preview

    def record_review(self, decision: str) -> None:
        if self.proof_result is None or self.proof_result.status != "replay_proven":
            raise ValueError("A replay-proven candidate is required before visual review")
        if decision == "accepted":
            self.review_decision = decision
            self.state = SessionState.USER_ACCEPTED
            self.status_text = (
                "Exact base replay acknowledged; rechecking exact launch readiness…"
                if getattr(self.proof_result, "empty_override_byte_exact", False)
                else "Candidate accepted by the user; rechecking exact launch readiness…"
            )
        elif decision == "revision_needed":
            self.review_decision = decision
            self.state = SessionState.REVISION_NEEDED
            self.status_text = "Revision requested. Edit the override to create a new immutable proof attempt."
        else:
            raise ValueError("Unknown review decision")

    def mark_launch_ready(self) -> None:
        if self.review_decision != "accepted":
            raise ValueError("User acceptance is required before launch readiness")
        self.state = SessionState.LAUNCH_READY
        self.status_text = (
            "Acknowledged base replay is launch-ready; launch will recheck every binding and hash."
            if getattr(self.proof_result, "empty_override_byte_exact", False)
            else "Exact candidate is launch-ready; launch will recheck every binding and hash."
        )

    def reset(self) -> None:
        self.generation += 1
        self.state = SessionState.EMPTY
        self.finding = None
        self.bundle = None
        self.preview = None
        self.override_text = ""
        self._invalidate_proof()
        self.status_text = "Session reset. Durable findings, bundles, proofs, and preview caches were preserved."


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
    return _load_finding_context_from_import(import_result, workspace_root.resolve())


def _load_finding_context_from_import(
    import_result: ImportResult,
    workspace_root: Path,
) -> FindingContext:
    manifest = _load_object(import_result.workspace_manifest_path, "Finding workspace manifest")
    finding_dir = import_result.finding_dir.resolve()
    authoring_base = manifest.get("authoring_base")
    if not isinstance(authoring_base, dict):
        raise ValueError("Finding workspace manifest is missing authoring_base")
    state_path = _resolve_artifact(finding_dir, authoring_base.get("state_path"), "authoring base")
    if state_path is None:
        raise ValueError("Finding workspace manifest is missing authoring base state path")
    if sha256_file(state_path) != import_result.authoring_base_state_sha256:
        raise ValueError("Imported authoring base hash changed after workspace import")

    source_artifacts = manifest.get("source_artifacts")
    if not isinstance(source_artifacts, dict):
        raise ValueError("Finding workspace manifest is missing source_artifacts")
    frame_entry = source_artifacts.get("primary_frame")
    frame_path = (
        _resolve_artifact(finding_dir, frame_entry.get("workspace_path"), "primary frame")
        if isinstance(frame_entry, dict)
        else None
    )
    review_entry = source_artifacts.get("review_fractal_state")
    review_path = None
    review_sha256 = None
    if isinstance(review_entry, dict):
        review_path = _resolve_artifact(
            finding_dir, review_entry.get("workspace_path"), "review-focused fractal state"
        )
        if review_path is not None:
            review_sha256 = sha256_file(review_path)
            if review_entry.get("sha256") != review_sha256:
                raise ValueError("Review-focused fractal-state.json hash changed after workspace import")
            review_state = _load_object(review_path, "Review-focused fractal state")
            if review_state.get("schema_id") != "viewer.finding_fractal_state.v1":
                raise ValueError("Unsupported review-focused fractal-state.json schema_id")

    state = _load_object(state_path, "Authoring base state")
    render = state.get("render") if isinstance(state.get("render"), dict) else {}
    params = state.get("params") if isinstance(state.get("params"), dict) else {}
    view = state.get("view") if isinstance(state.get("view"), dict) else {}
    summary_lines = [
        f"Finding ID: {import_result.finding_id}",
        f"Authoring base SHA-256: {import_result.authoring_base_state_sha256}",
        f"Fractal family: {state.get('fractal_type', 'unknown')}",
        f"Render: {render.get('width', '?')} × {render.get('height', '?')} | device {render.get('device_id', '?')}",
        f"Iterations: {params.get('max_iter', '?')} | auto: {view.get('auto_max_iter', '?')}",
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


def load_existing_packet_context(packet_dir: Path) -> ExistingPacketContext:
    """Bind an existing immutable packet to its durable finding without regeneration."""
    bundle = load_existing_agent_bundle(packet_dir)
    resolved_packet_dir = bundle.packet_dir.resolve()
    packets_dir = resolved_packet_dir.parent
    finding_dir = packets_dir.parent
    findings_dir = finding_dir.parent
    workspace_root = findings_dir.parent
    if packets_dir.name != "packets" or findings_dir.name != "findings":
        raise ValueError(
            "Existing agent packet must use <workspace>/findings/<finding-id>/packets/<packet-id>"
        )
    if finding_dir.name != bundle.finding_id:
        raise ValueError("Agent packet finding_id does not match its durable finding directory")
    workspace_manifest_path = finding_dir / "workspace.json"
    workspace_manifest = _load_object(workspace_manifest_path, "Finding workspace manifest")
    if workspace_manifest.get("finding_id") != bundle.finding_id:
        raise ValueError("Agent packet finding_id disagrees with the durable workspace manifest")
    authoring_base = workspace_manifest.get("authoring_base")
    if not isinstance(authoring_base, dict) or not isinstance(authoring_base.get("sha256"), str):
        raise ValueError("Finding workspace manifest has no authoring-base hash")
    manifest = _load_object(bundle.manifest_path, "Agent packet manifest")
    authority_identities = manifest.get("authority_identities")
    if not isinstance(authority_identities, dict):
        raise ValueError("Agent packet manifest has no authority_identities")
    if authority_identities.get("state_sha256") != authoring_base["sha256"]:
        raise ValueError("Agent packet base state does not match its durable finding")
    import_result = ImportResult(
        finding_id=bundle.finding_id,
        finding_dir=finding_dir,
        workspace_manifest_path=workspace_manifest_path,
        findings_index_path=workspace_root / FINDINGS_INDEX_FILENAME,
        workspace_index_updated=(workspace_root / FINDINGS_INDEX_FILENAME).is_file(),
        authoring_base_state_sha256=authoring_base["sha256"],
    )
    finding = _load_finding_context_from_import(import_result, workspace_root)
    state = _load_object(finding.authoring_base_state_path, "Authoring base state")
    if state.get("fractal_type") != bundle.selected_fractal_type:
        raise ValueError("Agent packet selected fractal disagrees with its durable authoring base")
    return ExistingPacketContext(finding=finding, bundle=bundle)
