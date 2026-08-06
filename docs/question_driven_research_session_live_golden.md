# Question-Driven Research Session — Live Golden Evidence

## Attempt 1 — strict protocol failure before execution

The user authorized automated testing under a `$0.30` hard cap. Runtime drift
was detected before spending, so the exact Packet V8 was rebuilt against the
currently active published executable and the five-member epsilon replay court
was repeated successfully.

```text
packet ID: 89e01069-e42e-48bd-a370-30c59635060d
manifest SHA-256: 10dd1c7f1b2534f93260d94d62ecc10bd97bdbb6bb38d85304acb85522d2dc9b
local sweep ID: 707230e3-8bdb-4555-bdc2-6295c25322bd
local sweep: 5 / 5 REPLAY_PROVEN
```

Count-only authorized the exact 170,983-token first planner request:

```text
exact first-call estimate: $0.0437966
required with reserves:    $0.1629966
adaptive ceiling:          $0.2632
hard budget:               $0.30
```

Durable run:

```text
D:\salt-fractal\cuda-fractal-engine-state-tool\question-runs\question-research-93da8506-30c6-434a-b989-b8541fea08e1
```

The provider selected a coherent logarithmic epsilon sweep while preserving
the camera, dynamics, and captured active Color Pipeline. The semantic plan
and bare Scalar Bracket Sweep V1 payload were valid, but the first response
omitted the required `RESEARCH_ACTION:` line. The one bounded correction then
returned `RESEARCH_ACTION SCALAR_SWEEP`, again omitting the mandatory colon.
The strict parser rejected both responses.

```text
planner actual cost:       $0.0386738
correction actual cost:    $0.0363198
calculated total:          $0.0749936
experiment attempts used:  0
local experiments run:     0
scientific conclusion:     NO_SCIENTIFIC_CONCLUSION
controller disposition:    MANUAL_REVIEW_REQUIRED
provider retry authorized: false
```

The initial shell harness also exposed a local crash window after the provider
response was durably written but before controller transition. No provider
turn was silently resent. Provider-file cleanup completed with no remaining
file IDs.

## Bounded hardening response

The resulting hardening slice keeps the protocol strict and does not normalize
malformed model output:

- require the literal colon-bearing first line in the planner prompt;
- persist the response text and turn bindings directly beside the raw response;
- recover a completed durable response without provider redispatch;
- treat an exact repeat of immutable evidence bytes as restart-idempotent while
  continuing to reject any changed bytes.

The next paid boundary is one fresh count-gated rerun of the same golden brief
after focused and full-suite qualification of this hardening checkpoint.

## Attempt 2 — planner and sweep pass; review incomplete

The hardened planner prompt passed without a correction. Luna selected a
three-member epsilon bracket, and the controller executed all members through
the canonical Scalar Bracket Sweep V1 and action-free replay path.

```text
run:
D:\salt-fractal\cuda-fractal-engine-state-tool\question-runs\question-research-5a2e9f01-6c64-4779-9f15-f56d856e6982

planner actual:         $0.0379758
experiment attempts:    1
sweep ID:               f1750d5e-1707-4797-8ea0-bc78e0397ed7
sweep disposition:      COMPLETE
members:                3 / 3 REPLAY_PROVEN
controller boundary:    REVIEW_READY
scientific conclusion:  NO_SCIENTIFIC_CONCLUSION
```

The provider returned an `incomplete` review response. The transport correctly
did not treat it as a review gate and did not retry, but it exposed two further
bounded pressure points:

- the non-completed provider object was rejected before its exact status and
  `incomplete_details` were written to durable evidence;
- the 4,000-token review output ceiling was too narrow for Luna/high at this
  context size.

The review call was authorized at a conservative `$0.0411112`; the pre-existing
transport did not preserve enough usage evidence to calculate its actual billed
cost. Even treating the authorized maximum as spent, the attempt remained well
below the `$0.30` hard cap.

The next hardening checkpoint preserves incomplete response evidence before
raising and raises only the review output ceiling to 8,000 tokens. It does not
authorize a provider retry within Attempt 2. A fresh count-gated run is required.

## Attempt 3 — full sweep and review content pass; review wire shape fails

The 8,000-token review allowance eliminated the incomplete response. The
planner again passed without correction, and all five sweep members were
replay-proven.

```text
run:
D:\salt-fractal\cuda-fractal-engine-state-tool\question-runs\question-research-d7bca1d4-d0ec-419a-87c8-70ba6e5902f4

planner actual:         $0.0368214
review actual:          $0.0425990
calculated total:       $0.0794204
experiment attempts:    1
sweep ID:               47c37043-605b-462c-9b03-ba5350b19345
sweep disposition:      COMPLETE
members:                5 / 5 REPLAY_PROVEN
controller boundary:    REVIEW_READY
scientific conclusion:  NO_SCIENTIFIC_CONCLUSION
```

The review contained a useful prediction comparison and correctly described
the five proof identities, but returned a JSON object with
`"RESEARCH_GATE": "HOLD"`. The public protocol requires a colon-bearing plain
text header and one of four exact legal gate values. The controller did not
infer a gate from this malformed response and did not continue to synthesis.

The next bounded hardening change makes the review wire contract literal in
the fresh-context prompt: exact header, legal values, ordered field labels,
selection syntax, and an explicit prohibition on JSON and code fences. The
strict parser remains unchanged.

## Attempt 4 — legal review gate; second-round TPM refusal

The literal review contract passed. The first round again produced five
replay-proven members, and the fresh review legally selected
`CONTINUE_RETAIN_BASE`: the simple monotone-radius prediction was not supported,
so a measured follow-up should retain the exact base rather than promote a
sweep member.

```text
run:
D:\salt-fractal\cuda-fractal-engine-state-tool\question-runs\question-research-272db7b3-c2b9-4ac8-80b8-686a26f811f6

planner actual:         $0.0373686
review actual:          $0.0396350
calculated total:       $0.0770036
experiment attempts:    1
sweep ID:               c2e8cc02-8d9f-40ce-8638-dcbbe817a3e7
sweep disposition:      COMPLETE
members:                5 / 5 REPLAY_PROVEN
review gate:            CONTINUE_RETAIN_BASE
controller boundary:    PLANNING round 2
```

The immediate 170,702-token second planner dispatch was refused by the
organization's 200,000 tokens-per-minute limit because the preceding
184,537-token review still occupied the active window. No planner-02 response
was generated and no retry was attempted.

The smallest truthful correction is pre-dispatch pacing in the shared research
provider dispatcher. A completed provider response starts a conservative
65-second generation spacing window. Any following provider call waits before
dispatch, remains cancellable during the wait, and records the pacing event.
This is not a retry policy and does not resend failed or ambiguous turns.
