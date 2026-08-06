# Pick Up Here — State Tool Paused For Engine Color Pipeline Handoff

## Stop reason

The state-tool implementation is intentionally paused while the CUDA fractal
engine completes its current Color Pipeline work.

Do not resume product mutation from chat memory. Re-establish the exact Git and
published-runtime authority described below, wait for a clean engine handoff,
then create a new bounded state-tool plan.

```text
pause date: 2026-08-06
state-tool repository: C:\code\cuda-fractal-engine-state-tool
engine repository: C:\code\cuda_newton_fractal_clone
published runtime: D:\salt-fractal\cuda_newton_fractal_clone\runtime
engine mutation from this repository: not authorized
next product mutation: blocked on clean merged and published engine handoff
```

## State-tool checkpoint

The pause was prepared on:

```text
branch: codex/question-driven-research-session-poc
pre-handoff feature HEAD: 7141859cd6d9cbfb994883669e00befe082a8240
feature branch relationship before handoff commit: 17 commits ahead of origin/main
merge target: origin/main
```

The exact final pause/merge commit is the commit containing this file. Verify it
from Git rather than relying on a chat transcript:

```powershell
git status --short --branch
git log -1 --oneline --decorate
git rev-parse HEAD
git rev-parse origin/main
git merge-base --is-ancestor HEAD origin/main
```

Expected final state after the pause PR is merged:

```text
branch: main
HEAD == origin/main
working tree: clean
the commit containing this file is an ancestor of origin/main
```

## What is complete

The repository now contains the operational left-side finding/Packet V8 route,
sparse state overrides, replay proof, visual review and launch gating, scalar
sweeps, finding enrichment, compact packet transport, bounded OpenAI automation,
and the question-driven research-session POC.

The most recent bounded qualification completed successfully:

```text
run:
D:\salt-fractal\cuda-fractal-engine-state-tool\question-runs\question-research-a9001590-b54a-403c-a3bc-3cd4ddfcbbad

controller disposition: COMPLETED
scientific conclusion: ANSWER_PARTIAL
structured confidence: MODERATE
experiment attempts: 1
sweep members: 5 / 5 REPLAY_PROVEN
calculated provider cost: $0.0896828
artifact index: 26 entries, all present and hash-matching
provider cleanup: complete, zero remaining IDs
human acceptance: false
```

The implementation checkpoint passed the complete Python 3.14 suite with 299
tests. The user has not yet completed a normal manual review of the new research
question form. Do not describe the form or its scientific presentation as
human-accepted.

Read these current campaign records first:

1. `docs/question_driven_research_session_poc_plan.md`
2. `docs/question_driven_research_session_live_golden.md`
3. `docs/question_driven_research_session_post_run_alignment.md`
4. `docs/question_driven_research_session_slice0_authority.md`
5. `docs/v8_automated_route_authority_trace.md`
6. `docs/question_driven_research_session_slice5_paid_gate.md`

Earlier V9 economic qualification and enrichment plans remain useful historical
context, but their status text is not the current restart authority. Revalidate
every runtime, model, price, and budget fact before reuse.

## New blocking evidence

The capture that exposed the compatibility gap is:

```text
D:\salt-fractal\cuda_newton_fractal_clone\findings\manual_capture\2026-08-06\165143_451__newton
```

Its `state.json.color_pipeline_draft` contains 13 enabled rows:

```text
Source:   4 rows
Shape:    4 rows
Palette:  1 row
Grading:  4 rows
```

Two rows share `ui_row_id: 2`:

```text
Shape / phase_mirror_v1
Grading / levels_gamma_v1
```

Packet construction currently fails at:

```text
ValueError: Captured Color Pipeline repeats ui_row_id 2
```

The rejection originates in:

```text
src/cuda_fractal_state_tool/agent_bundle.py
validate_captured_color_pipeline_draft
```

The state tool currently treats `ui_row_id` as globally unique. The engine's
state loader does not enforce that invariant: it requires positive row IDs and
`next_row_id` greater than every row ID, while UI automation identities include
both lane ID and row ID.

A read-only in-memory diagnostic changed only the repeated Grading row ID and
advanced `next_row_id`. After that synthetic change, all 13 captured functions,
complete parameter arrays, carrier types, ranges, enum choices, and ordering
validated against the exact published UI-Salt contract. No packet or capture
artifact was modified.

This means:

```text
fail-closed behavior: correct
immediate incompatibility: state-tool row-identity assumption
function/parameter catalog compatibility: passes
```

Do not simply delete the check without first settling the engine-owned row-ID
scope. The engine's global `next_row_id` allocator suggests global identity may
have been intended even though the loader and lane-qualified UI paths accept the
captured duplicate. The correct restart action is to obtain an explicit engine
contract or engine-team decision, then make Python enforce that exact rule.

## Published-runtime snapshot at pause

The runtime used for the read-only diagnosis was an intermediate published
authority, not the engine's dirty composite worktree:

