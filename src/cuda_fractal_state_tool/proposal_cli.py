from __future__ import annotations

import argparse
from pathlib import Path
from typing import Optional

from .baseline import BASELINE_ID, load_frozen_baseline
from .json_utils import dumps_pretty
from .proposal import (
    build_color_grading_example,
    build_color_shape_example,
    build_color_triplet_example,
    build_max_iter_example,
    build_noop_example,
    parse_proposal_v1,
)
from .workspace_layout import WorkspaceLayout


def _default_baseline_manifest(repo_root: Optional[Path]) -> Path:
    layout = WorkspaceLayout.from_repo_root(repo_root)
    return layout.baseline_manifest_path(BASELINE_ID)


def _build_triplet_text(
    baseline_id: str,
    baseline_sha256: str,
    signal: str,
    palette: str,
    grading: str,
) -> str:
    return dumps_pretty(
        {
            "proposal_version": 1,
            "base_state": {"id": baseline_id, "sha256": baseline_sha256},
            "overrides": {
                "params.color_signal": signal,
                "params.color_palette": palette,
                "params.color_grading": grading,
            },
        }
    )


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Generate proposal_v1 JSON examples from the frozen baseline")
    parser.add_argument(
        "--example",
        choices=["noop", "max-iter", "color-shape", "color-grading", "color-triplet"],
        default="noop",
    )
    parser.add_argument("--repo-root", type=Path, default=None, help="Optional repository root for default paths")
    parser.add_argument("--baseline-manifest", type=Path, default=None, help="Baseline manifest path")
    parser.add_argument("--out", type=Path, default=None, help="Output file path (default: stdout)")
    parser.add_argument("--max-iter", type=int, default=700, help="max_iter value for max-iter example")
    parser.add_argument("--signal", type=str, default="iteration_count", help="Signal id for color-triplet example")
    parser.add_argument("--palette", type=str, default="cyclic_escape", help="Palette id for color-triplet example")
    parser.add_argument("--grading", type=str, default="escape_default", help="Grading id for color-triplet example")
    args = parser.parse_args(argv)

    baseline_manifest = args.baseline_manifest.resolve() if args.baseline_manifest else _default_baseline_manifest(args.repo_root)
    baseline = load_frozen_baseline(baseline_manifest)
    baseline_id = baseline.baseline_id
    baseline_sha = str(baseline.manifest["state_sha256"])

    if args.example == "noop":
        proposal_text = build_noop_example(baseline_sha)
    elif args.example == "max-iter":
        proposal_text = dumps_pretty(
            {
                "proposal_version": 1,
                "base_state": {"id": baseline_id, "sha256": baseline_sha},
                "overrides": {"params.max_iter": args.max_iter},
            }
        )
    elif args.example == "color-shape":
        proposal_text = build_color_shape_example(baseline_sha)
    elif args.example == "color-grading":
        proposal_text = build_color_grading_example(baseline_sha)
    else:
        proposal_text = _build_triplet_text(baseline_id, baseline_sha, args.signal, args.palette, args.grading)

    # Validate before writing so generated files are guaranteed proposal_v1-compliant.
    parse_proposal_v1(proposal_text, baseline_id, baseline_sha)

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(proposal_text, encoding="utf-8")
    else:
        print(proposal_text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
