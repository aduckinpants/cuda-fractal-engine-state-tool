from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import os
from pathlib import Path
from typing import Any, Optional

from .baseline import BASELINE_ID, freeze_phase0_baseline, load_frozen_baseline
from .intake import build_intake_packet
from .json_utils import dumps_pretty, loads_no_duplicates
from .materializer import materialize_transport_candidate
from .process_utils import find_processes_by_name
from .proposal import (
    COLOR_TRIPLET_PATHS,
    PATH_SPECS,
    build_color_grading_example,
    build_color_shape_example,
    build_color_triplet_example,
    build_noop_example,
    parse_proposal_v1,
)
from .runtime_surface import DEFAULT_RUNTIME_CMD
from .state_workflow import PROMOTION_PROFILES, WorkflowResult, execute_proposal_workflow, launch_proven_candidate
from .workspace_layout import WorkspaceLayout


@dataclass
class Phase1Paths:
    data_root: Path
    probe_root: Path
    baselines_root: Path
    baseline_manifest_path: Path
    working_states_root: Path
    validation_runs_root: Path


def default_phase1_paths(repo_root: Optional[Path] = None) -> Phase1Paths:
    layout = WorkspaceLayout.from_repo_root(repo_root)
    data_root = layout.data_root
    return Phase1Paths(
        data_root=data_root,
        probe_root=layout.runtime_probe_root,
        baselines_root=layout.baselines_root,
        baseline_manifest_path=layout.baseline_manifest_path(BASELINE_ID),
        working_states_root=layout.working_states_root,
        validation_runs_root=layout.validation_runs_root,
    )


