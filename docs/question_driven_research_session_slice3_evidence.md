# Question-Driven Research Session — Slice 3 Evidence

## Outcome

Slice 3 completes the provider-independent research transaction around the
Slice 2 experiment controller:

```text
fresh planner context
-> canonical local experiment
-> fresh review context
-> audience-neutral synthesis
-> deterministic Working Session report
-> optional bounded communication render
```

Every provider stage is dispatched with `previous_response_id = null`.
Conversation continuity is represented by immutable controller artifacts, not
an ever-growing provider history.

## Cost authority

`ResearchCostController` owns the stage ceilings locked in the campaign plan:

```text
planner       200,000 input / 8,000 output
review        200,000 input / 8,000 output
correction    200,000 input / 4,000 output
synthesis     100,000 input / 12,000 output
communication 50,000 input / 6,000 output
```

The review and synthesis ceilings were raised by the bounded live-golden
hardening recorded in `question_driven_research_session_live_golden.md`: the
original 4,000-token review and 8,000-token synthesis ceilings each produced a
preserved incomplete provider response. The current plan explicitly adopts the
proved 8,000/12,000 values.

For each dispatch it distinguishes:

1. exact next-request input-token count and conservative call estimate;
2. hard run budget;
3. mandatory future-stage reserves;
4. conservative adaptive ceiling from all remaining stage caps.

The exact count is never called an exact whole-run cost. A planner that may
execute evidence reserves review, synthesis, selected communication, and the
one correction while still available. Terminal non-executable planning paths
release experiment reserves because synthesis is authorized independently.

Under the tracked 2026-08-03 Luna standard/no-cache pricing policy, the local
ceiling calculation currently reports:

```text
one attempt + correction + synthesis:                    $0.1688
one attempt + correction + synthesis + communication:    $0.1860
two attempts + correction + synthesis:                    $0.2632
two attempts + correction + synthesis + communication:   $0.2804
```

These are policy-derived safety ceilings, not predicted invoices. Provider
billing remains authoritative and the Slice 5 live gate must revalidate the
pricing policy.

## Review and evidence contexts

The fresh review context contains:

- the sealed brief and exact current Packet binding;
- the Packet-derived active Color Pipeline chain;
- exact locked round plan and execution reference;
- proof receipt plus candidate PNG for a single override; or
- compact sweep review, evidence, and contact sheet for a sweep.

The fresh synthesis context contains compact run history, packet lineage,
current research-base disposition, active pipeline context, the strict record
contract, and a closed inventory of evidence references.

Evidence references are rooted and hash-bound:

```text
artifact_role
artifact_root
root_identity
relative_path
sha256
proof_id / sweep_id / member_index when applicable
```

Resolution rejects absolute paths, traversal, root escape, stale root identity,
missing files, and hash mismatch. Multiple proof or sweep roots are
distinguished by their exact root identities.

## Scientific and communication records

The audience-neutral scientific record separates established, inferred,
contradicted, and unresolved claims. Every claim and experiment summary
requires resolved evidence. Requested/canonical/emitted values must match an
existing proof receipt. A canonical value can be marked available only when an
existing receipt explicitly supplies it; otherwise status is `unavailable`.

Invalid or ungrounded synthesis receives no provider retry. The deterministic
fallback is:

```text
scientific_conclusion: NO_SCIENTIFIC_CONCLUSION
controller_disposition: MANUAL_REVIEW_REQUIRED
scientific claims: none
```

The Working Session report is deterministic and includes claims, experiments,
requested/canonical/emitted values, unresolved questions, the best next
experiment, and the science-record identity.

The optional Adult Beginner / Carl Sagan / Concept First report is a fresh call
over the sealed scientific record only. Stable claim-ID coverage is validated.
Failure does not invalidate the science or Working Session report; when that
profile is the selected deliverable, it closes at `MANUAL_REVIEW_REQUIRED`.

## Focused and full validation

Focused Slice 3 and adjacent regression court:

```text
tests.test_research_runner
tests.test_research_results
tests.test_research_context
tests.test_scientific_record
tests.test_research_provider
tests.test_research_cost
tests.test_research_session
tests.test_research_protocol
tests.test_openai_transport

53 passed
```

Complete Python 3.14 suite before documentation closeout:

```text
274 passed
```

## Real offline canonical workflow

A zero-provider simulation drove the complete blocking runner over the actual
published runtime and the Slice 1 epsilon Packet V8. The local experiment
changed only `params.epsilon` to `2e-6`; the existing proof owner materialized
and replayed it. Deterministic fake stage responses then exercised fresh review
and synthesis parsing without network traffic.

```text
run:
C:\code\cuda-fractal-engine-state-tool\.local\slice3-question-research\question-runs\slice3-14c0b5e925f34e75967c1157c8bdef5f

provider stages: planner -> review -> synthesis
attempts consumed: 1
controller disposition: COMPLETED
scientific conclusion: ANSWER_PARTIAL
scientific record SHA-256: 76254f35d43700205f690c83e84a6b3cfb7ee81ceb9f7a90f0c65a3356ce2fad
working report SHA-256: 9ae4cd470d0b8db447e165d5eaa387db8b75cfc4a275f890f9efa469102a76b8
proof ID: recorded in the run execution reference
human acceptance: false
```

The working report distinguishes requested `2e-6`, unavailable canonical
value, and engine-emitted `1.9999999949504854e-6`. It does not infer a complete
proportional law from one comparison.

## Hostile review

- Fresh provider contexts prevent prior Packet V8 authorities from silently
  accumulating across review and synthesis.
- Exact transport resources remain manifest/hash checked; a fresh non-Packet
  stage requires at least one exact additional resource.
- The research dispatcher cannot bypass count-before-generation.
- The controller cannot deliberately begin an experiment without reserving its
  mandatory review and synthesis calls.
- Provisional planner answers are passed to synthesis as proposed text and are
  explicitly excluded from the evidence inventory.
- Scientific claims cannot cite free-text paths or missing files.
- The communication renderer cannot rewrite the science record.
- Provider-owned files are closed through the existing transport cleanup owner.
- No paid provider count or generation request was made.

No open Slice 3 defect blocks the thin Research Question UI.
