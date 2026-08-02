# V9 Cost-Controlled Automation and Scalar Bracket Sweep — Restart Plan

## Status and authority

```text
status: DOCUMENTED_AND_PAUSED
implementation: NOT_STARTED
starting repository: C:\code\cuda-fractal-engine-state-tool
clean merged baseline: main@12ebd9659439ad28d00458a0346e1ff5314c4fff
engine mutation: NOT AUTHORIZED
paid provider execution: NOT AUTHORIZED DURING THE PAUSE
```

This document is a restart-safe implementation plan. It records decisions made
after the Packet V8 automated-route POC and the first manual vortex-ablation
witness. It does not itself authorize product mutation after the pause. At
re-entry, verify live repository, runtime, provider, pricing, and budget facts
before creating an implementation branch.

The two future lanes are ordered deliberately:

```text
control model/API cost
-> retain the accepted Packet V8 authority workflow
-> add one local deterministic scalar bracket
-> qualify the combined V9 route
```

Cost is the gatekeeper. A larger automated battery, model ablation, or broader
sweep system must not begin while the current context architecture remains
economically unbounded.

## Proven baseline

The merged Packet V8 route already proves:

- seven-file manifest-driven packet transport;
- sparse state-shaped override extraction and validation;
- deterministic merge;
- authoritative engine materialization and action-free replay;
- proof-owned full-resolution PNG;
- non-human derived-finding promotion;
- refreshed Packet V8 generation;
- exact `ROUND_ADVANCE` and `ROUND_REVISE` rebinding;
- append-only run events and atomic active-turn projection;
- per-run provider-file ownership and cleanup;
- combined authoring and review responses;
- model, cached-input, uncached-input, output, and latency telemetry.

Manual and automated routes already converge on the canonical owners recorded
in [`v8_automated_route_authority_trace.md`](v8_automated_route_authority_trace.md).
V9 must reuse those owners.

## Cost witness

The completed two-round Phoenix run is preserved at:

```text
D:\salt-fractal\cuda-fractal-engine-state-tool\automated-runs\v8-auto-7adc3bb4-9b5e-4b73-a13e-4848e58ddd2f
```

Its durable event history records:

| Call | Role | Input | Cached | Uncached | Output |
|---|---|---:|---:|---:|---:|
| 1 | Round 1 authoring | 165,386 | 0 | 165,386 | 2,946 |
| 2 | Round 1 review | 330,248 | 164,892 | 165,356 | 929 |
| 3 | Round 2 authoring | 162,110 | 0 | 162,110 | 2,248 |
| 4 | Round 2 review | 326,252 | 161,616 | 164,636 | 664 |
| Total | | 983,996 | 326,508 | 657,488 | 6,787 |

The user-observed billing review estimated roughly `$6.73` for this run under
the pricing active at the time. Provider billing remains the dollar authority;
the repository evidence proves tokens and model identity, not the historical
invoice calculation.

At the pause boundary, the user reported approximately `$0.42` of API credit.
That is explicitly volatile and must be rechecked. It prohibits another live
automated test now.

The dominant defect is architectural: a review call retains the original
round's full packet through response continuation and also receives the
refreshed derived packet. The review calls therefore carry roughly two packet
loads. Visible output is not the main cost.

## Locked V9 context architecture

Do not use one ever-growing provider conversation containing every fixture and
every complete packet. Logical continuity and provider-context accumulation are
separate concerns.

V9 should partition authority into:

```text
shared stable foundation
+ one isolated case capsule
+ one compact round ledger
-> one bounded authoring context

refreshed result capsule
+ exact selected experiment
+ exact locked prediction
+ exact override
+ proof identity and result
-> one fresh bounded review context
```

### Shared stable foundation

This contains cross-case behavioral and contract material whose exact bytes are
identical. It may be uploaded or cached once when the provider contract proves
that reuse is safe. Hash identity, expiry, provider-file ownership, and cache
cost must remain visible.

It must not become a hand-maintained replacement for Packet V8 authority.
Packet construction still owns the exact resources. The transport layer may
deduplicate only byte-identical resources by role and SHA-256.

### Case capsule

Each fixture retains its exact state, finding-specific authoring authorities,
context, and image. Cases remain independently bound and independently
reviewable even when they share stable foundation resources.

### Compact round ledger

The controller—not model memory—owns:

- selected experiment;
- locked prediction;
- exact sparse override text and hash;
- current packet identity;
- proof identity and disposition;
- generated finding and refreshed-packet identity;
- gate proposal and controller transition.

The ledger is a concise transport projection of already durable facts, not a
second domain authority.

