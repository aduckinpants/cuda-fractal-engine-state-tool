# Packet V8 Seven-File Authority Compaction

Date: 2026-08-01

## Objective

Reduce the web-session handoff to seven drag-all files without discarding the
exact authority already carried by Packet V7:

```text
packet.md
manifest.json
state.json
state-authoring-authorities.md
color-pipeline-authority.md
finding-context.md
web-agent-frame.png
```

When a finding has no captured frame, the packet contains the same six
non-image files. Packet V6 and V7 remain readable and immutable. Packet V8 is a
new transport representation, not a weaker authority model.

The campaign also replaces unconditional runtime-identity rejection with one
central compatibility policy:

- `development` is the default: warn, record the exact drift, and attempt the
  authoritative current-runtime proof;
- `strict`: warn and stop before materialization;
- either mode fails closed on corrupt packet authority, runtime changes during
  packet construction or a proof, post-proof runtime changes, tampering, or an
  invalid override.

## Non-Goals

- No CUDA engine or published-runtime mutation.
- No engine state-format, Color Pipeline, or parameter-authority changes.
- No override grammar expansion, family switching, or camera-math invention.
- No UI redesign beyond Packet V8 status, attachment, and compatibility-mode
  surfaces required by this campaign.
- No remote-agent automation, ZIP transport, portable full-frame archive,
  image-analysis toolchain, Reality Toolkit work, or finding-sweep framework.
- No claim that an old packet is guaranteed to remain operational forever.
- No historical runtime registry and no bundled runtime executable.

## Explicit User Asks

- [done] Preserve a clean pre-change baseline and implement Packet V8 from
  clean `main` at `a440f257a51dd958b273f034d3edb13f0fe01648` on
  `codex/packet-v8-seven-file-compaction`.
- [done] Reduce the normal handoff to approximately six or seven files plus no
  hidden attachment-picking workflow; the intended operation is drag all files
  in the packet directory, including `packet.md`.
- [done] Preserve every exact engine/finding authority byte currently needed
  for exploration, sparse-override validation, proof, and auditability.
- [done] Keep the full-resolution capture in the durable finding workspace and
  use a bounded PNG derivative for web-agent transport.
- [done] Treat runtime/build drift as a warning and attempted proof in normal
  development use, with a configurable strict mode that warns and stops.
- [done] Preserve Packet V6 and V7 readability without rewriting historical
  packet directories or silently regenerating their authority.
- [done] Run the bounded slices through local acceptance, inventory the newer
  captures, receive explicit user selection, prepare exactly those six Packet
  V8 fixtures and their manual gate, then stop for user-run web sessions.

## Locked Public Contract

### Physical Packet Files

Packet V8 uses `packet_version: 8`, `bundle_manifest_version: 4`, and
`authority_container_version: 1`.

`packet.md` is the concise behavioral contract and navigation surface.
`manifest.json` records all physical files, embedded artifacts, identities,
hashes, sizes, the drag-all attachment list, source-image provenance, and
runtime policy facts. The manifest does not hash itself; the UI session and
proof receipt retain its exact SHA-256.

`state.json` remains a byte-exact standalone authoring base because it is the
merge and engine-load authority.

`web-agent-frame.png` is a bounded PNG derivative. The original captured frame
is not copied into Packet V8. Its finding-relative identity, media type, byte
size, dimensions, SHA-256, and derivative relationship are recorded without a
machine-local absolute path.

### Authority Containers

The three Markdown containers are deterministic byte-preserving envelopes.
Their prose and indexes are navigation only; authority exists solely in
machine-marked embedded-artifact records.

Every embedded artifact record declares:

- exact logical filename;
- authority role;
- media type;
- UTF-8 requirement;
- exact byte length;
- SHA-256;
- a collision-resistant dynamic fence;
- unambiguous begin and end markers.

The shared encoder/parser must round-trip exact embedded bytes and reject
duplicate names, missing or unknown records, malformed markers, truncated or
extra payload bytes, ambiguous fences, invalid UTF-8, length mismatch, and hash
mismatch. Markdown headings and explanatory prose never grant authority.

Container allocation is fixed:

1. `state-authoring-authorities.md`
   - finding-specific state-override authoring surface first;
   - exact deployed fractal binding UI schema;
   - exact selected-fractal parameter surface.