class Phase1Controller:
    def __init__(self, paths: Phase1Paths, runtime_cmd_path: Path = DEFAULT_RUNTIME_CMD) -> None:
        self.paths = paths
        self.runtime_cmd_path = runtime_cmd_path.resolve()
        self.last_workflow_result: Optional[WorkflowResult] = None
        self.last_materialized_candidate: Optional[Path] = None
        self._ensure_baseline()

    def _ensure_baseline(self) -> None:
        if self.paths.baseline_manifest_path.exists():
            self.baseline = load_frozen_baseline(self.paths.baseline_manifest_path)
            return
        self.baseline = freeze_phase0_baseline(self.paths.probe_root, self.paths.baselines_root)

    def baseline_status_text(self) -> str:
        return f"Baseline {self.baseline.baseline_id} frozen at {self.baseline.state_path}"

    def example_noop_proposal(self) -> str:
        return build_noop_example(self.baseline.manifest["state_sha256"])

    def example_color_proposal(self) -> str:
        return build_color_shape_example(self.baseline.manifest["state_sha256"])

    def example_grading_proposal(self) -> str:
        return build_color_grading_example(self.baseline.manifest["state_sha256"])

    def example_color_triplet_proposal(self) -> str:
        return build_color_triplet_example(self.baseline.manifest["state_sha256"])

    def materialize(self, proposal_text: str) -> Path:
        proposal = parse_proposal_v1(proposal_text, self.baseline.baseline_id, self.baseline.manifest["state_sha256"])
        state_id = "materialize_preview"
        state_dir = self.paths.working_states_root / state_id
        state_dir.mkdir(parents=True, exist_ok=True)
        proposal_path = state_dir / "proposal.json"
        proposal_path.write_text(proposal.raw_text, encoding="utf-8")
        candidate_path = state_dir / "transport_candidate.json"
        materialize_transport_candidate(self.baseline.state_path, proposal, candidate_path)
        self.last_materialized_candidate = candidate_path
        return candidate_path

    def available_promotion_profiles(self) -> list[str]:
        profiles = list(PROMOTION_PROFILES.keys())
        profiles.sort(key=lambda item: (item != "none", item))
        return profiles

    def replay_prove(self, proposal_text: str, promotion_profile: str = "none") -> WorkflowResult:
        state_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_phase1")
        self.last_workflow_result = execute_proposal_workflow(
            proposal_text,
            self.paths.baseline_manifest_path,
            self.paths.working_states_root,
            state_id,
            runtime_cmd_path=self.runtime_cmd_path,
            promotion_profile=promotion_profile,
        )
        return self.last_workflow_result

    def intake_packet(self) -> str:
        replay_state = self.paths.probe_root / "replay_one" / "state.json"
        if self.last_workflow_result and self.last_workflow_result.replay_state_path:
            replay_state = self.last_workflow_result.replay_state_path
        return build_intake_packet(self.paths.baseline_manifest_path, replay_state)

    def launch_new_viewer(self) -> int:
        if not self.last_workflow_result or not self.last_workflow_result.proven_state_path:
            raise ValueError("No replay-proven candidate is available to launch")
        process = launch_proven_candidate(self.runtime_cmd_path, self.last_workflow_result.proven_state_path)
        return process.pid

    def save_proposal_for_session(self, proposal_text: str, proposal_path: Path) -> Path:
        proposal = parse_proposal_v1(proposal_text, self.baseline.baseline_id, self.baseline.manifest["state_sha256"])
        proposal_path = proposal_path.resolve()
        proposal_path.parent.mkdir(parents=True, exist_ok=True)
        proposal_path.write_text(proposal.raw_text, encoding="utf-8")
        return proposal_path

    def build_web_session_command_bundle(self, proposal_path: Path, state_id: str, promotion_profile: str) -> str:
        proposal_path = proposal_path.resolve()
        baseline_manifest_path = self.paths.baseline_manifest_path.resolve()
        working_root = self.paths.working_states_root.resolve()
        return "\n".join(
            [
                '$env:PYTHONPATH = "src"',
                (
                    "py -3.14 -m cuda_fractal_state_tool.workflow_cli "
                    f"--proposal \"{proposal_path}\" "
                    f"--baseline-manifest \"{baseline_manifest_path}\" "
                    f"--working-root \"{working_root}\" "
                    f"--state-id {state_id} "
                    f"--promotion-profile {promotion_profile}"
                ),
                "py -3.14 -m cuda_fractal_state_tool.validation_runs --latest",
                "git status --short",
            ]
        )

    def build_web_session_prompt_template(self, proposal_path: Path, state_id: str, promotion_profile: str) -> str:
        proposal_path = proposal_path.resolve()
        return "\n".join(
            [
                "Run this workflow and paste back evidence:",
                "1) workflow status/runtime_status",
                "2) validation_path",
                "3) validation_run_manifest_path",
                "4) validation_runs_index_path",
                "5) git status --short output",
                "",
                f"proposal_path: {proposal_path}",
                f"state_id: {state_id}",
                f"promotion_profile: {promotion_profile}",
            ]
        )

    def build_last_result_evidence_bundle(self) -> str:
        if not self.last_workflow_result:
            raise ValueError("No workflow result is available yet")
        result = self.last_workflow_result
        return "\n".join(
            [
                f"status: {result.status}",
                f"runtime_status: {result.runtime_status}",
                f"promotion_profile: {result.promotion_profile}",
                f"working_state_dir: {result.working_state_dir.resolve()}",
                f"validation_path: {result.validation_path.resolve()}",
                f"validation_run_manifest_path: {result.validation_run_manifest_path.resolve()}",
                f"validation_runs_index_path: {result.validation_runs_index_path.resolve()}",
                f"transport_candidate_path: {result.transport_candidate_path.resolve()}",
                f"replay_state_path: {result.replay_state_path.resolve() if result.replay_state_path else None}",
                f"promoted_state_path: {result.promoted_state_path.resolve() if result.promoted_state_path else None}",
            ]
        )

    def output_folder_groups(self, next_state_id: str) -> dict[str, str]:
        state_id = (next_state_id or "").strip()
        if not state_id:
            state_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_web")

        groups: dict[str, str] = {
            "capture_finding_output_folder": str(self.paths.probe_root.resolve()),
            "local_files_root": str(self.paths.data_root.resolve()),
            "local_baseline_group": str(self.paths.baselines_root.resolve()),
            "next_working_state_subfolder": str((self.paths.working_states_root / state_id).resolve()),
            "next_validation_run_subfolder": str((self.paths.validation_runs_root / state_id).resolve()),
        }

        if self.last_workflow_result is not None:
            groups["last_working_state_subfolder"] = str(self.last_workflow_result.working_state_dir.resolve())
            groups["last_validation_run_subfolder"] = str(self.last_workflow_result.validation_run_dir.resolve())

        return groups

    @staticmethod
    def _read_path_value(document: dict[str, Any], path: str) -> tuple[bool, Any]:
        current: Any = document
        for part in path.split("."):
            if not isinstance(current, dict) or part not in current:
                return False, None
            current = current[part]
        return True, current

    def proposal_from_state_json_path(self, state_json_path: Path) -> str:
        state_json_path = state_json_path.resolve()
        state_doc = loads_no_duplicates(state_json_path.read_text(encoding="utf-8"))
        baseline_doc = loads_no_duplicates(self.baseline.state_path.read_text(encoding="utf-8"))
        if not isinstance(state_doc, dict):
            raise ValueError("Input state.json must be a JSON object")
        if not isinstance(baseline_doc, dict):
            raise ValueError("Baseline state.json must be a JSON object")

        overrides: dict[str, Any] = {}
        for path in PATH_SPECS.keys():
            has_state_value, state_value = self._read_path_value(state_doc, path)
            if not has_state_value:
                continue
            has_baseline_value, baseline_value = self._read_path_value(baseline_doc, path)
            if has_baseline_value and baseline_value == state_value:
                continue
            overrides[path] = state_value

        if COLOR_TRIPLET_PATHS & set(overrides.keys()):
            for path in COLOR_TRIPLET_PATHS:
                has_state_value, state_value = self._read_path_value(state_doc, path)
                if not has_state_value:
                    raise ValueError(f"State JSON is missing required triplet path: {path}")
                overrides[path] = state_value

        proposal_text = dumps_pretty(
            {
                "proposal_version": 1,
                "base_state": {
                    "id": self.baseline.baseline_id,
                    "sha256": self.baseline.manifest["state_sha256"],
                },
                "overrides": overrides,
            }
        )

        # Validate before returning so the UI fails clearly when the captured state is outside bounded proposal_v1.
        parse_proposal_v1(proposal_text, self.baseline.baseline_id, self.baseline.manifest["state_sha256"])
        return proposal_text


