# McMullen Color Authoring Brittleness

## Reported fixture

- Capture:
  `D:\salt-fractal\cuda_newton_fractal_clone\findings\manual_capture\2026-07-21\232809_573__mcmullen`
- Finding ID:
  `cc2cb68da25f649f2de674750b04c2b15f5e1416a806a0329b09743491525e63`
- Packet ID: `8efa52dd-2523-494f-8327-82ca4f9e6221`
- Rejected proof ID: `7813c620-4131-49d6-88f4-2a1a210d3986`
- Runtime executable SHA-256:
  `e8d3449644ef004247162933a758957e75173aeea59c7c7c1dffca56cb4c9e3c`

The downstream agent returned a sparse override changing the McMullen lambda
and flat color-panel fields. Every requested path appeared in the packet's
generated authoring surface, so this was not agent noncompliance with the
published packet.

## Classification

Controlled one-field proofs established:

- `params.mcmullen_lambda`: survives materialization and replay;
- `params.coloring_mode`: engine reverts to the stack-owned value;
- `params.exposure`: engine reverts to the grading-stack value;
- `params.color_saturation`: engine reverts to the grading-stack value;
- `params.color_contrast`: engine reverts to the grading-stack value;
- `params.color_grading: bands_default`: runtime exits 1 without state, frame,
  stdout, or stderr.

The copied UI schema correctly describes interactive controls, but direct
serialized-field presence does not make the legacy flat Color panel a safe
state-overlay authority when complete Color Pipeline state is present. Packet
V6 incorrectly promoted that whole panel into its authoring surface.

## Bounded correction

- The selected-family parameter surface remains dynamics applicability
  authority.
- The exact UI schema still supplies control identity and typing.
- The exact UI-Salt contract and copied draft remain Color Pipeline function,
  parameter, and topology authority.
- The tool excludes controls from the exact UI-schema panel `color` from flat
  state-overlay authoring.
- Color changes are pipeline-only when a complete draft is present; otherwise
  color authoring is unavailable for that packet.
- No flat-color path list or draft-to-runtime mapping is maintained in Python.
- Runtime failures preserve exit classification and artifact evidence rather
  than collapsing to `missing state/frame`.

Function validity and recipe compatibility are separate authorities inside the
same copied UI-Salt contract. Packet guidance now points function changes to
`composition_recipe_contract.compatibility` and states that function IDs are
not freely composable. Python still does not duplicate that table; the engine
remains final materialization authority.

## Corrected real workflow evidence

Packet V6 was regenerated from the reported capture after the correction:

- packet ID: `593c994f-e7a8-4824-8ae5-b5e06d32c257`;
- manifest SHA-256:
  `23a8ee3f300cad722933a6da6df5ee98eb4f327e2c4d7e81c4497e6892a91fb6`;
- authoring-surface version: `2`;
- advertised ordinary paths: McMullen dynamics, iteration limit, and paired
  camera controls only;
- color mode: `color_pipeline_draft_only`.

The following real proofs use the exact copied bundle authorities and the
published runtime whose executable SHA-256 is recorded above.

### Complex captured pipeline parameter edit

A complete topology-preserving override kept the captured Source, Shape, and
two Palette rows and changed the existing `grade_glow` exposure, saturation,
and contrast through contract-ordered typed parameters.

- proof ID: `f1a7163c-3fe2-4444-8a4f-41c2e8030cf0`;
- status: `replay_proven`;
- materialization and replay exit code: `0`;
- requested pipeline values: survived;
- action-free replay decoded pixels: exact match;
- base-to-candidate decoded pixels: changed;
- visual review: pending, as required.

This proves that the complex two-palette capture is not inherently unsupported.
Its color controls must travel through the complete typed draft rather than the
flat compatibility mirrors.

### Runtime-supported recipe boundary

Changing only the Source row to `banded_signal` while retaining the two
`explaino_cmap` Palette rows was schema-valid but runtime-incompatible. The
engine rejected it with its explicit supported-pair diagnostic. Changing the
Source, both Palette rows, and Grading row to the contract-declared banded
compatibility tuple materialized and replayed successfully. This confirms that
function membership alone does not establish composability.

### Requested McMullen lambda

The requested `mcmullen_lambda: 0.147` materialized and replayed successfully
with representation normalization to the engine float. It independently
produced the nearly black candidate, even without a Color Pipeline edit. The
result is therefore a visually degenerate but engine-valid dynamics change, not
a Color Pipeline transport failure. Mandatory candidate preview and explicit
user acceptance remain the correct product boundary; replay proof alone does
not make it launch-ready.

The engine repository and published runtime remain read-only for this fix.
