from __future__ import annotations

import argparse
import hashlib
import os
import queue
from pathlib import Path
from typing import Callable, Optional

from PIL import Image, ImageTk

from .agent_bundle import (
    AgentBundle,
    build_agent_bundle,
    copy_agent_packet,
    load_agent_bundle_handoff,
    open_agent_bundle_folder,
)
from .async_jobs import AsyncJobRunner, JobOutcome, JobRequestIdentity, WorkerQueueFullError
from .preview_service import PreviewService
from .runtime_surface import DEFAULT_RUNTIME_CMD
from .state_override_proof import (
    StateOverrideProofResult,
    execute_state_override_proof,
    launch_state_override_candidate,
    record_state_override_review,
    validate_state_override_launch_readiness,
)
from .user_workflow import FindingContext, SessionState, UserWorkflowSession, load_finding_context


DEFAULT_FINDING_WORKSPACE = Path(r"D:\salt-fractal\cuda-fractal-engine-state-tool")


class UserWorkflowApp:
    def __init__(
        self,
        root,
        runtime_cmd_path: Path = DEFAULT_RUNTIME_CMD,
        workspace_root: Path = DEFAULT_FINDING_WORKSPACE,
        runner: Optional[AsyncJobRunner] = None,
        preview_service: Optional[PreviewService] = None,
    ) -> None:
        import tkinter as tk
        from tkinter import ttk

        self.root = root
        self.tk = tk
        self.ttk = ttk
        self.runtime_cmd_path = runtime_cmd_path.resolve()
        self.session = UserWorkflowSession()
        self.preview_service = preview_service or PreviewService()
        self._completion_queue: queue.Queue[Callable[[], None]] = queue.Queue()
        self.runner = runner or AsyncJobRunner(self._completion_queue.put)
        self._owns_runner = runner is None
        self._busy_kinds: set[str] = set()
        self._base_preview_photo = None
        self._candidate_preview_photo = None
        self._candidate_full_frame_opened = False
        self._setting_override = False
        self._last_copyable_error = ""
        self._closed = False

        self.source_path_var = tk.StringVar(value="")
        self.workspace_root_var = tk.StringVar(value=str(workspace_root.resolve()))
        self.state_var = tk.StringVar(value=SessionState.EMPTY.value)
        self.status_var = tk.StringVar(value=self.session.status_text)
        self.binding_var = tk.StringVar(value="No Agent Bundle V6 binding yet.")
        self.packet_info_var = tk.StringVar(value="Bundle is generated automatically after finding import.")
        self.attachment_var = tk.StringVar(value="Required attachments will appear here.")
        self.preview_status_var = tk.StringVar(value="No finding frame loaded.")
        self.candidate_preview_status_var = tk.StringVar(value="No candidate frame yet.")
        self.changed_paths_var = tk.StringVar(value="No override changes have been proven.")

        self._configure_root()
        self._build_shell()
        self._render()
        self.root.after(25, self._drain_completions)
        self.root.protocol("WM_DELETE_WINDOW", self.close)

    def _configure_root(self) -> None:
        self.root.title("CUDA Fractal State Tool — Finding State Override")
        self.root.geometry("1480x940")
        self.root.minsize(1120, 720)
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=1)

    def _build_shell(self) -> None:
        ttk = self.ttk
        header = ttk.Frame(self.root, padding=(12, 10, 12, 6))
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(1, weight=1)
        ttk.Label(
            header,
            text="Exact Base State + Sparse Override → Engine Candidate → Visual Review",
            font=("Segoe UI", 15, "bold"),
        ).grid(row=0, column=0, sticky="w")
        ttk.Label(header, textvariable=self.state_var, padding=(10, 4)).grid(row=0, column=1, sticky="e")
        self.reset_button = ttk.Button(header, text="Reset Session", command=self.reset_session)
        self.reset_button.grid(row=0, column=2, sticky="e", padx=(12, 0))

        self.panes = ttk.PanedWindow(self.root, orient="horizontal")
        self.panes.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 8))
        self.left = ttk.Frame(self.panes, padding=8)
        self.right = ttk.Frame(self.panes, padding=8)
        self.panes.add(self.left, weight=1)
        self.panes.add(self.right, weight=1)
        self._build_finding_side()
        self._build_override_side()

        footer = ttk.Frame(self.root, padding=(12, 4, 12, 10))
        footer.grid(row=2, column=0, sticky="ew")
        footer.columnconfigure(0, weight=1)
        ttk.Label(footer, textvariable=self.status_var, wraplength=1280).grid(row=0, column=0, sticky="w")
        self.copy_error_button = ttk.Button(footer, text="Copy Error", command=self.copy_last_error)
        self.copy_error_button.grid(row=0, column=1, sticky="e", padx=(8, 0))

    def _build_finding_side(self) -> None:
        from tkinter.scrolledtext import ScrolledText

        ttk = self.ttk
        self.left.columnconfigure(0, weight=1)
        self.left.rowconfigure(2, weight=2)
        self.left.rowconfigure(3, weight=4)

        source = ttk.LabelFrame(self.left, text="1. Finding intake", padding=8)
        source.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        source.columnconfigure(1, weight=1)
        ttk.Label(source, text="Capture source").grid(row=0, column=0, sticky="w", padx=(0, 8))
        ttk.Entry(source, textvariable=self.source_path_var).grid(row=0, column=1, sticky="ew")
        ttk.Button(source, text="Browse File…", command=self._browse_file).grid(row=0, column=2, padx=(6, 0))
        ttk.Button(source, text="Browse Folder…", command=self._browse_folder).grid(row=0, column=3, padx=(6, 0))
        ttk.Label(source, text="Durable workspace").grid(row=1, column=0, sticky="w", padx=(0, 8), pady=(6, 0))
        ttk.Entry(source, textvariable=self.workspace_root_var).grid(
            row=1, column=1, columnspan=2, sticky="ew", pady=(6, 0)
        )
        ttk.Button(source, text="Browse…", command=self._browse_workspace).grid(
            row=1, column=3, padx=(6, 0), pady=(6, 0)
        )
        self.open_finding_button = ttk.Button(source, text="Open Finding", command=self.open_finding)
        self.open_finding_button.grid(row=2, column=0, columnspan=4, sticky="ew", pady=(8, 0))
        ttk.Label(
            source,
            text="The capture remains read-only; exact artifacts are mirrored into the durable workspace.",
            wraplength=620,
        ).grid(row=3, column=0, columnspan=4, sticky="w", pady=(6, 0))

        summary = ttk.LabelFrame(self.left, text="2. Finding context", padding=8)
        summary.grid(row=1, column=0, sticky="nsew", pady=(0, 8))
        summary.columnconfigure(0, weight=1)
        summary.rowconfigure(0, weight=1)
        self.summary_text = ScrolledText(summary, height=7, wrap="word", state="disabled")
        self.summary_text.grid(row=0, column=0, sticky="nsew")

        preview = ttk.LabelFrame(self.left, text="Base frame preview (bounded derivative)", padding=8)
        preview.grid(row=2, column=0, sticky="nsew", pady=(0, 8))
        preview.columnconfigure(0, weight=1)
        preview.rowconfigure(0, weight=1)
        self.preview_label = ttk.Label(preview, text="No preview", anchor="center")
        self.preview_label.grid(row=0, column=0, sticky="nsew")
        preview_controls = ttk.Frame(preview)
        preview_controls.grid(row=1, column=0, sticky="ew", pady=(6, 0))
        preview_controls.columnconfigure(0, weight=1)
        ttk.Label(preview_controls, textvariable=self.preview_status_var).grid(row=0, column=0, sticky="w")
        self.open_full_frame_button = ttk.Button(
            preview_controls, text="Open Full Base Frame", command=self.open_full_frame
        )
        self.open_full_frame_button.grid(row=0, column=1, sticky="e")

        packet = ttk.LabelFrame(self.left, text="3. Exact Agent Bundle V6", padding=8)
        packet.grid(row=3, column=0, sticky="nsew")
        packet.columnconfigure(0, weight=1)
        packet.rowconfigure(2, weight=1)
        packet_actions = ttk.Frame(packet)
        packet_actions.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        packet_actions.columnconfigure(1, weight=1)
        self.build_packet_button = ttk.Button(packet_actions, text="Refresh Bundle", command=self.build_packet)
        self.build_packet_button.grid(row=0, column=0, sticky="w")
        ttk.Label(packet_actions, textvariable=self.packet_info_var).grid(row=0, column=1, sticky="e", padx=8)
        self.copy_packet_button = ttk.Button(packet_actions, text="Copy Packet", command=self.copy_packet)
        self.copy_packet_button.grid(row=0, column=2, sticky="e", padx=(0, 6))
        self.open_bundle_button = ttk.Button(
            packet_actions, text="Open Agent Bundle Folder", command=self.open_bundle_folder
        )
        self.open_bundle_button.grid(row=0, column=3, sticky="e")
        ttk.Label(packet, textvariable=self.attachment_var, wraplength=640).grid(
            row=1, column=0, sticky="w", pady=(0, 6)
        )
        self.packet_text = ScrolledText(packet, height=16, wrap="word", state="disabled")
        self.packet_text.grid(row=2, column=0, sticky="nsew")

    def _build_override_side(self) -> None:
        from tkinter.scrolledtext import ScrolledText

        ttk = self.ttk
        self.right.columnconfigure(0, weight=1)
        self.right.rowconfigure(1, weight=3)
        self.right.rowconfigure(3, weight=3)
        self.right.rowconfigure(4, weight=2)

        binding = ttk.LabelFrame(self.right, text="Exact bundle binding", padding=8)
        binding.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        binding.columnconfigure(0, weight=1)
        ttk.Label(binding, textvariable=self.binding_var, wraplength=670).grid(row=0, column=0, sticky="w")

        override = ttk.LabelFrame(self.right, text="4. Incoming State Override JSON", padding=8)
        override.grid(row=1, column=0, sticky="nsew", pady=(0, 8))
        override.columnconfigure(0, weight=1)
        override.rowconfigure(0, weight=1)
        self.override_text = ScrolledText(override, height=17, wrap="none", undo=True)
        self.override_text.grid(row=0, column=0, sticky="nsew")
        self.override_text.bind("<<Modified>>", self._override_modified)
        ttk.Label(
            override,
            text="Starts empty. Paste one sparse state-shaped JSON object—no envelope, hashes, or action commands.",
            wraplength=670,
        ).grid(row=1, column=0, sticky="w", pady=(6, 0))

        actions = ttk.LabelFrame(self.right, text="5. Validate and replay-prove", padding=8)
        actions.grid(row=2, column=0, sticky="ew", pady=(0, 8))
        actions.columnconfigure(0, weight=1)
        self.prove_button = ttk.Button(actions, text="Validate & Replay Prove", command=self.prove_override)
        self.prove_button.grid(row=0, column=0, sticky="ew")
        ttk.Label(actions, textvariable=self.changed_paths_var, wraplength=670).grid(
            row=1, column=0, sticky="w", pady=(7, 0)
        )

        candidate = ttk.LabelFrame(self.right, text="6. Engine-emitted candidate preview", padding=8)
        candidate.grid(row=3, column=0, sticky="nsew", pady=(0, 8))
        candidate.columnconfigure(0, weight=1)
        candidate.rowconfigure(0, weight=1)
        self.candidate_preview_label = ttk.Label(candidate, text="No candidate", anchor="center")
        self.candidate_preview_label.grid(row=0, column=0, sticky="nsew")
        candidate_controls = ttk.Frame(candidate)
        candidate_controls.grid(row=1, column=0, sticky="ew", pady=(6, 0))
        candidate_controls.columnconfigure(0, weight=1)
        ttk.Label(candidate_controls, textvariable=self.candidate_preview_status_var).grid(
            row=0, column=0, columnspan=4, sticky="w", pady=(0, 6)
        )
        self.open_candidate_frame_button = ttk.Button(
            candidate_controls, text="Open Full Candidate", command=self.open_candidate_frame
        )
        self.open_candidate_frame_button.grid(row=1, column=0, sticky="ew", padx=(0, 3))
        self.accept_button = ttk.Button(candidate_controls, text="Accept Candidate", command=self.accept_candidate)
        self.accept_button.grid(row=1, column=1, sticky="ew", padx=3)
        self.revision_button = ttk.Button(
            candidate_controls, text="Revision Needed", command=self.request_revision
        )
        self.revision_button.grid(row=1, column=2, sticky="ew", padx=3)
        self.launch_button = ttk.Button(
            candidate_controls, text="Launch Accepted State", command=self.launch_accepted_state
        )
        self.launch_button.grid(row=1, column=3, sticky="ew", padx=(3, 0))
        for column in range(4):
            candidate_controls.columnconfigure(column, weight=1)

        proof = ttk.LabelFrame(self.right, text="Proof and review status", padding=8)
        proof.grid(row=4, column=0, sticky="nsew")
        proof.columnconfigure(0, weight=1)
        proof.rowconfigure(0, weight=1)
        self.proof_text = ScrolledText(proof, height=10, wrap="word", state="disabled")
        self.proof_text.grid(row=0, column=0, sticky="nsew")
        self._set_text(
            self.proof_text,
            "No proof has run. Paste a sparse state override after the exact Agent Bundle V6 is ready.",
        )

    def _browse_file(self) -> None:
        from tkinter import filedialog

        path = filedialog.askopenfilename(
            title="Choose finding state, manifest, or frame",
            filetypes=[("Finding artifacts", "*.json *.png *.bmp *.jpg *.jpeg"), ("All files", "*.*")],
        )
        if path:
            self.source_path_var.set(path)

    def _browse_folder(self) -> None:
        from tkinter import filedialog

        path = filedialog.askdirectory(title="Choose capture bundle folder")
        if path:
            self.source_path_var.set(path)

    def _browse_workspace(self) -> None:
        from tkinter import filedialog

        path = filedialog.askdirectory(title="Choose initialized durable workspace")
        if path:
            self.workspace_root_var.set(path)

    def open_finding_path(self, source_path: Path, workspace_root: Optional[Path] = None) -> None:
        self.source_path_var.set(str(source_path))
        if workspace_root is not None:
            self.workspace_root_var.set(str(workspace_root))
        self.open_finding()

    def open_finding(self) -> None:
        source_text = self.source_path_var.get().strip()
        workspace_text = self.workspace_root_var.get().strip()
        if not source_text or not workspace_text:
            self._set_error("Capture source and durable workspace are both required.")
            return
        self.runner.cancel_all()
        self._busy_kinds.clear()
        generation = self.session.begin_finding_change()
        self._clear_finding_views(retain_override=True)
        self._submit(
            "finding_import",
            JobRequestIdentity(generation=generation),
            lambda _context: load_finding_context(Path(source_text), Path(workspace_text)),
            self._finding_loaded,
        )
        self._render()

    def _finding_loaded(self, outcome: JobOutcome) -> None:
        self._busy_kinds.discard(outcome.kind)
        if outcome.identity.generation != self.session.generation or outcome.cancelled:
            self._render()
            return
        if outcome.error:
            self._set_error(f"Finding import failed: {outcome.error}")
            self._render()
            return
        finding = outcome.value
        if not isinstance(finding, FindingContext):
            self._set_error("Finding import returned an invalid result.")
            self._render()
            return
        self.session.accept_finding(finding)
        self._set_text(self.summary_text, finding.summary_text)
        if finding.primary_frame_path is not None:
            self.preview_status_var.set("Building bounded base preview…")
            identity = JobRequestIdentity(
                generation=self.session.generation,
                finding_id=finding.finding_id,
                authoring_base_sha256=finding.authoring_base_sha256,
            )
            self._submit(
                "base_preview",
                identity,
                lambda context: self.preview_service.prepare(
                    finding.primary_frame_path,
                    finding.import_result.finding_dir / "preview_cache" / "base",
                    context,
                ),
                self._base_preview_loaded,
            )
        else:
            self.preview_status_var.set("Finding has no primary frame; bundle work remains available.")
        self.build_packet()
        self._render()

    def _base_preview_loaded(self, outcome: JobOutcome) -> None:
        self._busy_kinds.discard(outcome.kind)
        finding = self.session.finding
        if (
            outcome.identity.generation != self.session.generation
            or finding is None
            or outcome.identity.finding_id != finding.finding_id
            or outcome.identity.authoring_base_sha256 != finding.authoring_base_sha256
            or outcome.cancelled
        ):
            self._render()
            return
        if outcome.error:
            self.preview_status_var.set(f"Preview unavailable: {outcome.error}")
            self.preview_label.configure(image="", text="Preview unavailable\nOpen Full Base Frame remains explicit.")
            self._render()
            return
        preview = outcome.value
        self.session.accept_preview(preview)
        self._base_preview_photo = self._photo_from_preview(preview.preview_path, (560, 300))
        self.preview_label.configure(image=self._base_preview_photo, text="")
        cache_note = "cache hit" if preview.cache_hit else "new cached derivative"
        self.preview_status_var.set(
            f"{preview.source_width}×{preview.source_height} → {preview.preview_width}×{preview.preview_height} ({cache_note})"
        )
        self._render()

    @staticmethod
    def _photo_from_preview(path: Path, size: tuple[int, int]):
        with Image.open(path) as image:
            image.load()
            displayed = image.copy()
            displayed.thumbnail(size, Image.Resampling.LANCZOS)
        return ImageTk.PhotoImage(displayed)

    def build_packet(self) -> None:
        finding = self.session.finding
        if finding is None:
            self._set_error("Open a finding before building its exact Agent Bundle V6.")
            return
        self.session.status_text = "Building one coherent immutable authority snapshot…"
        identity = JobRequestIdentity(
            generation=self.session.generation,
            finding_id=finding.finding_id,
            authoring_base_sha256=finding.authoring_base_sha256,
        )
        self._submit(
            "bundle",
            identity,
            lambda context: build_agent_bundle(
                finding.import_result.finding_dir, self.runtime_cmd_path, job=context
            ),
            self._bundle_built,
        )
        self._render()

    def _bundle_built(self, outcome: JobOutcome) -> None:
        self._busy_kinds.discard(outcome.kind)
        finding = self.session.finding
        if (
            outcome.identity.generation != self.session.generation
            or finding is None
            or outcome.identity.finding_id != finding.finding_id
            or outcome.identity.authoring_base_sha256 != finding.authoring_base_sha256
            or outcome.cancelled
        ):
            self._render()
            return
        if outcome.error:
            self._set_error(f"Agent Bundle V6 generation failed: {outcome.error}")
            self._render()
            return
        bundle = outcome.value
        if not isinstance(bundle, AgentBundle):
            self._set_error("Bundle generation returned an invalid result.")
            self._render()
            return
        handoff = load_agent_bundle_handoff(bundle.packet_dir)
        self.session.accept_bundle(bundle)
        self._set_text(self.packet_text, handoff.packet_text)
        self._set_text(self.proof_text, "No proof has run for this exact Agent Bundle V6 binding.")
        self.binding_var.set(
            f"Packet {bundle.packet_id}\nManifest SHA-256 {bundle.manifest_sha256}\n"
            f"Finding {bundle.finding_id}\nSelector {bundle.selected_fractal_type}"
        )
        self.packet_info_var.set(f"{len(handoff.packet_text.encode('utf-8')):,} byte index")
        required = ", ".join(handoff.required_attachments)
        recommended = ", ".join(handoff.recommended_attachments) or "none"
        unavailable = ", ".join(handoff.unavailable_optional_attachments) or "none"
        self.attachment_var.set(
            f"Attach required: {required}\nRecommended: {recommended} · Unavailable optional: {unavailable}"
        )
        self._render()

    def copy_packet(self) -> None:
        bundle = self.session.bundle
        if bundle is None:
            self._set_error("Build an exact Agent Bundle V6 before copying packet.md.")
            return
        copy_agent_packet(bundle.packet_dir, self._write_clipboard)
        self.session.status_text = (
            f"Copied packet.md for {bundle.packet_id}. Attach the listed files from the bundle folder separately."
        )
        self._render()

    def open_bundle_folder(self) -> None:
        bundle = self.session.bundle
        if bundle is None:
            self._set_error("No Agent Bundle V6 folder is active.")
            return
        try:
            open_agent_bundle_folder(bundle.packet_dir)
            self.session.status_text = f"Opened exact Agent Bundle V6 folder {bundle.packet_id}."
        except Exception as exc:
            self._set_error(str(exc))
        self._render()

    def _override_modified(self, _event=None) -> None:
        if self._setting_override or not self.override_text.edit_modified():
            return
        self.override_text.edit_modified(False)
        self.session.set_override_text(self.override_text.get("1.0", "end-1c"))
        self._clear_candidate_views()
        self._set_text(self.proof_text, "Override changed. Every prior proof and review binding is invalidated.")
        self._render()

    def set_override_text(self, text: str) -> None:
        self._setting_override = True
        try:
            self.override_text.delete("1.0", "end")
            self.override_text.insert("1.0", text)
            self.override_text.edit_modified(False)
        finally:
            self._setting_override = False
        self.session.set_override_text(text)
        self._clear_candidate_views()
        self._set_text(self.proof_text, "Override changed. Every prior proof and review binding is invalidated.")
        self._render()

    def prove_override(self) -> None:
        finding = self.session.finding
        bundle = self.session.bundle
        override_text = self.session.override_text
        if finding is None or bundle is None or not override_text.strip():
            self._set_error("Open a finding, build its exact bundle, and paste a sparse state override before proof.")
            self._render()
            return
        override_sha256 = hashlib.sha256(override_text.encode("utf-8")).hexdigest()
        identity = JobRequestIdentity(
            generation=self.session.generation,
            finding_id=finding.finding_id,
            authoring_base_sha256=finding.authoring_base_sha256,
            packet_id=bundle.packet_id,
            packet_manifest_sha256=bundle.manifest_sha256,
            override_text_sha256=override_sha256,
        )
        self.session.begin_proof()
        self._clear_candidate_views()
        self._set_text(
            self.proof_text,
            "PROVING\n\nValidating exact Packet V6 authority, deterministically merging the override, "
            "loading the complete state through the engine without actions, and replaying the engine-emitted state…",
        )
        self._submit(
            "proof",
            identity,
            lambda context: execute_state_override_proof(
                bundle.packet_dir,
                override_text,
                self.runtime_cmd_path,
                context,
                expected_manifest_sha256=bundle.manifest_sha256,
            ),
            self._proof_completed,
        )
        self._render()

    def _proof_completed(self, outcome: JobOutcome) -> None:
        self._busy_kinds.discard(outcome.kind)
        finding = self.session.finding
        bundle = self.session.bundle
        current_override_sha = hashlib.sha256(self.session.override_text.encode("utf-8")).hexdigest()
        if (
            outcome.identity.generation != self.session.generation
            or finding is None
            or bundle is None
            or outcome.identity.finding_id != finding.finding_id
            or outcome.identity.authoring_base_sha256 != finding.authoring_base_sha256
            or outcome.identity.packet_id != bundle.packet_id
            or outcome.identity.packet_manifest_sha256 != bundle.manifest_sha256
            or outcome.identity.override_text_sha256 != current_override_sha
            or outcome.cancelled
        ):
            self._render()
            return
        if outcome.error:
            self.session.state = SessionState.REJECTED
            self._set_error(f"Proof operation failed: {outcome.error}")
            self._set_text(self.proof_text, f"PROOF OPERATION FAILED\n\n{outcome.error}")
            self._render()
            return
        result = outcome.value
        if not isinstance(result, StateOverrideProofResult):
            self.session.state = SessionState.REJECTED
            self._set_error("Proof operation returned an invalid result.")
            self._render()
            return
        self.session.accept_proof_result(result)
        if result.status == "replay_proven":
            receipt = self._read_json(result.receipt_path)
            normalized = [
                item
                for item in receipt.get("requested_value_receipts", [])
                if item.get("classification") == "representation_normalization"
            ]
            changed = receipt.get("override", {}).get("changed_paths", [])
            paths = [item.get("path", "?") for item in changed]
            self.changed_paths_var.set("Changed paths: " + (", ".join(paths) if paths else "none (exact no-op)"))
            normalization_note = (
                "\nRepresentation normalization:\n"
                + "\n".join(
                    f"- {item['path']}: {item['requested_value']!r} → {item['engine_emitted_value']!r}"
                    for item in normalized
                )
                if normalized
                else ""
            )
            self._set_text(
                self.proof_text,
                "OVERRIDE ACCEPTED\nREPLAY PROVEN\nVISUAL REVIEW PENDING\n\n"
                f"{result.message}\n\nEngine candidate SHA-256: {result.engine_candidate_sha256}"
                f"{normalization_note}\n\nReceipt: {result.receipt_path}",
            )
            assert result.candidate_frame_path is not None
            self.candidate_preview_status_var.set("Building bounded candidate preview…")
            preview_identity = JobRequestIdentity(
                generation=self.session.generation,
                finding_id=finding.finding_id,
                packet_id=bundle.packet_id,
                packet_manifest_sha256=bundle.manifest_sha256,
                override_text_sha256=current_override_sha,
                candidate_sha256=result.engine_candidate_sha256,
            )
            self._submit(
                "candidate_preview",
                preview_identity,
                lambda context: self.preview_service.prepare(
                    result.candidate_frame_path,
                    finding.import_result.finding_dir
                    / "preview_cache"
                    / "candidates"
                    / (result.engine_candidate_sha256 or "unknown"),
                    context,
                ),
                self._candidate_preview_loaded,
            )
        else:
            self._last_copyable_error = result.message
            self._set_text(
                self.proof_text,
                f"REJECTED\n\n{result.message}\n\nPreserved receipt: {result.receipt_path}",
            )
        self._render()

    def _candidate_preview_loaded(self, outcome: JobOutcome) -> None:
        self._busy_kinds.discard(outcome.kind)
        result = self.session.proof_result
        bundle = self.session.bundle
        current_override_sha = hashlib.sha256(self.session.override_text.encode("utf-8")).hexdigest()
        if (
            outcome.identity.generation != self.session.generation
            or result is None
            or bundle is None
            or outcome.identity.packet_id != bundle.packet_id
            or outcome.identity.packet_manifest_sha256 != bundle.manifest_sha256
            or outcome.identity.override_text_sha256 != current_override_sha
            or outcome.identity.candidate_sha256 != result.engine_candidate_sha256
            or outcome.cancelled
        ):
            self._render()
            return
        if outcome.error:
            self.candidate_preview_status_var.set(
                f"Candidate preview unavailable: {outcome.error}. Open Full Candidate remains explicit."
            )
            self.candidate_preview_label.configure(image="", text="Candidate preview unavailable")
            self._render()
            return
        preview = outcome.value
        self.session.accept_candidate_preview(preview)
        self._candidate_preview_photo = self._photo_from_preview(preview.preview_path, (600, 320))
        self.candidate_preview_label.configure(image=self._candidate_preview_photo, text="")
        cache_note = "cache hit" if preview.cache_hit else "new cached derivative"
        self.candidate_preview_status_var.set(
            f"{preview.source_width}×{preview.source_height} → {preview.preview_width}×{preview.preview_height} ({cache_note})"
        )
        self._render()

    def accept_candidate(self) -> None:
        result = self.session.proof_result
        bundle = self.session.bundle
        if result is None or bundle is None:
            self._set_error("No replay-proven candidate is available for review.")
            return
        if self.session.candidate_preview is None and not self._candidate_full_frame_opened:
            self._set_error("Wait for the candidate preview or open the full candidate frame before accepting it.")
            self._render()
            return
        try:
            record_state_override_review(result, "accepted")
            self.session.record_review("accepted")
            errors = validate_state_override_launch_readiness(
                result, bundle.packet_dir, self.session.override_text, self.runtime_cmd_path
            )
            if errors:
                raise ValueError("; ".join(errors))
            self.session.mark_launch_ready()
            self._set_text(
                self.proof_text,
                "OVERRIDE ACCEPTED\nREPLAY PROVEN\nUSER ACCEPTED\nLAUNCH READY\n\n"
                "The exact candidate, frame, packet, override, proof receipt, review decision, and runtime were rechecked.\n\n"
                f"Candidate: {result.engine_candidate_path}\nReview decision: {result.proof_dir / 'review-decision.json'}",
            )
        except Exception as exc:
            self.session.state = SessionState.REJECTED
            self._set_error(f"Review or launch readiness failed: {exc}")
            self._set_text(self.proof_text, f"LAUNCH READINESS INVALIDATED\n\n{exc}\n\nRun a fresh proof.")
        self._render()

    def request_revision(self) -> None:
        result = self.session.proof_result
        if result is None:
            self._set_error("No replay-proven candidate is available for review.")
            return
        if self.session.candidate_preview is None and not self._candidate_full_frame_opened:
            self._set_error("Wait for the candidate preview or open the full candidate frame before reviewing it.")
            self._render()
            return
        try:
            record_state_override_review(result, "revision_needed")
            self.session.record_review("revision_needed")
            self._set_text(
                self.proof_text,
                "OVERRIDE ACCEPTED\nREPLAY PROVEN\nREVISION NEEDED\n\n"
                "This proof remains immutable evidence. Edit the override to begin a new attempt.\n\n"
                f"Decision: {result.proof_dir / 'review-decision.json'}",
            )
        except Exception as exc:
            self._set_error(str(exc))
        self._render()

    def launch_accepted_state(self) -> None:
        result = self.session.proof_result
        bundle = self.session.bundle
        if result is None or bundle is None:
            self._set_error("No exact user-accepted candidate is launch-ready.")
            return
        try:
            process = launch_state_override_candidate(
                result,
                bundle.packet_dir,
                self.session.override_text,
                self.runtime_cmd_path,
            )
            self.session.status_text = (
                f"Launched exact user-accepted engine candidate in a new viewer (PID {process.pid})."
            )
            self._set_text(
                self.proof_text,
                "LAUNCH READY → LAUNCHED\n\n"
                f"PID: {process.pid}\nCandidate: {result.engine_candidate_path}\n"
                f"Launch receipt: {result.proof_dir / 'launch.json'}",
            )
        except Exception as exc:
            self.session.state = SessionState.REJECTED
            self._set_error(f"Launch readiness invalidated: {exc}. Run a fresh proof.")
            self._set_text(self.proof_text, f"LAUNCH READINESS INVALIDATED\n\n{exc}\n\nRun a fresh proof.")
        self._render()

    def open_full_frame(self) -> None:
        finding = self.session.finding
        if finding is None or finding.primary_frame_path is None:
            self._set_error("This finding has no primary frame to open.")
            return
        os.startfile(str(finding.primary_frame_path))

    def open_candidate_frame(self) -> None:
        result = self.session.proof_result
        if result is None or result.candidate_frame_path is None:
            self._set_error("No engine-emitted candidate frame is available.")
            return
        try:
            os.startfile(str(result.candidate_frame_path))
            self._candidate_full_frame_opened = True
            self.session.status_text = "Opened the exact full-resolution engine candidate for visual review."
        except Exception as exc:
            self._set_error(f"Could not open the full candidate frame: {exc}")
        self._render()

    def copy_last_error(self) -> None:
        if not self._last_copyable_error:
            return
        self._write_clipboard(self._last_copyable_error)
        self.session.status_text = "Copied the exact proof error."
        self._render()

    def _write_clipboard(self, text: str) -> None:
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self.root.update_idletasks()

    def reset_session(self) -> None:
        self.runner.cancel_all()
        self._busy_kinds.clear()
        self.session.reset()
        self.source_path_var.set("")
        self._clear_finding_views(retain_override=False)
        self._render()

    def _clear_finding_views(self, retain_override: bool) -> None:
        self._set_text(self.summary_text, "")
        self._set_text(self.packet_text, "")
        self._set_text(self.proof_text, "No proof has run. Paste a sparse state override to begin.")
        self.binding_var.set("No Agent Bundle V6 binding yet.")
        self.packet_info_var.set("Bundle is generated automatically after finding import.")
        self.attachment_var.set("Required attachments will appear here.")
        self.preview_status_var.set("No finding frame loaded.")
        self.preview_label.configure(image="", text="No preview")
        self._base_preview_photo = None
        self._clear_candidate_views()
        if not retain_override:
            self.set_override_text("")

    def _clear_candidate_views(self) -> None:
        self.candidate_preview_status_var.set("No candidate frame yet.")
        self.candidate_preview_label.configure(image="", text="No candidate")
        self.changed_paths_var.set("No override changes have been proven.")
        self._candidate_preview_photo = None
        self._candidate_full_frame_opened = False

    def _submit(self, kind: str, identity, operation, completion: Callable[[JobOutcome], None]) -> None:
        self._busy_kinds.add(kind)
        try:
            self.runner.submit(kind, identity, operation, completion)
        except (WorkerQueueFullError, RuntimeError) as exc:
            self._busy_kinds.discard(kind)
            self._set_error(str(exc))

    def _drain_completions(self) -> None:
        if self._closed:
            return
        while True:
            try:
                callback = self._completion_queue.get_nowait()
            except queue.Empty:
                break
            callback()
        self.root.after(25, self._drain_completions)

    def _set_error(self, message: str) -> None:
        self._last_copyable_error = message
        self.session.status_text = message

    @staticmethod
    def _set_text(widget, text: str) -> None:
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        widget.insert("1.0", text)
        widget.configure(state="disabled")

    @staticmethod
    def _read_json(path: Path) -> dict:
        import json

        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}

    def _render(self) -> None:
        self.state_var.set(self.session.state.value)
        self.status_var.set(self.session.status_text)
        finding_ready = self.session.finding is not None
        bundle_ready = self.session.bundle is not None
        proof_busy = "proof" in self._busy_kinds
        result = self.session.proof_result
        replay_proven = isinstance(result, StateOverrideProofResult) and result.status == "replay_proven"
        review_surface_seen = self.session.candidate_preview is not None or self._candidate_full_frame_opened
        undecided = replay_proven and self.session.review_decision is None and review_surface_seen
        self.open_finding_button.configure(state="disabled" if "finding_import" in self._busy_kinds else "normal")
        self.build_packet_button.configure(
            state="normal" if finding_ready and "bundle" not in self._busy_kinds else "disabled"
        )
        self.copy_packet_button.configure(state="normal" if bundle_ready else "disabled")
        self.open_bundle_button.configure(state="normal" if bundle_ready else "disabled")
        self.open_full_frame_button.configure(
            state="normal"
            if finding_ready and self.session.finding.primary_frame_path is not None
            else "disabled"
        )
        override_ready = bundle_ready and bool(self.session.override_text.strip())
        self.prove_button.configure(state="normal" if override_ready and not proof_busy else "disabled")
        self.open_candidate_frame_button.configure(state="normal" if replay_proven else "disabled")
        self.accept_button.configure(state="normal" if undecided and not proof_busy else "disabled")
        self.revision_button.configure(state="normal" if undecided and not proof_busy else "disabled")
        self.launch_button.configure(
            state="normal" if self.session.state == SessionState.LAUNCH_READY and not proof_busy else "disabled"
        )
        self.copy_error_button.configure(state="normal" if self._last_copyable_error else "disabled")

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        if self._owns_runner:
            self.runner.shutdown(wait=False)
        self.root.destroy()


def _enable_dpi_awareness() -> None:
    try:
        import ctypes

        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--capture-source", type=Path, default=None)
    parser.add_argument("--workspace-root", type=Path, default=DEFAULT_FINDING_WORKSPACE)
    args, _unknown = parser.parse_known_args(argv)
    _enable_dpi_awareness()
    import tkinter as tk

    root = tk.Tk()
    app = UserWorkflowApp(root, workspace_root=args.workspace_root)
    if args.capture_source is not None:
        root.after(100, lambda: app.open_finding_path(args.capture_source, args.workspace_root))
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
