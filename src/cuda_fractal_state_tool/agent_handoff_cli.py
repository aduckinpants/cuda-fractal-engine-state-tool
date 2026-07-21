from __future__ import annotations

import argparse
from pathlib import Path
from typing import Optional

from .baseline import BASELINE_ID, load_frozen_baseline
from .intake import build_intake_packet
from .runtime_surface import DEFAULT_RUNTIME_CMD
from .workspace_layout import WorkspaceLayout


def _default_baseline_manifest(repo_root: Optional[Path]) -> Path:
    layout = WorkspaceLayout.from_repo_root(repo_root)
    return layout.baseline_manifest_path(BASELINE_ID)


def _default_replay_state(repo_root: Optional[Path]) -> Path:
    layout = WorkspaceLayout.from_repo_root(repo_root)
    return layout.runtime_probe_root / "replay_one" / "state.json"


def build_agent_handoff_packet(
    baseline_manifest_path: Path,
    replay_state_path: Path,
    layout: WorkspaceLayout,
    runtime_cmd_path: Path,
) -> str:
    baseline = load_frozen_baseline(baseline_manifest_path)
    intake_packet = build_intake_packet(baseline_manifest_path, replay_state_path)

    return "\n".join(
        [
            "# Agent Handoff Packet",
            "",
            "## Mission",
            "Generate bounded proposal_v1 changes that replay-proof against runtime and remain fail-closed.",
            "",
            "## Core terms (must use these words)",
            "- state.json: full runtime state snapshot (engine-wide document).",
            "- proposal.json (proposal_v1): sparse overrides relative to frozen baseline.",
            "- transport_candidate.json: baseline + proposal materialization result.",
            "- replay artifact: runtime-captured state after replaying transport candidate.",
            "- proven state: candidate accepted by replay-proof workflow.",
            "",
            "## Authoritative loop",
            "1. Baseline + proposal -> transport candidate",
            "2. Runtime replay of candidate",
            "3. Compare candidate vs replay artifact",
            "4. Only replay-accepted outcomes are considered proven",
            "",
            "## Paths",
            f"- baseline_manifest: {baseline_manifest_path.resolve()}",
            f"- baseline_state: {baseline.state_path.resolve()}",
            f"- runtime_cmd: {runtime_cmd_path.resolve()}",
            f"- local_data_root: {layout.data_root.resolve()}",
            f"- working_states_root: {layout.working_states_root.resolve()}",
            f"- validation_runs_root: {layout.validation_runs_root.resolve()}",
            "",
            "## Required agent output format",
            "Return exactly these sections:",
            "1) intent: one short sentence",
            "2) proposal_json: valid proposal_v1 JSON only",
            "3) expected_outcome: expected status/runtime_status",
            "4) rationale: short explanation tied to allowed paths",
            "",
            "## Do not do",
            "- Do not return full state.json as proposal.",
            "- Do not invent unsupported paths.",
            "- Do not bypass replay-proof or classification gates.",
            "",
            "## Runtime-bounded intake context",
            intake_packet,
            "",
            "## Operator run commands",
            "$env:PYTHONPATH = \"src\"",
            (
                "py -3.14 -m cuda_fractal_state_tool.workflow_cli "
                f"--proposal <proposal_path> --baseline-manifest \"{baseline_manifest_path.resolve()}\" "
                f"--working-root \"{layout.working_states_root.resolve()}\" --state-id <state_id> --runtime-cmd \"{runtime_cmd_path.resolve()}\""
            ),
            "py -3.14 -m cuda_fractal_state_tool.validation_runs --latest",
        ]
    )


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build a canonical handoff packet for a fresh agent session",
        epilog="Use this instead of ad-hoc command snippets when onboarding a new agent.",
    )
    parser.add_argument("--repo-root", type=Path, default=None, help="Optional repository root for defaults")
    parser.add_argument("--baseline-manifest", type=Path, default=None, help="Baseline manifest path")
    parser.add_argument("--replay-state", type=Path, default=None, help="Replay state path for intake context")
    parser.add_argument("--runtime-cmd", type=Path, default=DEFAULT_RUNTIME_CMD, help="Runtime command path")
    parser.add_argument("--out", type=Path, default=None, help="Optional output .md path")
    args = parser.parse_args(argv)

    layout = WorkspaceLayout.from_repo_root(args.repo_root)
    baseline_manifest = args.baseline_manifest.resolve() if args.baseline_manifest else _default_baseline_manifest(args.repo_root)
    replay_state = args.replay_state.resolve() if args.replay_state else _default_replay_state(args.repo_root)

    packet = build_agent_handoff_packet(baseline_manifest, replay_state, layout, args.runtime_cmd)
    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(packet + "\n", encoding="utf-8")
    print(packet)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
