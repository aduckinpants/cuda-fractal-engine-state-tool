from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping, Optional

from .json_utils import DuplicateKeyError, loads_no_duplicates
from .baseline import BASELINE_ID


ValidationFunc = Callable[[Any], None]


@dataclass(frozen=True)
class ProposalPathSpec:
    path: str
    value_kind: str
    accepted_values: tuple[Any, ...] | None
    validator: ValidationFunc
    provenance: str
    accepted_values_source: str
    type_range_source: str
    pipeline_mapping_source: str
    runtime_or_source_provenance: str


def _validate_positive_int(value: Any) -> None:
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("params.max_iter must be an integer")
    if value < 1:
        raise ValueError("params.max_iter must be >= 1")


def _validate_color_shape(value: Any) -> None:
    if not isinstance(value, str):
        raise ValueError("params.color_shape must be a string enum id")
    if value not in {"identity", "repeat"}:
        raise ValueError("params.color_shape must be one of: identity, repeat")


def _validate_color_grading(value: Any) -> None:
    if not isinstance(value, str):
        raise ValueError("params.color_grading must be a string enum id")
    if value not in {
        "basin_default",
        "escape_default",
        "phase_default",
        "bands_default",
        "neutral_default",
        "tone_map_default",
        "glow_default",
        "balance_void_default",
    }:
        raise ValueError(
            "params.color_grading must be one of: "
            "basin_default, escape_default, phase_default, bands_default, "
            "neutral_default, tone_map_default, glow_default, balance_void_default"
        )


def _validate_color_signal(value: Any) -> None:
    if not isinstance(value, str):
        raise ValueError("params.color_signal must be a string enum id")
    if value not in {
        "root_index",
        "iteration_count",
        "smooth_escape",
        "phase_angle",
        "iteration_bands",
        "sdf_signed_distance",
        "sdf_inside_outside",
        "sdf_boundary_band",
        "sdf_normal_angle",
        "sdf_curvature",
        "lens_field_v2_distance",
        "root_proximity",
        "root_phase",
        "escape_magnitude",
        "orbit_stripe",
    }:
        raise ValueError("params.color_signal contains an unsupported value for proposal_v1")


def _validate_color_palette(value: Any) -> None:
    if not isinstance(value, str):
        raise ValueError("params.color_palette must be a string enum id")
    if value not in {
        "root_classic",
        "cyclic_escape",
        "joy",
        "phase_wheel",
        "banded_escape",
        "explaino_cmap",
    }:
        raise ValueError("params.color_palette contains an unsupported value for proposal_v1")


def _validate_color_pipeline_draft(value: Any) -> None:
    if not isinstance(value, dict):
        raise ValueError("color_pipeline_draft must be an object")
    actual_keys = set(value.keys())
    if actual_keys != {"lanes"}:
        raise ValueError("color_pipeline_draft must contain only: lanes")
    lanes = value.get("lanes")
    if not isinstance(lanes, list):
        raise ValueError("color_pipeline_draft.lanes must be an array")
    seen_lane_ids: set[str] = set()
    for index, lane in enumerate(lanes):
        if not isinstance(lane, dict):
            raise ValueError(f"color_pipeline_draft.lanes[{index}] must be an object")
        lane_keys = set(lane.keys())
        if lane_keys != {"lane_id", "function_id"}:
            raise ValueError(
                f"color_pipeline_draft.lanes[{index}] must contain only lane_id and function_id"
            )
        if not isinstance(lane["lane_id"], str) or not lane["lane_id"].strip():
            raise ValueError(f"color_pipeline_draft.lanes[{index}].lane_id must be a non-empty string")
        if not isinstance(lane["function_id"], str) or not lane["function_id"].strip():
            raise ValueError(f"color_pipeline_draft.lanes[{index}].function_id must be a non-empty string")
        lane_id = lane["lane_id"]
        if lane_id in seen_lane_ids:
            raise ValueError(f"color_pipeline_draft contains duplicate lane_id: {lane_id}")
        seen_lane_ids.add(lane_id)


