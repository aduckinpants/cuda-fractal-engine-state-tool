# Packet V8 Automated Route — Live Qualification and Hardening

## Scope and code identity

This report records the first failed live run, the bounded hardening response,
and the single authorized replacement run. The replacement ran from clean
commit:

```text
859c95c6f3a50f79538a4d98985d0c83699b89e6
```

The engine repository and published runtime were not changed.

## First live run: orchestration-store failure

Run directory:

```text
D:\salt-fractal\cuda-fractal-engine-state-tool\automated-runs\v8-auto-f7db887a-317a-4c37-a814-213c8d347896
```

The run completed five provider turns, selected one valid Color Pipeline
change, and passed sparse-override validation. The engine proof was never
called. Event 13 was durably appended before Windows denied the atomic
replacement of `active-turn.json`; the generic exception path then mislabeled
the stop as `RUNTIME_FAILED`. All six run-owned provider files were deleted.

Usage before the stop:

```text
responses: 5
input tokens: 855,767
output tokens: 11,302
proven rounds: 0
```

## Implemented hardening

- `events.ndjson` remains append-only orchestration authority.
- `active-turn.json` remains a derived current-state projection.
- One in-process lock coordinates UI readers with controller writers.
- Windows sharing violations receive bounded retry; no fallback or indefinite
  wait is introduced.
- Persistent run-store writes terminate as `RUN_STORE_FAILED` with a precise
  code and event-append status.
- The automation panel reads a field-allowlisted event view at 250 ms and labels
  its durable-folder action `Open Run Folder`.
- Each round uses one combined authoring response and one combined review/gate
  response. One correction response remains available only for an ineligible
  override.
- The response chain resets at round boundaries and the controller-selected
  Packet V8 is reattached as sole current authority.
- Evidence records requested/resolved model, total/cached/uncached input,
  output, provider latency, and cumulative totals. Dollar cost is not inferred.

Focused automation, run-store, transport, protocol, and UI tests passed 45
checks. The full Python 3.14 suite passed 154 tests before the paid run.

## Single replacement live run

Run directory:

```text
D:\salt-fractal\cuda-fractal-engine-state-tool\automated-runs\v8-auto-hardening-306212e1-9d7f-44f2-80fe-c914efbdc627
```

Initial authority was the same immutable packet used by the first run:

```text
packet ID: 5e0684b4-77ce-4ada-ae71-e76065fcb746
manifest SHA-256: 6afeffc7377167ecf4003614e399ee61498bcfbdc1b5eb7abe696c0ef92f29a6
finding ID: 3cec9a08d9f9132e7bafc812085d23cc95e69b970d2047eb0ad14aca5a797aeb
```

### Round 1

One combined authoring response selected a color-only change:

```text
palette.seed_phase: 0 -> 0.25
```

The override changed one authorized leaf. Materialization and action-free
replay both completed, the requested value survived, and encoded plus decoded
RGBA frames matched exactly. The verified proof-owned PNG was promoted through
the canonical importer with `human_acceptance: false`, and a fresh Packet V8
was generated.

```text
proof ID: b0fd9099-8864-4be7-b502-b2ba3ef385f4
proof receipt SHA-256: 51db5a9e46a3bbad8ab8711b16808a568985ea4e14e2c566836b72c3a2ede8da
derived finding ID: ad3618a3e02f28ddcb9604fe52034cea3a2bd20dec9778e479c58e6496a53bc3
derived packet ID: 71a9eb28-7d9b-47d0-87b4-ff298d2a7183
derived manifest SHA-256: e97d4b6324c8789550f56a7d9953673f7708f7be4517f8864ecf0c6343f649a8
model gate proposal: ROUND_ADVANCE
```

### Round 2

The new round began a fresh provider conversation against the exact derived
packet. The model proposed:

```text
params.max_iter: 1167 -> 1800
```

Local validation accepted the leaf as state-authorable. The engine then emitted
`1167`, so proof rejected the candidate rather than silently accepting an
ineffective experiment. No derived finding was promoted from this round.

```text
proof ID: 5c53ffd0-b84f-44fe-9a07-a7266ec965d1
proof receipt SHA-256: e0564dec79b403a93666dd5f8fb3c1505106d316da02eb589f67600d2f599697
controller disposition: PROOF_FAILED
error: Engine reverted requested value at params.max_iter: requested 1800, emitted 1167
```

This is an authoritative domain rejection, not a controller, run-store, or CUDA
process failure. The derived packet had `view.auto_max_iter: true`; whether the
agent-facing authority should more explicitly warn about that interaction is a
future review question, not an unapproved compatibility rule added here.

### Usage and lifecycle

```text
requested model: gpt-5.6
resolved model: gpt-5.6-sol
responses: 3
input tokens: 654,530
cached input tokens: 164,109
uncached input tokens: 490,421
output tokens: 4,993
cumulative provider latency: 88.680 seconds
proven rounds: 1
terminal disposition: PROOF_FAILED
provider cleanup complete: true
```

The replacement used about 23.5 percent fewer total input tokens than the first
run while completing a replay-proven round, canonical promotion, derived packet
refresh, model review/gate, and a second authoritative proof attempt.

Run-store identities:

```text
events.ndjson SHA-256: a7bf0d58f88fb368c8d41c41662b698a4593636861c6b9998d4fbaeb86d843f7
active-turn.json SHA-256: a22933735d7a5602f1e4851319aa4582f9cf48496ed4ee3dc690615eea30d791
last event sequence: 31
```

The local console monitor used only for this qualification could not print the
Unicode transition arrow under the active Windows code page and stopped its own
display after event 2. It did not affect the controller or run store. The Tk
event widget is Unicode-native, while deterministic tests separately exercise
concurrent reads across 30 writes.

## Qualification verdict

```text
run-store race repair: PASS
failure taxonomy: PASS
two-response round protocol: PASS
model/usage telemetry: PASS
round-1 validation and replay proof: PASS
canonical non-human promotion and Packet V8 refresh: PASS
round-boundary provider-chain reset: PASS
engine contradiction rejection: PASS
provider cleanup: PASS
terminal all-round session pass: NOT REACHED
```

The POC is acceptance-ready for user review. The replacement run proves the
hardening and the complete first-round route; it also preserves an honest
second-round engine rejection for later protocol evaluation. No additional
paid run, product mutation, merge, or Packet V9 model-ablation work is
authorized by this report.
