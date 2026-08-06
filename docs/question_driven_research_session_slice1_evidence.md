# Question-Driven Research Session — Slice 1 Evidence

## Outcome

Slice 1 establishes two shared foundations without adding a second domain
authority:

1. Packet V8 front-loads the exact captured active Color Pipeline as readable
   observation context.
2. Question runs extend the same durable event/projection owner already used by
   automated sessions.

## Packet V8 observation context

`derive_active_color_pipeline_context` validates the captured draft against the
exact copied UI-Salt contract and produces deterministic presentation data:

- deployed lane and row order;
- `ui_row_id` and enablement;
- exact function ID;
- contract-owned function display label when present;
- enabled-function chain text;
- complete lane/row topology for non-flattened inspection.

The compact chain appears before experiment guidance. Detailed rows remain in
the finding section. When a complete draft exists, the flat serialized color
tuple is explicitly labeled as a replay/compatibility mirror. Historical Packet
V8 directories remain readable; their context can be derived from exact packet
bytes without rewriting them.

The real epsilon packet produced:

```text
Phase Orbit [phase_orbit]
-> Identity [identity]
-> Phase Wheel [phase_wheel_palette]
-> Phase Finish [phase_finish]
```

This identifies the observation channel. It does not claim that every
configured value has a visible contribution.

## Shared durable run-store owner

`DurableRunStore` now owns:

- append-only `events.ndjson`;
- atomically replaced `active-turn.json` projection;
- projection recovery from the event history;
- Windows retry handling for access-denied and sharing-violation replacement;
- safe run-relative evidence paths;
- atomic ordinary evidence writes;
- write-once immutable evidence publication.

`AutomatedRunStore` preserves the existing `automated-runs` contract.
`ResearchRunStore` adds only its `question-runs` manifest and `attempts`
directory. It does not copy the write, retry, event, projection, or recovery
implementation.

Immutable research evidence is published through a same-volume hard-link from
a flushed temporary file. Existing targets fail with `FileExistsError` and are
never replaced.

## Focused and full validation

Focused tests:

```text
tests.test_agent_bundle
tests.test_automated_run_store
tests.test_research_run_store

31 passed
```

Coverage includes:

- contract labels and missing-label fallback;
- enabled and disabled rows;
- unavailable pipeline drafts;
- front-loaded packet ordering;
- exact immutable-packet context loading;
- automated-run compatibility;
- research manifest and directory ownership;
- append-only events and projection recovery;
- immutable artifact replacement rejection;
- WinError 5 and WinError 32 projection retry.

Complete Python 3.14 suite after the first Slice 1 implementation pass:

```text
237 passed
```

## Real Packet V8 workflow proof

Source capture:

```text
D:\salt-fractal\cuda_newton_fractal_clone\findings\manual_capture\2026-08-05\143014_930__explaino_transcendental
```

New immutable packet:

```text
D:\salt-fractal\cuda-fractal-engine-state-tool\findings\3209208bc5ccbc09a8f36fbc60b95d125f082761e0195b8c9aaee1af80f3c2cc\packets\2f37edbc-002e-4808-8313-80e9b60e834b
```

```text
manifest SHA-256: cece96fc5f5cd7a3509fa30fecd742f605aa6aca2eb0f0b7ede6a13554c09903
packet.md SHA-256: 481324ba237056b03ba0f80cb3d9fa34414ad4e99d9c54cb9ce30bd1b8f60092
runtime identity SHA-256: 567faf2008974cf386605550ae97f6f5de2c7e9fa0418e7a23a4015178b0d1bb
executable SHA-256: f000d50e439112758a1afbfc9980a12518866e76855b8b87641d3af02666c489
```

The freshly derived authoring surface still exposes `params.epsilon` as the
direct float sweep axis with captured value `9.999999974752427e-07` and UI range
`[1e-12, 0.01]`.

The published executable changed after the Slice 0 baseline was recorded. The
packet builder detected no within-construction drift and bound the new packet
coherently to the later runtime identity. No engine repository files were
inspected as substitute authority or modified by this campaign.

## Hostile review

- The pipeline summary is derived from copied contract/state bytes, not a
  parallel function table.
- Disabled rows remain visible in topology and absent from the active chain.
- Historical Packet V8 remains immutable and readable.
- The research store extends a neutral shared durability owner, not the
  automated controller's semantic protocol.
- State, proof, sweep, packet, promotion, pricing, and provider semantics remain
  outside the run store.
- No paid provider request was made.

No open Slice 1 defect blocks the planner/controller slice.