2. `color-pipeline-authority.md`
   - captured topology and finding-specific structural edit example first;
   - exact deployed UI-Salt Color Pipeline function-library contract.
3. `finding-context.md`
   - selected engine-owned fractal description first;
   - exact `fractal-state.json` when present;
   - viewport facts;
   - capture manifest;
   - field notes;
   - complete exact descriptive-catalog export as appendix;
   - explicit notices for absent optional artifacts.

Generated summaries may repeat values for navigation but are not alternate
authorities.

### Runtime Compatibility Policy

The central setting is named `runtime_compatibility_mode` and accepts exactly:

```text
development
strict
```

Resolution order is explicit CLI argument, then
`CUDA_FRACTAL_STATE_TOOL_RUNTIME_COMPATIBILITY`, then the default
`development`. Unknown values fail clearly.

In `development` mode, packet/runtime identity differences:

1. are shown prominently in the UI and logs;
2. are compared field by field;
3. do not by themselves block proof;
4. cause materialization and replay to use the current configured runtime;
5. are persisted with packet identity, current identity, differences, selected
   mode, and disposition in binding and receipt evidence;
6. bind a successful result to the runtime actually used.

In `strict` mode, the same drift evidence is recorded and shown, then proof
stops before materialization.

Both modes fail closed when:

- packet files or embedded authorities disagree with the manifest;
- an authority is missing, malformed, ambiguous, or corrupt;
- an override is invalid;
- the runtime or deployed authority changes during packet construction;
- the runtime or deployed authority changes during one proof;
- candidate, binding, receipt, or review evidence is tampered with;
- the runtime changes after proof and before launch. This last case invalidates
  readiness and requires a new proof under the current runtime.

Runtime drift is compatibility uncertainty, not proof of incompatibility.
Engine load, requested-value survival, action-free replay, and user visual
review remain the behavioral gates.

### Backward Compatibility

Packet V6 and V7 use their existing filename-based authority loading. Packet
V8 uses validated container extraction. Existing packet validation may inspect
only the bytes bound by that historical packet; it must not silently repair or
regenerate them from the current runtime.

## Phase Checklist

- [x] Slice 0 - contract lock, architecture audit, baseline, and clean
  checkpoint.
- [x] Slice 1 - authority-container codec, Packet V8 staged builder, manifest,
  and bounded PNG transport.
- [x] Slice 2 - V8 override/proof extraction, central runtime compatibility
  policy, receipts, and UI cutover.
- [x] Slice 3 - navigation/status hardening, backward compatibility, local
  workflow acceptance, and stale-architecture audit.
- [x] Slice 4 - inventory newer captures, stop for user fixture selection,
  prepare the selected packets and manual gate, then stop for user review.

## Current Phase

Slices 0 through 4 are complete. After the read-only inventory checkpoint at
`b1010da20c66f58ae71270d4c27b81a65a0a1bf0`, the user selected six fixtures.
Their immutable Packet V8 directories and exact prompts are recorded in
`docs/packet_v8_six_fixture_manual_gate.md`. The campaign is stopped at the
user-run external-session boundary. The suite contains 100 passing Python 3.14
tests.

## Architecture Audit

The active architecture is already the sparse-state-override rescue. No active
proposal envelope, action lowering, capability-profile, repair-packet, or
tuple-allowlist architecture remains to preserve or remove in this campaign.

Packet and proof ownership is:

- `agent_bundle.py`
  - builds Packet V7 through a staged immutable directory;
  - copies exact finding/runtime artifacts and rechecks their identities;
  - emits three Markdown transport views that currently duplicate neighboring
    JSON files but are explicitly non-authoritative;
  - emits the bounded PNG web derivative while retaining the original frame in
    the packet as local authority;
  - validates immutable directory membership and file hashes when a packet is
    reopened.
- `state_override.py`
  - loads `state.json`, authoring surface, parameter surface, UI schema, and
    UI-Salt contract by physical filename;
  - mechanically regenerates and verifies the authoring surface;
  - owns strict sparse parsing, path validation, merge, and serialization.
