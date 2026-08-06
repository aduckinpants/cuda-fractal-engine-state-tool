from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Callable

from PIL import Image, ImageTk

from .research_protocol import ResearchBrief


def _lines(value: str) -> list[str]:
    return [line.strip() for line in value.splitlines() if line.strip()]


@dataclass(frozen=True)
class ResearchQuestionFormData:
    question: str
    attention_context: str
    user_hypotheses_text: str
    fixed_conditions_text: str
    useful_answer_details: str
    allow_params: bool
    allow_view: bool
    allow_color_pipeline: bool
    allowed_paths_text: str
    allow_scalar_sweep: bool
    maximum_experiment_rounds: int
    communication_profile: str
    hard_dollar_budget_text: str

    def to_brief(self) -> ResearchBrief:
        domains = []
        if self.allow_params:
            domains.append("params")
        if self.allow_view:
            domains.append("view")
        if self.allow_color_pipeline:
            domains.append("color_pipeline_draft")
        raw_paths = _lines(self.allowed_paths_text.replace(",", "\n"))
        allowed_paths = raw_paths or None
        try:
            budget = Decimal(self.hard_dollar_budget_text.strip())
        except (InvalidOperation, ValueError) as exc:
            raise ValueError("Research budget must be a finite non-negative decimal") from exc
        return ResearchBrief.from_dict(
            {
                "question": self.question,
                "attention_context": self.attention_context,
                "user_hypotheses": _lines(self.user_hypotheses_text),
                "experiment_permissions": {
                    "domains": domains,
                    "allowed_paths": allowed_paths,
                    "allow_scalar_sweep": self.allow_scalar_sweep,
                },
                "fixed_conditions": {"notes": _lines(self.fixed_conditions_text)},
                "useful_answer": {
                    "kind": "user_question_research_result",
                    "details": self.useful_answer_details,
                },
                "maximum_experiment_rounds": self.maximum_experiment_rounds,
                "communication_profile": self.communication_profile,
                "hard_dollar_budget": format(budget, "f"),
            }
        )


