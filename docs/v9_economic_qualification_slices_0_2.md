# V9 Economic Qualification — Zero-Provider Preparation

Date: 2026-08-03

Status: Slices 0 through 3 complete; one provider input count was authorized and
completed without generation; response generation remains unauthorized

## Locked authority

The campaign ceiling is `$8.00`. It is a cumulative planning gate, not dispatch
authorization. The first prepared cell is separately capped at `$0.10` under
the conservative two-call Luna/high limits.

```text
state-tool base: df5b9f1fcc2d4ecf20837e90d82fc6aa906c4630
implementation branch: codex/v9-economic-qualification-harness
published runtime SHA-256:
501002f174068641b9a6105e56c277e6a4080bc9dbeb5e672282e77562b96f56
pricing policy: openai-standard-2026-08-03
pricing policy SHA-256:
7934d36c4865098494c52da4001f6c008b92a8f0cce2e261b8bd273ed44c088e
```

The exact fixtures are recorded in
`docs/v9_economic_qualification_fixtures.v1.json`. The hard calibrator is the
Rational Escape critical-seed Packet V8 in assisted mode. Its deterministic
analysis was reopened through the production enrichment service and returned
the already-receipted analysis ID
`4db4181f7b1e8108a0c571daea99d4750f1bce5587ff5fd2f230fea3aabd27e6`
as a cache hit.

The dynamics confirmation deliberately uses the earlier Inertial capture whose
finite-iteration black fuzz motivated the iteration-horizon test, not the later
generic Inertial packet. A fresh immutable Packet V8 was generated locally for
that already-existing capture. No provider was contacted.

The observation confirmation reuses the ten-function ExplainO All Color
Pipeline packet from the accepted manual battery.

## Responsibility trace

The qualification route is only an entry and evaluation layer:

```text
QualificationCaseV1
→ AutomatedSessionController
→ PacketV8ResponsesTransport
→ ordinary sparse-override validator
→ ordinary proof service and timeout owner
→ ordinary proof-owned PNG promotion
→ ordinary derived Packet V8 builder
→ fresh review context and controller gate
→ automatic qualification receipt
```

It introduces no second packet loader, validator, proof launcher, timeout
policy, image converter, promotion path, or human-acceptance owner.

`ModelProfileV1` is local orchestration identity. It is not Packet authority and
does not add a provider `service_tier` field. The profile binds:

```text
model
reasoning effort
tracked standard pricing tier
explicit-no-cache request policy
deterministic profile SHA-256
```

The profile identity is carried in the run manifest, projections, dispatch
estimate, exact-count receipt, request evidence, response evidence, and model
response event. Changing model or effort changes the identity and prevents a
serialized qualification case from reopening as the old cell.

## Offline harness

`RecordedResponsesTransport` exercises the real controller without uploading a
file, counting through the provider, or generating a response. Recorded turns
still enter the controller's pre-dispatch dollar calculation and produce
explicitly marked offline request, count, response, and cleanup evidence.

The focused offline witness completed:

```text
.local/v9-economic-qualification/offline-witness/
witness-6fa92824-80ff-47fc-8077-d08936aee402/workspace/automated-runs/
offline-recorded-controller-witness
```

```text
author response
→ sparse override validation
→ replay-proven proof
→ non-human promotion
→ derived Packet V8 refresh
→ fresh review response
→ SESSION_PASS proposal
→ automatic gate receipt
```

Automatic gates cover terminal controller state, exact packet binding, profile
and resolved-family identity, no-cache behavior, disclosure binding, replay
proof, cell/campaign cost, immutable evidence, and absence of fabricated human
acceptance. The human rubric remains a separate pending artifact owned by the
user.

## Historical Sol/high calibration

The preserved Sol evidence is classified as
`HISTORICAL_BEHAVIORAL_REFERENCE`, not an exact A/B cell. The clearest complete
round is round 1 of:

```text
D:\salt-fractal\cuda-fractal-engine-state-tool\automated-runs\
v8-auto-hardening-306212e1-9d7f-44f2-80fe-c914efbdc627
```

That round selected one authorized observable Color Pipeline change, locked a
prediction, produced a replay-stable candidate, promoted it without human
acceptance, reviewed the derived result, and proposed `ROUND_ADVANCE`. Against
the V1 human rubric it is a usable positive reference:

