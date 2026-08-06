# Question-Driven Research Session POC

## Status and authority

```text
status: APPROVED_FOR_IMPLEMENTATION
branch: codex/question-driven-research-session-poc
starting commit: cdfc516405080ba9604d8f16901068ed3018465a
engine mutation: NOT AUTHORIZED
paid provider generation: NOT AUTHORIZED UNTIL THE SLICE 5 COUNT/BUDGET GATE
```

The campaign adds one bounded unattended research route over the existing
Packet V8, sparse override, proof, scalar sweep, finding promotion, packet
refresh, provider cleanup, pricing, and run-store owners:

```text
sealed user research brief
-> answer, single override, scalar sweep, or unresolved report
-> local validation and execution
-> fresh evidence review
-> optional second experiment attempt
-> sealed audience-neutral scientific record
-> deterministic or audience-adapted report
```

The route does not automate human acceptance or launch authority.

## Contract 1: sealed research brief

One immutable brief records:

```text
question
attention_context
user_hypotheses[]
experiment_permissions:
  domains[]
  allowed_paths[] | null
  allow_scalar_sweep
fixed_conditions:
  notes[]
useful_answer:
  kind
  details
maximum_experiment_rounds: 0..2
communication_profile
hard_dollar_budget
```

Executable authority is the intersection of permitted domains, any exact
`allowed_paths`, and the current Packet V8 authoring surface. `null` permits
all Packet-authorable paths in the selected domains; `[]` permits no mutation.
Free text guides the planner but is never described as mechanically enforced.
The POC has no clarification pause: insufficient input closes with a detailed
unresolved report.

## Contract 2: active Color Pipeline context

Packet V8 presents the exact captured pipeline draft and copied UI-Salt
contract. It must additionally front-load one deterministic human-readable
summary derived from those same copied bytes:

```text
Active Color Pipeline at capture:
Phase Orbit [phase_orbit]
-> Identity [identity]
-> Phase Wheel [phase_wheel_palette]
-> Phase Finish [phase_finish]
```

The summary preserves deployed lane and row order, exposes disabled rows as
disabled, represents multiple rows without flattening topology, always retains
function IDs, and uses display names only when the copied contract supplies
them. When a complete draft exists, the flat serialized color tuple is labeled
as a replay/compatibility mirror rather than active authoring authority. The
same packet-bound summary enters planner and review contexts. It is a
presentation of current authority, not another pipeline schema.

## Contract 3: planner decisions and locked predictions

The planner returns exactly one action:

```text
ANSWER_READY
SINGLE_OVERRIDE
SCALAR_SWEEP
UNRESOLVED_REPORT
```

Executable responses keep their existing bare payload contracts. Their
surrounding response has these exact required fields.

Single override:

```text
RESEARCH_ACTION: SINGLE_OVERRIDE

Chosen experiment:
Why this experiment:
Locked prediction:
Observation channel:
Disconfirmation condition:
Camera and fixed-state policy:
Hostile self-review conclusion:

<one fenced JSON block containing an ordinary sparse override>
```

Scalar sweep:

```text
RESEARCH_ACTION: SCALAR_SWEEP

Selected bracket:
Why this bracket:
Locked trend prediction:
Observation channel:
Disconfirmation condition:
Fixed-state and camera policy:
Hostile self-review conclusion:

<one fenced JSON block containing an ordinary Scalar Bracket Sweep V1 plan>
```

Before execution the controller preserves the raw response and seals a
`round-plan.json` containing the action, prediction, observation channel,
disconfirmation condition, camera policy, payload SHA-256, and source-response
SHA-256. Review binds to the exact round-plan identity, so predictions cannot
be rewritten after evidence exists.

Round-plan identity is explicit:

```text
round_plan_contract_sha256
  SHA-256 of canonical JSON under round_plan_canonicalization_version

round_plan_file_sha256
  SHA-256 of the exact persisted round-plan.json bytes
```

The generic name `round_plan_sha256` is not used because it does not identify
which representation was hashed.

`ANSWER_READY` is a provisional answer supplied to synthesis, not evidence.
`UNRESOLVED_REPORT` uses one reason:

