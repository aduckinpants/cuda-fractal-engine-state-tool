from __future__ import annotations

from pathlib import Path
from typing import Any

from .baseline import load_frozen_baseline
from .json_utils import loads_no_duplicates
from .proposal import ALLOWED_COLOR_TRIPLETS, PATH_SPECS


def _format_allowed_paths() -> str:
    lines: list[str] = []
    for path, spec in PATH_SPECS.items():
        lines.append(f"- {path}")
        lines.append(f"  type: {spec.value_kind}")
        if spec.accepted_values is not None:
            lines.append(f"  accepted values: {', '.join(str(value) for value in spec.accepted_values)}")
        lines.append(f"  accepted values source: {spec.accepted_values_source}")
        lines.append(f"  type/range source: {spec.type_range_source}")
        lines.append(f"  pipeline mapping source: {spec.pipeline_mapping_source}")
        lines.append(f"  provenance: {spec.runtime_or_source_provenance}")
    return "\n".join(lines)


def _format_allowed_color_triplets() -> str:
    lines = [
        "Color triplet coupling rule:",
        "- If any of params.color_signal / params.color_palette / params.color_grading is present, all three must be present.",
        "Allowed replay-proven triplets:",
    ]
    for signal, palette, grading in sorted(ALLOWED_COLOR_TRIPLETS):
        lines.append(f"- {signal} + {palette} + {grading}")
    return "\n".join(lines)


def build_intake_packet(baseline_manifest_path: Path, replay_state_path: Path) -> str:
    baseline = load_frozen_baseline(baseline_manifest_path)
    baseline_state = loads_no_duplicates(baseline.state_path.read_text(encoding="utf-8"))
    replay_state = loads_no_duplicates(replay_state_path.read_text(encoding="utf-8"))
    if not isinstance(baseline_state, dict) or not isinstance(replay_state, dict):
        raise ValueError("Baseline and replay state must both be JSON objects")
    runtime_identity = baseline.manifest["runtime_identity"]
    compatibility = "mismatched" if runtime_identity.get("runtime_schema_sha256") != runtime_identity.get("source_schema_sha256") else "matched"
    current_family = baseline_state.get("fractal_type", "unknown")
    params = baseline_state.get("params", {})
    replay_pipeline = replay_state.get("color_pipeline_draft", {})
    return "\n".join(
        [
            "1. Task",
            "Return a sparse proposal_v1 JSON document, not a full state.json.",
            "",
            "2. Runtime identity",
            f"launcher sha256: {runtime_identity.get('launcher_sha256')}",
            f"resolved executable sha256: {runtime_identity.get('resolved_executable_sha256')}",
            f"runtime schema sha256: {runtime_identity.get('runtime_schema_sha256')}",
            f"source schema sha256: {runtime_identity.get('source_schema_sha256')}",
            f"schema provenance status: {compatibility}",
            "",
            "3. Baseline identity",
            f"baseline id: {baseline.baseline_id}",
            f"baseline sha256: {baseline.manifest['state_sha256']}",
            f"current fractal family: {current_family}",
            "",
            "4. Current scalar color state",
            f"params.color_signal = {params.get('color_signal')}",
            f"params.color_shape = {params.get('color_shape')}",
            f"params.color_palette = {params.get('color_palette')}",
            f"params.color_grading = {params.get('color_grading')}",
            "",
            "5. Observed replay pipeline",
            f"color_pipeline_draft present: {'color_pipeline_draft' in replay_state}",
            f"replay pipeline lanes: {', '.join(lane.get('lane_id', '?') for lane in replay_pipeline.get('lanes', []))}",
            "",
            "6. Metadata authority chain expectations",
            "Treat the deployed compiled UI-Salt contract as Color Pipeline lane/function authority.",
            "Runtime describe outputs remain separate callable/parameter metadata and must not be interpreted as the lane catalog.",
            "Keep source schema as supplementary provenance only; do not override deployed runtime authority with source-only assumptions.",
            "",
            "7. Allowed override paths",
            _format_allowed_paths(),
            "",
            "8. Color triplet contract",
            _format_allowed_color_triplets(),
            "",
            "9. Exact finding packet requirement",
            "This baseline packet does not authorize color_pipeline_draft authoring.",
            "Use the desktop workflow's exact finding packet for finding-color-first-row-v1 authoring and packet-bound proof.",
            "",
            "10. Output contract",
            "Return JSON only.",
            "Preserve the exact base_state id and sha256.",
            "Do not add unlisted paths.",
            "",
            "11. Proposal envelope",
            "{",
            '  "proposal_version": 1,',
            '  "base_state": {',
            f'    "id": "{baseline.baseline_id}",',
            f'    "sha256": "{baseline.manifest["state_sha256"]}"',
            "  },",
            '  "overrides": {',
            '    "params.max_iter": 700',
            "  }",
            "}",
        ]
    )
