# Slice 5B Color Pipeline Engine Integration

Status: implementation, automated real-runtime acceptance, manual candidate
review, exact launch, and launched-viewer recapture acceptance complete.

## Engine authority

- Merged engine commit: `337d66c8e2571f59b5757a27497ebe38717e30df`
- Published executable SHA-256: `e8d3449644ef004247162933a758957e75173aeea59c7c7c1dffca56cb4c9e3c`
- Engine operation: `--apply-loaded-color-pipeline-draft`

Ordinary state load remains draft-preserving and non-applying. The state tool
adds the explicit engine flag only to materialization when the sparse override
contains `color_pipeline_draft`. Replay loads the complete engine-emitted state
without the flag.

Python owns no Color Pipeline mapping. The captured draft fixes topology; the
exact copied UI-Salt contract validates functions, parameter types, ranges,
options, carriers, and ordering. The tool rejects lane/row count, identity,
label, ordering, enablement, and `next_row_id` changes.

## Real proof

- Source capture:
  `D:\salt-fractal\cuda_newton_fractal_clone\findings\manual_capture\2026-07-21\192324_921__explaino_multibrot_root_trap`
- Finding ID: `2e60174704a9e5920169fac2cb608bbb3d8ed3efd4b7813409376a365aa3669d`
- Packet ID: `65e2bf54-16db-410f-a977-c60095c98935`
- Packet manifest SHA-256: `18aa73bc2d0057b0203076355043e9f1e8d47d44c87ce1ea1cb4396ee7cf07fa`
- Proof ID: `64802ae6-e362-440a-a9e0-597d1b9c82f0`
- Change: `grade.saturation` from `1.6795599460601807` to `1.25`
- Requested value classification: `survived`
- Engine candidate SHA-256: `040d9947618f7fc6c01d2198bb75e3c245694d8177a4a5d143adccb1d17e38da`
- Base/candidate decoded pixels equal: `false`
- Mean absolute RGBA channel difference:
  `[0.120522848280578, 4.00369292509281, 54.5417834420184, 0.0]`
- Materialization/replay decoded pixels equal: `true`
- Visual review: `pending`
- Launch ready: `false`

This reproduces the rendered effect previously obtainable only by manually
aligning the draft and live serialized mirrors, but now the engine itself owns
that lowering. Replay success does not authorize launch; the candidate remains
at the normal visual-review gate.

## Desktop workflow proof

The real two-column application was exercised with the same capture and override:

- Packet ID: `7ed79dbc-c5f5-448b-b461-060e3001d0d9`
- Packet manifest SHA-256: `137f8ec26d6e37a0603011b24a56a4e522fbb4e97c7f10c879188ade30db048e`
- Proof ID: `d78b0f6f-00a9-4f27-81a0-f6e4ce2f0d88`
- Engine candidate SHA-256: `77131c600eae48f31508f19189cd0ae56841c5f3f655d88a53f626c3bf7aea1e`
- Candidate frame SHA-256: `db6279a6a6768da4171ac33e4a2c5af43f79c50b325175e327fa8513d562be83`
- Base/candidate decoded pixels equal: `false`
- Materialization/replay decoded pixels equal: `true`
- UI state: `VISUAL REVIEW PENDING`
- Launch ready: `false`

Raw screenshots and their manifest are under:

```text
.local/slice5b_color_pipeline_ui_review/
  01_empty.png
  02_bundle_ready_empty_override.png
  03_override_dirty.png
  04_visual_review_pending.png
  manifest.json
```

## Manual acceptance, launch, and recapture

The user inspected the candidate in the desktop workflow, accepted it, launched
the exact engine-emitted state, and captured the resulting viewer:

- Packet ID: `2455cfb0-caae-4b81-8bfb-29e4276c0b9c`
- Packet manifest SHA-256:
  `3b85e82307decd98eac907b51449322f862c938b85ddce9ec8b0b90c16588432`
- Proof ID: `7b0b850a-2f8d-466b-a989-6a3439bb4026`
- Review decision: `accepted`
- Engine launch candidate SHA-256:
  `937954debda158ccf93a329d4d6790493aa67a85c2e07de5adaa96b10fabd98d`
- Launched PID: `80272`
- Recapture:
  `D:\salt-fractal\cuda_newton_fractal_clone\findings\manual_capture\2026-07-21\230610_719__explaino_multibrot_root_trap`

The recaptured `state.json` is semantically equal to the launched candidate.
Its only difference is `stats.last_render_ms`, classified by the state
comparator as volatile diagnostic data. The candidate BMP and recaptured PNG
both decode to 4096 x 2559 RGBA pixels with SHA-256:

```text
9050608c76297d8c6d908d44f546a82405a5580303ab26a5af83bff64e360277
```

The different encoded image hashes therefore reflect BMP-versus-PNG encoding,
not a rendered difference. This completes the manual Color Pipeline path:

```text
fixed-topology draft override
-> engine-owned application
-> action-free replay
-> candidate preview
-> explicit user acceptance
-> exact-candidate launch
-> byte-identical decoded-pixel recapture
```

The Agent State Override rescue implementation and its planned acceptance work
are complete. The next boundary is review and merge authorization for the ready
pull request; no further product mutation is authorized by this plan.
