# Finding Enrichment Slice 5 — Scalar Bracket Sweep Evidence

## Closure

Headless Scalar Bracket Sweep V1 is complete. It is an orchestration route over
the existing Packet V8 state-override and proof owners, not another authoring
language or validator.

The service accepts:

```json
{
  "sweep_version": 1,
  "axis": {
    "path": "params.vortex_strength",
    "values": [0, 0.25, 0.5, 0.75, 1]
  },
  "member_failure_policy": "continue_independent"
}
```

It rejects the entire plan before rendering unless all members pass the same
canonical packet-authorability and merge validation used by ordinary sparse
overrides. A fixed override is preserved exactly, may be empty, and may not
contain the sweep axis.

## Failure and lifecycle contract

- malformed plans, unsupported axes, duplicate/non-finite/out-of-range values,
  fixed-axis collisions, stale packets, and preflight failures create no sweep
  run;
- `continue_independent` preserves one failed proof and starts later members
  independently from the exact base;
- `stop_on_first_failure` records all later values as not started;
- cancellation prevents new members, preserves completed proof evidence, and
  cancels only the currently owned proof process;
- packet or runtime drift stops every remaining member regardless of member
  failure policy;
- the aggregate receipt indexes ordinary proof receipts and records
  `human_acceptance: false`.

The shared `enumerate_override_leaf_paths` helper lives beside the canonical
duplicate-safe parser. It exists only for fixed-axis collision detection and is
not a sweep-owned authorability registry.

## Real vortex bracket

Source capture:

```text
D:\salt-fractal\cuda_newton_fractal_clone\findings\manual_capture\
2026-08-02\132248_955__explaino_all
```

Generated Packet V8:

```text
finding_id 68eae29408ef2c533d7cf27c452bf7e5f93e51d9b611c2e4a6d7636c31a11963
packet_id  72980336-bc21-44b0-bb00-754182718ef5
manifest   6a530bfe1c4ba00b8cf17686a5e426b20c4488674c8e842d972c9d6452671898
```

Sweep evidence:

```text
D:\salt-fractal\cuda-fractal-engine-state-tool\findings\
68eae29408ef2c533d7cf27c452bf7e5f93e51d9b611c2e4a6d7636c31a11963\sweeps\
f061a5bb-94cb-4943-bbb6-f4a6ac41895a
```

All five values were independently `REPLAY_PROVEN`:

| Value | Proof ID | Candidate display SHA-256 |
|---:|---|---|
| 0 | `007eaa48-29a7-4ffd-90a6-7c6a101925eb` | `92b9cde1fcdcb58d44c22ddaf4c4be49a2180cff4a2877f934332ef369dc2470` |
| 0.25 | `3d8ad2f3-87f3-4a09-b086-52db5ecb228f` | `7bd9bfb779141d3dbba2897530d952caaee4f8eb8942f82b8655401887f19eef` |
| 0.5 | `1b1803af-ffc5-4e69-9d86-30d7cc841006` | `41bed065afc47cd54942f280b2f2c5bf3848cc66f0bea9f5c36d560ce096b3b2` |
| 0.75 | `1c9da69e-38a5-481b-9d5e-075eb18b55dd` | `4cd5ec73da1e8352a90252ee25df5d628a19d5e60f51734181e8a5f7c176259c` |
| 1 | `ab6ce821-3dfb-4ccb-a0c9-757ee3967967` | `8d09abb11662f4d5d7aadee73834a17af1215d79f74b6445fa24808de17f5370` |

Every action-free replay decoded identically to its materialization frame. The
five display hashes are distinct. That establishes five stable rendered
outcomes; it does not automatically classify a cusp, bifurcation, or cause.

The end-to-end CLI run took about 300 seconds. Individual materialization and
replay processes took approximately 23–29 seconds each. Slice 6 therefore must
show per-member progress while retaining the existing packet-derived timeout
owner.

## Validation

Focused tests prove:

- strict duplicate/non-finite/shape rejection;
- fixed-axis collision and range failure before proof/allocation;
- independently continued member failure;
- strict stop after the first member failure;
- cancellation preservation;
- runtime authority-drift termination;
- blank fixed-editor handling;
- reuse of ordinary state materialization and proof services.

The full Python 3.14 suite and diff checks are recorded at the slice checkpoint.

## Hostile review

- A sweep-specific range/type registry would duplicate Packet V8 authority.
  Preflight materializes every concrete ordinary override instead.
- A fixed override could silently lose precedence. Exact leaf enumeration makes
  any collision a plan failure.
- Cumulative mutation could make later members depend on earlier engine output.
  Every proof receives the same packet and its own complete concrete override.
- Runtime drift could masquerade as a member failure. Packet and runtime
  identity are checked around each member and drift stops all remaining work.
- An aggregate success could be mistaken for acceptance. The receipt and
  presentation index explicitly retain `human_acceptance: false` and visual
  review remains pending.

## Next approved boundary

Slice 6 adds a thin UI route and grouped contact-sheet presentation over these
same artifacts. It is the final preplanned implementation slice before stopping
for user manual review.
