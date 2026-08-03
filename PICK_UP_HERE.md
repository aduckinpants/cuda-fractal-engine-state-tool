# Pick Up Here — V9 Economic Qualification Planning

## Active campaign state

The completed finding-enrichment and scalar-sweep campaign is merged on clean
main:

```text
main@027a7419085dc28fe2af0a9108754b8c4030c3c4
```

The engine E0-E2 prerequisites are merged and published:

```text
engine master: deca3d93fac92ad93742e8d47714f91329808ead
fractal_ui.exe sha256:
501002f174068641b9a6105e56c277e6a4080bc9dbeb5e672282e77562b96f56
```

The planning-only branch is:

```text
codex/v9-economic-qualification-plan
```

Read first:

1. [`docs/v9_economic_qualification_model_ladder_plan.md`](docs/v9_economic_qualification_model_ladder_plan.md)
2. [`docs/finding_enrichment_v9_scalar_sweep_campaign.md`](docs/finding_enrichment_v9_scalar_sweep_campaign.md)
3. [`docs/finding_enrichment_slice3_cost_gate_evidence.md`](docs/finding_enrichment_slice3_cost_gate_evidence.md)
4. [`docs/finding_enrichment_slice4_context_evidence.md`](docs/finding_enrichment_slice4_context_evidence.md)
5. [`docs/finding_enrichment_slice5_scalar_sweep_evidence.md`](docs/finding_enrichment_slice5_scalar_sweep_evidence.md)
6. [`docs/finding_enrichment_slice6_manual_gate.md`](docs/finding_enrichment_slice6_manual_gate.md)
7. [`docs/packet_v8_automated_route_live_qualification.md`](docs/packet_v8_automated_route_live_qualification.md)
8. [`docs/v8_automated_route_authority_trace.md`](docs/v8_automated_route_authority_trace.md)

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

The exact-count dollar dispatch gate and fresh-review context architecture are
implemented and reviewed. No paid qualification run was made; the UI still
defaults to an explicit `$0.00` ceiling and stops before context/provider work.

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

The Slice 6 UI gate passed and PR #10 merged at `027a741`. The next proposed
campaign is the minimum-acceptable model ladder. Review
`docs/v9_economic_qualification_model_ladder_plan.md` and obtain explicit plan
approval before product mutation.

Plan approval authorizes only zero-paid-call preparation Slices 0-2. Provider
count calls and every paid model cell remain separate user approval gates. No
diagnostic-mosaic work, additional production provider, sweep expansion, or
engine mutation is authorized.
