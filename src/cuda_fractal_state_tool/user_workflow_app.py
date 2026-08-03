from __future__ import annotations

import argparse
import hashlib
import os
import queue
import time
import uuid
from decimal import Decimal, InvalidOperation
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
from .automated_protocol import AGENT_SESSION_PROTOCOL_SCHEMA, SessionBudgets
from .automated_run_store import AutomatedRunStore
from .enrichment_disclosure import DisclosureProfile
from .automated_session import (
    AutomatedSessionController,
    AutomatedSessionResult,
    create_job_bound_automated_route_services,
)
from .openai_credentials import resolve_openai_api_key, set_openai_api_key as store_openai_api_key
from .openai_transport import OpenAISDKProvider, PacketV8ResponsesTransport
from .preview_service import PreviewService
from .pricing_policy import load_pricing_policy
from .runtime_surface import DEFAULT_RUNTIME_CMD
from .runtime_compatibility import resolve_runtime_compatibility_mode
from .scalar_sweep import ScalarBracketSweepService, ScalarSweepResult
from .state_override_proof import (
    StateOverrideProofResult,
    execute_state_override_proof,
    launch_state_override_candidate,
    record_state_override_review,
    validate_state_override_launch_readiness,
)
from .user_workflow import (
    ExistingPacketContext,
    FindingContext,
    SessionState,
    UserWorkflowSession,
    load_existing_packet_context,
    load_finding_context,
)


DEFAULT_FINDING_WORKSPACE = Path(r"D:\salt-fractal\cuda-fractal-engine-state-tool")


def _is_exact_base_replay(result: object | None) -> bool:
    return bool(getattr(result, "empty_override_byte_exact", False))


def _candidate_accept_action_label(result: object | None) -> str:
    return "Acknowledge Base Replay" if _is_exact_base_replay(result) else "Accept Candidate"


def _candidate_preview_pixel_note(
    result: object | None, base_frame_comparison: object
) -> str:
    exact_base_replay = _is_exact_base_replay(result)
    if not isinstance(base_frame_comparison, dict):
        return " | EXACT BASE REPLAY | base-frame comparison unavailable" if exact_base_replay else ""
    if base_frame_comparison.get("decoded_equal") is True:
        return (
            " | EXACT BASE REPLAY | PIXELS IDENTICAL TO BASE"
            if exact_base_replay
            else " | PIXELS IDENTICAL TO BASE"
        )
    return (
        " | EXACT BASE REPLAY | PIXELS DIFFER FROM CAPTURED BASE"
        if exact_base_replay
        else " | pixels differ from base"
    )


def _automated_budget_text(projection: dict) -> str:
    pricing = projection.get("pricing_policy")
    pricing_id = pricing.get("policy_id", "unbound") if isinstance(pricing, dict) else "unbound"
    return (
        f"Rounds {projection.get('proven_rounds', 0)}/2 · "
        f"Responses {projection.get('model_responses', 0)}/6 · "
        f"Tokens total/cached/uncached/out {projection.get('cumulative_input_tokens', 0):,}/"
        f"{projection.get('cumulative_cached_input_tokens', 0):,}/"
        f"{projection.get('cumulative_uncached_input_tokens', 0):,}/"
        f"{projection.get('cumulative_output_tokens', 0):,} · "
        f"Cache writes {projection.get('cumulative_cache_write_tokens', 0):,} · "
        f"Calculated USD {projection.get('cumulative_calculated_cost_usd', '0')}/"
        f"{projection.get('maximum_calculated_cost_usd', '0')} · "
        f"Next max {projection.get('last_estimated_call_cost_usd', '0')} · "
        f"Pricing {pricing_id}"
    )


def _format_automated_event(event: dict) -> str:
    sequence = event.get("sequence", "?")
    event_type = str(event.get("event_type", "unknown")).upper()
    payload = event.get("payload") if isinstance(event.get("payload"), dict) else {}
    if event_type == "CONTROLLER_TRANSITION":
        detail = f"{payload.get('from', '?')} → {payload.get('to', '?')}"
    elif event_type == "MODEL_RESPONSE":
        detail = (
            f"model={payload.get('requested_model', '?')}→{payload.get('resolved_model', '?')} "
            f"tokens={payload.get('input_tokens', 0):,}/"
            f"{payload.get('cached_input_tokens', 0):,}/"
            f"{payload.get('uncached_input_tokens', 0):,}/"
            f"{payload.get('output_tokens', 0):,} "
            f"cache_write={payload.get('cache_write_tokens', 0):,} "
            f"cost=${payload.get('calculated_call_cost', {}).get('cost_usd', '0')} "
            f"latency={payload.get('latency_seconds', 0):.1f}s"
        )
    elif event_type in {"PROVIDER_DISPATCH_ESTIMATED", "PROVIDER_DISPATCH_REJECTED"}:
        estimate = payload.get("estimate") if isinstance(payload.get("estimate"), dict) else {}
        detail = (
            f"max=${estimate.get('cost_usd', '?')} tier={estimate.get('context_tier', '?')} "
            f"reason={payload.get('reason', 'allowed')}"
        )
    elif event_type == "OVERRIDE_VALIDATED":
        detail = (
            f"changed_paths={payload.get('changed_path_count', '?')} "
            f"effect={payload.get('effect', '?')} correction={payload.get('correction_used', False)}"
        )
    elif event_type == "SESSION_DISPOSITION":
        detail = str(payload.get("disposition", "?"))
    elif event_type == "MODEL_GATE_PROPOSAL":
        detail = str(payload.get("model_gate_proposal", "?"))
    elif event_type == "CANDIDATE_REPLAY_PROVEN":
        detail = f"proof={payload.get('proof_id', '?')}"
    elif event_type == "ROUND_CONVERSATION_STARTED":
        detail = (
            f"round={payload.get('round_number', '?')} "
            f"chain_reset={payload.get('provider_chain_reset', False)}"
        )
    else:
        detail = ""
    return f"{sequence:>3}  {event_type}{('  ' + detail) if detail else ''}"


def _format_scalar_sweep_progress(event: dict) -> str:
    kind = str(event.get("event", "UNKNOWN"))
    if kind == "PLAN_VALIDATED":
        return f"PLAN VALIDATED  {event.get('axis_path')}  values={event.get('values')}"
    if kind == "MEMBER_STARTED":
        return f"MEMBER {event.get('index')}  value={event.get('value')}  RUNNING"
    if kind == "MEMBER_COMPLETED":
        proof = f"  proof={event.get('proof_id')}" if event.get("proof_id") else ""
        return (
            f"MEMBER {event.get('index')}  value={event.get('value')}  "
            f"{event.get('status')}{proof}"
        )
    if kind == "SWEEP_COMPLETED":
        return f"SWEEP {event.get('disposition')}  {event.get('sweep_id')}"
    return kind