```text
BRIEF_INSUFFICIENT
AUTHORITY_INSUFFICIENT
CAPABILITY_UNAVAILABLE
QUESTION_OUT_OF_SCOPE
```

## Contract 4: attempts, review, and promotion

- At most two experiment attempts are allowed.
- An attempt is consumed when a validated experiment begins local execution.
- Proof failure, no effect, or partial sweep failure does not refund it.
- A sweep counts as one attempt regardless of member count.
- No automatic runtime retry is authorized.
- One executable correction turn is available for the complete session.

Review returns one gate:

```text
COMPLETE_RESEARCH
CONTINUE_RETAIN_BASE
CONTINUE_PROMOTE_RESULT
UNRESOLVED
```

Review classifies every exact single result or sweep member once as:

```text
SUPPORTED
CONTRADICTED
CENSORED_OUT_OF_FRAME
UNOBSERVABLE
EXECUTION_FAILED
```

Loss of a subject or measurement boundary from the retained viewport is
`CENSORED_OUT_OF_FRAME`. It contributes neither confirmation nor contradiction.
The controller validates exact result coverage and execution-status consistency;
the reviewer owns the evidence interpretation for replay-proven results.

Automatic continuation may promote at most one exact replay-proven single
result or sweep member per review gate. Promotion requires explicit model
nomination plus controller validation. Replay proof alone never promotes.
Promotion creates the `current_research_base` and records:

```text
promotion_kind: automated_research_promotion
replay_proven: true
human_acceptance: false
launched: false
```

`CONTINUE_RETAIN_BASE` keeps the preceding packet as authoring authority and
retains the candidate as evidence only.

## Contract 5: cost authority

Defaults are:

```text
model: gpt-5.6-luna
reasoning effort: high
disclosure profile: assisted
pricing tier: standard
prompt cache policy: explicit_no_cache
hard dollar budget: 0 until entered
```

`assisted` describes packet-bound enrichment disclosure; it is not an API
service tier.

Current stage ceilings are:

```text
planner: 200,000 input / 8,000 output tokens
review: 200,000 input / 8,000 output tokens
correction: 200,000 input / 4,000 output tokens
final synthesis: 100,000 input / 12,000 output tokens
alternate communication render: 50,000 input / 6,000 output tokens
```

These are safety and conservative-reserve ceilings, not expected usage.

Before every provider dispatch the controller counts the exact prepared
request and estimates its cost using the recorded active pricing policy. Before
an experiment-capable planner call, remaining budget must cover:

```text
exact current planner dispatch
+ conservative mandatory review reserve
+ mandatory final-synthesis reserve
+ selected communication-render reserve
+ correction reserve while relevant
```

Correction reserve is released after successful payload validation or after it
is consumed. Review, correction, and second-round planner reserves are released
after `ANSWER_READY` or `UNRESOLVED_REPORT`. The controller never deliberately
executes evidence that ordinary accounting says it cannot afford to review.

The paid gate separately reports the exact initial-dispatch count and estimate,
the user-entered hard run budget, and the conservative remaining-stage ceiling.
Every later request is recounted. The hard dollar budget is the enforceable
maximum; count-only is not misrepresented as an exact full adaptive-run cost.

## Contract 6: scientific records and communication

Scientific conclusions are:

```text
ANSWER_ESTABLISHED
ANSWER_PARTIAL
QUESTION_UNRESOLVED
CONTRADICTED
NO_SCIENTIFIC_CONCLUSION
```

`CONTRADICTED` is reserved for contradiction of the question's principal
proposition. Failed subsidiary predictions remain `contradicted_claims`.
`best_next_experiment` is nullable.

Requested, canonical, and emitted values are distinct. Canonical values come
only from existing validator or proof normalization receipts; otherwise
`canonical_value_status` is `unavailable`.

Evidence references carry `artifact_role`, `artifact_root`, `root_identity`,
safe relative path, SHA-256, and applicable proof, sweep, and member identities.
Supported roots are `question_run`, `state_tool_workspace`, `finding`, `packet`,
`proof`, `sweep`, and `engine_capture`. Resolution rejects absolute paths,
traversal, root escape, stale identity, and hash mismatch.

