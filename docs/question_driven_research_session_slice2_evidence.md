# Question-Driven Research Session — Slice 2 Evidence

## Outcome

Slice 2 adds the provider-independent planner and experiment controller. It
does not call OpenAI and does not reinterpret engine, state, proof, sweep, or
promotion semantics.

The controller accepts four strict planner outcomes:

```text
ANSWER_READY
SINGLE_OVERRIDE
SCALAR_SWEEP
UNRESOLVED_REPORT
```

Executable responses retain the ordinary sparse override or Scalar Bracket
Sweep V1 JSON payload. A strict surrounding preflight is parsed and sealed as
`round-plan.json`, including the prediction, observation channel,
disconfirmation condition, camera/fixed-state policy, payload hash, source
response hash, exact Packet V8 binding, and sealed research-brief hash.

## Authority and lifecycle rules

- Domain and exact-path permission is enforced before local validation.
- `{}` remains valid for exact base replay but is rejected as an intended
  research experiment with `UNINTENDED_NO_EFFECT`.
- A materializer result with no changed paths is rejected the same way.
- Invalid syntax, permission, or local validation consumes no experiment
  attempt and permits at most one correction response.
- An attempt is consumed exactly when local execution begins. Runtime or proof
  failure does not refund it and does not trigger an automatic retry.
- Failed execution becomes review evidence rather than being misclassified as
  an unconsumed planning failure.
- Review gates are strict and bind to the exact sealed round plan.
- Continuation after the final attempt is rejected before an accepted review
  artifact is written.
- Replay proof alone never promotes a result. Promotion requires
  `CONTINUE_PROMOTE_RESULT`, an exact proof or sweep-member identity, and a
  replay-proven result.
- `CONTINUE_RETAIN_BASE` leaves the preceding Packet V8 authoritative.
- Promotion builds the next Packet V8 only through the canonical derived
  finding importer and packet builder.

`create_job_bound_research_route_services` binds execution directly to the
existing owners:

```text
materialize_state_override
execute_state_override_proof
ScalarBracketSweepService
promote_replay_proven_candidate
build_agent_bundle
```

The scalar sweep member carries its exact in-process proof object only long
enough to authorize same-process promotion. Durable sweep evidence remains the
existing proof ID and receipt hash; no second proof format was introduced.

## Focused and full validation

Focused court:

```text
tests.test_research_protocol
tests.test_research_session
tests.test_scalar_sweep
tests.test_automated_session

44 passed
```

Coverage includes strict field ordering, exact JSON payload count, unresolved
taxonomy, permission intersection, no-op handling, immutable round plans,
correction limits, attempt accounting, execution failure, final-round
continuation rejection, exact sweep-member promotion, and terminal
non-executable planner outcomes.

Complete Python 3.14 suite:

```text
254 passed
```

## Real canonical proof workflow

The provider-independent controller was exercised against the fresh epsilon
Packet V8 from Slice 1 and the configured published runtime. It changed only
`params.epsilon` from the captured approximately `1e-6` value to `2e-6`.

```text
run:
C:\code\cuda-fractal-engine-state-tool\.local\slice2-question-research\question-runs\slice2-380d2d26adc24459882fd65aaa766366

packet ID: 2f37edbc-002e-4808-8313-80e9b60e834b
packet manifest SHA-256: cece96fc5f5cd7a3509fa30fecd742f605aa6aca2eb0f0b7ede6a13554c09903
round-plan semantic SHA-256: 5eac802bccdcf3cc6d60389e2da4e2380c7c1618a2c703eeb52f93c64de3a005
proof ID: b96e52f6-98ed-4e1c-8874-31a88d3cac51
proof receipt SHA-256: eb82785c87a8530a2479aa866183ed7bddbbc3136a9ca8f10571fca0841e9e0a
proof status: replay_proven
attempts consumed: 1
terminal controller state: READY_FOR_SYNTHESIS
```

The test review deliberately made no scientific conclusion and requested no
promotion. It proves the canonical local execution path only.

## Hostile review

- The new parser adds a decision contract around existing bare payloads; it
  does not add a proposal envelope.
- Exact-path permission narrows Packet V8 authority and cannot broaden it.
- Fixed-condition prose remains guidance, not falsely claimed machine proof.
- The controller checks local materialization before consuming an attempt and
  consumes the attempt before runtime execution.
- Illegal promotion and final-round continuation are rejected before canonical
  review evidence is occupied.
- Single and sweep execution reuse the same proof and timeout owners as the
  manual and existing automated routes.
- Promotion still records `human_acceptance: false`; the controller calls the
  selected packet the current research base.
- The active pipeline text in the sealed round plan is descriptive observation
  context derived by Packet V8, not a parallel Color Pipeline authority.
- No provider count or generation request was made.

No open Slice 2 defect blocks the cost, review, synthesis, and report slice.
