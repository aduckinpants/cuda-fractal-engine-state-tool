# Finding Enrichment Slice 2 Evidence

## Checkpoint scope

Slice 2 consumes the exact published runtime active-model receipt and canonical
`fractal.sample` surface. It adds one static state-tool provider for the engine
model `laurent_polynomial_escape_time.v1` and keeps analytical records separate
from annotation-render identity.

The implementation does not inspect engine source at runtime, duplicate the
fractal recurrence, infer causality from annotations, support nonzero ExplainO
warp, or add a diagnostic mosaic.

## Validation

Focused tests:

```text
py -3.14 -m unittest tests.test_finding_enrichment tests.test_polynomial_model_provider -v
Ran 9 tests - OK
```

Full local suite:

```text
py -3.14 -m unittest discover -s tests
Ran 163 tests - OK
```

Diff hygiene:

```text
git diff --check
PASS
```

## Published runtime authority

```text
runtime executable:
D:\salt-fractal\cuda_newton_fractal_clone\runtime\fractal_ui.exe

SHA-256:
501002f174068641b9a6105e56c277e6a4080bc9dbeb5e672282e77562b96f56
```

The exact Rational Escape Packet V8 state has SHA-256:

```text
5aac28d253e2dbe405418d06bea9ccd92d6447538831e303aa87567734d1b57d
```

The runtime receipt selected:

```text
provider: polynomial_over_power_escape.v1 / version 1
model: laurent_polynomial_escape_time.v1
numeric backend: float64
evaluation authority: fractal.sample
```

## Real Rational Escape witness

```text
packet_id: 6e9ca581-fcb3-45aa-8aa9-5d03997f3569
analysis_id: 4db4181f7b1e8108a0c571daea99d4750f1bce5587ff5fd2f230fea3aabd27e6
repeat result: cache_hit true
```

The provider derived four critical points, three fixed points, and one
structural singular point. Polynomial residuals remained below the bounded
solver tolerances. The fixture critical point was:

```text
0.4670551578633721 - 0.8585835852044102 i
source projection: (1995.881805892533, 1301.9726683019635)
distance from camera center: 56.4993933757538 source pixels
```

One canonical CUDA point-set request evaluated all eight features through the
exact Packet V8 `state.json`. The structural singular point returned
`termination_kind: pole`; the other records retain their exact runtime
statuses. The separately receipted annotated derivative has SHA-256:

```text
e0f171ca43c7837bac01e5e70f8649db36c8150ca69b6c0f7ebeac8a7750be6c
```

Only the contained critical point was rendered. The annotation set retains all
feature coordinates and containment results without claiming visible cause.

## Fail-soft and compatibility witnesses

An unrelated Multibrot Packet V8 produced:

```text
analysis_id: a2d8fe336125938806a04a53479fb41e9a16dca6cb926c665bfe67b81242d27a
provider status: unavailable
reason: unsupported_fractal_type
```

The historical packet records an older runtime executable. Development mode
recorded the exact hash difference and continued against the current runtime.
Strict mode exited before active-model invocation with status 2. No fallback
model was selected in either case.

## Hostile review

Checked explicitly:

- active-model state, runtime, selector, provider, numeric, and evaluation
  identities fail closed on disagreement;
- nonzero-warp and unsupported receipts remain valid unavailable authority;
- the sampler loads the exact packet state through `base_state.load_state_json`;
- no Python path-to-runtime-parameter translation is used;
- point coordinates and returned numeric backend must agree with the request and
  active-model receipt;
- analytical, engine-evaluation, annotation-set, and annotation-render evidence
  remain separately classified;
- volatile runtime timing remains preserved in the first immutable response but
  is not used as analysis/cache identity;
- cache hits validate the complete artifact hash ledger and exact binding rather
  than rerunning the sampler;
- provider/annotation version fields prevent changed semantics from silently
  reusing an older analysis identity.

## Closure

Slice 2 is complete. The common and first model-specific enrichment path is
operational. Slice 3 is the next approved boundary: implement a versioned,
conservative dollar estimate and reject provider dispatch before any request
whose maximum estimated cost exceeds the remaining run budget. No paid request
is authorized for that work.
