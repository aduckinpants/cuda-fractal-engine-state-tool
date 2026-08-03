# Finding Enrichment and V9 Baseline Receipt

Recorded: 2026-08-03

## Repository authority

```text
state tool repository: C:\code\cuda-fractal-engine-state-tool
starting branch: main
starting commit: 28a6da4f6949ef01e6ea7b45a9affab0e32ee735
origin/main divergence: 0 ahead, 0 behind
starting worktree: clean
campaign branch: codex/finding-enrichment-v9-sweep
```

## Engine handoff

```text
engine repository: C:\code\cuda_newton_fractal_clone
merged master: deca3d93fac92ad93742e8d47714f91329808ead
merged PR: https://github.com/aduckinpants/cuda_newton_fractal/pull/7
published runtime:
  D:\salt-fractal\cuda_newton_fractal_clone\runtime\fractal_ui.exe
published runtime sha256:
  501002f174068641b9a6105e56c277e6a4080bc9dbeb5e672282e77562b96f56
engine rearward review: ok
```

The exact merged engine head passed its focused and full native suites, runtime
publication, active-model/canonical-sampling runtime tests, code-quality
baseline, diff hygiene, hostile audit, contract receipts, and rearward review.

## State-tool test baseline

Command:

```powershell
$env:PYTHONPATH = (Resolve-Path .\src).Path
py -3.14 -m unittest discover -s tests
```

Result:

```text
Ran 154 tests in 27.676s
OK
```

## Rational Escape authority smoke

Fixture state:

```text
D:\salt-fractal\cuda_newton_fractal_clone\findings\manual_capture\
2026-08-02\160241_458__explaino_rational_escape\state.json
```

State SHA-256:

```text
5aac28d253e2dbe405418d06bea9ccd92d6447538831e303aa87567734d1b57d
```

The published runtime command:

```text
fractal_ui.exe --load-state-json <state> --describe-active-fractal-model
```

returned:

- provider status `available`;
- provider ID `polynomial_over_power_escape.v1` version `1`;
- model ID `laurent_polynomial_escape_time.v1`;
- denominator power `3`;
- zero warp in participating state;
- resolved backend `float64`, strategy `direct`;
- evaluation authority `fractal.sample`;
- exact matching state and executable SHA-256 values.

## Hostile baseline review

The planning pass checked these failure modes before product mutation:

- stale pre-engine report identities were not reused as runtime authority;
- the untracked review was not treated as a second execution plan;
- enrichment was not narrowed to the Rational Escape selector;
- the engine model payload, not selector prose, selects the production provider;
- disclosure was kept outside analysis/cache identity;
- E3 diagnostic mosaics and nonzero warp stayed excluded;
- no paid call was made;
- both repositories remained independently clean through the handoff.

## Disposition

Slice 0 establishes an implementation-capable, current-runtime contract.
Slice 1 common enrichment is the next approved product boundary.