- `state_override_proof.py`
  - requires the V6/V7 physical authority filenames;
  - compares the packet runtime identity at proof start, proof end, and launch;
  - currently treats any start-time mismatch as a hard rejection;
  - owns materialization, action-free replay, requested-value survival,
    receipts, visual-review decisions, and exact-candidate launch readiness.
- `user_workflow.py` and `user_workflow_app.py`
  - bind the exact immutable packet manifest;
  - permit loading an existing packet directory without regeneration;
  - render the current required/recommended attachment list;
  - dispatch proof through the shared bounded asynchronous worker.
- `test_agent_bundle.py`, `test_state_override.py`,
  `test_state_override_proof.py`, `test_user_workflow.py`, and
  `test_app_controller.py`
  - are the focused regression owners for the Packet V8 cutover.

V8 must therefore change packet construction and consumption together. The
three existing Markdown views are reusable presentation work, but their
current ad hoc fenced blocks are not an authority codec and cannot simply be
declared authoritative. The full source frame's removal from the physical V8
packet also means any base/candidate pixel comparison must not silently treat
the bounded derivative as full-resolution evidence.

## Goal Continuation Policy

- Run mode: `multi_slice`.
- Queue name: `packet-v8-seven-file-authority-compaction`.
- Ordered owners:
  1. `slice0_contract_and_baseline`;
  2. `slice1_container_and_builder`;
  3. `slice2_proof_and_ui_cutover`;
  4. `slice3_local_acceptance_and_hardening`;
  5. `slice4_capture_inventory_and_manual_gate_preparation`.
- Allowed slice classes: focused Python product code, tests, documentation,
  local packet/workflow evidence, screenshots, and state-tool Git checkpoints.
- Approved campaign boundary: Packet V8 through an acceptance-ready manual
  gate; no engine mutation and no self-grading of external web sessions.
- Blocked lanes: engine/runtime mutation, new authoring semantics, transport
  redesign beyond the seven-file contract, automated remote sessions, and
  manual fixture selection on the user's behalf.
- `slice_stop` handling: checkpoint each coherent slice, record
  `continue_to=<next_owner>` or `goal_hold=<reason>`, reset hostile review, and
  continue when the next owner remains in this queue.
- Review-checkpoint handling: local review-ready checkpoints do not complete
  the campaign. The dedicated fresh-capture selection and external manual test
  are explicit user-action holds.
- `goal_stop` handling: stop on explicit user pause, failed checkpoint, unsafe
  dirty state, stale-evidence contradiction, real authority ambiguity, need
  for engine mutation, or a decision outside this plan.
- Completion rule: do not treat a slice checkpoint as campaign completion.
  Stop this campaign when Slice 4 reaches the prepared user manual gate or an
  earlier true goal-stop condition.
- Closeout decision vocabulary:
  `slice_checkpointed_continue`, `slice_checkpointed_plan_reset_required`,
  `goal_stopped_user_pause`, `goal_stopped_failed_checkpoint`,
  `goal_stopped_scope_boundary`, `goal_stopped_real_ambiguity`, or
  `goal_stopped_stale_evidence_contradiction`.

## Presumption Loop

- Guilty-until-proven-innocent posture: assume compaction can silently weaken
  authority, hide missing files, or make a proof depend on live runtime bytes
  that were not in the immutable packet.
- Action-level hostile review before each meaningful edit: identify the likely
  failure mode, correct owner, proof surface, and blocked action.
- Forward TDD: add a failing focused test for each new container, builder,
  compatibility-mode, proof, and UI behavior before its implementation.
- After first green: attack malformed boundaries, hash/length collisions,
  runtime drift races, V6/V7 regression, and misleading UI readiness.
- Owner-change reset: each slice checkpoint resets hostile review before the
  next queued owner begins.
- Evidence rule: exact packet bytes and current-runtime proof decide behavior;
  generated prose and remembered Packet V7 assumptions do not.

## Presumption Evidence

- Owner proof: clean `main` and `origin/main` both resolved to
  `a440f257a51dd958b273f034d3edb13f0fe01648`; the campaign branch was created
  from that exact commit.
- Baseline proof: `PYTHONPATH=src; py -3.14 -m unittest discover -s tests`
  passed 87 tests on 2026-08-01.
