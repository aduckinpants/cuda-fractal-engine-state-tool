# Pick Up Here — V9 Cost and Scalar Sweep

## Pause state

The Packet V8 automated-route POC is merged on:

```text
main@12ebd9659439ad28d00458a0346e1ff5314c4fff
```

The next work is documented but intentionally not started. The user is pausing
before travel rather than leaving cost or sweep implementation half complete.

Read first:

1. [`docs/v9_cost_controlled_automation_and_scalar_bracket_sweep_plan.md`](docs/v9_cost_controlled_automation_and_scalar_bracket_sweep_plan.md)
2. [`docs/packet_v8_automated_route_live_qualification.md`](docs/packet_v8_automated_route_live_qualification.md)
3. [`docs/manual-test-results/v9_vortex_bracket_discovery_2026-08-02.md`](docs/manual-test-results/v9_vortex_bracket_discovery_2026-08-02.md)
4. [`docs/v8_automated_route_authority_trace.md`](docs/v8_automated_route_authority_trace.md)

## Why cost is first

The completed Phoenix run used:

```text
983,996 input tokens
326,508 cached input tokens
657,488 uncached input tokens
6,787 output tokens
```

Each review call carried about two packet loads. The user reported only `$0.42`
of remaining API credit at the pause boundary. Both pricing and credit are
volatile; verify them before relying on those values.

Do not start another paid automated run until the context architecture and
dollar dispatch gate are implemented and reviewed.

## Locked next architecture

```text
shared byte-identical foundation
+ isolated exact case capsule
+ compact controller-owned round ledger
-> bounded authoring context

fresh result authority
+ locked prediction/override/proof ledger
-> fresh bounded review context
```

Logical battery continuity must not mean one ever-growing provider context.

## Locked first local sweep

```text
base:
D:\salt-fractal\cuda_newton_fractal_clone\findings\manual_capture\2026-08-02\132248_955__explaino_all

axis:
params.vortex_strength

values:
[0, 0.25, 0.5, 0.75, 1]
```

Use one separate sweep JSON document. Do not put template markers inside sparse
state JSON. Reject the plan if the fixed override already changes the sweep
axis.

Plan failures abort before rendering. Independent member proof failures are
recorded and remaining members continue unless `stop_on_first_failure` was
selected. Authority drift always stops the remaining plan.

## Re-entry commands

From `C:\code\cuda-fractal-engine-state-tool`:

```powershell
git status --short --branch
git fetch origin
git rev-parse HEAD
git rev-parse origin/main
Get-Content .\AGENTS.md
$env:PYTHONPATH = (Resolve-Path .\src).Path
py -3.14 -m unittest discover -s tests
```

Then verify:

- current root instructions and goal protocol;
- clean exact merged `main`;
- published runtime identity;
- official model/pricing/cache contracts;
- available API credit and an explicit run budget;
- whether this plan needs revision before implementation.

## Exact continuation

Resume at **Slice 0 — Re-entry and contract refresh** in the V9 plan.

No engine work, paid provider call, scalar-sweep implementation, model
ablation, or broader Packet V9 mutation is authorized during the pause.
