# Descriptive Catalog And Viewport Continuity Integration

## Status

Active implementation plan on `codex/catalog-viewport-continuity-integration`.

## Exact engine handoff

- Merged engine commit: `09d5664b77116b716f83dd8df1085e88596498d0`
- Published runtime: `D:\salt-fractal\cuda_newton_fractal_clone\runtime`
- Published executable SHA-256: `ae329398693a5872faced0fa6f9cf57868788fc975b07ece5150954ac4face78`
- Deterministic descriptive catalog SHA-256: `8038ab867cd40dd4af6ca5b26aca11cd5e7c6b6a28816b00f7d4afdb4a4909fd`
- Catalog coverage: 51 live selectors, 51 reviewed descriptions, 0 unavailable descriptions.
- Viewport mapping identity: `cuda_fractal_renderer_pixel_center_v1`.

The engine repository was clean and synchronized at the merged commit, its exact
merged master was rebuilt and published, and its rearward review returned `ok`
before this repository was branched from clean `main` at
`faf226caf41b0cb38255bf78c1892ebdb0703d06`.

## Product contract

Packet V6 remains the product boundary. New bundles require manifest schema 2
and add one required authority:

```text
fractal-viewport-facts.json
```

The artifact is produced by the published engine from the exact staged
`state.json`. When a capture already contains the engine sidecar, the importer
preserves its exact bytes and packet construction requires byte identity with a
fresh export from the bound runtime. A missing capture sidecar is not an error:
the packet records that the facts were derived from the copied base state.

Python validates the V1 shape, selector identity, render identity, finiteness,
and neighboring-file hash. It does not reproduce the renderer mapping, compute
camera companions, choose a subject, predict feature motion, or auto-frame a
candidate.

Every proof binds the exact viewport-facts hash. Older Packet V6 manifests are
preserved on disk but must be rebuilt before new proof work.

## Packet interpretation rule

The packet applies one general rule to every selector:

- color-only changes preserve the exact camera unless the user asks to reframe;
- every non-color dynamics change at meaningful zoom states one camera intent in
  prose: `same_window_comparison`, `feature_tracking`, or `transition_survey`;
- small numerical changes never imply small visual changes;
- uniquely continued features may be recentered, while splits, merges,
  disappearances, or ambiguity require the branch set or transition neighborhood;
- exact framing uses the attached engine viewport facts and image aspect;
- when feature locations cannot be grounded, the agent states the limitation and
  uses an honest comparison view rather than fabricating precision.

Camera intent is explanatory prose, not a new JSON field or proposal envelope.
The sparse override remains a state-shaped object.

## Phases

- [x] Phase 0 — verify both repository boundaries, merged runtime identities,
  clean state-tool base, and baseline suite.
- [x] Phase 1 — add failing importer, bundle, manifest, proof-binding, and packet
  guidance tests.
- [x] Phase 2 — implement exact viewport sidecar preservation/runtime derivation,
  validation, coherent snapshot recheck, and manifest/proof binding.
- [x] Phase 3 — integrate concise all-selector camera-continuity guidance and
  update active documentation without changing the accepted UI hierarchy.
- [x] Phase 4 — run focused and full tests, generate real representative
  high-zoom bundles, perform hostile review, commit/push, and stop at the manual
  web-session review boundary.

## Hostile review findings

- The first V1 viewport validator required all engine fields but would have
  silently accepted undeclared root fields. A RED regression now proves the
  validator rejects undeclared V1 fields, preventing packet data from broadening
  the engine contract.
- The existing dynamic attachment checklist already surfaced the new required
  file; no UI hierarchy mutation was needed.
- Capture-sidecar bytes are preserved only when the exact bound runtime reproduces
  them for the copied state. Older captures without a sidecar use a clearly
  identified runtime-derived authority instead of a historical fallback.

## Boundaries

No engine mutation, formula duplication, Python camera mathematics, automatic
feature detection, automatic framing, proposal envelope, action DSL, family
switching, render/lens authoring, UI redesign, or returned-proposal expansion is
authorized.

## Acceptance

The implementation closes only when:

1. every new packet carries the exact engine viewport facts and hash;
2. source-sidecar and runtime-derived paths are both proven;
3. stale/malformed/mismatched authority fails closed;
4. proof receipts bind the viewport facts;
5. the UI exposes the new file through its existing dynamic attachment checklist;
6. real high-zoom bundles across representative selector domains are generated;
7. repository tests, workflow proof, diff checks, and hostile review pass;
8. the branch is clean, pushed, and ready for manual agent-session review.
