# Fixture D — Luna High Assisted Automated Session

## Authority and result

- Case SHA-256: `2414489f4fe0eee1a7e0a1ede78b0b0551c37e62fe1941aaaa113746931d4f35`
- Run: `v9-v8-d-luna-high-live-6bf863f8-780f-4eaa-ac43-2f7b4fdad182`
- Packet: `73d407bd-618d-4c49-9505-c0fe2a21087d`
- Actual calculated cost: `$0.0758272`
- Input/output tokens: `346622 / 5419`
- Proof: `2f0a6f92-b7ca-4108-a8ad-3887b1865116`, `replay_proven`
- Derived packet: `11d5b3c2-2aaf-4152-857e-bd2dde5d4827`
- Automatic gates: `10 / 10 passed`
- Model gate: `ROUND_ADVANCE`
- Human disposition: `pending`

Raw evidence:

```text
D:\salt-fractal\cuda-fractal-engine-state-tool\automated-runs\v9-v8-d-luna-high-live-6bf863f8-780f-4eaa-ac43-2f7b4fdad182
```

## Selected experiment

The model increased only the second active source row's root-proximity blend:

```text
signal.blend_weight: 0.27900999784469604 -> 1.0
```

The complete captured pipeline was returned. Dynamics and the exact high-zoom
camera were preserved. The locked prediction expected stronger root-field color
contribution without geometric displacement, while acknowledging that sequential
blending could produce a broad chromatic change rather than a localized one.

The exact `2048 x 1280` derivatives differed substantially, with mean absolute
RGBA channel differences:

```text
[115.79210243225097, 94.76755294799804, 97.1068214416504, 0.0]
```

The review correctly treated this as a strong global color response, not proof
that a particular visible contour was caused by the root field.

## Historical comparison boundary

Historical Fixture D also used a color-only experiment at fixed camera, but
changed band density and softness. The current run chose the active
root-proximity contribution instead. Both safely exercise exact-camera discipline;
the current result adds a useful causal comparison for one source-row weight but
does not reproduce the historical band-quantization question.