```text
active executable: fractal_ui.exe
executable SHA-256:
4a2d4980a3efbaac87d5ab56e3249fa981b0b44a88f1d0c7d79fcf1a0482db86

published Color Pipeline contract SHA-256:
1fbbedc370a6ed9613ab4f332d5f7468c9a1b8035d1c21bcbb572cfbf7becd4c

clean engine HEAD contract SHA-256 at the review point:
9a74474476327f65de680c2f3c7a3040cab6f255f87a9030a32d627cecd0eb04

dirty engine worktree contract SHA-256 at the review point:
be56b787df68cfa973b609cdf705a083faefea3e445c5980b75db87a030b6a74
```

Those differing hashes are why state-tool implementation must not target the
current dirty source tree. They are historical pause evidence only; recompute
all identities after the engine publishes its final checkpoint.

## Engine repository boundary

At the pause, the engine was deliberately left untouched:

```text
branch: codex/color-pipeline-composite-function-v1
HEAD: 7c4c0a7c86ff1dec690976cdcb8943e9ae6da5ba
worktree: dirty, active authorized engine work
```

The active engine plan is:

```text
C:\code\cuda_newton_fractal_clone\docs\notes\color_pipeline_composite_function_v1_PHASED_PLAN.md
```

Its relevant contract decisions are:

- composite descriptors are separate from primitive function descriptors;
- the V1 pilot is Shape-local `unit_contours_v1`;
- a generic Prepare transaction will own expansion, typed validation,
  capabilities, routes, normalization, and receipts;
- `state.json.color_pipeline_draft` remains expanded primitive-row replay
  authority;
- `color_pipeline_composite_projection` is optional wrapper provenance;
- missing or mismatched composite metadata must flatten to primitive replay
  rather than invalidate the state.

Whenever inspecting or changing the engine, read its current `AGENTS.md` and
all required protocols first. Engine-local rules supersede this handoff. Do not
reuse the branch, hashes, plan phase, dirty file list, or runtime identities
above without live verification.

## Why a larger state-tool adjustment is needed

The immediate row-ID defect is small, but packet guidance has also fallen behind
the engine's graph model.

The state tool already does several things correctly:

- reads the exact deployed UI-Salt function library;
- accepts multiple rows per lane;
- validates function membership and complete parameter arrays mechanically;
- validates carriers, ranges, enums, and declared parameter order;
- copies exact authority bytes into immutable Packet V8 bundles;
- preserves fixed captured topology for sparse overrides;
- leaves final materialization and replay to the engine.

Do not replace those seams or introduce a Python function catalog.

The stale parts are:

1. Packet prose treats `composition_recipe_contract.compatibility` as the
   general Source/Palette/Grading authoring model. The engine now exposes typed
   ports, signal types, adapters, edge-resolution policy, arbitrary row stacks,
   graph receipts, and runtime capability/applicability receipts.
2. The packet presents enabled functions as one flat arrow chain. A multi-row
   source lane is an ordered weighted fold, while Shape and Grading are
   sequential transformations. The exact engine graph receipt already records
   nodes, edges, source-stack kind, active execution, and unsupported routes.
3. Python can validate local function parameters but cannot truthfully solve all
   graph compatibility, adapter, capability, composite-expansion, and
   normalization behavior. The upcoming engine Prepare seam should own that.

For the blocking Newton capture, `fractal-state.json` already reports:

```text
graph schema: viewer.color_pipeline_graph_receipt.v1
execution authority: linear_row_stack
source stack kind: non_sdf_only
nodes: 13
edges: 12
unsupported routes: 0
recipe match: modified
```

The deployed contract also declares the source fold as
`ordered_destination_weighted_lerp`. The future packet should project those
facts directly instead of asking an agent to reconstruct them from raw JSON.

## Required engine-to-tool handoff gate

Do not open a state-tool implementation slice until all of these are true:

- [ ] Engine composite work is checkpointed through its repository-native plan.
- [ ] Engine work is merged under its authorized workflow.
- [ ] Local engine `master` is at the exact merged commit.
- [ ] Engine worktree is clean.
- [ ] Required engine closure and rearward-review receipts are complete.
- [ ] Published runtime is rebuilt from exact merged `master`.
- [ ] Published executable SHA-256 is recorded.
- [ ] Published UI schema SHA-256 is recorded.
- [ ] Published function-library contract SHA-256 is recorded.
- [ ] Published composite-contract SHA-256 is recorded when shipped.
- [ ] Headless and viewer-path smoke tests pass from the published runtime.
- [ ] Row-ID identity scope is explicitly settled by engine authority.
- [ ] No state-tool files were changed during engine work.

If the engine campaign changes its planned state/projection/receipt contracts,
revise the state-tool recovery plan from the final published truth. Do not force
the engine to conform to this historical handoff.

## Proposed bounded recovery slices

These are reviewed recommendations, not yet an approved checked-in
implementation campaign.

### Slice 0 — Lock the post-engine authority

