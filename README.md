# CUDA Fractal Engine State Tool

This repository implements one bounded exploration workflow without duplicating
CUDA-engine state authority:

```text
Exact Finding Bundle
+ Sparse Agent State Override
→ Deterministic Merged Candidate
→ Engine Materialization
→ Action-Free Replay
→ Candidate Preview
→ User Accept / Revise
→ Exact-Candidate Launch
```

The active application contains no proposal envelope, capability profile,
action-lowering path, repair packet, tuple allowlist, reduced Color Pipeline
catalog, or legacy workflow entry point. Historical proposal artifacts remain
untouched in existing workspaces and Git history, but are not active inputs.

## Launch

The supported interpreter is Python 3.14.x on Windows.

From the repository root:

```powershell
.\run_ui.cmd
```

Open the July 20 review fixture directly:

```powershell
.\run_ui.cmd `
  --capture-source "D:\salt-fractal\cuda_newton_fractal_clone\findings\manual_capture\2026-07-20\192515_961__explaino_all" `
  --workspace-root "D:\salt-fractal\cuda-fractal-engine-state-tool"
```

Equivalent module launch:

```powershell
$env:PYTHONPATH = (Resolve-Path .\src).Path
py -3.14 -m cuda_fractal_state_tool.app
```

## Visible workflow

The left side owns the captured finding, bounded base preview, readable context,
and immutable Agent Bundle V8. The primary handoff is deliberately simple:
`Open Agent Bundle Folder`, select every file in that directory, and drag all of
them into the web session. This includes `packet.md` and `manifest.json`.
`Copy Packet` remains a secondary convenience for pasting the behavioral index;
it does not transport the other authority files.

The ordinary `Capture or Agent Packet folder` input accepts either a source
capture or an already-published supported packet directory. Opening an existing packet binds
that exact packet and its durable finding read-only; it does not import the
packet as a capture or generate a replacement packet. This is the supported path
for pasting an override returned for a packet prepared before the UI session.
`Refresh Bundle` is a deliberate new-packet operation and must not be used when
testing a response bound to the existing packet.

The right side starts with an empty State Override editor. It accepts one sparse
state-shaped JSON object. Proof performs no action translation: it loads the
complete deterministic merged state through the published runtime, captures the
engine-emitted state and frame, and replays that emitted state without actions.

Successful replay stops at:

```text
OVERRIDE ACCEPTED
REPLAY PROVEN
VISUAL REVIEW PENDING
```

`Accept Candidate` or `Revision Needed` writes one immutable review decision.
Only acceptance plus fresh binding/hash checks reaches `LAUNCH READY`. Launch
loads the exact engine-emitted candidate, not the Python merged input.
`Open Full Candidate` opens a full-resolution PNG display derivative only after
its decoded RGBA identity has been verified against the authoritative engine
BMP. Both encoded hashes and the shared decoded identity remain in the proof
receipt.
`launch.json` proves creation of the exact-candidate launcher process; it does
not claim machine-verified viewer startup or rendering.

## Bounded automated Packet V8 route

`Automated Session...` opens the optional Packet V8 automation panel without
changing the manual two-column workflow. It runs the same packet, sparse
override, timeout, engine proof, proof-image, finding-import, and packet-build
services as the manual route. It does not click Tk controls and never records
human candidate acceptance or launches a viewer.

The POC is intentionally bounded:

- model `gpt-5.6` with high reasoning;
- at most two replay-proven rounds;
- two primary responses per round (combined authoring, then combined review/gate);
- at most six model responses including one correction turn per round;
- cumulative total/cached/uncached input and output token usage shown in the panel;
- one correction turn for malformed, unauthorized, or unintended `{}` output;
- exact `ROUND_ADVANCE` and `ROUND_REVISE` current-packet rebinding;
- explicit terminal controller disposition and durable result folder.

The Run button remains disabled until an exact Packet V8 is bound and an API
key is available. `Set OpenAI API Key...` stores a key in Windows Credential
Manager at target `openai/api_key`. An `OPENAI_API_KEY` environment value takes
precedence. Secret values are never written to app evidence, packets, receipts,
logs, or Git.

`Auto-promote replay-proven candidates` means automation may create a derived
finding from the exact engine state and proof-owned PNG, then refresh Packet V8
for the next round. That promotion records `human_acceptance: false`. Clearing
the option stops at `MANUAL_REVIEW_REQUIRED` immediately after replay proof.

Cancellation is session-local. It stops local progression, cancels owned
runtime work, never resends an ambiguous provider turn, and preserves the run
store for inspection. `events.ndjson` is append-only history;
`active-turn.json` is its atomic current-state projection. Domain receipts and
packet/state/frame artifacts remain the underlying authority.
The automation panel streams a compact field-allowlisted view of
`events.ndjson`; `Open Run Folder` is available as soon as durable run evidence
exists, even when a session stops before final qualification.
The bounded paid-run outcome and exact receipts are summarized in
[`docs/packet_v8_automated_route_live_qualification.md`](docs/packet_v8_automated_route_live_qualification.md).

