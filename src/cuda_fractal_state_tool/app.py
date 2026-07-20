from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from .baseline import BASELINE_ID, freeze_phase0_baseline, load_frozen_baseline
from .intake import build_intake_packet
from .materializer import materialize_transport_candidate
from .process_utils import find_processes_by_name
from .proposal import build_color_grading_example, build_color_shape_example, build_noop_example, parse_proposal_v1
from .runtime_surface import DEFAULT_RUNTIME_CMD
from .state_workflow import WorkflowResult, execute_proposal_workflow, launch_proven_candidate
from .workspace_layout import WorkspaceLayout


@dataclass
class Phase1Paths:
    data_root: Path
    probe_root: Path
    baselines_root: Path
    baseline_manifest_path: Path
    working_states_root: Path


def default_phase1_paths(repo_root: Optional[Path] = None) -> Phase1Paths:
    layout = WorkspaceLayout.from_repo_root(repo_root)
    data_root = layout.data_root
    return Phase1Paths(
        data_root=data_root,
        probe_root=layout.runtime_probe_root,
        baselines_root=layout.baselines_root,
        baseline_manifest_path=layout.baseline_manifest_path(BASELINE_ID),
        working_states_root=layout.working_states_root,
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

    def replay_prove(self, proposal_text: str) -> WorkflowResult:
        state_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_phase1")
        self.last_workflow_result = execute_proposal_workflow(
            proposal_text,
            self.paths.baseline_manifest_path,
            self.paths.working_states_root,
            state_id,
            runtime_cmd_path=self.runtime_cmd_path,
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
        self.root.rowconfigure(2, weight=1)

        import tkinter as tk

        self.baseline_status = tk.StringVar(value=self.controller.baseline_status_text())
        ttk.Label(self.root, textvariable=self.baseline_status).grid(row=0, column=0, sticky="ew", padx=8, pady=8)

        button_row = ttk.Frame(self.root)
        button_row.grid(row=1, column=0, sticky="ew", padx=8)
        for column in range(7):
            button_row.columnconfigure(column, weight=1)

        ttk.Button(button_row, text="Load Example No-Op Proposal", command=self._load_noop).grid(row=0, column=0, sticky="ew", padx=2, pady=2)
        ttk.Button(button_row, text="Load Example Color Proposal", command=self._load_color).grid(row=0, column=1, sticky="ew", padx=2, pady=2)
        ttk.Button(button_row, text="Load Example Grading Proposal", command=self._load_grading).grid(row=0, column=2, sticky="ew", padx=2, pady=2)
        ttk.Button(button_row, text="Materialize", command=self._materialize).grid(row=0, column=3, sticky="ew", padx=2, pady=2)
        ttk.Button(button_row, text="Replay Prove", command=self._replay).grid(row=0, column=4, sticky="ew", padx=2, pady=2)
        ttk.Button(button_row, text="Copy Intake Packet", command=self._copy_intake).grid(row=0, column=5, sticky="ew", padx=2, pady=2)
        ttk.Button(button_row, text="Launch New Viewer", command=self._launch).grid(row=0, column=6, sticky="ew", padx=2, pady=2)

        self.proposal_text = tk.Text(self.root, height=18, width=120)
        self.proposal_text.grid(row=2, column=0, sticky="nsew", padx=8, pady=8)

        self.status_text = tk.Text(self.root, height=14, width=120)
        self.status_text.grid(row=3, column=0, sticky="nsew", padx=8, pady=(0, 8))
        self.status_text.insert("1.0", "Phase 1 UI ready. Load an example proposal or paste one manually.\n")
        self.status_text.configure(state="disabled")

        self._load_noop()

    def _set_status(self, text: str) -> None:
        self.status_text.configure(state="normal")
        self.status_text.delete("1.0", "end")
        self.status_text.insert("1.0", text)
        self.status_text.configure(state="disabled")

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

    def _materialize(self) -> None:
        try:
            candidate = self.controller.materialize(self.proposal_text.get("1.0", "end"))
        except Exception as exc:
            self._set_status(f"Materialize failed: {exc}\n")
            return
        self._set_status(f"Materialized transport candidate:\n{candidate}\n")

    def _replay(self) -> None:
        try:
            result = self.controller.replay_prove(self.proposal_text.get("1.0", "end"))
        except Exception as exc:
            self._set_status(f"Replay prove failed before runtime invocation: {exc}\n")
            return
        self._set_status(
            "\n".join(
                [
                    f"Status: {result.status}",
                    f"Working state: {result.working_state_dir}",
                    f"Transport candidate: {result.transport_candidate_path}",
                    f"Replay artifact: {result.replay_state_path}",
                    f"Validation record: {result.validation_path}",
                ]
            )
            + "\n"
        )

    def _copy_intake(self) -> None:
        try:
            packet = self.controller.intake_packet()
        except Exception as exc:
            self._set_status(f"Intake packet generation failed: {exc}\n")
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(packet)
        self._set_status("Copied the Phase 1 intake packet to the clipboard.\n")

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
                self._set_status("Viewer launch cancelled.\n")
                return
        try:
            pid = self.controller.launch_new_viewer()
        except Exception as exc:
            self._set_status(f"Viewer launch failed: {exc}\n")
            return
        self._set_status(f"Launched a new viewer process from the replay-proven candidate. PID: {pid}\n")


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
