# Morning Operational Acceptance — 2026-07-21

## Review boundary

The rescue implementation is complete through the requested morning review
boundary. Final operational UX acceptance remains pending user review.

Launch from the repository root:

```powershell
.\run_ui.cmd
```

Equivalent module launch:

```powershell
$env:PYTHONPATH = "src"
py -3.14 -m cuda_fractal_state_tool.app
```

## Real finding workflow

The operational capture used finding
`22a35168b3a7c02b6a3b8eb271d9b9a7611813ff5e558336197ac931fbcd29ae`
with authoring base
`6d68b95d89445deef0ee1300150acb4c5283e4493212b1bb98b814e3ab72c7ef`.

The UI automatically generated a 58,200-byte agent exploration packet. It
contains the exact captured `state.json`, exact engine-captured
`fractal-state.json` review sidecar, and a 22-control `explaino_all` applicability
projection generated from the published runtime's parameter-surface descriptor
and deployed UI schema. Each projected control includes its current value when
resolvable plus exact binding, state key, label, help, type, defaults, ranges,
step, validation/animation status, and visibility metadata. Multibrot power,
Julia constants, and `explaino_mix` are absent because the engine-generated
`explaino_all` lane does not declare them. The packet also contains current
finding/render context, UI-Salt descriptions, three parser-accepted proposal
examples, and closing binding metadata. The incoming proposal editor was empty
at packet readiness.

Accepted proposal:

```text
shape row 0: identity -> repeat
```

The engine action was `select_function:shape:0:repeat`. Materialization and
action-free replay both exited successfully. Their encoded frame SHA-256 was
`0eda5672a61336c91ef66b72e95ae27cbad9f01d6564cc56fc862f91d8096ffc`;
decoded RGBA hashes also matched exactly at 4096×2560. Candidate/replay state
differed only at volatile `stats.last_render_ms`. Candidate SHA-256 was
`c256c95fcdb2428856f9057ccf70e37c23e48977d31456b2a44881af99eb24e7`,
and the immediate launch-readiness audit returned no errors.

An invalid `shape:0=definitely_missing` proposal was rejected before an engine
process started. Its repair packet retained the original packet ID/hash,
capability profile, exact proposal-text hash, rejection receipt ID, original
text, and actionable `function_unknown` error.

Raw screenshots, the manifest, and exact receipt handles are under
`.local/morning_operational_review/`. Principal states are:

- `01_empty.png`;
- `02_packet_ready_empty_proposal.png`;
- `03_proposal_dirty.png`;
- `04_proven_launch_ready.png`;
- `05_rejected_repair_ready.png`.

## Qualification ledger

- Focused parameter-authority and workflow suite: 27 tests passed in 9.705 seconds.
- Full local suite: 119 tests passed in 27.429 seconds.
- Exact packet rebinding and proposal whitespace edits invalidate readiness.
- Runtime, compiled-contract, persisted-packet, and candidate-state tampering
  are rejected before launch.
- Optional `fractal-state.json` is mirrored read-only, schema/hash checked, and
  embedded exactly; older findings without it remain supported with an explicit
  applicability warning.
- The raw engine parameter-surface descriptor is retained with the packet; its
  selected-fractal controls must resolve and agree with deployed UI-schema
  bindings or packet generation fails closed.
- Duplicate lane actions, unknown functions, and unsupported capability
  operations fail explicitly.
- Corrupt images and preview timeout fail only the preview operation; owned
  worker/process cleanup remains bounded to this application session.
- Reset, stale completion, and shutdown paths cancel or ignore session-owned
  work without touching durable findings, caches, or unrelated viewers.
- The final real workflow exercised `EMPTY`, `PACKET_READY`,
  `PROPOSAL_DIRTY`, `PROVEN`, and `REJECTED` through the running Tk
  application and closed it cleanly.

## Preview measurements

Measurements are preserved under `.local/morning_preview_measurements/`.
Defaults remained 640×480 maximum, no upscaling, 50 million decoded pixels,
16,384 maximum dimension, and a 30-second timeout.

| Source class | Encoded size | Decoded dimensions | Cold | Cache hit | Worker peak RSS |
|---|---:|---:|---:|---:|---:|
| small | 1,013,474 B | 4096×2560 | 0.378 s | 0.008 s | 155,140,096 B |
| 5 MB | 5,271,632 B | 4096×4096 | 0.499 s | 0.017 s | 232,370,176 B |
| >20 MB | 21,432,219 B | 4096×4096 | 0.604 s | 0.046 s | 232,783,872 B |

The measured policy needs no adjustment. Full decode remains isolated in the
owned worker process; Tk opens only the cached derivative.

## Declarative limitations

- The capability profile supports bounded scalar overrides and at most one
  first-row function selection per shipped Color Pipeline lane.
- Color Pipeline parameters, additional rows, recipes, and generalized graph
  editing are unavailable.
- The application launches a new proven viewer; it does not control an existing
  viewer.
- Full-resolution navigation remains an explicit OS `Open Full Frame` action.
- Repair packets are available only for actionable proposal/binding errors, not
  runtime infrastructure failure.
- The two exact state artifacts, generated parameter projection, and function catalog make the exploration
  packet materially larger than the rejected receipt packet; the measured real
  packet is about 58 KB.
