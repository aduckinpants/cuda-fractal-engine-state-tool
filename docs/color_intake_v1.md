# Color Intake V1 Coverage

This document records the bounded Phase 1 color override support and its provenance.

## Scope

Phase 1 does not expose arbitrary `color_pipeline_draft` authorship. The supported color override surface is intentionally limited to replay-proven scalar paths with an explicit coupling rule for color signal/palette/grading:

- `params.color_shape`
- `params.color_signal`
- `params.color_palette`
- `params.color_grading`

The non-color Phase 1 path is:

- `params.max_iter`

## Coverage Table

| serialized path | serialized-value source | accepted values source | type/range source | function-signature source | pipeline mapping source | runtime/source provenance | authorable in proposal_v1? | reason |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `params.color_shape` | baseline and replay-proven state JSON | runtime `--describe-parameter-surface` plus source enum ids in `ui_app/src/enum_id_utils.h` | `ColorPipelineShape` ids in `ui_app/src/enum_id_utils.h` and parameter-surface metadata | not needed for scalar replacement | direct mapping through `AdvancedColorShapeFunctionId` in `ui_app/src/color_pipeline_core.h` where `identity -> identity` and `repeat -> repeat` | mixed: runtime parameter-surface output plus source mapping helper | yes, bounded to `identity` and `repeat` | direct identifier bridge with no palette alias translation |
| `params.color_signal` | baseline and replay-proven state JSON | source enum ids plus replay-proven triplet matrix | enum ids from `ui_app/src/enum_id_utils.h` and `diagnostics_capture.cpp` | signal function mapping is family-dependent | admitted only when paired with replay-proven palette+grading | mixed: source ids plus published runtime replay evidence | yes, but only as part of a full color triplet | independent signal edits were runtime-rejected with baseline-coupled palette/grading |
| `params.color_palette` | baseline and replay-proven state JSON | source enum ids plus replay-proven triplet matrix | enum ids from `ui_app/src/enum_id_utils.h` and `diagnostics_capture.cpp` | palette function mapping includes aliases in `color_pipeline_core.h` | admitted only when paired with replay-proven signal+grading | mixed: source ids plus published runtime replay evidence | yes, but only as part of a full color triplet | coupling keeps Phase 1 fail-closed to known-good combinations |
| `params.color_grading` | baseline and replay-proven state JSON | source grading ids plus replay-proven triplet matrix | grading ids exposed in source helpers and diagnostics capture | `AdvancedColorGradingFunctionId` in `ui_app/src/color_pipeline_core.h` | admitted only when paired with replay-proven signal+palette | mixed: source ids plus published runtime replay evidence | yes, but only as part of a full color triplet | grading-only edits are now rejected by proposal validation |
| `color_pipeline_draft` | replay artifact only | replay artifact JSON | row/function metadata not surfaced by Phase 0 runtime outputs alone | requires function-library authority beyond the scalar surface | lane/function catalog is richer than the scalar contract | mixed and currently incomplete for V1 | no | arbitrary pipeline authorship is out of scope for Phase 1 |

## UI Salt Breadcrumb

Relevant generation breadcrumb observed in the authoritative source repository:

- `docs/ui_salt/color_pipeline_function_library.ui.salt`
- `docs/ui_salt/generated/color_pipeline_function_library.contract.v1.json`

Phase 0 established that the published runtime exposes `--describe-parameter-surface` and `--describe-functions`, but those outputs do not by themselves provide the full runtime color-pipeline lane/function catalog needed for general `color_pipeline_draft` authorship.

## Phase 1 Conclusion

Phase 1 supports useful bounded color overrides:

- `params.color_shape = "repeat"`
- replay-proven color triplets only:
	- `root_index + root_classic + basin_default`
	- `iteration_count + cyclic_escape + escape_default`
	- `smooth_escape + cyclic_escape + escape_default`
	- `smooth_escape + explaino_cmap + escape_default`
	- `root_index + joy + basin_default`
	- `phase_angle + phase_wheel + phase_default`
	- `iteration_bands + banded_escape + bands_default`
	- `sdf_signed_distance + cyclic_escape + escape_default`
	- `sdf_inside_outside + cyclic_escape + escape_default`
	- `sdf_boundary_band + cyclic_escape + escape_default`
	- `sdf_normal_angle + phase_wheel + phase_default`
	- `sdf_curvature + cyclic_escape + escape_default`
	- `lens_field_v2_distance + cyclic_escape + escape_default`
	- `root_proximity + explaino_cmap + escape_default`
	- `root_proximity + cyclic_escape + escape_default`
	- `root_phase + phase_wheel + phase_default`
	- `escape_magnitude + cyclic_escape + escape_default`
	- `escape_magnitude + explaino_cmap + escape_default`
	- `orbit_stripe + phase_wheel + phase_default`

These paths are accepted because the serialized identifiers and replay behavior are grounded by source-backed ids plus direct replay evidence from the published runtime, while maintaining strict fail-closed validation.