The approved finding-enrichment and V9 campaign is active on
`codex/finding-enrichment-v9-sweep`. Deterministic common/model enrichment is
implemented before final V9 context shaping so model turns do not repeatedly
rediscover engine-declared mathematics. Cost remediation still precedes any
paid battery, and the bounded one-axis scalar bracket remains a later local
route over ordinary independently proven sparse overrides. The current
execution contract is
[`docs/finding_enrichment_v9_scalar_sweep_campaign.md`](docs/finding_enrichment_v9_scalar_sweep_campaign.md);
[`PICK_UP_HERE.md`](PICK_UP_HERE.md) records the exact restart point.

Common Packet V8 enrichment can also be exercised headlessly without invoking
the runtime model provider:

```powershell
$env:PYTHONPATH = (Resolve-Path .\src).Path
py -3.14 -m cuda_fractal_state_tool.finding_enrichment_cli `
  --workspace-root D:\salt-fractal\cuda-fractal-engine-state-tool `
  --packet-dir <exact-packet-v8-directory>
```

This route validates the immutable packet through the same loader used by the
workflow, writes exact common facts under the finding's `analyses` directory,
and reports model enrichment as unavailable until an exact engine receipt is
bound. Slice 1 evidence is recorded in
[`docs/finding_enrichment_slice1_evidence.md`](docs/finding_enrichment_slice1_evidence.md).

## Packet V8 and override authority

Packet V8 is the seven-file authority handoff when a frame exists:

```text
packet.md
manifest.json
state.json
state-authoring-authorities.md
color-pipeline-authority.md
finding-context.md
web-agent-frame.png
```

The image is omitted when the finding has no frame, leaving six files. The
manifest's `drag_all_attachments` list must name every physical file exactly
once.

`state.json` remains a byte-exact standalone merge and replay base. The three
Markdown files are deterministic V1 authority containers, not loose prose
copies. Each embedded artifact has a machine-marked record with its exact
logical filename, role, media type, UTF-8 encoding, byte length, SHA-256,
dynamic fence, and record identity. The shared parser extracts by declared byte
length and rejects missing, unknown, duplicate, malformed, truncated, or
tampered records. Headings and explanatory prose grant no authority.

The containers preserve the finding-specific authoring surface, deployed UI
schema, parameter surface, captured Color Pipeline topology and example,
deployed UI-Salt contract, review sidecar, viewport facts, finding manifest,
field notes, selected description, and complete descriptive catalog. Override
validation mechanically regenerates the authoring surface from those exact
embedded bytes.

The PNG is never upscaled and has a provisional 2048-pixel maximum long edge.
Its manifest provenance identifies the durable finding-relative source artifact
and source/derivative hashes, dimensions, and resampling. It is visual
discussion evidence, not full-resolution pixel authority. The original capture
stays in the durable finding workspace and is not duplicated into Packet V8.

Packet V6/schema-2 and Packet V7/schema-3 directories remain loadable as exact
historical bindings through their original filename-based authority path. They
are never silently regenerated against the current runtime.

Allowed override domains are:

- `params` paths present in the packet-derived authoring surface;
- companion-paired `view` edits;
- complete fixed-topology `color_pipeline_draft.lanes` replacement when the
  captured state already contains a complete draft.

The legacy flat Color panel is never advertised as independent state authority.
Color edits use the complete copied draft, exact UI-Salt function/parameter
definitions, and that contract's runtime compatibility rows. Engine
materialization remains final authority for a selected recipe.

Objects merge recursively, arrays replace completely, and unknown, absent,
read-only, duplicate, null, or non-finite values fail closed. `{}` copies the
exact base `state.json` bytes. A nonempty candidate uses the documented stable
UTF-8 serialization.

An empty override is an explicit base-replay operation, not an ambiguity,
refusal, or unavailable-capability signal. Its proof remains valid, but the UI
labels it `NO-OP OVERRIDE — EXACT BASE REPLAY`, reports no changed paths, and
requires `Acknowledge Base Replay` before launch readiness.

The captured draft owns Color Pipeline topology. The exact deployed UI-Salt
contract owns function and parameter validity. Python owns no parallel function,
parameter, default, range, enum, compatibility, or coercion catalog.

For every selector, color-only edits preserve the camera unless the user asks to
reframe. Non-color dynamics edits at meaningful zoom must explain one camera
intent in prose: `same_window_comparison`, `feature_tracking`, or
`transition_survey`. Exact fitting uses the attached engine viewport facts;
Python does not duplicate renderer camera mathematics or choose a subject.