### Fresh review context

Review begins without the original full response chain. It receives only the
refreshed result authority and the compact ledger needed to audit the locked
prediction. This prevents a second complete copy of the original packet from
being charged merely to judge the result.

### Battery continuity

A future multi-fixture battery may present one logical session to the user, but
each case receives an isolated provider context. Shared facts may be reused by
hash; case packets and histories do not silently bleed across fixtures.

## Cost and budget contract

Before any provider dispatch, the controller must know or conservatively bound:

- requested and resolved model tier;
- pricing-table identity and effective date;
- expected uncached input;
- expected cache write and cache read;
- maximum output;
- context/pricing tier boundary;
- remaining per-run dollar budget;
- remaining account credit when the provider exposes it, otherwise a clearly
  labeled user-entered ceiling.

The controller must reject dispatch when the conservative next-call estimate
exceeds the remaining run budget. Token budgets remain useful safeguards but
are insufficient by themselves.

Receipts must separately record:

```text
estimated cost before dispatch
actual input/cached/uncached/output usage
pricing-table identity used for estimation
calculated post-response cost
provider billing authority disclaimer
```

No price table should be assumed current from this document. Re-entry must
verify official provider documentation and lock the prices used by that slice.

Initial qualification targets are planning hypotheses, not accepted contracts:

- no review call carries both a full original packet and a full refreshed
  packet;
- keep every call below the provider's then-current long-context surcharge
  boundary with explicit headroom;
- target no more than one packet-scale input per call;
- target at least a 50 percent reduction from the `983,996`-input-token Phoenix
  reference before beginning a fixture battery;
- do not hide cache-write cost behind a cached-token headline.

Model downgrade and reasoning-effort ablation belong after context compression.
The current `gpt-5.6-sol` behavior remains the golden reference. Candidate
models and tiers must be reverified at execution time and compared on the same
fixtures, gates, and receipt format.

## Scalar Bracket Sweep V1

### Purpose

One agent-selected hypothesis should be able to fan out into several local,
deterministic engine experiments without one paid conversation per value:

```text
one selected scalar axis and explicit bracket
-> N concrete ordinary sparse overrides
-> N existing engine proofs
-> one grouped local result
-> one compact model or human review
```

This is an alternate orchestration route over the existing override and proof
services. It is not a new state-authoring language.

### Public input shape

The existing State Override editor supplies an optional fixed override. A
second area supplies the sweep plan:

```json
{
  "sweep_version": 1,
  "axis": {
    "path": "params.vortex_strength",
    "values": [0.0, 0.25, 0.5, 0.75, 1.0]
  },
  "member_failure_policy": "continue_independent"
}
```

No placeholder is inserted into state-shaped JSON. No marker syntax enters the
ordinary override parser.

### V1 capability fence

V1 supports only:

- exactly one direct scalar leaf under `params`;
- a path present in the exact packet-derived authoring surface;
- one explicit ordered list of 3–9 concrete values;
- values of the declared scalar type;
- finite values within the attached authority's range;
- a fixed override that is independently valid against the same exact packet;
- independently materialized members from the same exact base.

V1 does not support:

- generated `min/max/count` floating-point ranges;
- template markers;
- multiple axes or Cartesian products;
- adaptive recursion inside one sweep;
- camera companion groups;
- array or custom-root member targeting;
- Color Pipeline row or parameter templating;
- family, render, or lens mutation;
- cumulative mutation from member to member;
- agent-authored code or analysis callbacks.

A later coarse-to-fine pass is a new explicit sweep plan with a new ordered
value list and its own receipt.

### Fixed-override collision rule

If the fixed override already contains the sweep axis leaf, reject the complete
plan before rendering anything.

There is no precedence rule. The editor must never show one fixed value while
the sweep silently substitutes another.

Collision detection is based on leaf presence in the duplicate-safe parsed
fixed override, not on whether that leaf would change the base. An explicitly
present axis path collides even when it repeats the captured value and would be
omitted from a semantic changed-path diff. Reuse or extract one shared canonical
override-leaf enumerator beside the existing parser/merge owner; do not create
a second validator or handwritten sweep-only path registry.

### Expansion and proof

For each declared value, the sweep service must:

1. begin with the exact packet-bound base;
2. copy the independently validated fixed override;
3. insert the one axis value;
4. serialize one ordinary concrete sparse override;
5. run the existing override parser, authorability validation, merge, proof,
   proof-image, and receipt services;
6. retain the concrete override and proof identity;
7. never inherit state or runtime output from the preceding member.

The engine-emitted candidate remains authority for each member. A sweep receipt
indexes existing member receipts; it does not replace them.

