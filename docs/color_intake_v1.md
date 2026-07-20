# Color Intake V1 Coverage

This document records the bounded Phase 1 color override support and its provenance.

## Scope

Phase 1 does not expose arbitrary `color_pipeline_draft` authorship. The supported color override surface is intentionally limited to one directly grounded scalar path:

- `params.color_shape`
- `params.color_grading`

The non-color Phase 1 path is:

- `params.max_iter`

## Coverage Table

| serialized path | serialized-value source | accepted values source | type/range source | function-signature source | pipeline mapping source | runtime/source provenance | authorable in proposal_v1? | reason |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `params.color_shape` | baseline and replay-proven state JSON | runtime `--describe-parameter-surface` plus source enum ids in `ui_app/src/enum_id_utils.h` | `ColorPipelineShape` ids in `ui_app/src/enum_id_utils.h` and parameter-surface metadata | not needed for scalar replacement | direct mapping through `AdvancedColorShapeFunctionId` in `ui_app/src/color_pipeline_core.h` where `identity -> identity` and `repeat -> repeat` | mixed: runtime parameter-surface output plus source mapping helper | yes, bounded to `identity` and `repeat` | direct identifier bridge with no palette alias translation |
| `params.color_palette` | baseline and replay-proven state JSON | serialized scalar and runtime state | enum ids available in source and runtime state | palette function library exists, but scalar `joy` maps to replay function `joy_root_palette` rather than a direct id match | alias bridge in `ui_app/src/color_pipeline_core.h` | mixed, with adaptation | no | Phase 1 excludes alias-translated palette authorship |
| `params.color_grading` | baseline and replay-proven state JSON | runtime parameter-surface metadata plus source grading ids | grading function ids exposed in source helpers | `AdvancedColorGradingFunctionId` in `ui_app/src/color_pipeline_core.h` | `basin_default -> basin_default` is direct | mixed: runtime parameter-surface output plus source grading helper | yes, bounded to `basin_default` | direct enough for V1 intake |
| `color_pipeline_draft` | replay artifact only | replay artifact JSON | row/function metadata not surfaced by Phase 0 runtime outputs alone | requires function-library authority beyond the scalar surface | lane/function catalog is richer than the scalar contract | mixed and currently incomplete for V1 | no | arbitrary pipeline authorship is out of scope for Phase 1 |

## UI Salt Breadcrumb

Relevant generation breadcrumb observed in the authoritative source repository:

- `docs/ui_salt/color_pipeline_function_library.ui.salt`
- `docs/ui_salt/generated/color_pipeline_function_library.contract.v1.json`

Phase 0 established that the published runtime exposes `--describe-parameter-surface` and `--describe-functions`, but those outputs do not by themselves provide the full runtime color-pipeline lane/function catalog needed for general `color_pipeline_draft` authorship.

## Phase 1 Conclusion

Phase 1 supports two useful color overrides:

- `params.color_shape = "repeat"`
- `params.color_grading = "basin_default"`

These paths are accepted because the serialized identifiers and replay-pipeline function identifiers are grounded by the source-backed mapping helpers, and because the baseline already carries the owner fields needed for a bounded proof.
