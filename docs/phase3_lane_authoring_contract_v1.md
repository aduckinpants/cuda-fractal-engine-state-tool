# Phase 3 Lane Authoring Contract V1 (Draft)

Date: 2026-07-20
Status: Draft, fail-closed

## Purpose

Define the bounded contract for introducing color-pipeline draft/lane authoring without bypassing runtime authority.

## Authority model

- Runtime replay behavior is authoritative.
- Runtime metadata outputs (`describe-parameter-surface`, `describe-functions`) are authoritative for lane/function discovery.
- Source schema and source enums remain supplementary provenance only.
- Unknown metadata shapes or unknown lane/function ids must fail with explicit errors.

## Allowed shape (proposal-side target, future P2 wiring)

`proposal_v1` may eventually carry one bounded draft payload path:

- `color_pipeline_draft`

The accepted payload shape will be a full deterministic replacement payload, not patch/merge semantics.

## Allowed operations (Phase 3 target)

- Replace the full `color_pipeline_draft` object with a complete candidate payload.
- Reference lane ids and function ids only if present in runtime-derived metadata catalog.
- Use unique `lane_id` entries in `color_pipeline_draft.lanes` (no duplicates).
- Keep scalar path contract unchanged (`params.max_iter`, `params.color_shape`, and coupled color triplet paths).
- Scalar/triplet overrides may coexist with `color_pipeline_draft`, but color triplet coupling remains mandatory whenever any triplet path is present.

## Disallowed operations

- Partial patch grammar (append, remove, merge, mutate-by-index) for lane rows.
- Implicit fallback from unknown lane/function ids to defaults.
- Metadata inference from source-only artifacts when runtime metadata is missing.
- Promotion rules that bypass replay classification gates.

## Error model

Errors must be deterministic and explainable:

- `runtime_metadata_unavailable`: required runtime metadata files missing.
- `runtime_metadata_shape_unsupported`: metadata JSON does not match any accepted parser shape.
- `lane_unknown`: lane id not present in runtime-derived catalog.
- `function_unknown`: function id not present in runtime-derived catalog for the lane.
- `proposal_path_unsupported`: proposal includes out-of-scope draft/lane paths before P2 acceptance.

## Provenance labels

Every lane/function validation decision should record:

- cache key
- cache directory
- describe-functions path
- parser shape selected (or unsupported)

## Immediate execution boundary after this document

- Implement metadata-backed lane/function catalog parser with strict shape checks.
- Add discovery CLI to inspect the parsed catalog.
- Add focused tests for supported/unsupported metadata shapes and unknown lane/function rejection.