COLOR_TRIPLET_PATHS = {
    "params.color_signal",
    "params.color_palette",
    "params.color_grading",
}


ALLOWED_COLOR_TRIPLETS = {
    ("root_index", "root_classic", "basin_default"),
    ("iteration_count", "cyclic_escape", "escape_default"),
    ("iteration_count", "cyclic_escape", "neutral_default"),
    ("iteration_count", "cyclic_escape", "tone_map_default"),
    ("iteration_count", "cyclic_escape", "glow_default"),
    ("iteration_count", "cyclic_escape", "balance_void_default"),
    ("smooth_escape", "cyclic_escape", "escape_default"),
    ("smooth_escape", "cyclic_escape", "neutral_default"),
    ("smooth_escape", "cyclic_escape", "tone_map_default"),
    ("smooth_escape", "cyclic_escape", "glow_default"),
    ("smooth_escape", "cyclic_escape", "balance_void_default"),
    ("root_index", "joy", "basin_default"),
    ("phase_angle", "phase_wheel", "phase_default"),
    ("phase_angle", "phase_wheel", "neutral_default"),
    ("phase_angle", "phase_wheel", "balance_void_default"),
    ("iteration_bands", "banded_escape", "bands_default"),
    ("iteration_bands", "banded_escape", "neutral_default"),
    ("iteration_bands", "banded_escape", "balance_void_default"),
    ("sdf_signed_distance", "cyclic_escape", "escape_default"),
    ("sdf_signed_distance", "cyclic_escape", "neutral_default"),
    ("sdf_signed_distance", "cyclic_escape", "tone_map_default"),
    ("sdf_signed_distance", "cyclic_escape", "glow_default"),
    ("sdf_signed_distance", "cyclic_escape", "balance_void_default"),
    ("sdf_inside_outside", "cyclic_escape", "escape_default"),
    ("sdf_inside_outside", "cyclic_escape", "neutral_default"),
    ("sdf_inside_outside", "cyclic_escape", "tone_map_default"),
    ("sdf_inside_outside", "cyclic_escape", "glow_default"),
    ("sdf_inside_outside", "cyclic_escape", "balance_void_default"),
    ("sdf_boundary_band", "cyclic_escape", "escape_default"),
    ("sdf_boundary_band", "cyclic_escape", "neutral_default"),
    ("sdf_boundary_band", "cyclic_escape", "tone_map_default"),
    ("sdf_boundary_band", "cyclic_escape", "glow_default"),
    ("sdf_boundary_band", "cyclic_escape", "balance_void_default"),
    ("sdf_normal_angle", "phase_wheel", "phase_default"),
    ("sdf_normal_angle", "phase_wheel", "neutral_default"),
    ("sdf_normal_angle", "phase_wheel", "balance_void_default"),
    ("sdf_curvature", "cyclic_escape", "escape_default"),
    ("sdf_curvature", "cyclic_escape", "neutral_default"),
    ("sdf_curvature", "cyclic_escape", "tone_map_default"),
    ("sdf_curvature", "cyclic_escape", "glow_default"),
    ("sdf_curvature", "cyclic_escape", "balance_void_default"),
    ("lens_field_v2_distance", "cyclic_escape", "escape_default"),
    ("lens_field_v2_distance", "cyclic_escape", "neutral_default"),
    ("lens_field_v2_distance", "cyclic_escape", "tone_map_default"),
    ("lens_field_v2_distance", "cyclic_escape", "glow_default"),
    ("lens_field_v2_distance", "cyclic_escape", "balance_void_default"),
    ("root_proximity", "explaino_cmap", "escape_default"),
    ("root_proximity", "explaino_cmap", "neutral_default"),
    ("root_proximity", "explaino_cmap", "tone_map_default"),
    ("root_proximity", "explaino_cmap", "glow_default"),
    ("root_proximity", "explaino_cmap", "balance_void_default"),
    ("root_proximity", "cyclic_escape", "escape_default"),
    ("root_proximity", "cyclic_escape", "neutral_default"),
    ("root_proximity", "cyclic_escape", "tone_map_default"),
    ("root_proximity", "cyclic_escape", "glow_default"),
    ("root_proximity", "cyclic_escape", "balance_void_default"),
    ("root_phase", "phase_wheel", "phase_default"),
    ("root_phase", "phase_wheel", "neutral_default"),
    ("root_phase", "phase_wheel", "balance_void_default"),
    ("escape_magnitude", "cyclic_escape", "escape_default"),
    ("escape_magnitude", "cyclic_escape", "neutral_default"),
    ("escape_magnitude", "cyclic_escape", "tone_map_default"),
    ("escape_magnitude", "cyclic_escape", "glow_default"),
    ("escape_magnitude", "cyclic_escape", "balance_void_default"),
    ("smooth_escape", "explaino_cmap", "escape_default"),
    ("smooth_escape", "explaino_cmap", "neutral_default"),
    ("smooth_escape", "explaino_cmap", "tone_map_default"),
    ("smooth_escape", "explaino_cmap", "glow_default"),
    ("smooth_escape", "explaino_cmap", "balance_void_default"),
    ("escape_magnitude", "explaino_cmap", "escape_default"),
    ("escape_magnitude", "explaino_cmap", "neutral_default"),
    ("escape_magnitude", "explaino_cmap", "tone_map_default"),
    ("escape_magnitude", "explaino_cmap", "glow_default"),
    ("escape_magnitude", "explaino_cmap", "balance_void_default"),
    ("orbit_stripe", "phase_wheel", "phase_default"),
    ("orbit_stripe", "phase_wheel", "neutral_default"),
    ("orbit_stripe", "phase_wheel", "balance_void_default"),
}