### Plan-level versus member-level failure

Plan-level failures abort before any member renders:

- malformed sweep JSON or unsupported version;
- invalid or stale packet/base binding;
- unauthorized, absent, non-scalar, or type-incompatible axis;
- fewer than 3 or more than 9 values;
- duplicate or non-finite values;
- out-of-range values;
- fixed-override/axis collision;
- invalid fixed override;
- authority or runtime hash drift before dispatch;
- inability to allocate an immutable sweep evidence directory.

Member-level failures are bound to one concrete value:

- engine process failure;
- materialization rejection;
- replay mismatch;
- timeout;
- missing or invalid proof frame;
- engine contradiction of the requested value.

With `continue_independent`, record the failed member and continue remaining
members from the exact base. With `stop_on_first_failure`, stop before starting
the next member. Already completed evidence is never rewritten.

Authority/runtime drift during execution stops the entire remaining plan even
under `continue_independent`; it is not an ordinary member failure.

### Sweep evidence

```text
sweeps/<sweep-id>/
  plan.json
  binding.json
  receipt.json
  members/
    000-<value>/
      override.json
      proof-ref.json
    ...
  presentation/
    contact-sheet.png
    adjacent-differences/
    index.md
```

The sweep receipt records:

- exact packet, manifest, finding, base-state, runtime, schema, and contract
  identities;
- fixed-override hash;
- canonical axis path and ordered values;
- member-failure policy;
- each concrete override hash;
- each proof ID, receipt hash, disposition, candidate-state hash, and frame
  hash;
- partial-completion and cancellation state;
- presentation-artifact hashes.

Contact sheets and difference images are derived review aids. They do not
replace full member frames or engine proof receipts.

### Cancellation

Cancellation prevents new members from starting and cancels only the currently
owned proof process through the existing job owner. Completed members remain
durable. Unstarted members are recorded as `NOT_STARTED_AFTER_CANCEL`, not as
proof failures.

## First scalar-sweep acceptance fixture

Use the reviewed witness in
[`manual-test-results/v9_vortex_bracket_discovery_2026-08-02.md`](manual-test-results/v9_vortex_bracket_discovery_2026-08-02.md).

```text
exact base:
D:\salt-fractal\cuda_newton_fractal_clone\findings\manual_capture\2026-08-02\132248_955__explaino_all

axis:
params.vortex_strength

values:
[0, 0.25, 0.5, 0.75, 1]
```

The manual `vortex_strength = 0` capture at `133520_315` is an endpoint witness,
not a byte-exact generated member. The generated sweep must preserve the base's
`4096 x 2560` render configuration and all other authorable state.

The acceptance question is whether the ear-like projections emerge gradually
or in a narrower transition interval. The tool must report evidence; it must
not automatically label the visual change a cusp or bifurcation.

## UI shape

Do not redesign the accepted two-column application.

The future UI may add an optional local route adjacent to the State Override
editor:

```text
Fixed State Override JSON
Scalar Bracket Sweep JSON
Validate Sweep
Run Local Sweep
Cancel Sweep
Open Sweep Folder
```

The UI shows:

- exact packet/base binding;
- validated axis and ordered values;
- fixed changed paths;
- per-member queued/running/proven/failed state;
- plan failure separately from member failure;
- aggregate completion without claiming human acceptance;
- the contact sheet only as derived review evidence.

The first sweep implementation is local and requires no provider credential.
Agent-assisted selection and result review attach only after local sweep proof
is accepted.

## Implementation slices

### Slice 0 — Re-entry and contract refresh

- Verify repository, branch, `HEAD`, upstream parity, worktree, runtime identity,
  Python 3.14, existing plans, and current test baseline.
- Reverify provider model, pricing, caching, context-tier, file-reuse, and
  usage-reporting contracts from official documentation.
- Reinspect the Phoenix run and this vortex witness from exact on-disk evidence.
- Convert this restart plan into the current repository-native goal/slice format
  if protocols have changed.
- Lock non-goals and exact acceptance budgets before code.

Stop if the accepted Packet V8 authority or canonical service ownership has
changed materially.

### Slice 1 — Cost accounting and dispatch gate

- Add a versioned pricing-policy input without treating it as provider billing
  authority.
- Estimate conservative next-call dollars before dispatch.
- Record estimated and actual usage-derived cost separately.
- Gate on remaining run dollars as well as tokens/responses/rounds.
- Expose the calculation and pricing identity in UI and run evidence.
- Use mocked provider usage only; make no paid request.

### Slice 2 — Context partition and transport deduplication

- Separate shared stable resources from exact case capsules by manifest role and
  byte hash.
