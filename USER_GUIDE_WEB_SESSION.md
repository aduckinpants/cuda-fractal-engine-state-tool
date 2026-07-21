# Finding-to-Proof Desktop Workflow

## Current checkpoint

The rescue implementation is operational and waiting for final user UX
acceptance. Finding import, the web-agent packet, proposal validation, engine
materialization, action-free replay, repair, and exact-candidate launch gating
are connected through the single application surface.

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
5. Review and copy the automatically generated outgoing exploration packet.
   It contains the complete captured `state.json`; the frame itself is attached
   separately to the web conversation.

The right side is agent output moving inward:

1. Confirm the packet ID, exact packet SHA-256, and capability profile.
2. Paste proposal JSON into the initially empty editor.
3. Observe the session move to `PROPOSAL_DIRTY` and run `Validate & Replay Prove`.
4. For an actionable rejection, review the error and copy the exact bound repair
   packet back into the same web conversation.
5. For a proven result, review the receipt and launch the exact candidate in a
   new viewer. Launch rechecks the candidate, packet, proposal text, runtime,
   and UI-Salt contract first.

The session states are `EMPTY`, `FINDING_READY`, `PACKET_READY`,
`PROPOSAL_DIRTY`, `PROVING`, `PROVEN`, and `REJECTED`.

## Packet and preview safety

- Packet payloads contain the exact captured engine `state.json`, readable
  finding context, model guidance, compiled UI-Salt descriptions, validated
  examples, and closing finding/hash/runtime/contract bindings. They do not
  expose local filesystem paths.
- The exact copied packet is persisted with a manifest under the mirrored
  finding.
- The active capability profile is `finding-color-first-row-v1`; proof receipts
  bind the exact packet ID and payload, finding and base, runtime and contract,
  and exact pasted proposal text.
- Frame decoding runs in an owned subprocess. Tk loads only the cached bounded
  derivative.
- Internal preview defaults are 640×480 maximum, no upscaling, 50 million
  decoded pixels, 16,384 maximum dimension, and a 30-second timeout.
- Preview failure does not prevent summary or packet use. “Open Full Frame” is
  an explicit OS-viewer action.

## Reset

Reset invalidates the active session and cancels its owned work. It does not
delete findings, packets, previews, configuration, or source captures.

## Capability boundary

The current packet may author `params.max_iter`, the bounded legacy color
surface, and at most one row-0 function selection per shipped Color Pipeline
lane. Parameters inside Color Pipeline functions, additional rows, recipes,
arbitrary graph editing, existing-viewer control, and full-resolution in-app
navigation are intentionally unavailable.

## Acceptance boundary

Review the complete operational round trip: finding context, exact packet and
web discussion, incoming proposal, accepted proof, actionable repair, and
exact-candidate launch readiness. No further product mutation is authorized
after the clean morning-review checkpoint until that review.