The implemented scientific-record V1 wire schema is authoritative for this
POC. It uses `answer`, classified claim arrays, `unresolved_questions`,
`experiment_summaries`, requested/canonical/emitted receipts,
`confidence_and_limitations`, and nullable `best_next_experiment`. Each
experiment summary copies the exact structured observation outcomes from its
referenced review decision. `confidence_and_limitations` contains one overall
`LOW`, `MODERATE`, or `HIGH` assessment plus at least one explicit limitation.

Research-base and packet-lineage lifecycle identity remain controller-owned in
the synthesis context, closeout, and active projection. They are not duplicated
as model-authored scientific facts. Likewise, structured observation outcomes
carry negative and unexpected findings without adding a second prose-only
negative-findings field.

The Working Session report is deterministic. The optional Adult Beginner / Carl
Sagan / Concept First report is one fresh model call over the sealed record.
Invalid or ungrounded synthesis is rejected without retry and closes with a
deterministic `NO_SCIENTIFIC_CONCLUSION` record plus
`MANUAL_REVIEW_REQUIRED`. Alternate-render failure does not invalidate sealed
science or the Working Session report; a selected required alternate report
closes at `MANUAL_REVIEW_REQUIRED`.

## Implementation slices

### Slice 0: contract lock and authority baseline

- Reverify Git, runtime, Python 3.14, workspace, and packet authority.
- Preserve the scanner's `NOT_APPLICABLE` verdict; do not synthesize an adapter.
- Trace canonical semantic owners reused by the route.
- Qualify the epsilon golden court and record the Rational Escape exclusion.
- Check in this contract and the supplied historical sweep evidence.

### Slice 1: packet context, research store, and recovery

- Add the active pipeline summary to Packet V8 and bounded model contexts.
- Add immutable research artifacts over a shared append-only event and atomic
  projection owner.
- Add exact resume rules and Windows replace-contention regression coverage.

### Slice 2: planner and experiment controller

- Parse and seal the four planner outcomes and locked round plan.
- Enforce domains, exact paths, attempts, correction, and sweep limits.
- Execute only through canonical override, proof, sweep, promotion, and packet
  services.

### Slice 3: cost, review, synthesis, and reports

- Add per-dispatch exact counting and conservative future-stage reserves.
- Build fresh review contexts from exact round plans and evidence.
- Seal and validate the audience-neutral scientific record.
- Render deterministic and bounded audience-adapted reports.

### Slice 4: thin Research Question UI

- Add the sealed brief form and Luna/high default.
- Show Answer, Experiments, Visuals, and Files results.
- Show the captured active pipeline, attempts, prediction, current research
  base, changed and normalized values, costs, gates, and durable artifacts.

### Slice 5: offline qualification and paid gate

- Run exhaustive offline contract, failure, recovery, and communication courts.
- Prepare the epsilon golden request and count-only command.
- Stop for approval of the exact first-call estimate, hard budget, and
  conservative adaptive ceiling before any provider generation.
- After one authorized golden run, stop for user review before broader use.

## Post-Golden Transaction Repair Addendum

The first complete paid golden run proved the vertical slice but exposed three
host-controller defects. The user authorized one bounded repair and rerun. This
addendum supersedes the earlier Slice 5 stop only for the work below.

### Repair slice A: continuous bounded investigation

- A second planner call remains a fresh provider context, but receives one
  compact controller-built ledger derived from immutable prior round plans,
  execution references, and review decisions.
- The ledger identifies the current research base, packet lineage, tested scalar
  values, prior predictions and outcomes, review gates and next steps, remaining
  attempt count, and remaining dollar budget.
- Scalar-sweep planner output declares `Replication controls`. A prior tested
  value may recur only when it is named there; undeclared repetition fails local
  validation, and a declared control must be both prior-tested and present in the
  new sweep.
- The planner rubric distinguishes a dense local bracket for response-law work
  from a broad logarithmic bracket for regime discovery.

### Repair slice B: executable review gates

- Review output adds one exact `Next action class`: `STATE_EXPERIMENT`,
  `ANALYSIS_ONLY`, `ANSWER_READY`, or `UNAVAILABLE`.