- Build compact authoring and review ledgers from durable controller facts.
- Start review in a fresh provider context.
- Reuse provider files or caches only where the verified API contract permits.
- Preserve independent case binding and provider-file cleanup.
- Replay captured provider fixtures to prove request construction and context
  size without dispatch.

No model downgrade is evaluated before this slice closes.

### Slice 3 — Capped cost qualification gate

- Present the exact estimated maximum cost before enabling dispatch.
- Require available credit and explicit user authorization for one paid golden
  run.
- Compare against the Phoenix token/cost witness.
- Require at least the agreed cost reduction and unchanged authority behavior.
- Stop for review if any call crosses the then-current surcharge threshold or
  if review needs the full prior packet history.

No fixture battery follows a failed cost gate.

### Slice 4 — Headless Scalar Bracket Sweep V1

- Implement plan parsing, capability fencing, fixed-path collision rejection,
  concrete override expansion, plan/member failure taxonomy, cancellation, and
  immutable sweep receipts.
- Call only the existing validator, merge, timeout, proof, and proof-image
  services.
- Add a headless CLI for deterministic local qualification.
- Prove partial-member continuation and strict stop behavior.
- Run the vortex fixture without provider calls.

### Slice 5 — Thin UI and grouped presentation

- Add the optional sweep controls without rearranging the accepted workflow.
- Stream per-member state through the existing async ownership model.
- Generate one bounded contact sheet and optional adjacent-frame differences
  from proof-owned PNGs through one shared image owner.
- Preserve exact frames and receipts as authority.
- Stop for manual review of the local sweep.

### Slice 6 — V9 model ablation and bounded battery

After the cost and local-sweep gates pass:

- select a small fixture battery including vortex, iteration-horizon,
  feature-split/disappearance, custom-root, and observation-channel cases;
- compare the golden model with cheaper candidate tiers using identical case
  capsules, instructions, budgets, and scoring;
- permit one model-selected bracket followed by local execution and one compact
  result review;
- preserve transcripts, receipts, calculated cost, and model compliance;
- stop for user acceptance before expanding fixtures or orchestration depth.

## Validation rails

Every implementation slice must run focused tests, then:

```powershell
$env:PYTHONPATH = (Resolve-Path .\src).Path
py -3.14 -m unittest discover -s tests
git diff --check
```

Each slice also exercises its affected real workflow, performs hostile review,
commits one coherent checkpoint, and proves a clean tree.

Required responsibility trace at closure:

```text
manual single override and automated single override and scalar sweep member
-> same authorability generator
-> same parser and merge owner
-> same timeout resolver
-> same engine proof launcher
-> same proof-image owner
-> distinct orchestration receipts
-> no fabricated human acceptance
```

## Non-goals

- engine or published-runtime mutation;
- Packet V9 redesign merely to support the sweep;
- generalized templating or JSON Patch;
- multidimensional or random sweeps;
- unbounded adaptive orchestration;
- Reality Toolkit replacement;
- automatic mathematical classification;
- aesthetic scoring or automatic feature selection;
- automatic camera tracking;
- array, custom-root, or Color Pipeline sweep axes in V1;
- multi-model paid testing before cost qualification;
- one long provider conversation spanning complete case histories.

## Hostile planning review

The plan must continue to defend against these likely regressions:

- A “shared foundation” becomes a second hand-maintained Packet V8 contract.
- File reuse is assumed to be free or durable without provider proof.
- Fresh review context loses the locked prediction needed for honest audit.
- Dollar estimation is presented as invoice authority.
- A visible fixed override collides with the sweep axis and implicit precedence
  hides the discrepancy.
- A malformed plan starts some members before failing.
- A failed member silently changes the base for later members.
- Authority drift is misclassified as an ordinary independent failure.
- Contact sheets replace exact member evidence.
- A local sweep quietly gains an agent turn per member and recreates the cost
  problem.
- “Coarse-to-fine” becomes an unbounded adaptive loop.
- Model downgrade begins before the context architecture is repaired, obscuring
  whether savings came from model quality loss or transport correction.

## Pause and re-entry boundary

Planned implementation has not begun. The repository may retain these planning
documents while the user is away without creating a half-completed product
branch.

At return, begin only with Slice 0. Do not run a provider request from the old
UI merely to “see if it still works.” Reverify available credit, official
pricing, runtime identity, and exact merged repository state first.

The next approved discussion boundary is review and refresh of this plan. The
next product-mutation boundary, after that review, is Slice 1 cost accounting
and dispatch gating—not scalar-sweep UI work and not a paid model battery.