class ResearchQuestionDialog:
    """Thin Tk view; all research authority remains in service modules."""

    def __init__(
        self,
        parent,
        *,
        on_set_api_key: Callable[[], None],
        on_count: Callable[[], None],
        on_run: Callable[[], None],
        on_cancel: Callable[[], None],
        on_open_run: Callable[[], None],
        on_open_report: Callable[[], None],
        on_open_visual: Callable[[], None],
        on_brief_changed: Callable[[], None],
    ) -> None:
        import tkinter as tk
        from tkinter import ttk
        from tkinter.scrolledtext import ScrolledText

        self.tk = tk
        self.ttk = ttk
        self._visual_photo = None
        window = tk.Toplevel(parent)
        window.title("Packet V8 Research Question POC")
        window.geometry("1180x900")
        window.minsize(920, 720)
        window.transient(parent)
        window.protocol("WM_DELETE_WINDOW", window.withdraw)
        window.columnconfigure(0, weight=1)
        window.rowconfigure(2, weight=1)
        window.withdraw()
        self.window = window
        self.pipeline_var = tk.StringVar(value="Active Color Pipeline: unavailable")

        header = ttk.Frame(window, padding=(12, 12, 12, 8))
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(0, weight=1)
        ttk.Label(
            header,
            text="Question-Driven Fractal Research",
            font=("Segoe UI", 14, "bold"),
        ).grid(row=0, column=0, sticky="w")
        ttk.Label(
            header,
            text=(
                "One sealed brief, at most two local experiment attempts, fresh review and "
                "synthesis contexts, and no human acceptance or launch authority."
            ),
            wraplength=1040,
        ).grid(row=1, column=0, sticky="w", pady=(4, 0))
        pipeline_strip = ttk.LabelFrame(
            header, text="Captured active Color Pipeline — exact Packet V8 context", padding=(8, 5)
        )
        pipeline_strip.grid(row=2, column=0, sticky="ew", pady=(8, 0))
        ttk.Label(
            pipeline_strip,
            textvariable=self.pipeline_var,
            wraplength=1050,
            font=("Segoe UI", 10, "bold"),
        ).grid(row=0, column=0, sticky="w")

        form = ttk.LabelFrame(window, text="Five-question research brief", padding=10)
        form.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 8))
        form.columnconfigure(1, weight=1)
        form.columnconfigure(3, weight=1)

        self.question_text = ScrolledText(form, height=3, wrap="word")
        self.attention_text = ScrolledText(form, height=3, wrap="word")
        self.hypotheses_text = ScrolledText(form, height=3, wrap="word")
        self.fixed_text = ScrolledText(form, height=3, wrap="word")
        self.useful_answer_text = ScrolledText(form, height=3, wrap="word")
        fields = (
            ("1. What do you want to understand?", self.question_text, 0, 0),
            ("2. What should receive special attention?", self.attention_text, 0, 2),
            ("3. Current hypotheses or context (one per line)", self.hypotheses_text, 2, 0),
            ("4. What must remain fixed? (one per line)", self.fixed_text, 2, 2),
            ("5. What would a useful answer contain?", self.useful_answer_text, 4, 0),
        )
        for label, widget, row, column in fields:
            ttk.Label(form, text=label).grid(row=row, column=column, sticky="w", padx=(0, 6))
            span = 3 if widget is self.useful_answer_text else 1
            widget.grid(
                row=row + 1,
                column=column,
                columnspan=span,
                sticky="ew",
                padx=(0, 8) if column == 0 and span == 1 else 0,
                pady=(2, 7),
            )

        policy = ttk.Frame(form)
        policy.grid(row=6, column=0, columnspan=4, sticky="ew", pady=(3, 0))
        self.allow_params_var = tk.BooleanVar(value=True)
        self.allow_view_var = tk.BooleanVar(value=False)
        self.allow_color_var = tk.BooleanVar(value=True)
        self.allow_sweep_var = tk.BooleanVar(value=True)
        ttk.Label(policy, text="Executable domains:").grid(row=0, column=0, sticky="w")
        self.allow_params_check = ttk.Checkbutton(
            policy, text="Dynamics params", variable=self.allow_params_var
        )
        self.allow_view_check = ttk.Checkbutton(
            policy, text="View/camera", variable=self.allow_view_var
        )
        self.allow_color_check = ttk.Checkbutton(
            policy, text="Color Pipeline", variable=self.allow_color_var
        )
        self.allow_sweep_check = ttk.Checkbutton(
            policy, text="Scalar sweep", variable=self.allow_sweep_var
        )
        self.allow_params_check.grid(row=0, column=1)
        self.allow_view_check.grid(row=0, column=2)
        self.allow_color_check.grid(row=0, column=3)
        self.allow_sweep_check.grid(row=0, column=4)
        ttk.Label(policy, text="Exact allowed paths (optional):").grid(row=1, column=0, sticky="w", pady=(5, 0))
        self.allowed_paths_var = tk.StringVar(value="")
        self.allowed_paths_var_entry = ttk.Entry(
            policy, textvariable=self.allowed_paths_var, width=55
        )
        self.allowed_paths_var_entry.grid(
            row=1, column=1, columnspan=4, sticky="ew", pady=(5, 0)
        )
        policy.columnconfigure(4, weight=1)

        settings = ttk.Frame(form)
        settings.grid(row=7, column=0, columnspan=4, sticky="ew", pady=(7, 0))
        self.maximum_rounds_var = tk.StringVar(value="2")
        self.communication_profile_var = tk.StringVar(value="working_session")
        self.budget_var = tk.StringVar(value="0.00")
        self.model_var = tk.StringVar(value="gpt-5.6-luna")
        self.reasoning_var = tk.StringVar(value="high")
        ttk.Label(settings, text="Experiment attempts:").grid(row=0, column=0)
        self.rounds_combo = ttk.Combobox(
            settings, textvariable=self.maximum_rounds_var, values=("0", "1", "2"), state="readonly", width=4
        )
        self.rounds_combo.grid(row=0, column=1, padx=(4, 12))
        ttk.Label(settings, text="Report:").grid(row=0, column=2)
        self.profile_combo = ttk.Combobox(
            settings,
            textvariable=self.communication_profile_var,
            values=("working_session", "adult_beginner_carl_sagan"),
            state="readonly",
            width=27,
        )
        self.profile_combo.grid(row=0, column=3, padx=(4, 12))
        ttk.Label(settings, text="Model:").grid(row=0, column=4)
        self.model_combo = ttk.Combobox(
            settings,
            textvariable=self.model_var,
            values=("gpt-5.6-luna", "gpt-5.6-terra", "gpt-5.6"),
            state="readonly",
            width=17,
        )
        self.model_combo.grid(row=0, column=5, padx=(4, 12))
        ttk.Label(settings, text="Reasoning:").grid(row=0, column=6)
        self.reasoning_combo = ttk.Combobox(
            settings, textvariable=self.reasoning_var, values=("high", "medium"), state="readonly", width=8
        )
        self.reasoning_combo.grid(row=0, column=7, padx=(4, 12))
        ttk.Label(settings, text="Hard budget USD:").grid(row=0, column=8)
        self.budget_entry = ttk.Entry(settings, textvariable=self.budget_var, width=9)
        self.budget_entry.grid(row=0, column=9, padx=(4, 0))

        body = ttk.PanedWindow(window, orient="horizontal")
        body.grid(row=2, column=0, sticky="nsew", padx=12, pady=(0, 8))
        status_side = ttk.Frame(body, padding=8)
        result_side = ttk.Frame(body, padding=8)
        body.add(status_side, weight=1)
        body.add(result_side, weight=2)
        status_side.columnconfigure(0, weight=1)
        status_side.rowconfigure(4, weight=1)

        controls = ttk.Frame(status_side)
        controls.grid(row=0, column=0, sticky="ew")
        self.set_key_button = ttk.Button(controls, text="Set API Key…", command=on_set_api_key)
        self.set_key_button.grid(row=0, column=0, padx=(0, 4))
        self.count_button = ttk.Button(controls, text="Count & Review Budget", command=on_count)
        self.count_button.grid(row=0, column=1, padx=4)
        self.run_button = ttk.Button(controls, text="Run Research", command=on_run)
        self.run_button.grid(row=0, column=2, padx=4)
        self.cancel_button = ttk.Button(controls, text="Cancel", command=on_cancel)
        self.cancel_button.grid(row=0, column=3, padx=(4, 0))
        self.credential_var = tk.StringVar(value="Credential: not checked")
        self.state_var = tk.StringVar(value="State: idle")
        self.authority_var = tk.StringVar(value="Authority: no Packet V8")
        self.cost_var = tk.StringVar(value="Cost: count not run")
        self.gate_var = tk.StringVar(value="Gate: not started")
        for row, variable in enumerate(
            (self.credential_var, self.state_var, self.authority_var, self.cost_var, self.gate_var),
            start=1,
        ):
            ttk.Label(status_side, textvariable=variable, wraplength=360).grid(
                row=row, column=0, sticky="w", pady=(3, 0)
            )
        ttk.Label(status_side, text="Sanitized run events").grid(row=7, column=0, sticky="w", pady=(8, 2))
        self.event_text = ScrolledText(status_side, height=16, wrap="word", state="disabled", font=("Consolas", 9))
        self.event_text.grid(row=8, column=0, sticky="nsew")
        status_side.rowconfigure(8, weight=1)

        result_side.columnconfigure(0, weight=1)
        result_side.rowconfigure(0, weight=1)
        notebook = ttk.Notebook(result_side)
        notebook.grid(row=0, column=0, sticky="nsew")
        self.answer_text = ScrolledText(notebook, wrap="word", state="disabled")
        self.experiments_text = ScrolledText(notebook, wrap="word", state="disabled", font=("Consolas", 9))
        visual_frame = ttk.Frame(notebook, padding=8)
        visual_frame.columnconfigure(0, weight=1)
        visual_frame.rowconfigure(0, weight=1)
        self.visual_label = ttk.Label(visual_frame, text="No experiment visual yet", anchor="center")
        self.visual_label.grid(row=0, column=0, sticky="nsew")
        self.visual_path_var = tk.StringVar(value="")
        ttk.Label(visual_frame, textvariable=self.visual_path_var, wraplength=620).grid(row=1, column=0, sticky="w")
        self.open_visual_button = ttk.Button(visual_frame, text="Open Current Visual", command=on_open_visual)
        self.open_visual_button.grid(row=2, column=0, sticky="w", pady=(5, 0))
        self.files_text = ScrolledText(notebook, wrap="word", state="disabled", font=("Consolas", 9))
        notebook.add(self.answer_text, text="Answer")
        notebook.add(self.experiments_text, text="Experiments")
        notebook.add(visual_frame, text="Visuals")
        notebook.add(self.files_text, text="Files")

        footer = ttk.Frame(window, padding=(12, 0, 12, 12))
        footer.grid(row=3, column=0, sticky="ew")
        self.open_run_button = ttk.Button(footer, text="Open Run Folder", command=on_open_run)
        self.open_run_button.grid(row=0, column=0, padx=(0, 5))
        self.open_report_button = ttk.Button(footer, text="Open Working Report", command=on_open_report)
        self.open_report_button.grid(row=0, column=1, padx=5)
        self._text_inputs = (
            self.question_text,
            self.attention_text,
            self.hypotheses_text,
            self.fixed_text,
            self.useful_answer_text,
        )
        self._check_inputs = (
            self.allow_params_check,
            self.allow_view_check,
            self.allow_color_check,
            self.allow_sweep_check,
        )
        self._on_brief_changed = on_brief_changed
        for widget in self._text_inputs:
            widget.bind("<<Modified>>", self._brief_text_modified)
            widget.edit_modified(False)
        for variable in (
            self.allow_params_var,
            self.allow_view_var,
            self.allow_color_var,
            self.allow_sweep_var,
            self.allowed_paths_var,
            self.maximum_rounds_var,
            self.communication_profile_var,
            self.budget_var,
            self.model_var,
            self.reasoning_var,
        ):
            variable.trace_add("write", self._brief_variable_changed)

    def show(self) -> None:
        self.window.deiconify()
        self.window.lift()
        self.window.focus_set()

    def _brief_text_modified(self, event=None) -> None:
        widget = event.widget
        if widget.edit_modified():
            widget.edit_modified(False)
            self._on_brief_changed()

    def _brief_variable_changed(self, *_args) -> None:
        self._on_brief_changed()

    @staticmethod
    def _read(widget) -> str:
        return widget.get("1.0", "end-1c")

    def read_form(self) -> ResearchQuestionFormData:
        return ResearchQuestionFormData(
            question=self._read(self.question_text),
            attention_context=self._read(self.attention_text),
            user_hypotheses_text=self._read(self.hypotheses_text),
            fixed_conditions_text=self._read(self.fixed_text),
            useful_answer_details=self._read(self.useful_answer_text),
            allow_params=bool(self.allow_params_var.get()),
            allow_view=bool(self.allow_view_var.get()),
            allow_color_pipeline=bool(self.allow_color_var.get()),
            allowed_paths_text=self.allowed_paths_var.get(),
            allow_scalar_sweep=bool(self.allow_sweep_var.get()),
            maximum_experiment_rounds=int(self.maximum_rounds_var.get()),
            communication_profile=self.communication_profile_var.get(),
            hard_dollar_budget_text=self.budget_var.get(),
        )

    @staticmethod
    def _set_text(widget, text: str) -> None:
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        widget.insert("1.0", text)
        widget.configure(state="disabled")

    def set_answer(self, text: str) -> None:
        self._set_text(self.answer_text, text)

    def set_experiments(self, text: str) -> None:
        self._set_text(self.experiments_text, text)

    def set_files(self, text: str) -> None:
        self._set_text(self.files_text, text)

    def set_events(self, text: str) -> None:
        self._set_text(self.event_text, text)
        self.event_text.see("end")

    def set_visual(self, path: Path | None) -> None:
        self._visual_photo = None
        if path is None or not path.is_file():
            self.visual_label.configure(image="", text="No experiment visual yet")
            self.visual_path_var.set("")
            return
        with Image.open(path) as image:
            preview = image.convert("RGBA")
            preview.thumbnail((640, 460), Image.Resampling.LANCZOS)
            self._visual_photo = ImageTk.PhotoImage(preview)
        self.visual_label.configure(image=self._visual_photo, text="")
        self.visual_path_var.set(str(path))

    def configure_controls(
        self,
        *,
        ready: bool,
        credential_available: bool,
        busy: bool,
        run_authorized: bool,
        has_run: bool,
        has_report: bool,
        has_visual: bool,
    ) -> None:
        self.set_key_button.configure(state="disabled" if busy else "normal")
        enabled = ready and credential_available and not busy
        self.count_button.configure(state="normal" if enabled else "disabled")
        self.run_button.configure(
            state="normal" if enabled and run_authorized else "disabled"
        )
        self.cancel_button.configure(state="normal" if busy else "disabled")
        self.open_run_button.configure(state="normal" if has_run else "disabled")
        self.open_report_button.configure(state="normal" if has_report else "disabled")
        self.open_visual_button.configure(state="normal" if has_visual else "disabled")
        for widget in self._text_inputs:
            widget.configure(state="disabled" if busy else "normal")
        for widget in self._check_inputs:
            widget.configure(state="disabled" if busy else "normal")
        self.budget_entry.configure(state="disabled" if busy else "normal")
        self.allowed_paths_var_entry.configure(state="disabled" if busy else "normal")
        self.rounds_combo.configure(state="disabled" if busy else "readonly")
        self.profile_combo.configure(state="disabled" if busy else "readonly")
        self.model_combo.configure(state="disabled" if busy else "readonly")
        self.reasoning_combo.configure(state="disabled" if busy else "readonly")
