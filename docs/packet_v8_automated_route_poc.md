# Packet V8 Automated Route POC

## Status

- Campaign: approved implementation.
- Starting branch: `codex/v8-automated-route-poc`.
- Exact starting commit: `3f42290abb734ae17e8ae95f2c2c9f111d631fb4`.
- Baseline: clean merged `main`, 100 Python 3.14 tests passing.
- Current owner: `timeout-and-contract-foundation`.

## Goal

Add one bounded automated route that follows the accepted Packet V8 workflow:

```text
Packet V8
-> exploratory model session
-> one sparse state override
-> shared validation and replay proof
-> proof-owned candidate PNG
-> automation-owned derived finding
-> refreshed Packet V8
-> bounded review loop and gate disposition
```

The automated route must reuse the manual route's semantic owners. It must not
automate Tk button clicks, fabricate human acceptance, or introduce alternate
packet, override, proof, timeout, image, or finding-promotion implementations.

## Goal Continuation Policy

- Run mode: multi-slice Continuation Queue Goal.
- Queue name: `packet-v8-automated-route-poc`.
- Ordered owners:
  1. `packet-v8-baseline-closure` (complete at the starting commit);
  2. `timeout-and-contract-foundation`;
  3. `openai-transport-and-run-store`;
  4. `automated-controller-and-promotion`;
  5. `thin-ui-entry`;
  6. `qualification-and-review-hold`.
- Allowed slice classes: focused Python code, tests, tracked documentation,
  ignored local evidence, and one explicitly capped live API qualification.
- Approved campaign boundary: a pushed, acceptance-ready POC checkpoint.
- Blocked lanes: engine or runtime mutation, Packet V9, multi-model sweeps,
  generalized orchestration, Reality Toolkit expansion, aesthetic scoring,
  scanner adaptation, and final merge before user review.
- slice_stop handling: checkpoint, record `continue_to=<next_owner>` or a typed
  hold, reset hostile review, and continue when the next owner is in the queue.
- goal_stop handling: stop only on explicit user pause, failed checkpoint,
  unsafe dirty state, stale-evidence contradiction, real ambiguity, unavailable
  required credential at the live gate, queue exhaustion, or an owner outside
  this plan.
- Completion rule: complete only after the qualification queue is exhausted and
  the branch is pushed at `V8_AUTOMATED_ROUTE_POC_READY_FOR_REVIEW`, or after a
  genuine earlier goal stop is recorded.

## Qualified Scanner Boundary

The Salticid Responsibility-Compression Scanner was inspected at
`origin/codex/pack-foundation-recovery@24c8afc3ab604937cec500abdbfde352d409f6fe`.
It is not present on the inspected `origin/master`. Its focused suite passes 12
tests, but it accepts Salticid-specific structured evidence and explicitly
prohibits source scraping. It cannot discover the Python/Tk/service/subprocess
relationships in this repository.

Applicability is `NOT_APPLICABLE`. Do not adapt it, imitate it, synthesize its
Salticid inputs, or create scanner scores for this campaign. Preserve the
qualification under `.local/`; track only reviewed conclusions and perform
source-grounded before/after authority traces.

## Locked Protocol Contracts

### State machine

Add `agent_session_protocol.v1` with:

```text
OBSERVE
EXPLORE
SELECT_EXPERIMENT
LOCK_PREDICTION
REQUEST_OVERRIDE
VALIDATE_OVERRIDE
PROVE_CANDIDATE
PROMOTE_DERIVED_FINDING
REFRESH_PACKET
REVIEW_RESULT
SELF_AUDIT
GATE_DECISION
```

The model may propose only:

```text
ROUND_ADVANCE
ROUND_REVISE
SESSION_PASS
SESSION_FAIL
MANUAL_REVIEW_REQUIRED
```

Persist `model_gate_proposal` separately from `controller_transition`. The
controller owns transition legality, current packet authority, budgets, proof
status, and lifecycle dispositions. `BUDGET_EXHAUSTED`, `CANCELLED`,
`PROOF_FAILED`, `TRANSPORT_FAILED`, and `RUNTIME_FAILED` are controller facts,
not model choices.

### Round authority

- `ROUND_ADVANCE`: the replay-proven derived Packet V8 becomes current
  authoring authority.
- `ROUND_REVISE`: the preceding round's base Packet V8 remains current
  authority; the candidate and derived packet remain historical evidence.
- Every override is validated against the explicitly current packet.
- Earlier packets never become silent alternative bases.

### No-op

`{}` remains a valid sparse override and exact-base replay. It is ineligible as
the intended automated experiment result and receives one correction turn as
`UNINTENDED_NO_EFFECT` without changing validator semantics.

### Defaults and budgets

```text
model: gpt-5.6
reasoning effort: high
auto-promote proven candidate: true
maximum proven rounds: 2
maximum model responses: 16
maximum cumulative input tokens: 2,000,000
maximum cumulative output tokens: 160,000
maximum output tokens per response: 24,000
model response timeout: 600 seconds
```