class UserWorkflowApp:
    def __init__(
        self,
        root,
        runtime_cmd_path: Path = DEFAULT_RUNTIME_CMD,
        workspace_root: Path = DEFAULT_FINDING_WORKSPACE,
        runner: Optional[AsyncJobRunner] = None,
        preview_service: Optional[PreviewService] = None,
        runtime_compatibility_mode: str | None = None,
    ) -> None:
        import tkinter as tk
        from tkinter import ttk

        self.root = root
        self.tk = tk
        self.ttk = ttk
        self.runtime_cmd_path = runtime_cmd_path.resolve()
        self.runtime_compatibility_mode = resolve_runtime_compatibility_mode(
            runtime_compatibility_mode
        )
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
        self._automated_job_id: str | None = None
        self._automated_run_store: AutomatedRunStore | None = None
        self._automated_result_dir: Path | None = None
        self._automated_last_event_sequence = 0
        self._next_automated_refresh_at = 0.0
        self._credential_available = False
        self._sweep_job_id: str | None = None
        self._sweep_result_dir: Path | None = None
        self._sweep_validation_binding: tuple[object, ...] | None = None
        self._sweep_contact_photo = None

        self.source_path_var = tk.StringVar(value="")
        self.workspace_root_var = tk.StringVar(value=str(workspace_root.resolve()))
        self.state_var = tk.StringVar(value=SessionState.EMPTY.value)
        self.status_var = tk.StringVar(value=self.session.status_text)
        self.binding_var = tk.StringVar(value="No Agent Bundle binding yet.")
        self.packet_info_var = tk.StringVar(value="Bundle is generated automatically after finding import.")
        self.attachment_var = tk.StringVar(value="Required attachments will appear here.")
        self.preview_status_var = tk.StringVar(value="No finding frame loaded.")
        self.candidate_preview_status_var = tk.StringVar(value="No candidate frame yet.")
        self.changed_paths_var = tk.StringVar(value="No override changes have been proven.")
        self.auto_promote_var = tk.BooleanVar(value=True)
        self.automated_run_budget_usd_var = tk.StringVar(value="0.00")
        self.automated_disclosure_profile_var = tk.StringVar(
            value=DisclosureProfile.ASSISTED.value
        )
        self.automated_credential_var = tk.StringVar(value="Credential: not checked")
        self.automated_state_var = tk.StringVar(value="Protocol: idle")
        self.automated_authority_var = tk.StringVar(value="Authority: no active automated run")
        self.automated_budget_var = tk.StringVar(
            value=(
                "Rounds 0/2 · Responses 0/6 · Tokens total/cached/uncached/out 0/0/0/0 · "
                "Cache writes 0 · Calculated USD 0/0 · Next max 0"
            )
        )
        self.automated_disposition_var = tk.StringVar(value="Disposition: not started")
        self.sweep_status_var = tk.StringVar(value="Sweep: not validated")
        self.sweep_binding_var = tk.StringVar(value="No validated scalar sweep binding.")
        self.automated_summary_var = tk.StringVar(
            value="Credential not configured · no automated run"
        )
        mode_detail = (
            "warn + attempt current runtime"
            if self.runtime_compatibility_mode == "development"
            else "warn + stop before materialization"
        )
        self.runtime_compatibility_var = tk.StringVar(
            value=f"Runtime compatibility: {self.runtime_compatibility_mode.upper()} ({mode_detail})"
        )

        self._configure_root()
        self._build_shell()
        self._build_automation_window()
        self._build_sweep_window()
        self._refresh_credential_status()
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
        ttk.Label(header, textvariable=self.runtime_compatibility_var).grid(
            row=1, column=0, columnspan=3, sticky="w", pady=(4, 0)
        )

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
        ttk.Label(source, text="Capture or Agent Packet folder").grid(row=0, column=0, sticky="w", padx=(0, 8))
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
        self.open_finding_button = ttk.Button(source, text="Open Finding / Packet", command=self.open_finding)
        self.open_finding_button.grid(row=2, column=0, columnspan=4, sticky="ew", pady=(8, 0))
        ttk.Label(
            source,
            text=(
                "Captures remain read-only and are mirrored into the durable workspace. "
                "An existing supported agent packet folder is bound read-only without refresh."
            ),
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

        packet = ttk.LabelFrame(self.left, text="3. Exact Agent Bundle V8", padding=8)
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
        automation_entry = ttk.Frame(binding)
        automation_entry.grid(row=1, column=0, sticky="ew", pady=(8, 0))
        automation_entry.columnconfigure(1, weight=1)
        self.open_automation_panel_button = ttk.Button(
            automation_entry,
            text="Automated Session…",
            command=self.open_automation_panel,
        )
        self.open_automation_panel_button.grid(row=0, column=0, sticky="w", padx=(0, 8))
        ttk.Label(
            automation_entry,
            textvariable=self.automated_summary_var,
            wraplength=520,
        ).grid(row=0, column=1, sticky="w")
        self._build_override_editor()

    def _build_automation_window(self) -> None:
        from tkinter.scrolledtext import ScrolledText

        ttk = self.ttk
        window = self.tk.Toplevel(self.root)
        window.title("Packet V8 Automated Session POC")
        window.geometry("840x620")
        window.minsize(720, 520)
        window.transient(self.root)
        window.protocol("WM_DELETE_WINDOW", window.withdraw)
        window.columnconfigure(0, weight=1)
        window.rowconfigure(1, weight=1)
        window.withdraw()
        self.automation_window = window

        header = ttk.Frame(window, padding=(12, 12, 12, 8))
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(0, weight=1)
        ttk.Label(
            header,
            text="Bounded Packet V8 Automated Session",
            font=("Segoe UI", 13, "bold"),
        ).grid(row=0, column=0, sticky="w")
        ttk.Label(
            header,
            text=(
                "This route reuses the exact Packet V8, sparse-override validator, proof service, "
                "timeout policy, and finding promotion path. It never records human acceptance."
            ),
            wraplength=720,
        ).grid(row=1, column=0, sticky="w", pady=(5, 0))

        automation = ttk.LabelFrame(window, text="Automated Packet V8 route (POC)", padding=10)
        automation.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))
        automation.columnconfigure(0, weight=1)
        automation.rowconfigure(8, weight=1)
        controls = ttk.Frame(automation)
        controls.grid(row=0, column=0, sticky="ew")
        self.set_api_key_button = ttk.Button(
            controls, text="Set OpenAI API Key…", command=self.set_automated_api_key
        )
        self.set_api_key_button.grid(row=0, column=0, padx=(0, 5))
        self.run_automated_button = ttk.Button(
            controls, text="Run Automated Session", command=self.run_automated_session
        )
        self.run_automated_button.grid(row=0, column=1, padx=5)
        self.cancel_automated_button = ttk.Button(
            controls, text="Cancel Automation", command=self.cancel_automated_session
        )
        self.cancel_automated_button.grid(row=0, column=2, padx=5)
        self.open_automated_results_button = ttk.Button(
            controls, text="Open Run Folder", command=self.open_automated_results
        )
        self.open_automated_results_button.grid(row=0, column=3, padx=(5, 0))
        ttk.Label(controls, text="Run budget USD:").grid(row=0, column=4, padx=(14, 4))
        self.automated_run_budget_entry = ttk.Entry(
            controls, textvariable=self.automated_run_budget_usd_var, width=9
        )
        self.automated_run_budget_entry.grid(row=0, column=5)
        ttk.Label(controls, text="Context:").grid(row=0, column=6, padx=(14, 4))
        self.automated_disclosure_profile = ttk.Combobox(
            controls,
            textvariable=self.automated_disclosure_profile_var,
            values=tuple(profile.value for profile in DisclosureProfile),
            state="readonly",
            width=12,
        )
        self.automated_disclosure_profile.grid(row=0, column=7)
        self.auto_promote_check = ttk.Checkbutton(
            automation,
            text="Auto-promote replay-proven candidates (never human acceptance)",
            variable=self.auto_promote_var,
        )
        self.auto_promote_check.grid(row=1, column=0, sticky="w", pady=(5, 0))
        ttk.Label(automation, textvariable=self.automated_credential_var, wraplength=650).grid(
            row=2, column=0, sticky="w", pady=(4, 0)
        )
        ttk.Label(automation, textvariable=self.automated_state_var, wraplength=650).grid(
            row=3, column=0, sticky="w"
        )
        ttk.Label(automation, textvariable=self.automated_authority_var, wraplength=650).grid(
            row=4, column=0, sticky="w"
        )
        ttk.Label(automation, textvariable=self.automated_budget_var, wraplength=650).grid(
            row=5, column=0, sticky="w"
        )
        ttk.Label(automation, textvariable=self.automated_disposition_var, wraplength=650).grid(
            row=6, column=0, sticky="w"
        )
        ttk.Label(
            automation,
            text="Sanitized live event stream (events.ndjson is authoritative)",
        ).grid(row=7, column=0, sticky="w", pady=(8, 2))
        self.automated_event_text = ScrolledText(
            automation,
            height=12,
            wrap="none",
            font=("Consolas", 9),
            state="disabled",
        )
        self.automated_event_text.grid(row=8, column=0, sticky="nsew")

    def open_automation_panel(self) -> None:
        self.automation_window.deiconify()
        self.automation_window.lift()
        self.automation_window.focus_set()

    def _build_sweep_window(self) -> None:
        from tkinter.scrolledtext import ScrolledText

        ttk = self.ttk
        window = self.tk.Toplevel(self.root)
        window.title("Local Scalar Bracket Sweep V1")
        window.geometry("1040x820")
        window.minsize(820, 650)
        window.protocol("WM_DELETE_WINDOW", window.withdraw)
        window.columnconfigure(0, weight=1)
        window.rowconfigure(2, weight=1)
        window.withdraw()
        self.sweep_window = window

        header = ttk.Frame(window, padding=(12, 12, 12, 8))
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(0, weight=1)
        ttk.Label(
            header,
            text="Bounded Local Scalar Bracket Sweep",
            font=("Segoe UI", 13, "bold"),
        ).grid(row=0, column=0, sticky="w")
        ttk.Label(
            header,
            text=(
                "Each value starts from the exact Packet V8 base and reuses the ordinary "
                "override, timeout, proof, and proof-owned PNG services. Results are review "
                "evidence and never human acceptance."
            ),
            wraplength=940,
        ).grid(row=1, column=0, sticky="w", pady=(5, 0))

        controls = ttk.Frame(window, padding=(12, 0, 12, 8))
        controls.grid(row=1, column=0, sticky="ew")
        self.validate_sweep_button = ttk.Button(
            controls, text="Validate Sweep", command=self.validate_scalar_sweep
        )
        self.validate_sweep_button.grid(row=0, column=0, padx=(0, 5))
        self.run_sweep_button = ttk.Button(
            controls, text="Run Local Sweep", command=self.run_scalar_sweep
        )
        self.run_sweep_button.grid(row=0, column=1, padx=5)
        self.cancel_sweep_button = ttk.Button(
            controls, text="Cancel Sweep", command=self.cancel_scalar_sweep
        )
        self.cancel_sweep_button.grid(row=0, column=2, padx=5)
        self.open_sweep_folder_button = ttk.Button(
            controls, text="Open Sweep Folder", command=self.open_sweep_folder
        )
        self.open_sweep_folder_button.grid(row=0, column=3, padx=5)
        self.open_contact_sheet_button = ttk.Button(
            controls, text="Open Contact Sheet", command=self.open_sweep_contact_sheet
        )
        self.open_contact_sheet_button.grid(row=0, column=4, padx=(5, 0))

        body = ttk.Frame(window, padding=(12, 0, 12, 12))
        body.grid(row=2, column=0, sticky="nsew")
        body.columnconfigure(0, weight=1)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(1, weight=1)

        plan = ttk.LabelFrame(body, text="Scalar Bracket Sweep JSON", padding=8)
        plan.grid(row=0, column=0, rowspan=2, sticky="nsew", padx=(0, 5))
        plan.columnconfigure(0, weight=1)
        plan.rowconfigure(1, weight=1)
        ttk.Label(
            plan,
            text=(
                "The main State Override editor is the optional fixed override. "
                "A fixed override containing the axis is rejected."
            ),
            wraplength=460,
        ).grid(row=0, column=0, sticky="w", pady=(0, 6))
        self.sweep_plan_text = ScrolledText(plan, height=22, wrap="none", undo=True)
        self.sweep_plan_text.grid(row=1, column=0, sticky="nsew")
        self.sweep_plan_text.insert(
            "1.0",
            '{\n  "sweep_version": 1,\n  "axis": {\n'
            '    "path": "params.vortex_strength",\n'
            '    "values": [0, 0.25, 0.5, 0.75, 1]\n'
            '  },\n  "member_failure_policy": "continue_independent"\n}\n',
        )
        self.sweep_plan_text.edit_modified(False)
        self.sweep_plan_text.bind("<<Modified>>", self._sweep_plan_modified)
        ttk.Label(plan, textvariable=self.sweep_binding_var, wraplength=460).grid(
            row=2, column=0, sticky="w", pady=(6, 0)
        )

        progress = ttk.LabelFrame(body, text="Per-member progress", padding=8)
        progress.grid(row=0, column=1, sticky="nsew", padx=(5, 0), pady=(0, 5))
        progress.columnconfigure(0, weight=1)
        progress.rowconfigure(1, weight=1)
        ttk.Label(progress, textvariable=self.sweep_status_var, wraplength=460).grid(
            row=0, column=0, sticky="w", pady=(0, 5)
        )
        self.sweep_progress_text = ScrolledText(
            progress, height=10, wrap="word", state="disabled", font=("Consolas", 9)
        )
        self.sweep_progress_text.grid(row=1, column=0, sticky="nsew")
        self._set_text(self.sweep_progress_text, "No local sweep has run.")

        contact = ttk.LabelFrame(body, text="Derived contact sheet (not acceptance)", padding=8)
        contact.grid(row=1, column=1, sticky="nsew", padx=(5, 0), pady=(5, 0))
        contact.columnconfigure(0, weight=1)
        contact.rowconfigure(0, weight=1)
        self.sweep_contact_label = ttk.Label(contact, text="No contact sheet", anchor="center")
        self.sweep_contact_label.grid(row=0, column=0, sticky="nsew")

    def open_sweep_panel(self) -> None:
        self.sweep_window.deiconify()
        self.sweep_window.lift()
        self.sweep_window.focus_set()

    def _build_override_editor(self) -> None:
        from tkinter.scrolledtext import ScrolledText

        ttk = self.ttk
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
        self.open_sweep_panel_button = ttk.Button(
            override,
            text="Local Scalar Sweep…",
            command=self.open_sweep_panel,
        )
        self.open_sweep_panel_button.grid(row=2, column=0, sticky="w", pady=(6, 0))

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
            "No proof has run. Paste a sparse state override after the exact Agent Bundle V8 is ready.",
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

        path = filedialog.askdirectory(title="Choose capture bundle or existing agent packet folder")
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

    def open_packet_path(self, packet_dir: Path) -> None:
        self.source_path_var.set(str(packet_dir))
        self.runner.cancel_all()
        self._busy_kinds.clear()
        generation = self.session.begin_finding_change()
        self._clear_finding_views(retain_override=True)
        self.session.status_text = "Loading one existing immutable agent-packet binding…"
        self._submit(
            "packet_load",
            JobRequestIdentity(generation=generation),
            lambda _context: load_existing_packet_context(packet_dir),
            self._packet_context_loaded,
        )
        self._render()

    def open_finding(self) -> None:
        source_text = self.source_path_var.get().strip()
        workspace_text = self.workspace_root_var.get().strip()
        if not source_text:
            self._set_error("A capture source or existing agent packet folder is required.")
            return
        source_path = Path(source_text)
        if source_path.is_dir() and (source_path / "packet.md").is_file() and (source_path / "manifest.json").is_file():
            self.open_packet_path(source_path)
            return
        if not workspace_text:
            self._set_error("A durable workspace is required when importing a capture source.")
            return
        self.runner.cancel_all()
        self._busy_kinds.clear()
        generation = self.session.begin_finding_change()
        self._clear_finding_views(retain_override=True)
        self._submit(
            "finding_import",
            JobRequestIdentity(generation=generation),
            lambda _context: load_finding_context(source_path, Path(workspace_text)),
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
        self._start_base_preview(finding)
        self.build_packet()
        self._render()

    def _packet_context_loaded(self, outcome: JobOutcome) -> None:
        self._busy_kinds.discard(outcome.kind)
        if outcome.identity.generation != self.session.generation or outcome.cancelled:
            self._render()
            return
        if outcome.error:
            self._set_error(f"Existing agent-packet load failed: {outcome.error}")
            self._render()
            return
        context = outcome.value
        if not isinstance(context, ExistingPacketContext):
            self._set_error("Existing packet load returned an invalid result.")
            self._render()
            return
        finding = context.finding
        self.workspace_root_var.set(str(finding.workspace_root))
        self.session.accept_finding(finding)
        self._set_text(self.summary_text, finding.summary_text)
        self._start_base_preview(finding)
        self._activate_bundle(context.bundle, loaded_existing=True)
        self._render()

    def _start_base_preview(self, finding: FindingContext) -> None:
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
            self._set_error("Open a finding before building its exact Agent Bundle V8.")
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
            self._set_error(f"Agent Bundle V8 generation failed: {outcome.error}")
            self._render()
            return
        bundle = outcome.value
        if not isinstance(bundle, AgentBundle):
            self._set_error("Bundle generation returned an invalid result.")
            self._render()
            return
        self._activate_bundle(bundle, loaded_existing=False)
        self._render()

    def _activate_bundle(self, bundle: AgentBundle, *, loaded_existing: bool) -> None:
        handoff = load_agent_bundle_handoff(bundle.packet_dir)
        self.session.accept_bundle(bundle)
        self._set_text(self.packet_text, handoff.packet_text)
        self._set_text(self.proof_text, "No proof has run for this exact Agent Bundle binding.")
        self.binding_var.set(
            f"Packet {bundle.packet_id}\nManifest SHA-256 {bundle.manifest_sha256}\n"
            f"Finding {bundle.finding_id}\nSelector {bundle.selected_fractal_type}"
        )
        self.packet_info_var.set(f"{len(handoff.packet_text.encode('utf-8')):,} byte index")
        required = ", ".join(handoff.required_attachments)
        recommended = ", ".join(handoff.recommended_attachments) or "none"
        unavailable = ", ".join(handoff.unavailable_optional_attachments) or "none"
        self.attachment_var.set(
            f"Drag all files in this packet folder: {required}\n"
            f"Recommended extras: {recommended} · Unavailable optional: {unavailable}"
        )
        if loaded_existing:
            self.session.status_text = (
                f"Loaded existing immutable Agent Bundle V{bundle.packet_version} {bundle.packet_id}; "
                "paste the override returned for this exact packet."
            )

    def copy_packet(self) -> None:
        bundle = self.session.bundle
        if bundle is None:
            self._set_error("Build an exact Agent Bundle V8 before copying packet.md.")
            return
        copy_agent_packet(bundle.packet_dir, self._write_clipboard)
        self.session.status_text = (
            f"Copied packet.md for {bundle.packet_id}. Primary handoff remains drag-all from the bundle folder."
        )
        self._render()

    def open_bundle_folder(self) -> None:
        bundle = self.session.bundle
        if bundle is None:
            self._set_error("No Agent Bundle folder is active.")
            return
        try:
            open_agent_bundle_folder(bundle.packet_dir)
            self.session.status_text = (
                f"Opened exact Agent Bundle V{bundle.packet_version} folder {bundle.packet_id}."
            )
        except Exception as exc:
            self._set_error(str(exc))
        self._render()

    def _refresh_credential_status(self) -> None:
        try:
            credential = resolve_openai_api_key()
        except Exception as exc:
            self._credential_available = False
            self.automated_credential_var.set(f"Credential unavailable: {exc}")
            return
        self._credential_available = credential is not None
        self.automated_credential_var.set(
            f"Credential: available from {credential.source}"
            if credential is not None
            else "Credential: not configured (no API request can start)"
        )

    def set_automated_api_key(self) -> None:
        from tkinter import simpledialog

        value = simpledialog.askstring(
            "Set OpenAI API Key",
            "Store the API key in Windows Credential Manager target openai/api_key.",
            show="*",
            parent=self.root,
        )
        if value is None:
            return
        try:
            store_openai_api_key(value)
            self._refresh_credential_status()
            self.session.status_text = (
                "Stored the OpenAI API key in Windows Credential Manager. The key was not written to app data."
            )
        except Exception as exc:
            self._set_error(f"Could not store OpenAI API key: {exc}")
        self._render()

    def run_automated_session(self) -> None:
        bundle = self.session.bundle
        finding = self.session.finding
        if bundle is None or finding is None:
            self._set_error("Open a finding and build its exact Packet V8 before automation.")
            self._render()
            return
        if bundle.packet_version != 8:
            self._set_error("Automated sessions require an exact Packet V8 binding.")
            self._render()
            return
        if self._busy_kinds:
            self._set_error("Wait for current finding, packet, preview, or proof work to finish first.")
            self._render()
            return
        try:
            credential = resolve_openai_api_key()
        except Exception as exc:
            self._set_error(f"OpenAI credential lookup failed: {exc}")
            self._render()
            return
        if credential is None:
            self._set_error("No OpenAI API key is configured. Use Set OpenAI API Key first.")
            self._refresh_credential_status()
            self._render()
            return
        workspace_root = Path(self.workspace_root_var.get().strip()).resolve()
        try:
            run_budget_usd = Decimal(self.automated_run_budget_usd_var.get().strip())
        except (InvalidOperation, ValueError):
            self._set_error("Run budget USD must be a finite non-negative decimal.")
            self._render()
            return
        if not run_budget_usd.is_finite() or run_budget_usd < 0:
            self._set_error("Run budget USD must be a finite non-negative decimal.")
            self._render()
            return
        budgets = SessionBudgets(maximum_calculated_cost_usd=run_budget_usd)
        try:
            disclosure_profile = DisclosureProfile(
                self.automated_disclosure_profile_var.get().strip()
            )
        except ValueError:
            self._set_error("Context profile must be blind, assisted, or break_blind.")
            self._render()
            return
        try:
            pricing_policy = load_pricing_policy()
        except Exception as exc:
            self._set_error(f"Pricing policy could not be loaded: {exc}")
            self._render()
            return
        run_id = f"v8-auto-{uuid.uuid4()}"
        try:
            store = AutomatedRunStore.create(
                workspace_root,
                run_id=run_id,
                protocol_snapshot={
                    "schema": AGENT_SESSION_PROTOCOL_SCHEMA,
                    "model": "gpt-5.6",
                    "reasoning_effort": "high",
                    "budgets": budgets.to_dict(),
                    "pricing_policy": pricing_policy.identity_dict(),
                    "auto_promote": bool(self.auto_promote_var.get()),
                    "disclosure_profile": disclosure_profile.value,
                    "credential_source": credential.source,
                },
                initial_packet={
                    "packet_id": bundle.packet_id,
                    "manifest_sha256": bundle.manifest_sha256,
                    "finding_id": bundle.finding_id,
                },
            )
        except Exception as exc:
            self._set_error(f"Could not create automated run store: {exc}")
            self._render()
            return
        self._automated_run_store = store
        self._automated_result_dir = store.run_dir
        self._automated_last_event_sequence = 0
        self._set_text(self.automated_event_text, "Run store created; waiting for events.")
        self.automated_state_var.set("Protocol: starting")
        self.automated_authority_var.set(f"Authority: packet {bundle.packet_id}")
        self.automated_disposition_var.set("Disposition: RUNNING")
        auto_promote = bool(self.auto_promote_var.get())
        api_key = credential.value
        identity = JobRequestIdentity(
            generation=self.session.generation,
            finding_id=finding.finding_id,
            authoring_base_sha256=finding.authoring_base_sha256,
            packet_id=bundle.packet_id,
            packet_manifest_sha256=bundle.manifest_sha256,
        )

        def operation(context):
            transport = PacketV8ResponsesTransport(OpenAISDKProvider(api_key))
            services = create_job_bound_automated_route_services(
                runtime_cmd_path=self.runtime_cmd_path,
                workspace_root=workspace_root,
                job=context,
                runtime_compatibility_mode=self.runtime_compatibility_mode,
            )
            return AutomatedSessionController(
                transport=transport,
                run_store=store,
                initial_bundle=bundle,
                services=services,
                budgets=budgets,
                pricing_policy=pricing_policy,
                cancelled=lambda: context.cancelled,
                auto_promote=auto_promote,
                disclosure_profile=disclosure_profile,
            ).run()

        self._automated_job_id = self._submit(
            "automated_session",
            identity,
            operation,
            self._automated_session_completed,
        )
        if self._automated_job_id is None:
            self.automated_disposition_var.set("Disposition: RUNTIME_FAILED")
            self.session.status_text = (
                f"Automated run store was preserved, but the worker did not start: {store.run_dir}"
            )
            self._render()
            return
        self.session.status_text = (
            f"Started bounded automated Packet V8 session {run_id}. No candidate will be marked user-accepted."
        )
        self._render()

    def cancel_automated_session(self) -> None:
        job_id = self._automated_job_id
        if job_id is None or not self.runner.cancel(job_id):
            self.session.status_text = "No active automated session owns cancellable work."
        else:
            self.session.status_text = (
                "Cancellation requested for the automated session only; ambiguous remote completion will stop at manual review."
            )
        self._render()

    def _automated_session_completed(self, outcome: JobOutcome) -> None:
        self._busy_kinds.discard(outcome.kind)
        self._automated_job_id = None
        bundle = self.session.bundle
        if (
            outcome.identity.generation != self.session.generation
            or bundle is None
            or outcome.identity.packet_id != bundle.packet_id
            or outcome.identity.packet_manifest_sha256 != bundle.manifest_sha256
        ):
            self._render()
            return
        if outcome.cancelled:
            self.automated_disposition_var.set("Disposition: CANCELLED")
            self.session.status_text = "Automated session cancelled; durable run evidence was preserved."
        elif outcome.error:
            self.automated_disposition_var.set("Disposition: RUNTIME_FAILED")
            self._set_error(f"Automated session worker failed: {outcome.error}")
        elif isinstance(outcome.value, AutomatedSessionResult):
            result = outcome.value
            self.automated_disposition_var.set(f"Disposition: {result.disposition.value}")
            self.automated_authority_var.set(
                f"Authority: packet {result.current_packet.packet_id} · finding {result.current_packet.finding_id}"
            )
            self.automated_budget_var.set(
                f"Rounds {result.proven_rounds}/2 · Responses {result.usage.model_responses}/6 · "
                "Tokens total/cached/uncached/out "
                f"{result.usage.cumulative_input_tokens:,}/"
                f"{result.usage.cumulative_cached_input_tokens:,}/"
                f"{result.usage.cumulative_uncached_input_tokens:,}/"
                f"{result.usage.cumulative_output_tokens:,}"
                f" · Cache writes {result.usage.cumulative_cache_write_tokens:,}"
                f" · Calculated USD {result.usage.cumulative_calculated_cost_usd}/"
                f"{self.automated_run_budget_usd_var.get().strip()}"
            )
            self.session.status_text = result.message
        else:
            self.automated_disposition_var.set("Disposition: RUNTIME_FAILED")
            self._set_error("Automated session returned an invalid result.")
        self._refresh_automated_projection()
        self._render()

    def _refresh_automated_projection(self) -> None:
        store = self._automated_run_store
        if store is None:
            return
        try:
            active, events = store.load_live_snapshot()
            if active is None:
                return
            projection = active.get("projection")
            if not isinstance(projection, dict):
                return
            self.automated_state_var.set(f"Protocol: {projection.get('state', 'unknown')}")
            packet = projection.get("current_packet")
            if isinstance(packet, dict):
                self.automated_authority_var.set(
                    f"Authority: packet {packet.get('packet_id', '?')} · finding {packet.get('finding_id', '?')}"
                )
            self.automated_budget_var.set(_automated_budget_text(projection))
            self.automated_disposition_var.set(
                f"Disposition: {projection.get('controller_disposition', 'unknown')}"
            )
            latest_sequence = events[-1]["sequence"] if events else 0
            if latest_sequence != self._automated_last_event_sequence:
                self._set_text(
                    self.automated_event_text,
                    "\n".join(_format_automated_event(event) for event in events),
                )
                self.automated_event_text.see("end")
                self._automated_last_event_sequence = latest_sequence
        except Exception as exc:
            self.automated_disposition_var.set(f"Disposition projection unavailable: {exc}")

    def open_automated_results(self) -> None:
        if self._automated_result_dir is None:
            self._set_error("No automated result folder exists yet.")
            self._render()
            return
        try:
            os.startfile(str(self._automated_result_dir))
            self.session.status_text = f"Opened automated run evidence: {self._automated_result_dir}"
        except Exception as exc:
            self._set_error(f"Could not open automated result folder: {exc}")
        self._render()

    def _override_modified(self, _event=None) -> None:
        if self._setting_override or not self.override_text.edit_modified():
            return
        self.override_text.edit_modified(False)
        self.session.set_override_text(self.override_text.get("1.0", "end-1c"))
        self._invalidate_sweep_validation("Fixed override changed; validate the sweep again.")
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
        self._invalidate_sweep_validation("Fixed override changed; validate the sweep again.")
        self._clear_candidate_views()
        self._set_text(self.proof_text, "Override changed. Every prior proof and review binding is invalidated.")
        self._render()

    def _sweep_plan_modified(self, _event=None) -> None:
        if not self.sweep_plan_text.edit_modified():
            return
        self.sweep_plan_text.edit_modified(False)
        self._invalidate_sweep_validation("Sweep plan changed; validate it again.")
        self._render()

    def _invalidate_sweep_validation(self, message: str) -> None:
        self._sweep_validation_binding = None
        self.sweep_binding_var.set(message)

    def _current_sweep_binding(self) -> tuple[object, ...] | None:
        finding = self.session.finding
        bundle = self.session.bundle
        if finding is None or bundle is None:
            return None
        override_text = self.session.override_text
        plan_text = self.sweep_plan_text.get("1.0", "end-1c")
        return (
            self.session.generation,
            finding.finding_id,
            finding.authoring_base_sha256,
            bundle.packet_id,
            bundle.manifest_sha256,
            hashlib.sha256(override_text.encode("utf-8")).hexdigest(),
            hashlib.sha256(plan_text.encode("utf-8")).hexdigest(),
        )

    def _sweep_identity(self) -> JobRequestIdentity | None:
        binding = self._current_sweep_binding()
        if binding is None:
            return None
        return JobRequestIdentity(
            generation=binding[0],
            finding_id=binding[1],
            authoring_base_sha256=binding[2],
            packet_id=binding[3],
            packet_manifest_sha256=binding[4],
            override_text_sha256=binding[5],
            sweep_plan_sha256=binding[6],
        )

    def _sweep_outcome_is_current(self, outcome: JobOutcome) -> bool:
        current = self._sweep_identity()
        return current is not None and outcome.identity == current

    def validate_scalar_sweep(self) -> None:
        bundle = self.session.bundle
        identity = self._sweep_identity()
        if bundle is None or identity is None:
            self._set_error("Open a finding and build its exact Packet V8 before validating a sweep.")
            self._render()
            return
        fixed_text = self.session.override_text
        plan_text = self.sweep_plan_text.get("1.0", "end-1c")
        self._sweep_validation_binding = None
        self.sweep_status_var.set("Sweep: validating exact Packet V8 authorability…")
        self._set_text(self.sweep_progress_text, "Validating every concrete member before rendering.")

        def operation(_context):
            return ScalarBracketSweepService().validate(
                packet_dir=bundle.packet_dir,
                fixed_override_text=fixed_text,
                plan_text=plan_text,
                runtime_cmd_path=self.runtime_cmd_path,
            )

        self._sweep_job_id = self._submit(
            "sweep_validation", identity, operation, self._sweep_validation_completed
        )
        self._render()

    def _sweep_validation_completed(self, outcome: JobOutcome) -> None:
        self._busy_kinds.discard(outcome.kind)
        self._sweep_job_id = None
        if not self._sweep_outcome_is_current(outcome) or outcome.cancelled:
            self._render()
            return
        if outcome.error:
            self.sweep_status_var.set("Sweep: PLAN INVALID")
            self._set_error(f"Scalar sweep validation failed: {outcome.error}")
            self._set_text(self.sweep_progress_text, f"PLAN FAILURE\n\n{outcome.error}")
            self._render()
            return
        validation = outcome.value
        binding = self._current_sweep_binding()
        self._sweep_validation_binding = binding
        values = list(validation.plan.values)
        self.sweep_status_var.set(
            f"Sweep: VALIDATED · {validation.plan.axis_path} · {len(values)} members"
        )
        self.sweep_binding_var.set(
            f"Packet {validation.binding.packet_id} · manifest "
            f"{validation.binding.manifest_sha256} · values {values}"
        )
        self._set_text(
            self.sweep_progress_text,
            "PLAN VALIDATED\nNo engine member has rendered. Run Local Sweep to begin.",
        )
        self._render()

    def run_scalar_sweep(self) -> None:
        bundle = self.session.bundle
        identity = self._sweep_identity()
        if (
            bundle is None
            or identity is None
            or self._sweep_validation_binding != self._current_sweep_binding()
        ):
            self._set_error("Validate the exact current sweep plan and fixed override before running.")
            self._render()
            return
        fixed_text = self.session.override_text
        plan_text = self.sweep_plan_text.get("1.0", "end-1c")
        self._sweep_result_dir = None
        self._sweep_contact_photo = None
        self.sweep_contact_label.configure(image="", text="Sweep running…")
        self.sweep_status_var.set("Sweep: starting local proofs")
        self._set_text(self.sweep_progress_text, "Starting independently bound members…")

        def progress(event: dict) -> None:
            self._completion_queue.put(
                lambda captured=dict(event), expected=identity: self._handle_scalar_sweep_progress(
                    captured, expected
                )
            )

        def operation(context):
            return ScalarBracketSweepService().execute(
                packet_dir=bundle.packet_dir,
                fixed_override_text=fixed_text,
                plan_text=plan_text,
                runtime_cmd_path=self.runtime_cmd_path,
                job=context,
                runtime_compatibility_mode=self.runtime_compatibility_mode,
                on_progress=progress,
            )

        self._sweep_job_id = self._submit(
            "scalar_sweep", identity, operation, self._scalar_sweep_completed
        )
        self._render()

    def _handle_scalar_sweep_progress(
        self, event: dict, expected_identity: JobRequestIdentity
    ) -> None:
        if self._closed or self._sweep_identity() != expected_identity:
            return
        line = _format_scalar_sweep_progress(event)
        current = self.sweep_progress_text.get("1.0", "end-1c")
        if current in {"Starting independently bound members…", "No local sweep has run."}:
            current = ""
        self._set_text(
            self.sweep_progress_text,
            (current + "\n" + line).strip(),
        )
        self.sweep_progress_text.see("end")
        if event.get("event") == "MEMBER_STARTED":
            self.sweep_status_var.set(
                f"Sweep: member {event.get('index')} · value {event.get('value')} · RUNNING"
            )
        elif event.get("event") == "SWEEP_COMPLETED":
            self.sweep_status_var.set(f"Sweep: {event.get('disposition')}")

    def _scalar_sweep_completed(self, outcome: JobOutcome) -> None:
        self._busy_kinds.discard(outcome.kind)
        self._sweep_job_id = None
        if not self._sweep_outcome_is_current(outcome) or outcome.cancelled:
            if outcome.cancelled:
                self.sweep_status_var.set("Sweep: CANCELLED")
            self._render()
            return
        if outcome.error:
            self.sweep_status_var.set("Sweep: FAILED")
            self._set_error(f"Scalar sweep failed: {outcome.error}")
            self._render()
            return
        result = outcome.value
        if not isinstance(result, ScalarSweepResult):
            self._set_error("Scalar sweep returned an invalid result.")
            self._render()
            return
        self._sweep_result_dir = result.sweep_dir
        self.sweep_status_var.set(
            f"Sweep: {result.disposition} · {len(result.members)} members · human acceptance: false"
        )
        receipt = self._read_json(result.receipt_path)
        contact_relative = receipt.get("presentation", {}).get("contact_sheet_path")
        if isinstance(contact_relative, str):
            contact_path = result.sweep_dir / contact_relative
            try:
                with Image.open(contact_path) as opened:
                    opened.load()
                    preview = opened.convert("RGB")
                preview.thumbnail((440, 330), Image.Resampling.LANCZOS)
                self._sweep_contact_photo = ImageTk.PhotoImage(preview)
                self.sweep_contact_label.configure(
                    image=self._sweep_contact_photo,
                    text="",
                )
            except Exception as exc:
                self.sweep_contact_label.configure(image="", text="Contact sheet unavailable")
                self._set_error(f"Could not preview the receipted contact sheet: {exc}")
        self.session.status_text = (
            f"Local scalar sweep {result.disposition}. Open the contact sheet and member proofs; "
            "no human acceptance was recorded."
        )
        self._render()

    def cancel_scalar_sweep(self) -> None:
        if self._sweep_job_id is None or not self.runner.cancel(self._sweep_job_id):
            self.session.status_text = "No active scalar sweep owns cancellable work."
        else:
            self.session.status_text = (
                "Cancellation requested for the local sweep; completed member proofs remain durable."
            )
        self._render()

    def open_sweep_folder(self) -> None:
        if self._sweep_result_dir is None:
            self._set_error("No completed or partial scalar sweep folder is available.")
            self._render()
            return
        try:
            os.startfile(str(self._sweep_result_dir))
            self.session.status_text = f"Opened scalar sweep evidence: {self._sweep_result_dir}"
        except Exception as exc:
            self._set_error(f"Could not open scalar sweep folder: {exc}")
        self._render()

    def open_sweep_contact_sheet(self) -> None:
        if self._sweep_result_dir is None:
            self._set_error("No scalar sweep contact sheet is available.")
            self._render()
            return
        path = self._sweep_result_dir / "presentation" / "contact-sheet.png"
        try:
            if not path.is_file():
                raise FileNotFoundError(path)
            os.startfile(str(path))
            self.session.status_text = f"Opened derived scalar sweep contact sheet: {path}"
        except Exception as exc:
            self._set_error(f"Could not open scalar sweep contact sheet: {exc}")
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
            "PROVING\n\nValidating exact agent-packet authority, deterministically merging the override, "
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
                runtime_compatibility_mode=self.runtime_compatibility_mode,
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
            compatibility = receipt.get("binding", {}).get("runtime_compatibility", {})
            runtime_drift_note = ""
            if compatibility.get("drift_detected") is True:
                differences = compatibility.get("differences", [])
                runtime_drift_note = (
                    "RUNTIME DRIFT WARNING\n"
                    f"Mode: {compatibility.get('mode')} · disposition: {compatibility.get('disposition')}\n"
                    f"Packet/current identity differences: {len(differences)}. "
                    "This proof is bound to the current runtime actually used.\n\n"
                )
                self.session.status_text = (
                    "Runtime identity differs from the packet snapshot; development mode proved against "
                    "and bound the current runtime. Review the receipt differences."
                )
            exact_base_replay = _is_exact_base_replay(result)
            normalized = [
                item
                for item in receipt.get("requested_value_receipts", [])
                if item.get("classification") == "representation_normalization"
            ]
            changed = receipt.get("override", {}).get("changed_paths", [])
            paths = [item.get("path", "?") for item in changed]
            self.changed_paths_var.set(
                "Changed paths: "
                + (
                    ", ".join(paths)
                    if paths
                    else "none — exact base replay"
                    if exact_base_replay
                    else "none"
                )
            )
            normalization_note = (
                "\nRepresentation normalization:\n"
                + "\n".join(
                    f"- {item['path']}: {item['requested_value']!r} → {item['engine_emitted_value']!r}"
                    for item in normalized
                )
                if normalized
                else ""
            )
            materialization_receipt = receipt.get("materialization", {})
            base_frame_comparison = materialization_receipt.get("base_to_candidate_frame_comparison")
            if isinstance(base_frame_comparison, dict):
                if base_frame_comparison.get("decoded_equal") is True:
                    visual_delta_note = (
                        "\nCandidate visual delta:\n"
                        "- IDENTICAL decoded pixels to the captured base frame. "
                        "The requested state may have been preserved without affecting rendered output."
                    )
                else:
                    visual_delta_note = "\nCandidate visual delta:\n- Decoded pixels differ from the captured base frame."
            else:
                visual_delta_note = "\nCandidate visual delta:\n- Captured base-frame comparison unavailable."
            emitted_differences = [
                item
                for item in materialization_receipt.get("merged_to_emitted_state_comparison", {}).get(
                    "differences", []
                )
                if item.get("classification") != "volatile_diagnostic_data"
            ]
            emitted_note = ""
            if emitted_differences:
                displayed = emitted_differences[:12]
                emitted_note = (
                    "\nEngine materialization changes beyond the requested diff:\n"
                    + "\n".join(
                        f"- {item.get('path', '?')}: {item.get('left')!r} → {item.get('right')!r} "
                        f"[{item.get('classification', 'unclassified')}]"
                        for item in displayed
                    )
                )
                if len(emitted_differences) > len(displayed):
                    emitted_note += f"\n- … {len(emitted_differences) - len(displayed)} additional changes in receipt"
            if exact_base_replay:
                proof_heading = (
                    "NO-OP OVERRIDE — EXACT BASE REPLAY\n"
                    "REPLAY PROVEN\n"
                    "EXPLICIT ACKNOWLEDGEMENT REQUIRED\n\n"
                    "Merged input is byte-identical to the authoritative base state. "
                    "The engine-emitted launch candidate may contain documented volatile diagnostic changes.\n\n"
                )
            else:
                proof_heading = "OVERRIDE ACCEPTED\nREPLAY PROVEN\nVISUAL REVIEW PENDING\n\n"
            self._set_text(
                self.proof_text,
                runtime_drift_note
                + proof_heading
                + f"{result.message}\n\nEngine candidate SHA-256: {result.engine_candidate_sha256}"
                + f"{normalization_note}{visual_delta_note}{emitted_note}\n\nReceipt: {result.receipt_path}",
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
            receipt = self._read_json(result.receipt_path)
            compatibility = receipt.get("binding", {}).get("runtime_compatibility", {})
            runtime_drift_note = (
                "RUNTIME DRIFT WARNING\n"
                f"Mode: {compatibility.get('mode')} · disposition: {compatibility.get('disposition')}\n\n"
                if compatibility.get("drift_detected") is True
                else ""
            )
            self._set_text(
                self.proof_text,
                runtime_drift_note
                + f"REJECTED\n\n{result.message}\n\nPreserved receipt: {result.receipt_path}",
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
        receipt = self._read_json(result.receipt_path)
        base_frame_comparison = receipt.get("materialization", {}).get(
            "base_to_candidate_frame_comparison"
        )
        pixel_note = _candidate_preview_pixel_note(result, base_frame_comparison)
        self.candidate_preview_status_var.set(
            f"{preview.source_width}×{preview.source_height} → {preview.preview_width}×{preview.preview_height} "
            f"({cache_note}){pixel_note}"
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
            record_state_override_review(
                result,
                "accepted",
                (
                    "User explicitly acknowledged exact base replay."
                    if _is_exact_base_replay(result)
                    else ""
                ),
            )
            self.session.record_review("accepted")
            errors = validate_state_override_launch_readiness(
                result, bundle.packet_dir, self.session.override_text, self.runtime_cmd_path
            )
            if errors:
                raise ValueError("; ".join(errors))
            self.session.mark_launch_ready()
            acceptance_heading = (
                "NO-OP BASE REPLAY ACKNOWLEDGED\nREPLAY PROVEN\nLAUNCH READY\n\n"
                if _is_exact_base_replay(result)
                else "OVERRIDE ACCEPTED\nREPLAY PROVEN\nUSER ACCEPTED\nLAUNCH READY\n\n"
            )
            self._set_text(
                self.proof_text,
                acceptance_heading
                + "The exact candidate, frame, packet, override, proof receipt, review decision, and runtime were rechecked.\n\n"
                + f"Candidate: {result.engine_candidate_path}\nReview decision: {result.proof_dir / 'review-decision.json'}",
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
            revision_heading = (
                "NO-OP BASE REPLAY\nREPLAY PROVEN\nREVISION NEEDED\n\n"
                if _is_exact_base_replay(result)
                else "OVERRIDE ACCEPTED\nREPLAY PROVEN\nREVISION NEEDED\n\n"
            )
            self._set_text(
                self.proof_text,
                revision_heading
                + "This proof remains immutable evidence. Edit the override to begin a new attempt.\n\n"
                + f"Decision: {result.proof_dir / 'review-decision.json'}",
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
                f"Started the exact-candidate launcher process (PID {process.pid}); viewer health is not machine-verified."
            )
            self._set_text(
                self.proof_text,
                "LAUNCH READY → LAUNCH COMMAND STARTED\n\n"
                f"Launcher process PID: {process.pid}\nViewer health: not machine-verified\n"
                f"Candidate: {result.engine_candidate_path}\n"
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
        try:
            os.startfile(str(finding.primary_frame_path))
        except Exception as exc:
            self._set_error(f"Could not open the full finding frame: {exc}")
            self._render()

    def open_candidate_frame(self) -> None:
        result = self.session.proof_result
        if result is None or result.candidate_display_path is None:
            self._set_error("No verified candidate PNG display derivative is available.")
            return
        try:
            os.startfile(str(result.candidate_display_path))
            self._candidate_full_frame_opened = True
            self.session.status_text = (
                "Opened the full-resolution PNG whose decoded RGBA pixels match the engine candidate."
            )
        except Exception as exc:
            self._set_error(f"Could not open the verified candidate PNG: {exc}")
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
        self._sweep_job_id = None
        self._sweep_validation_binding = None
        self._sweep_result_dir = None
        self._sweep_contact_photo = None
        self.sweep_status_var.set("Sweep: not validated")
        self.sweep_binding_var.set("No validated scalar sweep binding.")
        self._set_text(self.sweep_progress_text, "No local sweep has run.")
        self.sweep_contact_label.configure(image="", text="No contact sheet")
        self.session.reset()
        self.source_path_var.set("")
        self._clear_finding_views(retain_override=False)
        self._render()

    def _clear_finding_views(self, retain_override: bool) -> None:
        self._sweep_job_id = None
        self._sweep_validation_binding = None
        self._sweep_result_dir = None
        self._sweep_contact_photo = None
        self.sweep_status_var.set("Sweep: not validated")
        self.sweep_binding_var.set("No validated scalar sweep binding.")
        self._set_text(self.sweep_progress_text, "No local sweep has run.")
        self.sweep_contact_label.configure(image="", text="No contact sheet")
        self._set_text(self.summary_text, "")
        self._set_text(self.packet_text, "")
        self._set_text(self.proof_text, "No proof has run. Paste a sparse state override to begin.")
        self.binding_var.set("No Agent Bundle binding yet.")
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

    def _submit(
        self, kind: str, identity, operation, completion: Callable[[JobOutcome], None]
    ) -> str | None:
        self._busy_kinds.add(kind)
        try:
            return self.runner.submit(kind, identity, operation, completion)
        except (WorkerQueueFullError, RuntimeError) as exc:
            self._busy_kinds.discard(kind)
            self._set_error(str(exc))
            return None

    def _drain_completions(self) -> None:
        if self._closed:
            return
        while True:
            try:
                callback = self._completion_queue.get_nowait()
            except queue.Empty:
                break
            callback()
        now = time.monotonic()
        if now >= self._next_automated_refresh_at:
            self._next_automated_refresh_at = now + 0.25
            self._refresh_automated_projection()
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
        automated_busy = "automated_session" in self._busy_kinds
        sweep_busy = bool({"sweep_validation", "scalar_sweep"} & self._busy_kinds)
        workflow_busy = automated_busy or sweep_busy
        result = self.session.proof_result
        replay_proven = isinstance(result, StateOverrideProofResult) and result.status == "replay_proven"
        review_surface_seen = self.session.candidate_preview is not None or self._candidate_full_frame_opened
        undecided = replay_proven and self.session.review_decision is None and review_surface_seen
        self.open_finding_button.configure(
            state="disabled"
            if "finding_import" in self._busy_kinds or workflow_busy
            else "normal"
        )
        self.build_packet_button.configure(
            state="normal"
            if finding_ready and "bundle" not in self._busy_kinds and not workflow_busy
            else "disabled"
        )
        self.copy_packet_button.configure(state="normal" if bundle_ready else "disabled")
        self.open_bundle_button.configure(state="normal" if bundle_ready else "disabled")
        self.open_full_frame_button.configure(
            state="normal"
            if finding_ready and self.session.finding.primary_frame_path is not None
            else "disabled"
        )
        override_ready = bundle_ready and bool(self.session.override_text.strip())
        self.override_text.configure(state="disabled" if workflow_busy else "normal")
        self.prove_button.configure(
            state="normal" if override_ready and not proof_busy and not workflow_busy else "disabled"
        )
        self.open_candidate_frame_button.configure(state="normal" if replay_proven else "disabled")
        self.accept_button.configure(text=_candidate_accept_action_label(result))
        self.accept_button.configure(
            state="normal" if undecided and not proof_busy and not workflow_busy else "disabled"
        )
        self.revision_button.configure(
            state="normal" if undecided and not proof_busy and not workflow_busy else "disabled"
        )
        self.launch_button.configure(
            state="normal"
            if self.session.state == SessionState.LAUNCH_READY and not proof_busy and not workflow_busy
            else "disabled"
        )
        self.open_sweep_panel_button.configure(
            state="normal" if bundle_ready and not automated_busy else "disabled"
        )
        current_sweep_binding = self._current_sweep_binding()
        sweep_valid = (
            current_sweep_binding is not None
            and current_sweep_binding == self._sweep_validation_binding
        )
        self.sweep_plan_text.configure(state="disabled" if sweep_busy else "normal")
        self.validate_sweep_button.configure(
            state="normal" if bundle_ready and not self._busy_kinds else "disabled"
        )
        self.run_sweep_button.configure(
            state="normal" if sweep_valid and not self._busy_kinds else "disabled"
        )
        self.cancel_sweep_button.configure(state="normal" if sweep_busy else "disabled")
        self.open_sweep_folder_button.configure(
            state="normal" if self._sweep_result_dir is not None else "disabled"
        )
        contact_sheet = (
            self._sweep_result_dir / "presentation" / "contact-sheet.png"
            if self._sweep_result_dir is not None
            else None
        )
        self.open_contact_sheet_button.configure(
            state="normal" if contact_sheet is not None and contact_sheet.is_file() else "disabled"
        )
        self.run_automated_button.configure(
            state="normal"
            if bundle_ready and self._credential_available and not self._busy_kinds
            else "disabled"
        )
        self.cancel_automated_button.configure(state="normal" if automated_busy else "disabled")
        self.open_automated_results_button.configure(
            state="normal" if self._automated_result_dir is not None else "disabled"
        )
        self.set_api_key_button.configure(state="disabled" if automated_busy else "normal")
        self.auto_promote_check.configure(state="disabled" if automated_busy else "normal")
        self.automated_run_budget_entry.configure(
            state="disabled" if automated_busy else "normal"
        )
        self.automated_disclosure_profile.configure(
            state="disabled" if automated_busy else "readonly"
        )
        credential_summary = "credential available" if self._credential_available else "credential not configured"
        disposition_summary = self.automated_disposition_var.get().removeprefix("Disposition: ")
        self.automated_summary_var.set(
            f"{credential_summary} · {disposition_summary}"
        )
        self.copy_error_button.configure(state="normal" if self._last_copyable_error else "disabled")

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        if self._automated_job_id is not None:
            self.runner.cancel(self._automated_job_id)
        if self._sweep_job_id is not None:
            self.runner.cancel(self._sweep_job_id)
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
    parser.add_argument(
        "--runtime-compatibility",
        choices=("development", "strict"),
        default=None,
    )
    args, _unknown = parser.parse_known_args(argv)
    _enable_dpi_awareness()
    import tkinter as tk

    root = tk.Tk()
    app = UserWorkflowApp(
        root,
        workspace_root=args.workspace_root,
        runtime_compatibility_mode=args.runtime_compatibility,
    )
    if args.capture_source is not None:
        root.after(100, lambda: app.open_finding_path(args.capture_source, args.workspace_root))
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
