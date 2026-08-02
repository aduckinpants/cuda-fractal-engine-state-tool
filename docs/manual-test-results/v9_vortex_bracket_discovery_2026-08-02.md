# V9 Vortex Bracket Discovery — 2026-08-02

## Status

This is a reviewed planning witness, not an implemented sweep and not an
accepted causal classification of the rendered morphology.

It preserves the manual discovery that motivated a future bounded scalar
bracket sweep. Product implementation remains deferred to the phased plan in
[`../v9_cost_controlled_automation_and_scalar_bracket_sweep_plan.md`](../v9_cost_controlled_automation_and_scalar_bracket_sweep_plan.md).

## Captures

### Exploratory predecessor

```text
D:\salt-fractal\cuda_newton_fractal_clone\findings\manual_capture\2026-08-02\131256_861__explaino_all
state.json SHA-256: 9ffd37925cffd9f2ec121b0cc2ed3d6eee1a00469b98cfd6d74b251007b24fb6
frame.png SHA-256:  705a0d7984d599dc288b2add668924f8728972e771d6c38e8218447c29673576
```

This is discovery context only. It differs from the later bunny capture in
multiple dynamics, roots, camera, phase, seed, and other values. It is not a
controlled comparison and must not authorize a single-parameter conclusion.

### Bracket base — “space bunny”

```text
D:\salt-fractal\cuda_newton_fractal_clone\findings\manual_capture\2026-08-02\132248_955__explaino_all
state.json SHA-256: db9d88a010f1a225108f1dd3e7fd1d0fe5f21445a6b544c3b1b579df0119ccae
frame.png SHA-256:  f49fe9e74685d2b52b3f86006b26926891137b9e842572eda1fe0b4d75f389de
```

Relevant captured values include:

```text
fractal_type: explaino_all
params.vortex_strength: 1
params.field_curvature: -1
params.explaino_damping: 0.01
render.width: 4096
render.height: 2560
```

### Manual endpoint — vortex disabled

```text
D:\salt-fractal\cuda_newton_fractal_clone\findings\manual_capture\2026-08-02\133520_315__explaino_all
state.json SHA-256: 15eebff8e9f9c985622d7dc1e39cf29c6977207333f7621b95a77e6fbe1a50c0
frame.png SHA-256:  349c994a8d49877cba4c570a8d3e456a58bbc1dbdcc65e25054a2acc0e5cc4ad
```

The authorable dynamics change from the bracket base is:

```text
params.vortex_strength: 1 -> 0
```

The capture also changed `render.height` from `2560` to `2557`, and its runtime
statistics and derived sidecar receipts changed as expected. Those values are
not additional dynamics controls, but the height difference makes the two
manual captures an imperfect pixel-comparison fixture. A generated sweep must
inherit the exact base render configuration for every member.

## Reviewed observation

At `vortex_strength = 1`, the central structure supports a recognizable
two-eared “space bunny” reading. At `vortex_strength = 0`, the ears collapse
and the remaining enclosed figure reads more like a curled aquatic or
“Sea-Monkey” form.

This supports a narrow experimental claim:

> The visible ear-like projections and angular organization are sensitive to
> `params.vortex_strength` under this exact captured state.

It does not yet prove:

- a bifurcation or cusp at a particular value;
- that the transition is continuous or discontinuous;
- which other active terms generate the remaining body;
- a general role for `vortex_strength` across ExplainO states;
- a root, basin, or dynamical classification from appearance alone.

Those remain hypotheses for a controlled bracket.

## Proposed first bracket

Use the exact bunny capture as the sole base and generate each candidate
independently:

```text
params.vortex_strength in [0, 0.25, 0.5, 0.75, 1]
```

Hold every other state field fixed, including camera, iterations, roots,
Color Pipeline draft, and `4096 x 2560` render dimensions. Each member must be:

```text
exact base state
+ one concrete sparse override
-> existing validation
-> existing deterministic merge
-> existing engine materialization and replay proof
```

The first review question is whether the two projections emerge gradually or
within a narrower interval. A later refinement may use a new explicit value
list, but it must not silently accumulate mutations from an earlier member.

## Blind-session calibration conclusion

The blind agent did well at revising the role of `root_proximity` from
morphology to color contribution and at proposing an independently based
coarse-to-fine bracket. Its detailed attribution of the remaining form to
other active controls is still hypothesis rather than isolated evidence.

This witness is suitable as the first local scalar-sweep fixture because it has
two visually distinct endpoints and one direct authorable scalar axis. It is
not yet a Packet V9 automated-agent acceptance result.