### Shared engine timeout

One resolver owns manual and automated proof timeout:

```text
ceil(clamp(90, (captured_last_render_ms / 1000) * 2 + 30, 600))
```

Missing or invalid timing uses the current conservative default. Receipts
record inputs, resolved timeout, and outcome.

### Manifest-driven transport

Load Packet V8 through the validated handoff loader and follow
`drag_all_attachments` in manifest order. Validate mandatory roles, manifest
hash, and each non-manifest file's role, hash, and size. Send
`web_discussion_derivative` as vision input and remaining resources as file
inputs. Record provider file IDs and explicit optional absences. Transport must
not own a hard-coded file count or packet-membership policy.

### Proof image

`state_override_proof.py` owns `materialization/candidate-display.png` and its
decoded-RGBA equality proof against the engine BMP. Promotion copies those exact
verified PNG bytes. It must not add another BMP decoder, orientation path,
alpha conversion, or PNG writer.

### Cancellation and recovery

- Cancellation before API dispatch closes cleanly.
- Cancellation after dispatch stops local waiting and controller progression.
- Uncertain remote completion terminates at `MANUAL_REVIEW_REQUIRED`; never
  resend or silently continue that turn.
- A durably captured response may resume without another API call.
- `events.ndjson` is append-only orchestration history.
- `active-turn.json` is an atomically replaced projection derived from events.
- Packet, state, override, proof, frame, runtime, and finding artifacts remain
  domain authority.

### Credentials

Credential precedence is `OPENAI_API_KEY`, then Windows Credential Manager
target `openai/api_key`. Add `Set OpenAI API Key`. Secrets never enter config,
logs, retained requests, transcripts, receipts, packets, or Git.

## Slice Contracts

### Slice 0 - Baseline and authority trace

- Preserve the seven A-G results; Fixture F remains the timeout witness.
- Preserve scanner source identity, native test receipt, and `NOT_APPLICABLE`
  verdict under `.local/`.
- Trace manual UI/CLI actions through packet, override, timeout, proof,
  proof-image, finding-promotion, packet-refresh, review, and launch owners.
- Record only multiplicity that could cause automation to add another semantic
  owner.
- Close with this plan, focused checks, full suite, hostile review, commit,
  push, and clean tree.

### Slice 1 - Timeout, protocol, and run-store foundation

- Centralize adaptive timeout and migrate every proof caller.
- Implement protocol states, gate vocabulary, controller dispositions,
  rebinding, budgets, events, active projection, and recovery.
- Prove no-op outcome classification without changing base replay.

### Slice 2 - OpenAI transport

- Implement manifest-driven Responses API transport, stored response
  continuation, vision input, sanitized evidence, credentials, cancellation,
  and provider failure classification.
- Mock provider behavior; make no paid live request in this slice.

### Slice 3 - Controller and derived-finding promotion

- Select one observable authorized experiment, lock a prediction, request and
  validate one override, and allow one correction turn.
- Reuse shared proof and proof-image owners.
- Promote through the canonical finding and Packet V8 services.
- Apply exact advance/revise rebinding and stop after at most two proven rounds.
- Never record automation promotion as user acceptance.

### Slice 4 - Thin UI entry

Add credential, run, cancel, auto-promote, state, authority, budget, result,
disposition, and open-result-folder controls without redesigning or weakening
the manual workflow. Tk mutates widgets; workers own API and runtime processes.

### Slice 5 - Qualification and review hold

- Run deterministic two-round, rebinding, no-op, malformed output, authority,
  timeout, cancellation, ambiguity, tampering, recovery, promotion, and
  proof-image tests.
- Exercise Fixture F through the real adaptive-timeout route and Fixture G as
  the conversational milestone.
- Repeat the source-grounded authority trace and prove one owner for validator,
  timeout, proof, proof image, packet, and promotion semantics.
- Run at most one capped live `gpt-5.6` high-reasoning session after a credential
  is available. Otherwise stop at the explicit credential/manual gate.
- Push a ready PR and stop at `V8_AUTOMATED_ROUTE_POC_READY_FOR_REVIEW`.

## Validation and Closure

Every slice runs focused tests, then:

```powershell
$env:PYTHONPATH = (Resolve-Path .\src).Path
py -3.14 -m unittest discover -s tests
git diff --check
```

Every slice also exercises its affected workflow, performs hostile review,
commits, pushes, and proves a clean tree before continuing.

Final acceptance-ready wording:

```text
Packet V8 automated-route POC implementation complete.
Manual and automated routes converge on the recorded canonical semantic owners.
Packet transport is manifest-driven, proof-image publication retains one owner,
and round authority is explicitly rebound.
The Responsibility-Compression Scanner remains correctly classified as
NOT_APPLICABLE; no synthetic adapter or scanner authority was introduced.
Repository clean at <commit>, branch pushed, and PR ready.
User review of the automated session workflow is the next approved boundary.
No further product mutation or merge is authorized.
```
