# Slice 4 Atomic UI Cutover

Status: historical Slice 4 implementation and local workflow acceptance
complete. The user visual-review boundary was subsequently passed through the
launch-and-recapture evidence in `slice5_color_pipeline_engine_integration.md`.

## Active product

The single desktop surface now presents:

```text
Exact Base State + Sparse Override
→ Engine Candidate
→ Visual Review
→ Accept / Revise
→ Exact-Candidate Launch
```

The accepted two-column hierarchy remains intact. The left side owns finding
intake, summary, bounded base preview, Agent Bundle V6 preview/copy, a dynamic
attachment checklist, and `Open Agent Bundle Folder`. The right side owns the
initially empty State Override editor, exact bundle binding, changed-path
summary, engine-emitted candidate preview, proof evidence, review controls, and
launch.

The visible proof milestones are:

```text
OVERRIDE ACCEPTED
REPLAY PROVEN
VISUAL REVIEW PENDING
USER ACCEPTED
REVISION NEEDED
LAUNCH READY
```

Accept and Revision remain disabled until the bounded candidate preview is
available or the user explicitly opens the full candidate frame. Replay success
alone never enables launch. Accept writes an immutable decision and performs a
fresh launch-readiness check. Revision preserves the proof and decision and
requires a new proof after the override changes.

## Legacy removal

The active package no longer contains proposal parsing or generation, tuple
allowlists, proposal/workflow CLIs, prompt-session harnesses, capability
profiles, action lowering, reduced Color Pipeline catalogs, repair packets,
proposal-oriented proof/controller states, or their tests. There is no hidden
legacy entry point or compatibility importer.

Existing proposal directories and receipts remain untouched as historical
workspace data. New finding imports do not create an active proposal directory.
Ordinary Git history and the archive tag retain the old implementation.

## Real UI workflow

Fixture:

```text
D:\salt-fractal\cuda_newton_fractal_clone\findings\manual_capture\2026-07-20\192515_961__explaino_all
```

Override:

```json
{
  "params": {
    "explaino_damping": 0.9
  }
}
```

The automated screenshot walkthrough used the real finding import, Packet V6
runtime exports, base preview worker, direct engine proof, replay, and candidate
preview worker. It stopped at visual review pending and did not fabricate user
acceptance or launch.

- Packet ID: `fe08c47c-bb48-417c-9030-0943b99281c6`
- Packet manifest SHA-256: `4527b8039cec7f3f69ed3df958556cb5f046d535495b67fd16baeb04c1254018`
- Proof ID: `ffc8975c-4ce1-419c-a3aa-29ba8976d6b1`
- Engine candidate SHA-256: `35edd928d19d82cd933508db4361e933479841902fbfcb426c70de32d4157377`
- Candidate frame SHA-256: `fec3d9dd4ac68a3c5cdb9b98c074fe402647da182e08ce4589719e50685b535f`
- Visual review: pending
- Launch ready: false

Raw screenshots and their manifest are under:

```text
.local/slice4_state_override_ui_final/
  01_empty.png
  02_bundle_ready_empty_override.png
  03_override_dirty.png
  04_visual_review_pending.png
  manifest.json
```

## Validation

The post-removal Python 3.14 suite contains only active or reusable authority
surfaces and passes 72 tests. The lower count is intentional removal of obsolete
proposal/workflow tests, not lost coverage of the current bundle, override,
proof, preview, process ownership, or workspace behavior.

The user manual-review boundary is:

```powershell
.\run_ui.cmd `
  --capture-source "D:\salt-fractal\cuda_newton_fractal_clone\findings\manual_capture\2026-07-20\192515_961__explaino_all" `
  --workspace-root "D:\salt-fractal\cuda-fractal-engine-state-tool"
```

Review the base/candidate hierarchy, exact bundle handoff, empty override state,
changed-path and normalization reporting, preview behavior, Accept/Revision
gating, and disabled launch. Do not accept or launch unless the candidate itself
is visually acceptable.
