# V9 Luna/High Hard-Calibrator Result

Date: 2026-08-03

Status: technically complete; automatic qualification did not pass; independent
user review pending

## Exact run

```text
case SHA-256:
b191c64149e434612e710de626edd88f938eddefd6879ca885b37830a08e202a
model profile SHA-256:
dbf174b6e03c074b26588e606e6ddb4a27eb5d36bcbb70184863116e39e268b7
model: gpt-5.6-luna
reasoning: high
disclosure: assisted
packet: 6e9ca581-fcb3-45aa-8aa9-5d03997f3569
cell ceiling: $0.10
```

The first authorized attempt remains preserved as a provider-credit failure.
After the user replaced the stored key and explicitly authorized one retry, the
unchanged cell ran exactly once with no correction turn and no automatic retry.

```text
run:
D:\salt-fractal\cuda-fractal-engine-state-tool\automated-runs\
v9-luna-high-hard-retry-7e12cfc5-d419-462a-bcfc-8cd87eb91868

author: 176,676 input / 3,999 output
review: 175,993 input / 3,187 output
total input: 352,669
total output: 7,186
cached input: 0
cache writes: 0
calculated cost: $0.079157
remaining cell budget: $0.020843
```

Both requests stayed below the 200,000-token hard gate and below the long-context
threshold. Provider-file cleanup completed with no failures or remaining file
IDs.

## Authoring behavior

Luna distinguished state-authorable, analysis-only, and unavailable experiments
and deliberately chose a color-only intervention that could not move the high-
zoom subject:

```text
heatmap palette.cycle_scale: 1.0 -> 1.5
```

It returned one complete contract-ordered pipeline array. Validation reported
one authorized changed leaf and no correction turn. Its prediction separated
geometry from palette behavior, preserved the exact camera, identified the
observation channel, stated uncertainty, and supplied a falsification condition.

The ordinary engine path materialized the candidate and action-free replay
proved matching state and frame evidence:

```text
proof ID: 168fe17b-df5d-4bd8-b5aa-2e1a777482d6
proof status: replay_proven
derived finding:
8daf2ed9e748db6a4ed7783c3e91b8aa4ff0c9aaeb9ddb3002975cd6f9eade3a
derived packet: 74812874-1d81-4e2e-be75-f931c36cccf8
```

## Review behavior and missing evidence

The fresh review context correctly avoided carrying the original 176k-token
conversation. It contained the derived Packet V8, derived enrichment, and exact
controller review ledger. It did not contain a clean base/result image pair or
a quantitative pixel comparison.

Luna therefore concluded that state-level alignment passed but visible palette
redistribution was not demonstrated by the evidence it received, and proposed:

```text
GATE_DECISION: MANUAL_REVIEW_REQUIRED
```

This is a legal and appropriately conservative gate, not a malformed response.
It also reveals that the economical fresh-review contract omits evidence needed
to decide the locked visual prediction.

Local read-only comparison of the authoritative full-resolution source frame
and promoted result confirms that the intervention was strongly visible:

```text
dimensions: 4096 x 2559 for both frames
base frame SHA-256:
c341c605cc093bacdc8423c4bfbab275c9ad97746d0e8bb6d2401bf3f5109ab7
result frame SHA-256:
41a868e298ed156e89bcef3bb6297bd889dede77cf2f872b25361e3da9c9eb9c
changed pixels: 10,481,619 / 10,481,664
changed fraction: 0.9999957068
mean absolute RGB difference: 66.2919, 48.1168, 50.9997
```

The changed-state receipt limits the mutation to the one palette control, while
visual inspection shows the same geometry with substantially redistributed
color bands. These local diagnostics are post-run review evidence; they were not
available to Luna and must not be retroactively attributed to its review turn.

## Automatic-gate defect

The automatic receipt also failed `disclosure_binding`. The author disclosure
correctly binds the case's initial analysis:

```text
4db4181f7b1e8108a0c571daea99d4750f1bce5587ff5fd2f230fea3aabd27e6
```

The review disclosure correctly binds a new analysis of the derived state and
frame:

```text
518cfb9f54b2346370c055cdad16cc12191372be1781ae8a888c457083e1c04c
```

`evaluate_automatic_gates` currently requires every disclosure event to equal
the initial case analysis ID. That condition cannot truthfully pass for a
changed derived finding. The gate must instead verify:

```text
author disclosure -> exact initial packet and expected initial analysis
review disclosure -> exact derived packet and its receipted derived analysis
```

The immutable gate receipt remains unmodified and records the false result.

## Durable hashes

| Artifact | SHA-256 |
| --- | --- |
| `active-turn.json` | `b71e43ace73e4d4b11e73902684142c15ca25fdbd6371b8f1c74df7684afab92` |
| `events.ndjson` | `6fdada08433ac0e1ee6186c5308927338d9d4bedf67a9ac4ec41de3da7490ef1` |
| `qualification/automatic-gates.json` | `93de6e96603ecd0d1dc9c47a9eb57b6c5722d23e3223514d2377045a5967dfdf` |
| `rounds/round-01/context/round-review-ledger.json` | `eee81d84ee02e691f52f8f45b39fd602de5d232cf3466699d7509a7af3cea17e` |
| `rounds/round-01/context/author-enrichment-disclosure.json` | `68f4205e79b912c1e5cf7ceb388443848340f84b2acd0c9bb7f26a26ec3224df` |
| `rounds/round-01/context/review-enrichment-disclosure.json` | `d8fdcbd4a28b48524b07891c23e028393e9ac40a919141434d95ba3f65058dce` |
| `transport/turn-0001/response.json` | `132c3584f0cb3850a539f0ab6e180307e936e177a57d4a7175a50c07004ad499` |
| `transport/turn-0002/response.json` | `089dad6a7500b424622f6dd7bbef7c2124ddeda00860678ba878be13cf63c851` |
| `transport/provider-file-cleanup.json` | `c9f647df33b401bb16c3094fb5f3e1c952bd373de398ac08f90f8c6553e8dc1b` |

## Qualification disposition

The cell proves that Luna/high can perform the bounded authoring task strongly,
the controller can complete the full economical route for less than `$0.08`,
and replay/promotion/rebinding work. It does not satisfy the current automatic
qualification because:

1. the review context lacks decisive paired visual evidence;
2. Luna consequently chose `MANUAL_REVIEW_REQUIRED`, not `SESSION_PASS`;
3. the disclosure gate encodes an impossible same-analysis-ID condition.

Independent user review is the next boundary. No further provider call or
qualification retry is authorized. Any remediation should be a new bounded
slice that adds the smallest comparison evidence needed by fresh review and
corrects disclosure binding without restoring duplicated packet history.
