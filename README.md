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
and immutable Agent Bundle V6. `Copy Packet` copies only `packet.md`; `Open Agent
Bundle Folder` exposes the exact authority files and frame that must be attached
separately to a web session.

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

## Packet V6 and override authority

Each packet directory contains exact finding artifacts, the deployed UI schema,
the deployed UI-Salt function contract, full engine parameter and descriptive
catalog exports, and a finding-specific `state-override-authoring-surface.json`.
The latter is derived only from the neighboring copied bytes.

Allowed override domains are:

- `params` paths present in the packet-derived authoring surface;
- companion-paired `view` edits;
- complete fixed-topology `color_pipeline_draft.lanes` replacement when the
  captured state already contains a complete draft.

Objects merge recursively, arrays replace completely, and unknown, absent,
read-only, duplicate, null, or non-finite values fail closed. `{}` copies the
exact base `state.json` bytes. A nonempty candidate uses the documented stable
UTF-8 serialization.

The captured draft owns Color Pipeline topology. The exact deployed UI-Salt
contract owns function and parameter validity. Python owns no parallel function,
parameter, default, range, enum, compatibility, or coercion catalog.

Current runtime evidence shows that direct loading preserves an edited
`color_pipeline_draft` as pending editor state but does not lower it into the
live serialized color stacks that drive rendering. Proof receipts and the UI
now expose exact base/candidate pixel equality so this cannot masquerade as a
visual change. Typed draft authoring is not accepted until an
engine-authoritative lowering seam is approved; see
`docs/slice5_real_acceptance_checkpoint.md`.

## Durable evidence

```text
findings/<finding-id>/source/                 exact mirrored capture artifacts
findings/<finding-id>/packets/<packet-id>/    immutable Agent Bundle V6
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
  --packet-dir <packet-v6-directory> `
  --override <override.json> `
  --out .local\merged-candidate.json `
  --manifest-sha256 <manifest-sha256>
```

Run direct-state materialization and replay proof:

```powershell
py -3.14 -m cuda_fractal_state_tool.state_override_proof_cli `
  --packet-dir <packet-v6-directory> `
  --override <override.json> `
  --manifest-sha256 <manifest-sha256>
```

The proof CLI deliberately stops at visual review pending and never launches.

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

Earlier phase documents are historical evidence, not active product contracts.