PATH_SPECS: dict[str, ProposalPathSpec] = {
    "color_pipeline_draft": ProposalPathSpec(
        path="color_pipeline_draft",
        value_kind="object",
        accepted_values=None,
        validator=_validate_color_pipeline_draft,
        provenance="replay artifact path",
        accepted_values_source="Runtime metadata catalog (describe-functions) plus replay-authoritative validation.",
        type_range_source="Runtime describe-functions metadata shape parsed by fail-closed lane catalog helpers.",
        pipeline_mapping_source="Direct full replacement of color_pipeline_draft payload.",
        runtime_or_source_provenance="runtime-authoritative: cached describe-functions metadata",
    ),
    "params.max_iter": ProposalPathSpec(
        path="params.max_iter",
        value_kind="int",
        accepted_values=None,
        validator=_validate_positive_int,
        provenance="baseline serialized path",
        accepted_values_source="Positive integer contract enforced by the tool; runtime loader requires positive max_iter.",
        type_range_source="Published runtime parameter-surface metadata and diagnostics_state_io positive-int requirement.",
        pipeline_mapping_source="Not applicable.",
        runtime_or_source_provenance="mixed: runtime parameter surface plus source loader logic",
    ),
    "params.color_shape": ProposalPathSpec(
        path="params.color_shape",
        value_kind="enum",
        accepted_values=("identity", "repeat"),
        validator=_validate_color_shape,
        provenance="baseline serialized path",
        accepted_values_source="Runtime parameter-surface metadata and source enum ids for ColorPipelineShape.",
        type_range_source="enum_id_utils.h ColorPipelineShape ids and describe-parameter-surface output.",
        pipeline_mapping_source="color_pipeline_core AdvancedColorShapeFunctionId maps identity -> identity and repeat -> repeat.",
        runtime_or_source_provenance="mixed: runtime parameter surface plus source color-pipeline mapping helpers",
    ),
    "params.color_signal": ProposalPathSpec(
        path="params.color_signal",
        value_kind="enum",
        accepted_values=(
            "root_index",
            "iteration_count",
            "smooth_escape",
            "phase_angle",
            "iteration_bands",
            "sdf_signed_distance",
            "sdf_inside_outside",
            "sdf_boundary_band",
            "sdf_normal_angle",
            "sdf_curvature",
            "lens_field_v2_distance",
            "root_proximity",
            "root_phase",
            "escape_magnitude",
            "orbit_stripe",
        ),
        validator=_validate_color_signal,
        provenance="baseline serialized path",
        accepted_values_source="Runtime replay-proven color triplet sweep plus source color signal ids.",
        type_range_source="diagnostics_capture enum ids and replay acceptance evidence.",
        pipeline_mapping_source="color triplet bridge; signal is admitted only with a replay-proven palette+grading pair.",
        runtime_or_source_provenance="mixed: published runtime replay proofs plus source enum ids",
    ),
    "params.color_palette": ProposalPathSpec(
        path="params.color_palette",
        value_kind="enum",
        accepted_values=(
            "root_classic",
            "cyclic_escape",
            "joy",
            "phase_wheel",
            "banded_escape",
            "explaino_cmap",
        ),
        validator=_validate_color_palette,
        provenance="baseline serialized path",
        accepted_values_source="Runtime replay-proven color triplet sweep plus source color palette ids.",
        type_range_source="diagnostics_capture enum ids and replay acceptance evidence.",
        pipeline_mapping_source="color triplet bridge; palette is admitted only with a replay-proven signal+grading pair.",
        runtime_or_source_provenance="mixed: published runtime replay proofs plus source enum ids",
    ),
    "params.color_grading": ProposalPathSpec(
        path="params.color_grading",
        value_kind="enum",
        accepted_values=(
            "basin_default",
            "escape_default",
            "phase_default",
            "bands_default",
            "neutral_default",
            "tone_map_default",
            "glow_default",
            "balance_void_default",
        ),
        validator=_validate_color_grading,
        provenance="baseline serialized path",
        accepted_values_source="Runtime parameter-surface metadata and source grading ids.",
        type_range_source="enum ids exposed by the source grading helpers and runtime parameter surface.",
        pipeline_mapping_source="color triplet bridge; grading is admitted only with a replay-proven signal+palette pair.",
        runtime_or_source_provenance="mixed: runtime parameter surface plus source color-pipeline grading helpers",
    ),
}