- Start from exact clean merged state-tool `main`.
- Record engine commit, executable hash, schema hash, function-contract hash,
  and composite-contract hash.
- Preserve the Newton capture and its copied published authority as a focused
  regression fixture.
- Lock the engine-declared row identity, topology, and projection rules.
- Inventory contract deltas since the last accepted Packet V8 runtime.

### Slice 1 — Restore exact packet generation

- Replace Python's global row-ID assumption with the engine-declared rule.
- Keep strict function, parameter, carrier, range, enum, and ordering checks.
- Generate Packet V8 successfully from the unmodified 13-row Newton capture.
- Prove existing packets and historical workspace data remain readable.
- Do not redesign the UI or override format.

### Slice 2 — Add engine-owned graph presentation

Create one deterministic projection inside the existing compact Color Pipeline
authority container. Do not add another loose web attachment.

Project from copied packet bytes:

- lane-qualified row identity and order;
- function IDs, labels, and exact parameter values;
- typed ports and signal types;
- source-fold operation;
- exact graph nodes and edges;
- active execution and fail-closed status;
- chosen adapters or resolution receipts when available;
- capability/applicability status;
- recipe match and provenance;
- unsupported routes.

Replace tuple-centric packet prose with graph/Prepare guidance. The projection
is a navigation fact sheet, not a second pipeline authority.

### Slice 3 — Reuse engine Prepare for candidate validation

Preferred flow:

```text
exact Packet V8 base
+ fixed-topology sparse override
-> engine Prepare
-> normalized expanded draft and graph receipts
-> materialization
-> action-free replay
-> visual review
```

Python may retain cheap structural checks, but it must not own graph solving,
adapter legality, capability availability, composite expansion, or
normalization. If the generic engine Prepare seam is not exposed headlessly,
request the smallest reusable engine API/CLI exposure through a separate
engine-native plan.

### Slice 4 — Composite projection compatibility

- Treat expanded primitive rows as replay authority.
- Carry composite projection as read-only captured context initially.
- Allow engine-authoritative reconstruction or flattening.
- Record projection normalization or removal without mistaking it for dynamics
  loss.
- Do not permit agent-authored composite wrappers without a separately approved
  contract.

### Slice 5 — Real qualification and manual gate

Required courts:

1. Exact 13-row Newton capture packet generation.
2. Parameter-only edit inside the captured graph.
3. Function replacement accepted by engine Prepare.
4. Incompatible replacement rejected with exact graph/route evidence.
5. Composite-bearing `unit_contours_v1` capture.
6. Missing/mismatched composite contract with successful primitive replay.
7. Development compatibility mode warns and attempts.
8. Strict compatibility mode warns and stops.
9. Existing manual override, automated Packet V8, scalar-sweep, and research
   routes continue to use the same packet/proof owners.

Stop for user review before merge if the packet's interaction contract or file
transport changes materially.

## Re-entry commands

Start in the state-tool repository:

```powershell
Set-Location C:\code\cuda-fractal-engine-state-tool
git fetch origin
git switch main
git pull --ff-only origin main
git status --short --branch
git rev-parse HEAD
Get-Content .\AGENTS.md
Get-Content .\PICK_UP_HERE.md
$env:PYTHONPATH = (Resolve-Path .\src).Path
py -3.14 -m unittest discover -s tests
```

Then inspect the engine read-only before making any plan claims:

```powershell
Set-Location C:\code\cuda_newton_fractal_clone
Get-Content .\AGENTS.md
git status --short --branch
git rev-parse HEAD
git log -8 --oneline --decorate
Get-Content .\spec_intake\_STATUS.md
Get-Content .\HANDOFF_LOG.md -Tail 12
```

Run engine bootstrap or receipt-producing helpers only under the engine's live
instructions and only when the repository is no longer being treated as
strictly read-only.

After the engine handoff, recompute runtime identities from:

```text
D:\salt-fractal\cuda_newton_fractal_clone\runtime\fractal_ui.cmd
```

Do not reuse the hashes in this document as current authority.

## Deferred and unauthorized work

This pause does not authorize:

- engine mutation;
- a second Python Color Pipeline model or graph solver;
- UI redesign;
- family switching;
- pipeline topology editing from sparse overrides;
- agent-authored composite wrappers;
- remote-agent API expansion;
- diagnostic-mosaic or Reality Toolkit expansion;
- a new paid model battery;
- automatic scientific or human acceptance;
- deletion or migration of historical packets, proofs, captures, or runs.

The question-driven research-session plan is exhausted at its user-review
boundary. The Color Pipeline recovery work is not yet a checked-in approved
implementation plan. Replan after the engine handoff before further product
mutation.

## Pause closure statement

```text
State-tool work through the question-driven research POC is preserved and
published. The repository is paused because the engine's Color Pipeline
authority is actively evolving. The immediate packet failure is reproduced and
classified; the recovery architecture and engine handoff gate are documented.
No engine files were changed. Resume only from clean merged state-tool main and
a clean merged and published engine checkpoint. Replan before product mutation.
```
