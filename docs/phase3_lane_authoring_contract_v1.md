# Phase 3 Lane Authoring Contract V1 — Superseded

Date: 2026-07-20

This file marks an archived design checkpoint. Its earlier proposal to discover
Color Pipeline lanes through `--describe-functions` and directly replace a
sparse `color_pipeline_draft` was disproved during the UI rescue.

Current authority is documented in:

- `docs/user_workflow_ui_rescue.md`
- `docs/slice1_color_authority_proof.md`
- `docs/slice2_interaction_model_review.md`

The deployed compiled UI-Salt contract supplies lane and function IDs. Bounded
first-row selections are lowered through repeated engine
`--color-pipeline-action` arguments, and the engine-emitted complete state is
then replayed without actions. The callable `--describe-functions` registry is
not a Color Pipeline authoring catalog.

`proposal_v1` remains unchanged. The exact finding packet declares
`finding-color-first-row-v1`; proof enforcement of its packet, base, runtime,
contract, and proposal-text binding belongs to Slice 3 after interaction-model
acceptance.

The full obsolete document remains recoverable from
`archive/vscode-phase3-ui` and ordinary Git history. It must not be used as an
implementation plan on the active branch.