@dataclass(frozen=True)
class ProposalV1:
    proposal_version: int
    base_state_id: str
    base_state_sha256: str
    overrides: Mapping[str, Any]
    raw_text: str


def _ensure_exact_keys(obj: Mapping[str, Any], expected: set[str], label: str) -> None:
    actual = set(obj.keys())
    unknown = actual - expected
    missing = expected - actual
    if unknown:
        raise ValueError(f"{label} contains unknown fields: {sorted(unknown)}")
    if missing:
        raise ValueError(f"{label} is missing required fields: {sorted(missing)}")


def _has_overlap(path_a: str, path_b: str) -> bool:
    return path_a.startswith(path_b + ".") or path_b.startswith(path_a + ".")


def _reject_overlaps(paths: list[str]) -> None:
    for left_index, left_path in enumerate(paths):
        for right_path in paths[left_index + 1:]:
            if _has_overlap(left_path, right_path):
                raise ValueError(f"Proposal override paths overlap: {left_path} vs {right_path}")


def _validate_color_triplet_constraints(overrides: Mapping[str, Any]) -> None:
    triplet_in_overrides = COLOR_TRIPLET_PATHS & set(overrides.keys())
    if not triplet_in_overrides:
        return
    if triplet_in_overrides != COLOR_TRIPLET_PATHS:
        missing = sorted(COLOR_TRIPLET_PATHS - triplet_in_overrides)
        raise ValueError(
            "Color signal/palette/grading are coupled in proposal_v1. "
            f"Missing paths for a color triplet override: {missing}"
        )
    triplet = (
        overrides["params.color_signal"],
        overrides["params.color_palette"],
        overrides["params.color_grading"],
    )
    if triplet not in ALLOWED_COLOR_TRIPLETS:
        raise ValueError(
            "Color triplet is not in the replay-proven allowlist: "
            f"{triplet}"
        )


