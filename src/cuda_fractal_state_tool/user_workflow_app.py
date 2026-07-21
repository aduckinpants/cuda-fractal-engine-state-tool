from __future__ import annotations

import argparse
import hashlib
import os
import queue
from pathlib import Path
from typing import Callable, Optional

from PIL import Image, ImageTk

from .async_jobs import AsyncJobRunner, JobOutcome, JobRequestIdentity, WorkerQueueFullError
from .preview_service import PreviewService
from .runtime_surface import DEFAULT_RUNTIME_CMD
from .user_proof import ProofResult, execute_bound_proof, launch_proven_result
from .user_workflow import (
    FindingContext,
    PacketContext,
    SessionState,
    UserWorkflowSession,
    build_finding_intake_packet,
    load_finding_context,
)


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
        self._preview_photo = None
        self._setting_proposal = False
        self._closed = False

        self.source_path_var = tk.StringVar(value="")
        self.workspace_root_var = tk.StringVar(value=str(workspace_root.resolve()))
        self.state_var = tk.StringVar(value=SessionState.EMPTY.value)
        self.status_var = tk.StringVar(value=self.session.status_text)
        self.binding_var = tk.StringVar(value="No packet binding yet.")
        self.packet_info_var = tk.StringVar(value="Packet is generated automatically after finding import.")
        self.preview_status_var = tk.StringVar(value="No finding frame loaded.")

        self._configure_root()
        self._build_shell()
        self._render()
        self.root.after(25, self._drain_completions)
        self.root.protocol("WM_DELETE_WINDOW", self.close)

    def _configure_root(self) -> None:
        self.root.title("CUDA Fractal State Tool — Finding to Proof")
        self.root.geometry("1440x900")
        self.root.minsize(1080, 700)
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=1)

    def _build_shell(self) -> None:
        ttk = self.ttk
        tk = self.tk

        header = ttk.Frame(self.root, padding=(12, 10, 12, 6))
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(1, weight=1)
        ttk.Label(header, text="Finding → Packet → Proposal → Proof", font=("Segoe UI", 15, "bold")).grid(
            row=0, column=0, sticky="w"
        )
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
        self._build_proposal_side()

        footer = ttk.Frame(self.root, padding=(12, 4, 12, 10))
        footer.grid(row=2, column=0, sticky="ew")
        footer.columnconfigure(0, weight=1)
        ttk.Label(footer, textvariable=self.status_var, wraplength=1200).grid(row=0, column=0, sticky="w")

    def _build_finding_side(self) -> None:
        ttk = self.ttk
        tk = self.tk
        from tkinter.scrolledtext import ScrolledText
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
        ttk.Entry(source, textvariable=self.workspace_root_var).grid(row=1, column=1, columnspan=2, sticky="ew", pady=(6, 0))
        ttk.Button(source, text="Browse…", command=self._browse_workspace).grid(row=1, column=3, padx=(6, 0), pady=(6, 0))
        self.open_finding_button = ttk.Button(source, text="Open Finding", command=self.open_finding)
        self.open_finding_button.grid(row=2, column=0, columnspan=4, sticky="ew", pady=(8, 0))
        ttk.Label(
            source,
            text="The capture remains read-only; required artifacts are mirrored into the durable workspace.",
            wraplength=620,
        ).grid(row=3, column=0, columnspan=4, sticky="w", pady=(6, 0))

        summary = ttk.LabelFrame(self.left, text="2. Finding context", padding=8)
        summary.grid(row=1, column=0, sticky="nsew", pady=(0, 8))
        summary.columnconfigure(0, weight=1)
        summary.rowconfigure(0, weight=1)
        self.summary_text = ScrolledText(summary, height=7, wrap="word", state="disabled")
        self.summary_text.grid(row=0, column=0, sticky="nsew")

        preview = ttk.LabelFrame(self.left, text="Frame preview (bounded derivative)", padding=8)
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
            preview_controls, text="Open Full Frame", command=self.open_full_frame
        )
        self.open_full_frame_button.grid(row=0, column=1, sticky="e")

        packet = ttk.LabelFrame(self.left, text="3. Outgoing intake packet", padding=8)
        packet.grid(row=3, column=0, sticky="nsew")
        packet.columnconfigure(0, weight=1)
        packet.rowconfigure(1, weight=1)
        packet_actions = ttk.Frame(packet)
        packet_actions.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        packet_actions.columnconfigure(0, weight=1)
        self.build_packet_button = ttk.Button(packet_actions, text="Refresh", command=self.build_packet)
        self.build_packet_button.grid(row=0, column=0, sticky="w")
        ttk.Label(packet_actions, textvariable=self.packet_info_var).grid(row=0, column=1, sticky="e", padx=(8, 8))
        self.copy_packet_button = ttk.Button(packet_actions, text="Copy Packet", command=self.copy_packet)
        self.copy_packet_button.grid(row=0, column=2, sticky="e")
        self.packet_text = ScrolledText(packet, height=20, wrap="word", state="disabled")
        self.packet_text.grid(row=1, column=0, sticky="nsew")

    def _build_proposal_side(self) -> None:
        ttk = self.ttk
        tk = self.tk
        from tkinter.scrolledtext import ScrolledText
        self.right.columnconfigure(0, weight=1)
        self.right.rowconfigure(1, weight=3)
        self.right.rowconfigure(3, weight=2)

        binding = ttk.LabelFrame(self.right, text="Exact packet binding", padding=8)
        binding.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        binding.columnconfigure(0, weight=1)
        ttk.Label(binding, textvariable=self.binding_var, wraplength=650).grid(row=0, column=0, sticky="w")

        proposal = ttk.LabelFrame(self.right, text="4. Incoming proposal JSON", padding=8)
        proposal.grid(row=1, column=0, sticky="nsew", pady=(0, 8))
        proposal.columnconfigure(0, weight=1)
        proposal.rowconfigure(0, weight=1)
        self.proposal_text = ScrolledText(proposal, height=22, wrap="none", undo=True)
        self.proposal_text.grid(row=0, column=0, sticky="nsew")
        self.proposal_text.bind("<<Modified>>", self._proposal_modified)
        ttk.Label(
            proposal,
            text="Starts empty. Paste only the proposal returned for the exact packet shown above.",
        ).grid(row=1, column=0, sticky="w", pady=(6, 0))

        actions = ttk.LabelFrame(self.right, text="5. Validate, prove, and launch", padding=8)
        actions.grid(row=2, column=0, sticky="ew", pady=(0, 8))
        for column in (0, 1, 2):
            actions.columnconfigure(column, weight=1)
        self.prove_button = ttk.Button(actions, text="Validate & Replay Prove", command=self.prove_proposal)
        self.prove_button.grid(row=0, column=0, sticky="ew", padx=(0, 4))
        self.repair_button = ttk.Button(actions, text="Copy Repair Packet", command=self.copy_repair_packet)
        self.repair_button.grid(row=0, column=1, sticky="ew", padx=4)
        self.launch_button = ttk.Button(actions, text="Launch Proven State", command=self.launch_proven_state)
        self.launch_button.grid(row=0, column=2, sticky="ew", padx=(4, 0))
        ttk.Label(
            actions,
            text="Proof is bound to the exact packet and exact proposal text. Launch rechecks the candidate, runtime, and contract.",
            wraplength=650,
        ).grid(row=1, column=0, columnspan=3, sticky="w", pady=(8, 0))

        proof = ttk.LabelFrame(self.right, text="Proof status / repair context", padding=8)
        proof.grid(row=3, column=0, sticky="nsew")
        proof.columnconfigure(0, weight=1)
        proof.rowconfigure(0, weight=1)
        self.proof_text = ScrolledText(proof, height=12, wrap="word", state="disabled")
        self.proof_text.grid(row=0, column=0, sticky="nsew")
        self._set_text(
            self.proof_text,
            "No proof has run. Paste proposal_v1 JSON from the agent conversation, then validate and replay-prove it.",
        )

    def _browse_file(self) -> None:
        from tkinter import filedialog

        path = filedialog.askopenfilename(
            title="Choose finding state, manifest, or frame",
            filetypes=[
                ("Finding artifacts", "*.json *.png *.bmp *.jpg *.jpeg"),
                ("All files", "*.*"),
            ],
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
        source_path = Path(source_text)
        workspace_root = Path(workspace_text)
        self.runner.cancel_all()
        self._busy_kinds.clear()
        generation = self.session.begin_finding_change()
        self._clear_finding_views(retain_proposal=True)
        identity = JobRequestIdentity(generation=generation)
        self._submit(
            "finding_import",
            identity,
            lambda context: load_finding_context(source_path, workspace_root),
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
            self.preview_status_var.set("Building bounded preview…")
            preview_identity = JobRequestIdentity(
                generation=self.session.generation,
                finding_id=finding.finding_id,
                authoring_base_sha256=finding.authoring_base_sha256,
            )
            self._submit(
                "preview",
                preview_identity,
                lambda context: self.preview_service.prepare(
                    finding.primary_frame_path,
                    finding.import_result.finding_dir / "preview_cache",
                    context,
                ),
                self._preview_loaded,
            )
        else:
            self.preview_status_var.set("Finding has no primary frame; packet work remains available.")
        self.build_packet()
        self._render()

    def _preview_loaded(self, outcome: JobOutcome) -> None:
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
            self.preview_label.configure(image="", text="Preview unavailable\nOpen Full Frame remains explicit.")
            self._render()
            return
        preview = outcome.value
        self.session.accept_preview(preview)
        with Image.open(preview.preview_path) as image:
            image.load()
            displayed = image.copy()
            displayed.thumbnail((560, 350), Image.Resampling.LANCZOS)
            self._preview_photo = ImageTk.PhotoImage(displayed)
        self.preview_label.configure(image=self._preview_photo, text="")
        cache_note = "cache hit" if preview.cache_hit else "new cached derivative"
        self.preview_status_var.set(
            f"{preview.source_width}×{preview.source_height} → {preview.preview_width}×{preview.preview_height} ({cache_note})"
        )
        self._render()

    def build_packet(self) -> None:
        finding = self.session.finding
        if finding is None:
            self._set_error("Open a finding before building its packet.")
            return
        identity = JobRequestIdentity(
            generation=self.session.generation,
            finding_id=finding.finding_id,
            authoring_base_sha256=finding.authoring_base_sha256,
        )
        self.session.status_text = "Building exact packet and runtime/contract binding…"
        self._submit(
            "packet",
            identity,
            lambda context: build_finding_intake_packet(finding, self.runtime_cmd_path, job=context),
            self._packet_built,
        )
        self._render()

    def _packet_built(self, outcome: JobOutcome) -> None:
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
            self._set_error(f"Packet generation failed: {outcome.error}")
            self._render()
            return
        packet = outcome.value
        if not isinstance(packet, PacketContext):
            self._set_error("Packet generation returned an invalid result.")
            self._render()
            return
        self.session.accept_packet(packet)
        self._set_text(self.proof_text, "No proof has run for this exact packet binding.")
        self._set_text(self.packet_text, packet.packet_text)
        self.binding_var.set(
            f"Packet {packet.packet_id}\nSHA-256 {packet.packet_sha256}\nProfile {packet.capability_profile}"
        )
        self.packet_info_var.set(
            f"{len(packet.packet_text.encode('utf-8')):,} bytes · contract {packet.ui_salt_contract_sha256[:12]}…"
        )
        self._render()

    def copy_packet(self) -> None:
        packet = self.session.packet
        if packet is None:
            self._set_error("Build an exact intake packet before copying it.")
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(packet.packet_text)
        self.root.update_idletasks()
        self.session.status_text = f"Copied exact packet {packet.packet_id}."
        self._render()

    def _proposal_modified(self, _event=None) -> None:
        if self._setting_proposal:
            return
        if not self.proposal_text.edit_modified():
            return
        self.proposal_text.edit_modified(False)
        self.session.set_proposal_text(self.proposal_text.get("1.0", "end-1c"))
        self._set_text(self.proof_text, "Proposal changed. Prior proof readiness is invalidated.")
        self._render()

    def set_proposal_text(self, text: str) -> None:
        self._setting_proposal = True
        try:
            self.proposal_text.delete("1.0", "end")
            self.proposal_text.insert("1.0", text)
            self.proposal_text.edit_modified(False)
        finally:
            self._setting_proposal = False
        self.session.set_proposal_text(text)
        self._set_text(self.proof_text, "Proposal changed. Prior proof readiness is invalidated.")
        self._render()

    def prove_proposal(self) -> None:
        finding = self.session.finding
        packet = self.session.packet
        proposal_text = self.session.proposal_text
        if finding is None or packet is None or not proposal_text.strip():
            self._set_error("Open a finding, copy its exact packet, and paste proposal_v1 JSON before proof.")
            self._render()
            return
        proposal_sha256 = hashlib.sha256(proposal_text.encode("utf-8")).hexdigest()
        identity = JobRequestIdentity(
            generation=self.session.generation,
            finding_id=finding.finding_id,
            authoring_base_sha256=finding.authoring_base_sha256,
            packet_id=packet.packet_id,
            packet_sha256=packet.packet_sha256,
            proposal_text_sha256=proposal_sha256,
            runtime_identity_sha256=packet.runtime_identity_sha256,
            ui_salt_contract_sha256=packet.ui_salt_contract_sha256,
        )
        self.session.begin_proof()
        self._set_text(
            self.proof_text,
            "PROVING\n\nValidating packet and proposal binding, asking the engine to materialize the candidate, "
            "then replaying that emitted state without actions…",
        )
        self._submit(
            "proof",
            identity,
            lambda context: execute_bound_proof(
                finding,
                packet,
                proposal_text,
                self.runtime_cmd_path,
                context,
            ),
            self._proof_completed,
        )
        self._render()

    def _proof_completed(self, outcome: JobOutcome) -> None:
        self._busy_kinds.discard(outcome.kind)
        finding = self.session.finding
        packet = self.session.packet
        current_proposal_sha = hashlib.sha256(self.session.proposal_text.encode("utf-8")).hexdigest()
        if (
            outcome.identity.generation != self.session.generation
            or finding is None
            or packet is None
            or outcome.identity.finding_id != finding.finding_id
            or outcome.identity.authoring_base_sha256 != finding.authoring_base_sha256
            or outcome.identity.packet_id != packet.packet_id
            or outcome.identity.packet_sha256 != packet.packet_sha256
            or outcome.identity.proposal_text_sha256 != current_proposal_sha
            or outcome.cancelled
        ):
            self._render()
            return
        if outcome.error:
            self.session.state = SessionState.REJECTED
            self.session.status_text = f"Proof operation failed: {outcome.error}"
            self._set_text(self.proof_text, f"PROOF OPERATION FAILED\n\n{outcome.error}")
            self._render()
            return
        result = outcome.value
        if not isinstance(result, ProofResult):
            self.session.state = SessionState.REJECTED
            self._set_error("Proof operation returned an invalid result.")
            self._render()
            return
        self.session.accept_proof_result(result)
        if result.status == "proven":
            self._set_text(
                self.proof_text,
                "PROVEN\n\n"
                f"{result.message}\n\n"
                f"Candidate SHA-256: {result.candidate_sha256}\n"
                "Launch readiness: READY (candidate, runtime, contract, packet, and proposal are rechecked on click)\n"
                f"Receipt: {result.receipt_path}",
            )
        else:
            repair_note = "A bound repair packet is ready to copy." if result.repair_packet_text else "No repair packet is available for this operational failure."
            self._set_text(
                self.proof_text,
                "REJECTED\n\n"
                f"{result.message}\n\n{repair_note}\n"
                f"Receipt: {result.receipt_path}",
            )
        self._render()

    def copy_repair_packet(self) -> None:
        result = self.session.proof_result
        if not isinstance(result, ProofResult) or not result.repair_packet_text:
            self._set_error("No actionable rejection repair packet is available.")
            self._render()
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(result.repair_packet_text)
        self.root.update_idletasks()
        self.session.status_text = f"Copied repair packet for rejection {result.proof_id}."
        self._render()

    def launch_proven_state(self) -> None:
        result = self.session.proof_result
        packet = self.session.packet
        if not isinstance(result, ProofResult) or packet is None:
            self._set_error("No exact proven candidate is launch-ready.")
            self._render()
            return
        try:
            process = launch_proven_result(
                result,
                packet,
                self.session.proposal_text,
                self.runtime_cmd_path,
            )
        except Exception as exc:
            self.session.proof_result = None
            self.session.state = SessionState.PROPOSAL_DIRTY
            self._set_error(f"Launch readiness invalidated: {exc}. Prove the current binding again.")
            self._set_text(self.proof_text, f"LAUNCH READINESS INVALIDATED\n\n{exc}\n\nRun proof again.")
            self._render()
            return
        self.session.status_text = f"Launched exact proven candidate in a new viewer (PID {process.pid})."
        self._render()

    def open_full_frame(self) -> None:
        finding = self.session.finding
        if finding is None or finding.primary_frame_path is None:
            self._set_error("This finding has no primary frame to open.")
            return
        os.startfile(str(finding.primary_frame_path))

    def reset_session(self) -> None:
        self.runner.cancel_all()
        self._busy_kinds.clear()
        self.session.reset()
        self.source_path_var.set("")
        self._clear_finding_views(retain_proposal=False)
        self._render()

    def _clear_finding_views(self, retain_proposal: bool) -> None:
        self._set_text(self.summary_text, "")
        self._set_text(self.packet_text, "")
        self._set_text(self.proof_text, "No proof has run. Paste a bound proposal to begin.")
        self.binding_var.set("No packet binding yet.")
        self.packet_info_var.set("Packet is generated automatically after finding import.")
        self.preview_status_var.set("No finding frame loaded.")
        self.preview_label.configure(image="", text="No preview")
        self._preview_photo = None
        if not retain_proposal:
            self.set_proposal_text("")

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
        self.session.status_text = message

    @staticmethod
    def _set_text(widget, text: str) -> None:
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        widget.insert("1.0", text)
        widget.configure(state="disabled")

    def _render(self) -> None:
        self.state_var.set(self.session.state.value)
        self.status_var.set(self.session.status_text)
        finding_ready = self.session.finding is not None
        packet_ready = self.session.packet is not None
        self.open_finding_button.configure(state="disabled" if "finding_import" in self._busy_kinds else "normal")
        self.build_packet_button.configure(
            state="normal" if finding_ready and "packet" not in self._busy_kinds else "disabled"
        )
        self.copy_packet_button.configure(state="normal" if packet_ready else "disabled")
        self.open_full_frame_button.configure(
            state="normal"
            if finding_ready and self.session.finding.primary_frame_path is not None
            else "disabled"
        )
        proof_busy = "proof" in self._busy_kinds
        proposal_ready = packet_ready and bool(self.session.proposal_text.strip())
        result = self.session.proof_result
        self.prove_button.configure(state="normal" if proposal_ready and not proof_busy else "disabled")
        self.repair_button.configure(
            state="normal"
            if isinstance(result, ProofResult) and bool(result.repair_packet_text) and not proof_busy
            else "disabled"
        )
        self.launch_button.configure(
            state="normal"
            if isinstance(result, ProofResult) and result.status == "proven" and not proof_busy
            else "disabled"
        )

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
