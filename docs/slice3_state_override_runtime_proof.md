# Slice 3 State Override Runtime Proof

> Historical checkpoint: the typed draft proof below established persistence
> and deterministic replay, but Slice 5 base/candidate pixel comparison proved
> the then-current draft-only load visually inert. The merged engine now exposes
> explicit authoritative lowering; see `slice5_color_pipeline_engine_integration.md`.

Status: direct-state materialization, replay, immutable evidence, review decisions,
and exact-candidate launch readiness are implemented and locally accepted.

## Runtime boundary

The proof path passes `merged_candidate.json` directly to the published runtime:

```text
fractal_ui.cmd
  --load-state-json <merged_candidate.json>
  --capture-diagnostic
  --diagnostics-out-dir <materialization>
```

It submits no actions and does not translate the state override into a second
command language. The engine-emitted `materialization/state.json` is the sole
launch candidate. That complete state is then loaded again without actions into
`replay/`.

Replay permits differences only in fields already classified as volatile
diagnostics. Any Color Pipeline, view, parameter, render, lens, or other stable
state difference fails proof. Decoded frame pixels must match exactly.

Requested values are compared with the engine-emitted state. Exact values are
classified as `survived`. Finite numeric changes within the narrow generic
serialization tolerance of `rel_tol=1e-6`, `abs_tol=1e-9` are reported as
`representation_normalization`; Python does not synthesize camera companions or
reproduce engine precision rules. Missing, reverted, or materially contradictory
values fail proof.

## Durable evidence

Each proof directory contains:

```text
binding.json
override.json
merged_candidate.json
materialization/
replay/
receipt.json
review-decision.json   after Accept or Revision Needed
launch.json            only after an accepted candidate is launched
```

`receipt.json` remains immutable and closes at:

```text
status: replay_proven
visual_review: pending
launch_ready: false
```

An accepted review decision binds the packet manifest, exact pasted override,
proof receipt, engine-emitted state, and candidate frame. Launch readiness then
rehashes those artifacts, the merged candidate, replay evidence, current Packet
V6 directory, and published runtime identity. A revision decision or any
tampering keeps launch disabled.

## Real published-runtime evidence

Runtime: `D:\salt-fractal\cuda_newton_fractal_clone\runtime\fractal_ui.cmd`

### Dynamics

- Packet: `d1e71ba9-a302-42dc-9bd2-1e4c1936679d`
- Proof: `f61bf178-16d7-41a2-be04-cfd9f29a0104`
- Override: `params.explaino_damping = 0.9`
- Engine emission: `0.8999999761581421`, explicitly recorded as representation normalization
- Materialization/replay decoded RGBA SHA-256: `0df9089b55a2ace265803df82f1cf1858a6d9dd6ba41ca48bde4e002cd53ba3a`
- Replay differences: only `stats.last_render_ms`

### Companion-paired camera edit

- Packet: `d1e71ba9-a302-42dc-9bd2-1e4c1936679d`
- Proof: `f326f6a5-5b6f-4315-a805-f2d60c3bcc84`
- Both `view.center_x` and `view.center_hp_x` survived; the ordinary float received explicit representation normalization
- Materialization/replay decoded RGBA SHA-256: `4be4988b5404717827fa1582f1e18dca017c2eedd574575c5112b9877659ec2e`

### Typed Color Pipeline edit

- Packet: `af3795c1-2878-45f0-8d57-571958b0a90e`
- Proof: `5ab4d3e8-d11f-4441-8206-4a3df089608b`
- Complete contract-ordered lanes array changed `grade.saturation` from `1` to `1.5`
- The requested pipeline value survived exactly
- Materialization/replay decoded RGBA SHA-256: `f2d1f9cdee65838cdec7a52d3fcbb99c6ba2b1fd9962efcbd4211c8f28267034`

All three receipts remain at visual review pending; none was accepted or launched
during this implementation slice.

## Validation and next boundary

At this Slice 3 checkpoint, focused proof, Packet V6, state-override, and
asynchronous ownership tests passed and the then-current complete Python 3.14
suite passed 152 tests. The later atomic UI cutover exposed the override editor,
candidate preview, explicit Accept/Revision controls, and launch gating while
deleting the active proposal orchestration surface and its obsolete tests.