- `CONTINUE_RETAIN_BASE` and `CONTINUE_PROMOTE_RESULT` are legal only with
  `STATE_EXPERIMENT`. Analysis-only or unavailable advice cannot spend another
  planner round.
- The review artifact retains both the free-text next step and its exact class.

### Repair slice C: terminal authority and result workspace

- Expected closeout appends events for scientific-record sealing, deterministic
  Working Session rendering, provider cleanup, and terminal session closure.
- The final `active-turn.json` projection clears the pending plan and records the
  terminal state, controller disposition, scientific conclusion, record hash,
  and cleanup completion. Resume must not repeat a sealed synthesis turn.
- Results add a controller-generated navigation index and closeout receipt. A
  visual run gets one deterministic summary assembled from proof-owned PNG
  presentation artifacts; no second proof-image conversion path is introduced.
- Working Session and alternate communication statuses are represented
  separately.

### Repair qualification gate

- Run focused protocol, controller, result, and runner tests, then the complete
  Python 3.14 suite and the local golden workflow.
- Hostile-review the transaction and responsibility ownership.
- Run exactly one fresh count-gated paid golden rerun under the already approved
  `$0.30` hard cap. Record exact cost and compare continuity, gate legality,
  terminal projection, result navigation, and scientific discipline with the
  first live pass.
- Stop again for user review. Broader automated use remains unauthorized.

## Post-Qualification Contract Alignment Addendum

The successful paid rerun at
`question-research-6440724c-b38d-43de-9ec4-5af4720831a3` exposed narrow contract
alignment issues after the main transaction passed.

- The 8,000-token review ceiling is retained because live Attempt 2 proved the
  original 4,000-token ceiling incomplete. The 12,000-token synthesis ceiling
  is retained because Attempt 5 reached the original 8,000-token limit. These
  are explicit evidence-based amendments, not silent drift.
- Review now seals exact per-result observation classifications. Out-of-frame
  evidence is censored rather than falsifying.
- Scientific-record V1 keeps the implemented claim-oriented schema and adds
  required structured confidence and limitations. This explicitly supersedes
  earlier planning vocabulary such as `direct_answer`; lifecycle base and
  lineage remain controller receipts.
- Round-plan canonical-contract and exact-file hashes are named separately and
  the canonicalization version is persisted.
- Provider events distinguish a newly dispatched request from recovery of a
  durable response. A generation is not labeled a redispatch merely because a
  count-only request preceded it.
- Result disposition exposes `working_session_status` and
  `alternate_communication_status` only; the redundant generic communication
  alias is removed for new runs.

## Golden court

Historical source capture:

```text
D:\salt-fractal\cuda_newton_fractal_clone\findings\manual_capture\2026-08-05\143014_930__explaino_transcendental
```

Historical Packet V8:

```text
D:\salt-fractal\cuda-fractal-engine-state-tool\findings\3209208bc5ccbc09a8f36fbc60b95d125f082761e0195b8c9aaee1af80f3c2cc\packets\41de51de-0e49-4114-8c1a-0b6f86a09af3
```

Question:

```text
Why does the ring field terminate at a circle, and how does changing epsilon
affect that circle's radius?
```

Only `params.epsilon` is executable. One scalar sweep and one optional follow-up
attempt may establish the narrowest evidence-supported relationship or return a
truthful unresolved result. An exact proportional law is not required.

The historical packet remains immutable calibration evidence. Because its
runtime identity differs from the published runtime at Slice 0, any paid live
court must first generate and bind a fresh Packet V8 from the same source
capture and re-prove the epsilon authoring/sweep surface.

## Boundaries and closure

Deferred: Rational Escape seed drift pending truthful engine authority,
interactive clarification, generalized float canonicalization, new diagnostics,
automatic measurements, paired or multidimensional sweeps, adaptive sweeps,
more than two attempts, generalized communication profiles, engine mutation,
launch, and human-acceptance automation.

Every slice runs focused tests, the complete Python 3.14 suite, its applicable
workflow proof, `git diff --check`, hostile self-review, a coherent commit, and
a clean-tree check.