| Rubric item | Historical disposition | Note |
| --- | --- | --- |
| evidence hierarchy and restraint | PASS | Color-only claim remained downstream of dynamics. |
| executable observable experiment | PASS | One schema-valid palette phase change. |
| exactly one coherent state | PASS | One changed leaf in a complete required pipeline array. |
| falsifiable prediction and uncertainty | PASS | Visible phase change with fixed camera and dynamics. |
| camera and feature continuity | PASS | Color-only edit preserved view and subject. |
| narrative and JSON alignment | PASS | Receipt confirmed the selected leaf. |
| result review against prediction | PASS | Review used the replay-proven derived packet. |
| legal useful gate | PASS | `ROUND_ADVANCE` was legal for the informative result. |
| concise without omitted evidence | PARTIAL | Historical output predates final caps and exact profile receipts. |

Its later second-round `max_iter` rejection remains useful negative evidence,
but is not part of the positive one-round calibrator. Historical runs lack the
new profile, local calculated-cost, and exact fresh-review qualification
receipts, so the new automatic gates must not retroactively report them as an
exact pass.

## Prepared Luna/high cell

The exact case is tracked at
`docs/v9_luna_high_hard_calibrator_case.v1.json`.

```text
case SHA-256:
b191c64149e434612e710de626edd88f938eddefd6879ca885b37830a08e202a
profile SHA-256:
dbf174b6e03c074b26588e606e6ddb4a27eb5d36bcbb70184863116e39e268b7
model: gpt-5.6-luna
reasoning: high
disclosure: assisted
proven rounds: 1
model responses: 2
input cap per response: 200,000
author output cap: 8,000
review output cap: 4,000
cell ceiling: $0.10
campaign ceiling: $8.00
```

The case was reopened against the exact immutable packet and current pricing
policy. Its deterministic identity matched. Slice 3 subsequently uploaded the
exact manifest-declared packet and assisted disclosure resources for one
provider input-token count. No response generation occurred. The provider
returned 176,676 input tokens for the author request, below the 200,000-token
per-response gate. With the 8,000-token output ceiling, its conservative
maximum is `$0.0449352`.

The second review request cannot be counted exactly until an author response,
replay-proven candidate, and refreshed packet exist. Its existing 200,000-input
and 4,000-output hard limits cap it at `$0.0448` under the tracked Luna
short-context rates. Therefore the full one-round cell remains bounded by
`$0.0897352`, leaving `$0.0102648` below the `$0.10` cell ceiling.

The durable count receipt is summarized in
`docs/v9_luna_high_count_only_preflight.md`.

## Hostile review

- A recorded-response pass proves controller wiring, not model quality.
- The `$0.10` bound assumes both requests remain below the existing 200,000
  input-token hard gate; the count-only preflight must verify the real author
  request.
- The assisted annotation adds an image and evidence files. They are retained
  because dropping them would change the calibrator, not optimize it.
- The UI may select a profile, but its dollar default remains zero. Selection
  alone grants no provider authority.
- Two model responses leave no correction-turn budget. A malformed or empty
  author override therefore fails the qualification cell instead of purchasing
  an unplanned repair turn.
- The hard gates never convert model `SESSION_PASS` into human acceptance.
- Historical Sol behavior is not mislabeled as exact current-architecture cost
  evidence.
- The count-only lifecycle has a dedicated immutable qualification receipt; it
  is not a completed automated model session and does not claim a terminal
  model disposition.
- Credential resolution discovered an older Windows Credential Manager username
  still used by the proven local setup. The resolver now checks the current
  username first and the legacy username second; writes remain on the current
  username, while explicit deletion covers both. No secret migration or
  evidence exposure occurs.

## Closure

Slices 0 through 3 are implemented. Exact fixtures, rubric, profile plumbing,
offline controller witness, automatic gates, the Luna/high case manifest, and
the count-only preflight are complete. Provider files were cleaned, no response
generation was dispatched, and the exact bounded cell remains below `$0.10`.

The next planned boundary is Slice 4: one paid Luna/high hard-calibrator cell
using the exact case. It remains blocked on separate explicit authorization for
response generation. No generation authority is implied by the `$8` campaign
ceiling or by the completed count-only call.
