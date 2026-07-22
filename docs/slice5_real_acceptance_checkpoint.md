# Slice 5 Real Acceptance Checkpoint

Status: historical negative authority checkpoint. Scalar and camera paths were
accepted here; the Color Pipeline limitation recorded below was later resolved
by the merged engine-owned application operation documented in
`slice5_color_pipeline_engine_integration.md`.

## Scalar launch and recapture acceptance

The user asked an external agent for a concrete experiment against:

```text
D:\salt-fractal\cuda_newton_fractal_clone\findings\manual_capture\2026-06-18\200317_245__explaino_multibrot_root_trap
```

The agent returned the sparse override:

```json
{
  "params": {
    "max_iter": 512
  }
}
```

The desktop tool proved, visually reviewed, accepted, and launched proof
`e437d90d-e757-4f5e-9ae2-978c8c0b6d2e`. The requested value changed from
`484` to `512` and survived exactly. Materialization and action-free replay had
identical encoded and decoded pixels.

The launched viewer was recaptured at:

```text
D:\salt-fractal\cuda_newton_fractal_clone\findings\manual_capture\2026-07-21\192324_921__explaino_multibrot_root_trap
```

The recaptured state is semantically equal to the launched engine candidate;
only `stats.last_render_ms` differs. The recaptured PNG and proven BMP have the
same decoded RGBA SHA-256:

```text
5eb751a187350dee0662200696bb297ba284d621957f7245ae1c60d37afeeb8d
```

This accepts the external-agent trigger, sparse scalar override, validation,
materialization, replay, visual review, exact launch, and recapture loop.

## Camera companion-pair acceptance

The July 21 recapture was also exercised with a paired `view.center_x` and
`view.center_hp_x` edit through the desktop UI:

- Packet: `2cfa4833-0d95-4fda-8f6b-cb9b1c271f09`
- Proof: `85cf8f97-5343-476f-a729-ebfc225f5c70`
- Both requested fields survived; `center_x` received explicit representation
  normalization while the high-precision companion survived exactly.
- Base decoded RGBA SHA-256:
  `5eb751a187350dee0662200696bb297ba284d621957f7245ae1c60d37afeeb8d`
- Candidate decoded RGBA SHA-256:
  `76ef2c008af08f5eb7e059184a10c07d72199fad0833d8481210e06f3cbe6228`
- Materialization and action-free replay pixels matched exactly.

No Python precision conversion, logarithm, or companion synthesis was used.
The optional camera gate therefore passes.

## Color Pipeline authority result

The July 21 state carries the same grading saturation in three serialized
representations:

```text
color_pipeline_draft grading row 1: grade.saturation
params.color_saturation
params.color_grading_stack[1].saturation
```

Controlled direct-runtime experiments established:

1. Draft-only edit from `1.6795599460601807` to `1.25`
   - Proof: `d6620c4f-d386-4bf4-a7ee-6e1c7d7f7d3b`
   - The edited draft value survived and replay was deterministic.
   - Candidate decoded pixels were byte-identical to the captured base.
   - Therefore deserialization preserved pending editor state but did not lower
     it into the live render parameters.

2. `params.color_saturation`-only edit to `1.25`
   - Proof: `5f065a76-f983-49ff-a672-3462ad7bf1ce`
   - The engine reverted the request to `1.6795599460601807`.

3. Draft plus scalar edit to `1.25`
   - Proof: `6ff55785-0780-42fd-b217-378b5a40ff4a`
   - The engine again reverted the scalar while preserving the draft edit.

4. Controlled complete-state experiment changing the draft, scalar mirror, and
   grading-stack value together
   - All three emitted as `1.25`.
   - Emitted state SHA-256:
     `75bc53f34f7978f528b93ab8e5ca6dca050a14110a1f828ccb87d61d4fed89aa`
   - Candidate decoded RGBA SHA-256:
     `9050608c76297d8c6d908d44f546a82405a5580303ab26a5af83bff64e360277`
   - Mean absolute channel difference from the base:
     `[0.1205228483, 4.0036929251, 54.5417834420, 0.0]`.

The engine source agrees with the experiment: state loading parses the draft as
window state, while `ApplyColorPipelineDraftToLiveState` is the engine-owned
lowering step that updates live parameters. Current headless proof actions call
that function, but a direct complete-state load does not expose a single
apply-loaded-draft operation. The deployed UI-Salt contract validates draft
functions and parameter values but does not export the draft-to-live serialized
field mapping.

The state tool must not infer that mapping from equal captured values, duplicate
engine tables, or recreate `ApplyColorPipelineDraftToLiveState` in Python.
Accordingly, the Color Pipeline acceptance gate did not pass under the
direct-state-only contract that existed at this checkpoint.

## Hardening added at this checkpoint

Proof receipts now compare the captured base frame with the engine-emitted
candidate. The UI reports whether decoded pixels differ and shows a prominent
`PIXELS IDENTICAL TO BASE` marker when they do not. It also lists nonvolatile
engine materialization changes beyond the requested diff. These are factual
review aids; they do not perform aesthetic scoring or silently reject a valid
candidate.

## Decision boundary

This boundary was resolved by merged CUDA-engine PR #4. The state tool continues
to forbid Python action lowering and handwritten Color Pipeline mappings; it now
uses the engine's explicit loaded-draft operation for materialization only.