class Phase1App:
    def __init__(self, root: Any, controller: Phase1Controller) -> None:
        self.root = root
        self.controller = controller
        self.root.title("CUDA Fractal State Tool - Phase 1")
        from tkinter import ttk

        self._ttk = ttk
        self._build()

    def _build(self) -> None:
        ttk = self._ttk
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(3, weight=3)
        self.root.rowconfigure(4, weight=2)
        self.root.rowconfigure(5, weight=2)

        import tkinter as tk

        self.baseline_status = tk.StringVar(value=self.controller.baseline_status_text())
        ttk.Label(self.root, textvariable=self.baseline_status).grid(row=0, column=0, sticky="ew", padx=8, pady=8)

        controls_row = ttk.Frame(self.root)
        controls_row.grid(row=1, column=0, sticky="ew", padx=8)
        controls_row.columnconfigure(1, weight=1)
        controls_row.columnconfigure(3, weight=1)
        ttk.Label(controls_row, text="Promotion profile:").grid(row=0, column=0, sticky="w", padx=(0, 6), pady=2)
        self.promotion_profile = tk.StringVar(value="none")
        profile_options = self.controller.available_promotion_profiles()
        self.promotion_combo = ttk.Combobox(
            controls_row,
            textvariable=self.promotion_profile,
            values=profile_options,
            state="readonly",
        )
        self.promotion_combo.grid(row=0, column=1, sticky="ew", pady=2)
        if profile_options:
            self.promotion_combo.current(0)

        ttk.Label(controls_row, text="State id:").grid(row=0, column=2, sticky="e", padx=(12, 6), pady=2)
        self.state_id_var = tk.StringVar(value=datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_web"))
        self.state_id_entry = ttk.Entry(controls_row, textvariable=self.state_id_var)
        self.state_id_entry.grid(row=0, column=3, sticky="ew", pady=2)

        button_row = ttk.Frame(self.root)
        button_row.grid(row=2, column=0, sticky="ew", padx=8)
        for column in range(6):
            button_row.columnconfigure(column, weight=1)

        ttk.Button(button_row, text="Example: No-Op", command=self._load_noop).grid(row=0, column=0, sticky="ew", padx=2, pady=2)
        ttk.Button(button_row, text="Example: Color Shape", command=self._load_color).grid(row=0, column=1, sticky="ew", padx=2, pady=2)
        ttk.Button(button_row, text="Example: Grading", command=self._load_grading).grid(row=0, column=2, sticky="ew", padx=2, pady=2)
        ttk.Button(button_row, text="Example: Color Triplet", command=self._load_color_triplet).grid(row=0, column=3, sticky="ew", padx=2, pady=2)
        ttk.Button(button_row, text="Materialize", command=self._materialize).grid(row=0, column=4, sticky="ew", padx=2, pady=2)
        ttk.Button(button_row, text="Run Now (Replay + Proof)", command=self._replay).grid(row=0, column=5, sticky="ew", padx=2, pady=2)

        web_row = ttk.LabelFrame(self.root, text="Web Session Workflow")
        web_row.grid(row=4, column=0, sticky="nsew", padx=8, pady=(0, 8))
        web_row.columnconfigure(1, weight=1)
        web_row.columnconfigure(5, weight=1)

        ttk.Label(web_row, text="Proposal file:").grid(row=0, column=0, sticky="w", padx=(8, 6), pady=(6, 2))
        default_proposal_path = self.controller.paths.data_root / "proposal_web_session.json"
        self.proposal_file_var = tk.StringVar(value=str(default_proposal_path.resolve()))
        self.proposal_file_entry = ttk.Entry(web_row, textvariable=self.proposal_file_var)
        self.proposal_file_entry.grid(row=0, column=1, columnspan=5, sticky="ew", padx=(0, 8), pady=(6, 2))

        ttk.Label(web_row, text="Captured state.json path:").grid(row=2, column=0, sticky="w", padx=(8, 6), pady=(2, 6))
        default_captured_state = self.controller.paths.probe_root / "capture_one" / "state.json"
        self.capture_state_file_var = tk.StringVar(value=str(default_captured_state.resolve()))
        self.capture_state_file_entry = ttk.Entry(web_row, textvariable=self.capture_state_file_var)
        self.capture_state_file_entry.grid(row=2, column=1, columnspan=4, sticky="ew", padx=(0, 2), pady=(2, 6))
        ttk.Button(web_row, text="Build Proposal From state.json", command=self._build_proposal_from_capture_state).grid(row=2, column=5, sticky="ew", padx=(2, 8), pady=(2, 6))

        ttk.Button(web_row, text="Step 1: Save Proposal", command=self._save_proposal_file).grid(row=1, column=0, sticky="ew", padx=8, pady=4)
        ttk.Button(web_row, text="Step 2: Copy Commands", command=self._copy_command_bundle).grid(row=1, column=1, sticky="ew", padx=2, pady=4)
        ttk.Button(web_row, text="Step 2b: Copy Prompt", command=self._copy_prompt_template).grid(row=1, column=2, sticky="ew", padx=2, pady=4)
        ttk.Button(web_row, text="Step 3: Copy Evidence", command=self._copy_last_evidence).grid(row=1, column=3, sticky="ew", padx=2, pady=4)
        ttk.Button(web_row, text="Copy Intake Packet", command=self._copy_intake).grid(row=1, column=4, sticky="ew", padx=2, pady=4)
        ttk.Button(web_row, text="Launch New Viewer", command=self._launch).grid(row=1, column=5, sticky="ew", padx=(2, 8), pady=4)

        output_row = ttk.LabelFrame(self.root, text="Output Folder Map (Concept Bridge)")
        output_row.grid(row=5, column=0, sticky="nsew", padx=8, pady=(0, 8))
        output_row.columnconfigure(0, weight=1)
        output_row.rowconfigure(1, weight=1)

        output_button_row = ttk.Frame(output_row)
        output_button_row.grid(row=0, column=0, sticky="ew", padx=8, pady=(6, 4))
        for column in range(4):
            output_button_row.columnconfigure(column, weight=1)
        ttk.Button(output_button_row, text="Refresh Output Map", command=self._refresh_output_map).grid(row=0, column=0, sticky="ew", padx=2)
        ttk.Button(output_button_row, text="Copy Output Map", command=self._copy_output_map).grid(row=0, column=1, sticky="ew", padx=2)
        ttk.Button(output_button_row, text="Open Selected Path", command=self._open_selected_artifact_path).grid(row=0, column=2, sticky="ew", padx=2)
        ttk.Button(output_button_row, text="Copy Selected Path", command=self._copy_selected_artifact_path).grid(row=0, column=3, sticky="ew", padx=2)

        self.artifact_tree = ttk.Treeview(output_row, columns=("path",), show="tree headings", height=7)
        self.artifact_tree.heading("#0", text="Artifact")
        self.artifact_tree.heading("path", text="Path")
        self.artifact_tree.column("#0", width=260, anchor="w")
        self.artifact_tree.column("path", width=860, anchor="w")
        self.artifact_tree.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0, 4))
        self.artifact_tree.bind("<<TreeviewSelect>>", self._on_artifact_selected)

        self.artifact_detail_text = tk.Text(output_row, height=4, width=120)
        self.artifact_detail_text.grid(row=2, column=0, sticky="ew", padx=8, pady=(0, 8))
        self.artifact_detail_text.configure(state="disabled")
        self._artifact_descriptions: dict[str, str] = {}
        self._artifact_paths: dict[str, Path] = {}

        self.proposal_text = tk.Text(self.root, height=18, width=120)
        self.proposal_text.grid(row=3, column=0, sticky="nsew", padx=8, pady=8)

        self.status_text = tk.Text(self.root, height=14, width=120)
        self.status_text.grid(row=6, column=0, sticky="nsew", padx=8, pady=(0, 8))
        self.status_text.insert("1.0", self._quick_start_status_text())
        self.status_text.configure(state="disabled")

        self._load_noop()
        self._refresh_output_map()

    def _quick_start_status_text(self) -> str:
        return (
            "Quick Start (web-session copy/paste)\n"
            "1. Click 'Example: No-Op' (already loaded by default).\n"
            "2. Set Promotion profile and State id.\n"
            "3. In Web Session Workflow: click 'Step 1: Save Proposal'.\n"
            "4. Click 'Step 2: Copy Commands' and run them in terminal/web session.\n"
            "5. After run, click 'Step 3: Copy Evidence' and paste results back.\n\n"
        )

    def _set_status(self, text: str) -> None:
        self.status_text.configure(state="normal")
        self.status_text.delete("1.0", "end")
        self.status_text.insert("1.0", text)
        self.status_text.configure(state="disabled")

    def _append_status(self, text: str) -> None:
        self.status_text.configure(state="normal")
        self.status_text.insert("end", text)
        self.status_text.see("end")
        self.status_text.configure(state="disabled")

    def _render_output_map_text(self) -> str:
        groups = self.controller.output_folder_groups(self.state_id_var.get())
        lines = [
            "This maps the capture/probe output folder to per-run local subfolders:",
            "",
        ]
        for key, value in groups.items():
            lines.append(f"- {key}: {value}")
        return "\n".join(lines) + "\n"

    def _refresh_output_map(self) -> None:
        rendered = self._render_output_map_text()
        self._rebuild_artifact_tree()
        self._set_artifact_detail(
            "Select an artifact row above to see what it means. "
            "Use Build Proposal From state.json to convert a captured full engine state into a bounded proposal."
        )
        self._append_status(f"Output map refreshed.\n{rendered}\n")

    def _rebuild_artifact_tree(self) -> None:
        tree = self.artifact_tree
        for item in tree.get_children():
            tree.delete(item)
        self._artifact_descriptions.clear()
        self._artifact_paths.clear()

        capture_root = tree.insert("", "end", text="Capture Finding Output", values=("",), open=True)
        self._insert_artifact(
            capture_root,
            "capture_state",
            "Captured state.json (full engine snapshot)",
            Path(self.capture_state_file_var.get()),
            "This is a full engine state snapshot captured from runtime output. "
            "It is not a proposal; proposals are sparse overrides relative to frozen baseline.",
        )

        baseline_root = tree.insert("", "end", text="Baseline", values=("",), open=True)
        self._insert_artifact(
            baseline_root,
            "baseline_state",
            "Frozen baseline state.json",
            self.controller.baseline.state_path,
            "This is the frozen baseline full state that proposals are compared against.",
        )
        self._insert_artifact(
            baseline_root,
            "baseline_manifest",
            "Frozen baseline manifest.json",
            self.controller.paths.baseline_manifest_path,
            "Baseline identity and hash authority used for proposal validation.",
        )

        session_root = tree.insert("", "end", text="Session Inputs", values=("",), open=True)
        self._insert_artifact(
            session_root,
            "proposal_file",
            "Proposal file for web/session run",
            Path(self.proposal_file_var.get()),
            "This should contain sparse proposal_v1 JSON overrides only.",
        )

        next_root = tree.insert("", "end", text="Next Run Folders", values=("",), open=True)
        groups = self.controller.output_folder_groups(self.state_id_var.get())
        self._insert_artifact(
            next_root,
            "next_working",
            "Next working_state subfolder",
            Path(groups["next_working_state_subfolder"]),
            "Runtime workflow writes proposal/candidate/replay/validation artifacts for this state_id here.",
        )
        self._insert_artifact(
            next_root,
            "next_validation",
            "Next validation_run subfolder",
            Path(groups["next_validation_run_subfolder"]),
            "Validation run manifest for this state_id is recorded here.",
        )

        local_root = tree.insert("", "end", text="Local Files Root", values=("",), open=True)
        self._insert_artifact(
            local_root,
            "data_root",
            "Local files root (.local)",
            self.controller.paths.data_root,
            "All local subfolder groups live under this root.",
        )
        self._insert_artifact(
            local_root,
            "probe_root",
            "Capture/probe output group",
            self.controller.paths.probe_root,
            "Engine capture finding outputs are stored under runtime_probe.",
        )
        self._insert_artifact(
            local_root,
            "working_root",
            "Working states group",
            self.controller.paths.working_states_root,
            "Per-run candidate/replay/validation files grouped by state_id.",
        )
        self._insert_artifact(
            local_root,
            "validation_root",
            "Validation runs group",
            self.controller.paths.validation_runs_root,
            "Per-run manifest folders plus index.json.",
        )

        if self.controller.last_workflow_result is not None:
            last_root = tree.insert("", "end", text="Last Run", values=("",), open=True)
            result = self.controller.last_workflow_result
            self._insert_artifact(
                last_root,
                "last_working",
                "Last working_state subfolder",
                result.working_state_dir,
                "Most recent run working folder.",
            )
            self._insert_artifact(
                last_root,
                "last_validation",
                "Last validation_run subfolder",
                result.validation_run_dir,
                "Most recent run validation folder.",
            )

    def _insert_artifact(self, parent: str, artifact_id: str, label: str, path: Path, description: str) -> None:
        resolved = path.resolve()
        node_id = self.artifact_tree.insert(parent, "end", iid=artifact_id, text=label, values=(str(resolved),))
        self._artifact_paths[node_id] = resolved
        self._artifact_descriptions[node_id] = description

    def _set_artifact_detail(self, text: str) -> None:
        self.artifact_detail_text.configure(state="normal")
        self.artifact_detail_text.delete("1.0", "end")
        self.artifact_detail_text.insert("1.0", text + "\n")
        self.artifact_detail_text.configure(state="disabled")

    def _on_artifact_selected(self, event: Any) -> None:
        selection = self.artifact_tree.selection()
        if not selection:
            return
        selected = selection[0]
        description = self._artifact_descriptions.get(selected)
        path = self._artifact_paths.get(selected)
        if description is None or path is None:
            self._set_artifact_detail("Select a concrete artifact row to view details.")
            return
        self._set_artifact_detail(f"{description}\nPath: {path}")

    def _copy_output_map(self) -> None:
        rendered = self._render_output_map_text()
        self.root.clipboard_clear()
        self.root.clipboard_append(rendered)
        self._append_status("Copied output folder map to clipboard.\n\n")

    def _selected_artifact_path(self) -> Optional[Path]:
        selection = self.artifact_tree.selection()
        if not selection:
            return None
        return self._artifact_paths.get(selection[0])

    def _open_selected_artifact_path(self) -> None:
        selected_path = self._selected_artifact_path()
        if selected_path is None:
            self._set_status("Open selected path failed: no artifact row selected.\n")
            return
        if selected_path.exists() and selected_path.is_file():
            os.startfile(str(selected_path.parent))
            self._append_status(f"Opened parent folder for selected file: {selected_path.parent}\n\n")
            return
        selected_path.mkdir(parents=True, exist_ok=True)
        os.startfile(str(selected_path))
        self._append_status(f"Opened selected folder: {selected_path}\n\n")

    def _copy_selected_artifact_path(self) -> None:
        selected_path = self._selected_artifact_path()
        if selected_path is None:
            self._set_status("Copy selected path failed: no artifact row selected.\n")
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(str(selected_path))
        self._append_status(f"Copied selected artifact path: {selected_path}\n\n")

    def _open_data_root(self) -> None:
        data_root = self.controller.paths.data_root.resolve()
        data_root.mkdir(parents=True, exist_ok=True)
        os.startfile(str(data_root))
        self._append_status(f"Opened local files root: {data_root}\n\n")

    def _load_noop(self) -> None:
        self.proposal_text.delete("1.0", "end")
        self.proposal_text.insert("1.0", self.controller.example_noop_proposal())
        self._set_status("Loaded no-op proposal example.\n")

    def _load_color(self) -> None:
        self.proposal_text.delete("1.0", "end")
        self.proposal_text.insert("1.0", self.controller.example_color_proposal())
        self._set_status("Loaded color-shape proposal example.\n")

    def _load_grading(self) -> None:
        self.proposal_text.delete("1.0", "end")
        self.proposal_text.insert("1.0", self.controller.example_grading_proposal())
        self._set_status("Loaded color-grading proposal example.\n")

    def _load_color_triplet(self) -> None:
        self.proposal_text.delete("1.0", "end")
        self.proposal_text.insert("1.0", self.controller.example_color_triplet_proposal())
        self._set_status("Loaded color-triplet proposal example.\n")

    def _materialize(self) -> None:
        try:
            candidate = self.controller.materialize(self.proposal_text.get("1.0", "end"))
        except Exception as exc:
            self._set_status(f"Materialize failed: {exc}\n")
            return
        self._append_status(f"Materialized transport candidate:\n{candidate}\n\n")
        self._refresh_output_map()

    def _replay(self) -> None:
        selected_profile = self.promotion_profile.get() or "none"
        state_id = (self.state_id_var.get() or "").strip() or datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_phase1")
        try:
            result = execute_proposal_workflow(
                self.proposal_text.get("1.0", "end"),
                self.controller.paths.baseline_manifest_path,
                self.controller.paths.working_states_root,
                state_id,
                runtime_cmd_path=self.controller.runtime_cmd_path,
                promotion_profile=selected_profile,
            )
            self.controller.last_workflow_result = result
        except Exception as exc:
            self._set_status(f"Replay prove failed before runtime invocation: {exc}\n")
            return
        self._append_status(
            "\n".join(
                [
                    f"Status: {result.status}",
                    f"Runtime status: {result.runtime_status}",
                    f"Promotion profile: {result.promotion_profile}",
                    f"State id: {state_id}",
                    f"Working state: {result.working_state_dir}",
                    f"Transport candidate: {result.transport_candidate_path}",
                    f"Replay artifact: {result.replay_state_path}",
                    f"Promoted state: {result.promoted_state_path}",
                    f"Validation record: {result.validation_path}",
                ]
            )
            + "\n\n"
        )
        self.state_id_var.set(datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_web"))
        self._refresh_output_map()

    def _copy_intake(self) -> None:
        try:
            packet = self.controller.intake_packet()
        except Exception as exc:
            self._set_status(f"Intake packet generation failed: {exc}\n")
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(packet)
        self._append_status("Copied the Phase 1 intake packet to the clipboard.\n\n")

    def _save_proposal_file(self) -> None:
        proposal_path = Path(self.proposal_file_var.get())
        try:
            saved = self.controller.save_proposal_for_session(self.proposal_text.get("1.0", "end"), proposal_path)
        except Exception as exc:
            self._set_status(f"Save proposal failed: {exc}\n")
            return
        self.proposal_file_var.set(str(saved))
        self._append_status(f"Saved proposal file for web/session use:\n{saved}\n\n")
        self._refresh_output_map()

    def _build_proposal_from_capture_state(self) -> None:
        state_path = Path(self.capture_state_file_var.get())
        try:
            proposal_text = self.controller.proposal_from_state_json_path(state_path)
        except Exception as exc:
            self._set_status(
                "Build Proposal From state.json failed.\n"
                f"Reason: {exc}\n"
                "Tip: The captured state may include values outside bounded proposal_v1 contract.\n"
            )
            return
        self.proposal_text.delete("1.0", "end")
        self.proposal_text.insert("1.0", proposal_text)
        self._append_status(
            "Built proposal from captured state.json.\n"
            "Full state snapshot -> sparse proposal overrides relative to frozen baseline.\n\n"
        )

    def _copy_command_bundle(self) -> None:
        proposal_path = Path(self.proposal_file_var.get())
        state_id = (self.state_id_var.get() or "").strip() or datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_web")
        profile = self.promotion_profile.get() or "none"
        command_bundle = self.controller.build_web_session_command_bundle(proposal_path, state_id, profile)
        self.root.clipboard_clear()
        self.root.clipboard_append(command_bundle)
        self._append_status("Copied web-session CLI command bundle to the clipboard.\n\n")

    def _copy_prompt_template(self) -> None:
        proposal_path = Path(self.proposal_file_var.get())
        state_id = (self.state_id_var.get() or "").strip() or datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_web")
        profile = self.promotion_profile.get() or "none"
        prompt = self.controller.build_web_session_prompt_template(proposal_path, state_id, profile)
        self.root.clipboard_clear()
        self.root.clipboard_append(prompt)
        self._append_status("Copied web-session prompt template to the clipboard.\n\n")

    def _copy_last_evidence(self) -> None:
        try:
            evidence = self.controller.build_last_result_evidence_bundle()
        except Exception as exc:
            self._set_status(f"Evidence copy failed: {exc}\n")
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(evidence)
        self._append_status("Copied last workflow evidence bundle to the clipboard.\n\n")

    def _launch(self) -> None:
        from tkinter import messagebox

        viewer_procs = find_processes_by_name("fractal_ui.exe")
        if viewer_procs:
            proceed = messagebox.askyesno(
                "Launch New Viewer",
                "A fractal viewer is already running. This action will launch another instance.",
                parent=self.root,
            )
            if not proceed:
                self._append_status("Viewer launch cancelled.\n\n")
                return
        try:
            pid = self.controller.launch_new_viewer()
        except Exception as exc:
            self._set_status(f"Viewer launch failed: {exc}\n")
            return
        self._append_status(f"Launched a new viewer process from the replay-proven candidate. PID: {pid}\n\n")


def main() -> int:
    try:
        import tkinter as tk
    except ModuleNotFoundError as exc:
        raise RuntimeError("tkinter is required to run the Phase 1 desktop UI in this Python environment") from exc
    root = tk.Tk()
    controller = Phase1Controller(default_phase1_paths())
    Phase1App(root, controller)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