Exploratory recommendations distinguish `state-authorable`, `analysis-only`,
and work requiring an unavailable capability. Before emitting an override, the
agent must map the selected experiment to at least one authorized leaf change
and identify the active rendered signal or exported diagnostic that can observe
its intended effect. Otherwise it chooses an observable alternative, labels an
explicitly requested negative control, or asks one clarification question.

An override response also carries a concise visible decision preflight before
its single fenced JSON block: the selected experiment, why each path changes,
the expected effect, observation channel, and uncertainty, the camera/viewport
conclusion, and a hostile self-review conclusion. Generic assent after multiple
experiments, a multi-value sweep, analysis-only work, or an unavailable
operation requires clarification. An unchanged high-zoom window is not silently
retained when the predicted subject leaves it unless the user explicitly
selects that disappearance as a fixed-window control.

The merged runtime exposes an explicit engine-owned loaded-draft application
operation. State-tool materialization invokes it only when the sparse override
contains `color_pipeline_draft`; ordinary state loading and action-free replay
remain non-applying. The engine-emitted complete state is still the sole launch
candidate. See `docs/slice5_color_pipeline_engine_integration.md` for the real
draft-to-render proof.

## Runtime compatibility modes

Packet/runtime identity drift is compatibility uncertainty, not automatic
incompatibility. One central policy controls the proof boundary:

- `development` (default): show and persist every field-level identity
  difference, then attempt materialization and replay with the current runtime;
- `strict`: show and persist the same warning, then stop before
  materialization.

The successful proof is always bound to the runtime actually used. Both modes
still fail closed if packet authority is corrupt, the override is invalid, the
runtime changes during one proof, or the runtime changes after proof and before
launch.

Set the policy for the UI with either:

```powershell
$env:CUDA_FRACTAL_STATE_TOOL_RUNTIME_COMPATIBILITY = "strict"
.\run_ui.cmd
```

or:

```powershell
.\run_ui.cmd --runtime-compatibility strict
```

The explicit command-line value wins over the environment. Unknown values fail
clearly. The UI header and proof receipt always show the active mode; drift adds
a prominent warning and exact difference list.

## Durable evidence

```text
findings/<finding-id>/source/                 exact mirrored capture artifacts
findings/<finding-id>/packets/<packet-id>/    immutable Agent Bundle V6, V7, or V8
findings/<finding-id>/proofs/<proof-id>/      binding, override, merged state,
                                               materialization, replay, receipt,
                                               review and launch receipts
```

Reset cancels session-owned work and clears active UI state. It does not delete
findings, bundles, proofs, caches, source captures, or unrelated viewer
processes.

## Command-line proof surfaces

Build an exact bundle:

```powershell
$env:PYTHONPATH = (Resolve-Path .\src).Path
py -3.14 -m cuda_fractal_state_tool.agent_bundle_cli build `
  --workspace-root D:\salt-fractal\cuda-fractal-engine-state-tool `
  --source <capture-directory> `
  --runtime-cmd D:\salt-fractal\cuda_newton_fractal_clone\runtime\fractal_ui.cmd
```

Validate and merge an override without running the engine:

```powershell
py -3.14 -m cuda_fractal_state_tool.state_override_cli `
  --packet-dir <agent-packet-directory> `
  --override <override.json> `
  --out .local\merged-candidate.json `
  --manifest-sha256 <manifest-sha256>
```

Run engine materialization and action-free replay proof:

```powershell
py -3.14 -m cuda_fractal_state_tool.state_override_proof_cli `
  --packet-dir <agent-packet-directory> `
  --override <override.json> `
  --manifest-sha256 <manifest-sha256> `
  --runtime-compatibility development
```

The proof CLI deliberately stops at visual review pending and never launches.
Packets with an unsafe authoring-surface version are rejected with a rebuild
instruction rather than retaining unsafe color-path authority.

## Validation

```powershell
$env:PYTHONPATH = (Resolve-Path .\src).Path
py -3.14 -m unittest discover -s tests
```

Raw local proof and screenshot outputs live under ignored `.local/`. Stable
slice conclusions are tracked in:

- `docs/agent_state_override_rescue.md`
- `docs/slice1_packet_v6_manual_gate.md`
- `docs/slice2_state_override_validation.md`
- `docs/slice3_state_override_runtime_proof.md`
- `docs/slice4_atomic_ui_cutover.md`
- `docs/slice5_real_acceptance_checkpoint.md`
- `docs/slice5_color_pipeline_engine_integration.md`
- `docs/post_rescue_hardening.md`
- `docs/catalog_viewport_continuity_integration.md`
- `docs/compact_web_handoff_hardening.md`
- `docs/packet_v7_compact_handoff_manual_gate.md`
- `docs/packet_v8_seven_file_compaction.md`

Earlier phase documents are historical evidence, not active product contracts.