def parse_proposal_v1(text: str, expected_baseline_id: str, expected_baseline_sha256: str) -> ProposalV1:
    try:
        value = loads_no_duplicates(text)
    except DuplicateKeyError:
        raise
    if not isinstance(value, dict):
        raise ValueError("Proposal root must be a JSON object")
    _ensure_exact_keys(value, {"proposal_version", "base_state", "overrides"}, "Proposal root")

    if value["proposal_version"] != 1:
        raise ValueError("proposal_version must equal 1")
    if not isinstance(value["base_state"], dict):
        raise ValueError("base_state must be an object")
    base_state = value["base_state"]
    base_keys = set(base_state.keys())
    if base_keys == {"id", "sha256"}:
        base_state_id = base_state["id"]
    elif base_keys == {"finding_id", "sha256"}:
        base_state_id = base_state["finding_id"]
    else:
        raise ValueError("base_state must contain either {id, sha256} or {finding_id, sha256}")
    if base_state_id != expected_baseline_id:
        raise ValueError("Proposal base_state.id does not match the frozen baseline")
    if base_state["sha256"] != expected_baseline_sha256:
        raise ValueError("Proposal base_state.sha256 does not match the frozen baseline")
    overrides = value["overrides"]
    if not isinstance(overrides, dict):
        raise ValueError("overrides must be an object")

    override_paths = list(overrides.keys())
    _reject_overlaps(override_paths)
    for path, override_value in overrides.items():
        if path not in PATH_SPECS:
            raise ValueError(f"Unsupported override path: {path}")
        if override_value is None:
            raise ValueError(f"Override path {path} may not be null")
        if path != "color_pipeline_draft" and isinstance(override_value, (dict, list)):
            raise ValueError(f"Override path {path} does not support object or array replacement in proposal_v1")
        PATH_SPECS[path].validator(override_value)

    _validate_color_triplet_constraints(overrides)

    return ProposalV1(
        proposal_version=1,
        base_state_id=base_state_id,
        base_state_sha256=expected_baseline_sha256,
        overrides=overrides,
        raw_text=text,
    )


def build_noop_example(baseline_sha256: str) -> str:
    from .json_utils import dumps_pretty

    return dumps_pretty(
        {
            "proposal_version": 1,
            "base_state": {"id": BASELINE_ID, "sha256": baseline_sha256},
            "overrides": {},
        }
    )


def build_color_shape_example(baseline_sha256: str) -> str:
    from .json_utils import dumps_pretty

    return dumps_pretty(
        {
            "proposal_version": 1,
            "base_state": {"id": BASELINE_ID, "sha256": baseline_sha256},
            "overrides": {"params.color_shape": "repeat"},
        }
    )


def build_color_grading_example(baseline_sha256: str) -> str:
    from .json_utils import dumps_pretty

    return dumps_pretty(
        {
            "proposal_version": 1,
            "base_state": {"id": BASELINE_ID, "sha256": baseline_sha256},
            "overrides": {
                "params.color_signal": "root_index",
                "params.color_palette": "joy",
                "params.color_grading": "basin_default",
            },
        }
    )


def build_color_triplet_example(baseline_sha256: str) -> str:
    from .json_utils import dumps_pretty

    return dumps_pretty(
        {
            "proposal_version": 1,
            "base_state": {"id": BASELINE_ID, "sha256": baseline_sha256},
            "overrides": {
                "params.color_signal": "iteration_count",
                "params.color_palette": "cyclic_escape",
                "params.color_grading": "escape_default",
            },
        }
    )


def build_max_iter_example(baseline_sha256: str) -> str:
    from .json_utils import dumps_pretty

    return dumps_pretty(
        {
            "proposal_version": 1,
            "base_state": {"id": BASELINE_ID, "sha256": baseline_sha256},
            "overrides": {"params.max_iter": 700},
        }
    )
