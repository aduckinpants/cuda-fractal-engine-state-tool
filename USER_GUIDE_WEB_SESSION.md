# Finding-to-Proof Desktop Workflow

## Current checkpoint

The fresh interaction shell is implemented through Slice 2 and is waiting for
interaction-model acceptance. Runtime proof, repair, and launch controls are
intentionally disabled until that review passes.

Launch from the repository root:

```powershell
.\run_ui.cmd
```

Equivalent module launch:

```powershell
$env:PYTHONPATH = "src"
py -3.14 -m cuda_fractal_state_tool.app
```

## Visible workflow

The left side is finding context moving outward:

1. Select a capture artifact or capture directory.
2. Confirm the separate durable workspace path.
3. Open the finding. The source remains read-only while required artifacts are
   mirrored into the workspace.
4. Inspect the finding summary and bounded frame derivative.
5. Build and copy the exact outgoing intake packet.

The right side is agent output moving inward:

1. Confirm the packet ID, exact packet SHA-256, and capability profile.
2. Paste proposal JSON into the initially empty editor.
3. Observe the session move to `PROPOSAL_DIRTY`.
4. At this checkpoint, proof, repair, and launch remain disabled and explain
   why.

The session states are `EMPTY`, `FINDING_READY`, `PACKET_READY`,
`PROPOSAL_DIRTY`, `PROVING`, `PROVEN`, and `REJECTED`.

## Packet and preview safety

- Packet payloads contain finding/hash/runtime/contract authority, not local
  filesystem paths.
- The exact copied packet is persisted with a manifest under the mirrored
  finding.
- The active capability profile is `finding-color-first-row-v1`; Slice 3 will
  enforce its exact packet/proposal proof binding.
- Frame decoding runs in an owned subprocess. Tk loads only the cached bounded
  derivative.
- Internal preview defaults are 640×480 maximum, no upscaling, 50 million
  decoded pixels, 16,384 maximum dimension, and a 30-second timeout.
- Preview failure does not prevent summary or packet use. “Open Full Frame” is
  an explicit OS-viewer action.

## Reset

Reset invalidates the active session and cancels its owned work. It does not
delete findings, packets, previews, configuration, or source captures.

## Acceptance boundary

Review the shell for layout, hierarchy, finding context, packet/proposal
separation, empty proposal behavior, preview behavior, state indicators,
control grouping, and disabled-state logic. After acceptance, this hierarchy is
frozen while Slice 3 wires operational proof into the existing panels.
