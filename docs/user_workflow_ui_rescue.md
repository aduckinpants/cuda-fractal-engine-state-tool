# User Workflow UI Rescue

## Authority checkpoint

- Rescue branch: `codex/user-workflow-ui-rescue`
- Archived failed surface: `archive/vscode-phase3-ui`
- Archive commit: `0f0a63babf8d65c43cd43cc19b3c78a4c78c21bc`
- Runtime authority remains the published engine launcher and its deployed
  UI-Salt contract. This repository must not duplicate engine lowering rules.
- The existing backup branch, safety stash, `.local` evidence, and durable
  workspace are recovery surfaces and must remain intact.

## Why the previous surface failed

The archived application combined user workflow, developer controls, proposal
generation, synchronous runtime work, and launch state in one widget/controller
class. It prefilled the proposal editor, exposed a debug notebook, and allowed
widget-local state to stand in for an explicit finding/packet/proof session.
Passing backend tests therefore did not establish that the visible workflow
matched the intended user interaction.

The archived Phase 3 lane path also consumed `--describe-functions` as though it
were the Color Pipeline authoring catalog. The deployed callable registry is not
the compiled UI-Salt function-library contract. Directly inserting a sparse
draft into `state.json` likewise bypasses the engine-owned action seam that
materializes a complete draft.

## Reusable and rejected implementation boundaries

Reusable behavior is limited to lower-level operations that remain valid when
called without the archived controller: finding import and workspace layout,
JSON/proposal parsing, process supervision, runtime capture/replay, evidence
indexing, and exact candidate launch.

The archived widget hierarchy, notebook, controller state, action grouping,
button enablement, proposal prefilling, and synchronous orchestration are
rejected. After the fresh application lands, they will not remain importable on
the active branch. Git history and the archive tag are the sole recovery path.

## Five-slice execution contract

1. Archive, audit, and record this rescue contract.
2. Prove one controlled non-default first-row Color Pipeline selection through
   deployed UI-Salt authority, engine materialization, and action-free replay.
3. Build the fresh asynchronous finding/packet shell and stop for
   interaction-model acceptance.
4. After that acceptance, bind proposals to exact packets and complete proof,
   repair, and exact-candidate launch without rearranging the accepted shell.
5. Run the complete operational acceptance workflow and stop for final user
   acceptance.

## Renewed execution boundary — 2026-07-21

The user replaced the Slice 2 pause with one continuous execution boundary
through a morning operational review. The two-column direction remains stable,
but interaction acceptance was not granted to the receipt-like packet. Work now
continues through packet repair, operational proof wiring, real workflow
evidence, screenshots, and clean checkpoints before the next user review.

`state.json` is the engine's established serialized state contract. The rescue
must carry the exact captured payload and use the engine's existing model load,
Color Pipeline action, serialization, and replay behavior. It must not create a
replacement schema, reduced surrogate state, or new normalization theory.

The outgoing artifact is an agent exploration packet, not a validation receipt.
Its primary content is the session purpose, finding/render context, exact
authoritative `state.json`, deployed UI-Salt semantics, and parser-validated
proposal guidance. Packet hashes and runtime provenance close the packet as
binding metadata; they do not replace its working context.

## Interaction contract

The only session states are `EMPTY`, `FINDING_READY`, `PACKET_READY`,
`PROPOSAL_DIRTY`, `PROVING`, `PROVEN`, and `REJECTED`.

The left side owns incoming finding context and the outgoing packet. The right
side owns the incoming proposal, its exact packet binding, proof status, repair
packet, and launch. The proposal editor starts empty. Slow work never mutates Tk
widgets outside the Tk thread, and results are accepted only when their exact
session identity is still current.

Slice 2 accepts and then freezes this hierarchy. Slice 4 is the separate final
operational UX acceptance.

## Bounded Color Pipeline capability

`proposal_v1` is unchanged. The exact intake-packet manifest declares
`finding-color-first-row-v1`. A proof receipt binds packet ID, exact packet
payload hash, capability profile, finding ID, authoring-base hash, runtime
identity, UI-Salt contract hash, and exact pasted proposal-text hash.

The profile admits at most one first-row function selection per deployed lane.
Parameters, row operations, generalized recipes, and arbitrary graph editing
remain outside the rescue. Configured draft, engine-emitted materialized state,
and action-free replay are preserved as separate evidence surfaces.

## Slice closure

Each slice runs focused tests, the full local suite, the real proof appropriate
to that slice, `git diff --check`, hostile self-review, and a clean commit. A
slice does not manufacture an unrelated workflow demonstration merely to make
the checkpoints look identical.
