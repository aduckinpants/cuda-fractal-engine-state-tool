# Fixture B — Luna High Assisted Automated Session

## Authority and result

- Case SHA-256: `8744a3cc7c7308e8bb5a9078803ca9827f78aaee9f150cb1a0c18d1996487379`
- Run: `v9-v8-b-luna-high-live-2b92ffab-2182-4234-846a-b51c2b780f7d`
- Packet: `bb430c93-1747-490d-92a0-59f998fe451c`
- Actual calculated cost: `$0.0758634`
- Input/output tokens: `352191 / 4521`
- Proof: `c5b7408f-608d-4a5a-8df8-9495565efa71`, `replay_proven`
- Derived packet: `f14d8e53-33ae-457f-9a9f-140a13ff478d`
- Automatic gates: `10 / 10 passed`
- Model gate: `ROUND_ADVANCE`
- Human disposition: `pending`

Raw evidence:

```text
D:\salt-fractal\cuda-fractal-engine-state-tool\automated-runs\v9-v8-b-luna-high-live-2b92ffab-2182-4234-846a-b51c2b780f7d
```

## Selected experiment

The model selected one dynamics edit:

```json
{
  "params": {
    "ripple_amplitude": 0.15
  }
}
```

It predicted increased fine corrugation and local band displacement in a fixed-window comparison, while explicitly acknowledging nonlinear reorganization and possible masking by the existing pipeline.

The exact compared derivatives were both `2048 x 1280`. They differed with mean absolute RGBA channel differences:

```text
[72.69327392578126, 81.27309608459473, 68.49835090637207, 0.0]
```

The model's review correctly concluded that the response was much stronger and more global than predicted. It did not claim that the ripple term alone explained every visible structure.

## Historical comparison boundary

Historical Fixture B selected a color-only negative control by disabling the low-weight `root_proximity` contribution. The current generic automated prompt instead selected the previously neutral ripple dynamics axis. Both experiments were valid and both produced more global changes than their local predictions anticipated.

This is useful behavioral evidence, not an exact experiment-selection replay.
