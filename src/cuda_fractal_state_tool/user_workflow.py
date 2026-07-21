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

from .finding_workspace import ImportResult, SourceCaptureImporter
from .json_utils import loads_no_duplicates
from .lane_catalog import load_lane_catalog_from_ui_salt_contract
from .preview_service import PreviewResult
from .runtime_surface import DEFAULT_RUNTIME_CMD, build_runtime_identity, resolve_launcher, sha256_file


CAPABILITY_PROFILE = "finding-color-first-row-v1"
PACKET_VERSION = 1


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


@dataclass
class UserWorkflowSession:
    generation: int = 0
    state: SessionState = SessionState.EMPTY
    finding: Optional[FindingContext] = None
    packet: Optional[PacketContext] = None
    preview: Optional[PreviewResult] = None
    proposal_text: str = ""
    status_text: str = "Choose a captured finding to begin."

    def begin_finding_change(self) -> int:
        self.generation += 1
        retained_proposal = self.proposal_text
        self.finding = None
        self.packet = None
        self.preview = None
        self.state = SessionState.EMPTY
        self.status_text = "Loading finding…"
        if retained_proposal:
            self.status_text = "Loading finding; existing proposal will require a new packet binding."
        return self.generation

    def accept_finding(self, finding: FindingContext) -> None:
        self.finding = finding
        self.packet = None
        self.preview = None
        self.state = SessionState.PROPOSAL_DIRTY if self.proposal_text.strip() else SessionState.FINDING_READY
        self.status_text = "Finding ready. Build its exact intake packet."

    def accept_preview(self, preview: PreviewResult) -> None:
        self.preview = preview

    def accept_packet(self, packet: PacketContext) -> None:
        self.packet = packet
        self.state = SessionState.PROPOSAL_DIRTY if self.proposal_text.strip() else SessionState.PACKET_READY
        self.status_text = "Exact intake packet ready to copy."

    def set_proposal_text(self, proposal_text: str) -> None:
        if proposal_text == self.proposal_text:
            return
        self.proposal_text = proposal_text
        if proposal_text.strip() and self.finding is not None:
            self.state = SessionState.PROPOSAL_DIRTY
            self.status_text = "Proposal changed. Operational proof remains disabled until shell acceptance."
        elif self.packet is not None:
            self.state = SessionState.PACKET_READY
            self.status_text = "Exact intake packet ready to copy."
        elif self.finding is not None:
            self.state = SessionState.FINDING_READY
            self.status_text = "Finding ready. Build its exact intake packet."
        else:
            self.state = SessionState.EMPTY
            self.status_text = "Choose a captured finding to begin."

    def reset(self) -> None:
        self.generation += 1
        self.state = SessionState.EMPTY
        self.finding = None
        self.packet = None
        self.preview = None
        self.proposal_text = ""
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
        f"Workspace index: {'updated' if import_result.workspace_index_updated else 'imported; index update failed'}",
    ]
    return FindingContext(
        import_result=import_result,
        workspace_root=workspace_root.resolve(),
        workspace_manifest=manifest,
        authoring_base_state_path=state_path,
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


def build_finding_intake_packet(
    finding: FindingContext,
    runtime_cmd_path: Path = DEFAULT_RUNTIME_CMD,
) -> PacketContext:
    runtime_cmd_path = runtime_cmd_path.resolve()
    runtime_identity = build_runtime_identity(runtime_cmd_path, runtime_cmd_path.parent)
    resolution = resolve_launcher(runtime_cmd_path)
    if not resolution.ui_salt_contract_path:
        raise ValueError("Published runtime has no deployed UI-Salt contract")
    contract_path = Path(resolution.ui_salt_contract_path)
    catalog = load_lane_catalog_from_ui_salt_contract(contract_path)
    contract_sha256 = sha256_file(contract_path)
    runtime_summary = {
        "launcher_sha256": runtime_identity.get("launcher_sha256"),
        "resolved_executable_sha256": runtime_identity.get("resolved_executable_sha256"),
        "ui_salt_contract_sha256": contract_sha256,
    }
    runtime_identity_sha256 = _canonical_sha256(runtime_summary)
    packet_id = str(uuid.uuid4())
    lane_lines = [
        f"- {lane.lane_id}: {', '.join(lane.function_ids)}"
        for lane in catalog.lanes
    ]
    packet_text = "\n".join(
        [
            "CUDA Fractal Finding Intake Packet",
            "",
            f"packet_version: {PACKET_VERSION}",
            f"packet_id: {packet_id}",
            f"capability_profile: {CAPABILITY_PROFILE}",
            "",
            "Exact binding",
            f"- finding_id: {finding.finding_id}",
            f"- authoring_base_sha256: {finding.authoring_base_sha256}",
            f"- runtime_identity_sha256: {runtime_identity_sha256}",
            f"- ui_salt_contract_sha256: {contract_sha256}",
            "",
            "Task",
            "Return one proposal_v1 JSON object only. Do not return a full engine state.",
            "Keep base_state.finding_id and base_state.sha256 exactly equal to this packet binding.",
            "",
            "Supported Color Pipeline authoring",
            "Use color_pipeline_draft.lanes only for first-row function selections.",
            "Each lane may appear at most once and contain only lane_id and function_id.",
            "Parameters, row operations, recipes, and arbitrary graph editing are unsupported.",
            *lane_lines,
            "",
            "Existing bounded overrides",
            "- params.max_iter",
            "- params.color_shape",
            "- coupled params.color_signal + params.color_palette + params.color_grading",
            "",
            "Required envelope",
            "{",
            '  "proposal_version": 1,',
            '  "base_state": {',
            f'    "finding_id": "{finding.finding_id}",',
            f'    "sha256": "{finding.authoring_base_sha256}"',
            "  },",
            '  "overrides": {}',
            "}",
            "",
            "The desktop shell can receive this proposal, but proof execution remains disabled until interaction-model acceptance.",
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
        "runtime_identity": runtime_summary,
        "runtime_identity_sha256": runtime_identity_sha256,
        "ui_salt_contract_sha256": contract_sha256,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "packet_path": "packet.txt",
    }
    _atomic_write_text(packet_path, packet_text)
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
    )