- Existing authority owner: `agent_bundle.py` creates immutable Packet V7
  artifacts and `state_override.py`/`state_override_proof.py` consume them.
- Existing runtime behavior: proof currently rejects any packet/current runtime
  identity difference before materialization; this is the specific policy seam
  to replace, while preserving mid-proof and pre-launch change rejection.
- Dependency audit: current override and proof loaders are filename-based, the
  UI uses the packet handoff attachment lists, and launch readiness calls the
  same unconditional runtime-binding validator. These are the coordinated V8
  cutover seams; none requires engine mutation.
- User workflow evidence: V7 has been stable across extensive manual captures;
  file count and attachment friction are the remaining stated transport defect.

## Proof Ledger

- Manual RED: Packet V7 packet directories currently contain substantially
  more files than the intended drag-all handoff and force file selection in
  clients with upload-count limits.
- Baseline GREEN: 87 tests pass before Packet V8 mutation.
- Slice 0 proof target: tracked contract, dependency map, full suite, diff
  check, hostile review, clean pushed checkpoint. Result: contract and map are
  tracked; 87 tests passed; no engine files or runtime bytes changed.
- Slice 1 proof target: exact-byte container round trips, hostile malformed
  inputs, exactly seven/six physical files, source-frame provenance, staged
  snapshot race rejection, real V8 packet generation. Result: 7 codec tests
  cover exact round trip, opaque marker-shaped payloads, duplicates, unsafe
  names, invalid UTF-8, missing/unknown records, truncation, metadata, fence,
  length, and hash tampering. Packet tests prove seven files with a frame, six
  without one, manifest/container identity linkage, source-relative full-frame
  provenance, and V7 construction-race rejection carried forward.
- Slice 2 proof target: V8 authority extraction drives the same validator and
  proof; development drift attempts and records; strict drift stops; runtime
  changes during proof and before launch still invalidate. Result: V8 builder
  output drives the unchanged sparse validator; development/strict resolution,
  stable field-level drift comparison, pre-materialization strict stop,
  development proof binding, mid-proof rejection, and post-proof launch
  invalidation are covered by focused tests. UI and CLI expose the mode and
  receipt-backed warning.
- Slice 3 proof target: V6/V7/V8 loading, UI attachment/status truth, real local
  override/replay workflow, and stale filename-path audit. Result: focused
  regression reopens V6 and V7 byte-for-byte without runtime access or rewrite;
  V8 generation/reopening remains covered; the UI names V8, says drag all,
  displays development/strict policy, and stops at visual review; active docs
  describe the seven/six-file contract and current compatibility policy. Direct
  legacy filenames remain only in the explicit V6/V7 loader branches and
  historical documents.
- Slice 4 proof target: user-selected new captures only; exact prepared paths,
  prompts, checklist, and a clean acceptance-ready checkpoint. External model
  results are user-executed and not self-graded. Inventory result: 20 captures
  from 2026-07-24 through 2026-07-31 are recorded without ranking or selection
  in `docs/packet_v8_manual_fixture_inventory.md`. No Packet V8 directory was
  generated before selection. Final result: the user selected exactly six;
  those six were generated and independently reopened as seven-file Packet V8
  bundles, with paths, hashes, prompts, and checklist recorded in
  `docs/packet_v8_six_fixture_manual_gate.md`.

## Slice Validation

Every slice runs focused tests first, then:

```powershell
$env:PYTHONPATH = (Resolve-Path .\src).Path
py -3.14 -m unittest discover -s tests
git diff --check
```

Each slice also exercises its affected real workflow, performs hostile review,
commits, pushes, and proves a clean tree before continuing.

## Resume Point

The planned implementation queue was exhausted at the user-run manual gate.
The user subsequently returned seven fixture results, A through G. Their raw
transcripts, contemporaneous notebook, and reviewed conclusions are preserved
under `docs/manual-test-results/v8_six_fixture_manual_gate_08-01-2026/` and in
`docs/packet_v8_seven_fixture_manual_results.md`.

Packet V8 passed the reviewed authority and transport gate. A-E and G completed
the intended workflow. Fixture F reached a valid sparse override and then
timed out before the proof process emitted state or frame artifacts; its
captured render duration makes adaptive proof timeout the next grounded seam,
not a Packet V8 failure.

