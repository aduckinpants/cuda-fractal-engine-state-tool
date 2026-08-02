# Packet V8 Automated Route POC

## Status

- Campaign: approved implementation.
- Starting branch: `codex/v8-automated-route-poc`.
- Exact starting commit: `3f42290abb734ae17e8ae95f2c2c9f111d631fb4`.
- Baseline: clean merged `main`, 100 Python 3.14 tests passing.
- Current owner: `qualification-and-review-hold`.

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
`PROOF_FAILED`, `TRANSPORT_FAILED`, `RUN_STORE_FAILED`, and `RUNTIME_FAILED` are
controller facts, not model choices.

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
maximum model responses: 6
maximum cumulative input tokens: 2,000,000
maximum cumulative output tokens: 160,000
maximum output tokens per response: 24,000
model response timeout: 600 seconds
```

Each round uses two primary provider responses:

```text
combined observation + exploration + selection + prediction + hostile review + override
-> local validation and engine proof
-> combined result comparison + self-audit + gate proposal
```

One correction response is allowed only when the combined authoring response
does not yield an eligible override. The provider chain resets at each round
boundary; the exact controller-selected Packet V8 is reattached with a compact
authority handoff. Within a round, the review response continues from the
authoring response.

Usage evidence records requested and resolved model identities, total, cached,
and uncached input tokens, output tokens, provider latency, and cumulative
totals. It does not infer dollar cost; the provider billing dashboard remains
the cost authority.

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
- In-process readers and writers share one projection lock. Windows sharing
  violations receive bounded retry; persistent projection failure is
  `RUN_STORE_FAILED`, never a CUDA runtime failure.
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

## Execution Ledger

### Slice 0 - complete

- Packet V8 merged as PR #7 at
  `3f42290abb734ae17e8ae95f2c2c9f111d631fb4`.
- Seven A-G results are tracked; Fixture F remains the timeout witness.
- Scanner focused suite: 12 passed; applicability: `NOT_APPLICABLE`.
- Baseline authority trace records canonical owners and the bounded missing
  derived-finding promotion seam.
- Baseline and post-merge state-tool suites: 100 passed.
- Continuation: `continue_to=timeout-and-contract-foundation`.

### Slice 1 - complete

- One shared timeout resolver serves UI and CLI proof callers.
- Fixture F's exact Packet V8 resolves `203542.34375 ms` to `438 seconds`.
- Proof receipt V5 records the complete timeout resolution.
- Protocol foundation locks states, gate proposals, controller dispositions,
  round rebinding, no-op outcome classification, and budgets.
- Run store locks append-only `events.ndjson`, derived `active-turn.json`, and
  fail-closed recovery.
- The real slow Fixture F engine proof remains intentionally assigned to Slice
  5; Slice 1 proves its exact immutable packet resolves the correct policy.
- Continuation: `continue_to=openai-transport-and-run-store`.

### Slice 2 - complete

- The retry-free OpenAI SDK adapter targets `gpt-5.6` with high reasoning,
  `store=true`, explicit stable instructions on every turn, and
  `previous_response_id` continuation.
- Packet V8 transport follows the validated manifest order, submits the exact
  already-hashed snapshot bytes, uses the bounded web PNG as vision input, and
  uses owned `user_data` file uploads for the remaining resources.
- Provider files remain session-owned while stored-response continuation is
  possible because the public API contract does not guarantee that deleting an
  input file preserves later continuation. Definite pre-dispatch failures clean
  their turn; ambiguous post-dispatch outcomes retain ownership for recovery;
  session close deletes every remaining owned file and fails visibly on cleanup
  debt.
- `OPENAI_API_KEY` takes precedence over the Windows Credential Manager target
  `openai/api_key`; neither value is retained in evidence.
- Request/response evidence is sanitized and atomic. The retained request
  replaces the base64 image body with its packet-resource SHA-256 reference.
- Local cancellation before dispatch is clean. Cancellation after dispatch
  never resends; a captured response is retained for manual disposition.
- Official contract references:
  [conversation state](https://developers.openai.com/api/docs/guides/conversation-state),
  [image inputs](https://developers.openai.com/api/docs/guides/images-vision),
  and [GPT-5.6 guidance](https://developers.openai.com/api/docs/guides/model-guidance?model=gpt-5.6).
- No credential was read and no live or paid request was made in this slice.
- Continuation: `continue_to=automated-controller-and-promotion`.

### Slice 3 - complete

- One orchestration controller owns stage legality, response/token/proven-round
  budgets, one override correction, model gate proposals, controller
  dispositions, and exact `ROUND_ADVANCE` / `ROUND_REVISE` rebinding.
- The model gate and controller transition are retained as separate events.
  `SESSION_PASS` is not recorded as human candidate acceptance.
- Override extraction requires exactly one fenced `json` block. It delegates
  syntax and sparse-state semantics to `parse_state_override` and
  `materialize_state_override`; `{}` remains a valid base replay but receives
  one `UNINTENDED_NO_EFFECT` correction as an automated experiment result.
- The production service factory binds the controller to the active
  `JobContext`, `execute_state_override_proof`, `build_agent_bundle`, and the
  single derived-finding promoter. It does not add another runtime process or
  packet implementation.
- The derived-finding promoter rechecks packet, binding, receipt, candidate
  state, and proof-owned PNG hashes; copies those exact bytes; records explicit
  non-human lineage; then delegates publication to `SourceCaptureImporter`.
- A retained real replay-proven proof was promoted in an ignored disposable
  workspace, rebuilt through the published runtime, and accepted by the
  manifest transport as seven ordered Packet V8 resources. The promoted frame
  SHA-256 exactly matched `materialization/candidate-display.png`. No engine
  render and no API request occurred.
- A first disposable run rooted too deeply under `.local/campaigns/...` failed
  clearly when the runtime could not open its staged export path. The retry used
  a short ignored `.local/p/...` root. Production promotion imports into the
  configured durable workspace rather than nesting a second workspace beneath
  the run directory.
- Shared-worker cancellation is classified as `CANCELLED` and cannot proceed
  into promotion or packet refresh.
- Continuation: `continue_to=thin-ui-entry`.

### Slice 4 - complete

- The accepted two-column manual workflow retains its original hierarchy. A
  single compact `Automated Session...` entry opens a dedicated child panel;
  automation status no longer compresses the candidate-preview or human-review
  surfaces.
- The panel exposes credential setup, bounded run, per-session cancellation,
  automation-only promotion policy, protocol state, exact current packet
  authority, budgets, controller disposition, and the durable result folder.
- API and engine work run through the existing bounded `AsyncJobRunner`.
  Per-job cancellation stops only the automated session; reset and shutdown
  retain their established broader ownership semantics.
- Manual mutation controls are disabled while automated work owns the current
  packet binding. The controller still records no human acceptance and cannot
  enable the manual launch path by itself.
- Empty-state screenshots were rendered for both the preserved main workflow
  and the dedicated automation panel. Credential absence visibly disables the
  run control, and no credential lookup resulted in a live API request.
- Focused automation/UI checks: 34 passed. Full Python 3.14 suite: 146 passed.
- Continuation: `continue_to=qualification-and-review-hold`.

### Slice 5 - acceptance-ready review hold

- Deterministic qualification covers two-round advance/revise authority,
  no-op correction, malformed output, definite and ambiguous provider failure,
  cumulative budgets, cancellation, recovery, authority tampering, exact PNG
  promotion, and canonical service delegation.
- The exact historical Fixture F packet and override passed real engine
  materialization plus action-free replay in 523 seconds total. Both stages
  used the captured-timing-derived 438-second policy, completed normally, and
  produced identical decoded RGBA. Visual review remains pending and launch is
  false.
- Fixture G remains accepted manual conversational evidence. It has not been
  misrepresented as an automated provider session.
- The post-implementation responsibility trace proves one owner for packet,
  validator/merge, timeout, proof/process, proof image, importer, and packet
  refresh semantics. Human acceptance and launch remain independently owned.
- The first capped live run reached a valid one-leaf Color Pipeline override
  after five provider responses, then stopped before proof because a 25 ms UI
  reader raced the atomic `active-turn.json` replacement on Windows. The event
  append succeeded; the CUDA engine was never launched. Provider-file cleanup
  succeeded. The former `RUNTIME_FAILED` label was therefore inaccurate.
- The live run also recorded 855,767 input and 11,302 output tokens before
  proof, motivating the two-primary-response round contract above. V8 remains
  fixed to `gpt-5.6` high; model downgrade/ablation belongs to Packet V9.
- Current hardening adds Windows-safe projection coordination and retry,
  `RUN_STORE_FAILED`, compact live event telemetry, detailed cached/uncached
  usage evidence, and `Open Run Folder` labeling.
- Focused automation and UI tests pass 45 checks; the full Python 3.14 suite
  passes 154 tests.
- The single replacement live run completed one replay-proven Color Pipeline
  round, canonical non-human promotion, derived Packet V8 refresh, and
  `ROUND_ADVANCE`. Its second round stopped honestly at `PROOF_FAILED` when the
  engine emitted `max_iter=1167` after the model requested `1800` under an
  auto-iteration state. Three responses used 654,530 total input tokens, of
  which 164,109 were cached, and 4,993 output tokens. Provider cleanup passed.
- Detailed receipts and hashes are recorded in
  `docs/packet_v8_automated_route_live_qualification.md`.
- Hold: user review is the next approved boundary. No second replacement run,
  merge, Packet V9 ablation, or broader automation is authorized.

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