This Packet V8 campaign is complete. Further product mutation belongs to the
separately approved Packet V8 automated-route POC and its own checked plan.

Real Slice 1 workflow proof:

- finding: `fd91321945b2f65cb0926984318e523d0d8406d3c51935e39f541a41ea1cd6f3`
  (`explaino_bell`);
- Packet V8: `93554065-f13b-45bf-acfc-f9d5558caadb`;
- manifest SHA-256:
  `6556945178ba48ab79aa92f3bf518d1330b0c8679ca3a46472bb87f57fcf9eba`;
- exact physical result: seven files, including `packet.md`, `manifest.json`,
  the standalone state, three authority containers, and the bounded PNG;
- published-runtime generation and independent CLI inspection both passed.

Continuation decision: `continue_to=slice2_proof_and_ui_cutover` after the
Slice 1 commit, push, and clean-tree proof.

Real Slice 2 workflow proof:

- immutable Packet V8 input: `93554065-f13b-45bf-acfc-f9d5558caadb`;
- override: `params.explaino_damping` from `1.0` to `0.9`;
- proof: `95be4ee6-edc0-4851-8d2b-6dcaaebe8b09`;
- result: engine materialization and action-free replay proven; visual review
  intentionally pending and launch disabled;
- runtime compatibility: `development`, identity match, proof bound to
  `140707fd16283ac2db3c58a24146b73a7f29bbd15b0e1b36771c301f8b275e95`;
- candidate PNG was visually inspected and contains a healthy, non-blank Bell
  render.

Continuation decision: `continue_to=slice3_local_acceptance_and_hardening`
after the Slice 2 commit, push, and clean-tree proof.

Real Slice 3 UI proof:

- Packet V8: `58d6bd20-6f1f-4270-b09d-9ea123248a9f`;
- manifest SHA-256:
  `f67fcda184cb9af95abae03767446f22cd63d38b14f6440cc0c3ee17131beb27`;
- proof: `697842e4-095a-4786-9a2c-1bb26b6b2c2d`;
- UI states captured under ignored `.local/packet_v8_ui_acceptance/`:
  empty, bundle-ready empty override, override dirty, and visual review pending;
- screenshot review confirmed the seven-file drag-all list, visible development
  compatibility mode, healthy base/candidate previews, disabled launch, and no
  Packet V7/file-picker presentation.

Continuation decision: `continue_to=slice4_capture_inventory_and_manual_gate_preparation`
after the Slice 3 commit, push, and clean-tree proof.

Slice 4 inventory checkpoint:

- scope: 20 manual captures dated 2026-07-24 through 2026-07-31;
- result: six selectors and the captured iteration, zoom, render, pipeline, and
  frame-size distinctions are recorded in
  `docs/packet_v8_manual_fixture_inventory.md`;
- mutation boundary: no capture, engine, runtime, finding workspace, or packet
  directory changed;
- selection: deliberately not performed by the implementation agent.

The user approved exactly six fixtures after reviewing the inventory. No older
fallback was needed. The red 5,000-iteration ExplainO Balance Void capture is
retained deliberately as a diagnostic reasoning test, not an aesthetic
baseline.

Slice 4 prepared-gate result:

- six selected captures imported without source mutation;
- six immutable Packet V8 directories generated;
- each independently reopened with exactly seven physical/required files;
- no unavailable optional attachments;
- all bind one recorded runtime, executable, UI-Salt contract, and catalog
  identity;
- exact prompts and rule-by-rule acceptance checklist tracked in
  `docs/packet_v8_six_fixture_manual_gate.md`;
- external results deliberately not simulated or self-graded.

Slice 4 hostile review checked for source/packet mapping mistakes, stale or
mixed runtime authority, missing drag-all files, prompts that accidentally
force premature JSON, fixture-specific causal claims, and implementation-agent
self-grading. No unresolved defect remained: all six manifests independently
validated, the selection prompts explicitly withhold override output until the
later trigger, the Balance Void prompt treats color collapse as an observation
rather than established cause, and external evaluation remains user-owned.

Continuation decision: `goal_stopped_scope_boundary` at the user-run manual
gate. All preplanned sliced implementation work is exhausted.
