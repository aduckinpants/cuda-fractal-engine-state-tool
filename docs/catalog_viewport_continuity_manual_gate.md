# Catalog And Viewport Continuity Manual Gate

Status: the hardened primary McMullen calibration is the first strong
end-to-end pass. The first adversarial battery exposed two focused
decision-quality failures. Packet experiment observability and explicit
base-replay handling are now hardened, and fresh Counterfactual Pair and
ExplainO All packets are ready for user-run retests.

## What this gate tests

The engine now supplies reviewed mathematical background for all 51 live
selectors and exact viewport geometry for a loaded state. The state tool places
both authorities in Packet V6 and instructs the agent to handle camera
continuity for every non-color dynamics change at meaningful zoom.

The execution agent prepared and locally verified the bundles below. It did not
simulate or self-grade the external model sessions.

## Runtime binding

- Engine merged commit: `09d5664b77116b716f83dd8df1085e88596498d0`
- Published executable SHA-256: `ae329398693a5872faced0fa6f9cf57868788fc975b07ece5150954ac4face78`
- Descriptive catalog SHA-256: `8038ab867cd40dd4af6ca5b26aca11cd5e7c6b6a28816b00f7d4afdb4a4909fd`
- Viewport mapping: `cuda_fractal_renderer_pixel_center_v1`

## Primary fixture — McMullen dynamics continuity

- Capture: `D:\salt-fractal\cuda_newton_fractal_clone\findings\manual_capture\2026-07-21\232809_573__mcmullen`
- Finding ID: `cc2cb68da25f649f2de674750b04c2b15f5e1416a806a0329b09743491525e63`
- Packet ID: `8c1d791f-5122-4fbc-9458-554a52e84db4`
- Packet directory: `D:\salt-fractal\cuda-fractal-engine-state-tool\findings\cc2cb68da25f649f2de674750b04c2b15f5e1416a806a0329b09743491525e63\packets\8c1d791f-5122-4fbc-9458-554a52e84db4`
- Manifest SHA-256: `962fb8ff6f8424323ebe9b56b10b868fc630bc6cb1bd75b242a4b126ca93081d`
- Packet SHA-256: `0056a36a528b7f779df326e172943255ea1e3e599598055f1ccf307717f53878`
- Viewport-facts SHA-256: `4d40f7c64149ff112842fcefa0f49b0021e6b2a01703058c8267cc328d5eb934`
- `log2_zoom`: `6.6001691399968774`
- Complex frame size: `0.065967661108452882 × 0.04122978819278305`

The packet above is retained as the exact first-session artifact. It exposed
the decision-preflight defect and must not be reused for the hardened
calibration.

### Hardened primary calibration packet

- Packet ID: `4101a8d0-5b87-4bf0-af61-b7b1a8149483`
- Packet directory: `D:\salt-fractal\cuda-fractal-engine-state-tool\findings\cc2cb68da25f649f2de674750b04c2b15f5e1416a806a0329b09743491525e63\packets\4101a8d0-5b87-4bf0-af61-b7b1a8149483`
- Manifest SHA-256: `411e0d8999e4acc07a4269d3ea88d5c6ae40bbe43d20b8b8fd33fa9b66dc1ceb`
- Packet SHA-256: `c2a47a21bf4ef1a4980f6e27b72b52de0907cf2e2ddd7ef6a7a9e62e4e49d75f`
- Runtime identity SHA-256: `140707fd16283ac2db3c58a24146b73a7f29bbd15b0e1b36771c301f8b275e95`
- Base state SHA-256: `e68e611fd1b8014f98a59af689b53c299585bd62d8ed15dd3b81c1eadaba504d`
- Viewport-facts SHA-256: `4d40f7c64149ff112842fcefa0f49b0021e6b2a01703058c8267cc328d5eb934`

This immutable packet is the accepted input for the primary manual session.
The historical failed packet and pre-clarification packet
`2a8f4d43-a08b-487b-9ad8-49bd88b8e06f` remain untouched and must not be used
for this gate.

### Primary calibration result — strong pass

The user ran the hardened packet in a fresh Codex 5.6 Sol High session. The
session first explored the finding, clarified the selected experiment, reported
its decision preflight, and returned one sparse override that moved
`mcmullen_lambda` to the parabolic threshold while recentering the camera on the
predicted transition neighborhood.

- Proof ID: `96ab8393-97e2-4576-85cd-5039123a28d5`
- Proof directory: `D:\salt-fractal\cuda-fractal-engine-state-tool\findings\cc2cb68da25f649f2de674750b04c2b15f5e1416a806a0329b09743491525e63\proofs\96ab8393-97e2-4576-85cd-5039123a28d5`
- Receipt SHA-256: `a180f979fb0d9403981945bc92049df4806060c149a8acd48f42e7c487ef3ab3`
- Engine candidate SHA-256: `fc8912c6f5071136eef324c6f30b05122a4515ea7b6fd568bded9c7d233c23a6`
- Candidate encoded frame SHA-256: `95ebfcd3464ae6c7f7dbe9d54d81111e300f41873c4f6286cadc0fd64ae94b84`
- Candidate decoded RGBA SHA-256: `7aef7c1ab50c108f7d97af9b24585bdabb51e255308419073e6d61e7c16b9147`
- Review decision: `accepted`
- Launch PID recorded by the launcher receipt: `76504`

All five requested paths survived engine materialization exactly:
`params.mcmullen_lambda`, both ordinary center coordinates, and both serialized
high-precision center companions. Materialization and action-free replay had
identical encoded frames, identical decoded pixels, and semantically equal
authoring state after documented volatile diagnostics were excluded. The base
and candidate frames differed materially.

The user then captured the launched viewer at:

```text
D:\salt-fractal\cuda_newton_fractal_clone\findings\manual_capture\2026-07-22\180102_222__mcmullen
```

- Capture state SHA-256: `b8e5517a180f6fc632a6ba9b74b47510e80a57a29641e8e93af0345afd6d7af3`
- Capture PNG SHA-256: `9d9a63b6682ef11a3b3fc45ee095126a21ad2bd7291acdba5dd7ece867d116b8`
- Capture decoded RGBA SHA-256: `7aef7c1ab50c108f7d97af9b24585bdabb51e255308419073e6d61e7c16b9147`
- Captured center: `2/3 + 0i`
- Captured `log2_zoom`: `6.6001691399968774`
- Captured average iterations: `4838` of `5000`

The PNG and proof BMP differ as encoded files but decode to identical 4096 by
2560 RGBA pixels. This closes the full local chain from exact packet binding,
through model-selected override, validation, materialization, replay, visual
review, launch, and independent viewer capture.

The extra pre-render prediction question was useful because it made the
session state falsifiable before the image existed. Keep it as a manual
calibration prompt rather than expanding Packet V6. A malformed displayed
formula in the preserved transcript was traced to response copy/paste handling,
not packet generation or engine behavior. A repeated JSON block during later
discussion was harmless conversational overproduction; the discussion-only
post-render wording below is the preferred control for future tests.

## Completed three-packet adversarial battery

These were the only packets in that manual round. The previously prepared
ExplainO Multibrot and ExplainO All packets remain historical calibration
evidence and are not part of this battery. Deeper reserve captures and a new
custom capture are deferred until this battery completes without requiring a
packet change.

All three packets bind runtime identity
`140707fd16283ac2db3c58a24146b73a7f29bbd15b0e1b36771c301f8b275e95`,
contain nine required and three recommended attachments, report no unavailable
optional attachments, and passed an independent manifest/file/hash inspection.

### A — Reverse McMullen split

- Source capture: `D:\salt-fractal\cuda_newton_fractal_clone\findings\manual_capture\2026-07-22\180102_222__mcmullen`
- Finding ID: `f7e4a203a6783e173c390c155a4d51d4010247f2d9c89679b95cf9a99622466c`
- Packet ID: `e0eb0a99-5353-44df-bb24-b6f8fc2cfb01`
- Packet directory: `D:\salt-fractal\cuda-fractal-engine-state-tool\findings\f7e4a203a6783e173c390c155a4d51d4010247f2d9c89679b95cf9a99622466c\packets\e0eb0a99-5353-44df-bb24-b6f8fc2cfb01`
- Packet SHA-256: `d6da3b6f8ef39ca9335a2e00a61f75091116a729f0e536da49559d5a0e911d86`
- Manifest SHA-256: `38c54a66e6da739d104c0911e723e927404d9023e1d6f0e117ef291c3488c3a2`
- Selected description status: `reviewed`
- `log2_zoom`: `6.6001691399968774`
- Complex frame size: `0.065967661108452882 × 0.04122978819278305`

This starts from the accepted parabolic-threshold result. The manual experiment
returns lambda to `0.15` and asks the agent to follow the complete fixed-point
split rather than silently choosing one branch. The evaluator retains the
expected branch geometry and viewport-containment calculation; it is not added
to Packet V6.

#### Result — passed with two downstream calibration notes

The blind-session prompt must be self-contained. The executed wording was:

```text
Consider changing the lambda to 0.15. Follow the complete fixed-point split rather than choosing one branch. What camera strategy and result would you expect?
```

The earlier wording, "Reverse the preceding transition," incorrectly assumed
conversation history a fresh session did not have and is retired.

- Proof ID: `7f1caa34-d9d3-42af-b65f-5f78abf4736e`
- Receipt SHA-256: `ed7a022f382c4aa311a9eb69f1082f5392c737691c17845a7bfc52b1a27c23b5`
- Candidate state SHA-256: `b7acb38dbffeb1df6409e0bfee9767bae815d25e51481cbbf80418500396eed3`
- Candidate encoded frame SHA-256: `a68204a34485496f558307857ba0fc9520a432ed4146621e6f7b4f5e12716002`
- Candidate decoded RGBA SHA-256: `d0198421f8b37006184d7cb06c8c0eb9d8b30d596f83b893438f7bdff3ab8971`
- Review decision: `accepted`
- Launch PID: `73244`
- Follow-up capture: `D:\salt-fractal\cuda_newton_fractal_clone\findings\manual_capture\2026-07-22\232401_164__mcmullen`
- Capture state SHA-256: `f107d9aa53f8aa287f4767960cb358946db8b17bf7e66b9589c4d196d06a5e7a`
- Capture PNG SHA-256: `5c9a2add7cd72c38de73981d01881f7d1857298dd9b829602124981d7dc86885`

The sparse override changed lambda, center X and its high-precision companion,
and zoom and its logarithmic companion. Every requested value survived engine
materialization. Materialization and action-free replay had identical encoded
and decoded frames and semantically equal authoring state. The launched PNG and
proof BMP use different encodings but decode to identical 4096 by 2560 RGBA
pixels.

The agent selected a transition survey containing both conjugate branches,
predicted upper/lower reorganization and collapse of the near-parabolic delay,
and returned a valid camera with Y bounds `[-0.05, 0.05]`. The resulting capture
contained the paired structure and reduced average iterations from `4838` to
`87` under the same `5000` cap.

Two statements exceeded the available evidence: the initial response assigned
intentional significance to the binary32-nearest representation of `4/27`, and
it claimed pixel-for-pixel symmetry without an image-array comparison. The
agent identified both defects in its requested performance review. They are
classified as downstream epistemic-calibration misses, not packet ambiguities;
the attached state and authority already permit the narrower correct claims.
The agent's suggestion for a new special-parameter and fixed-point-solver
sidecar is not accepted by this campaign because it would introduce a new
per-family derived authority beyond Packet V6's current contract.

### B — ExplainO Nova high-zoom dynamics

- Source capture: `D:\salt-fractal\cuda_newton_fractal_clone\findings\manual_capture\2026-07-16\105825_478__explaino_nova`
- Finding ID: `d25243e57c814c687b28e9634d31700edcc69655be68dba2454bc80dd16a512c`
- Packet ID: `bd84ce6b-19d9-435d-a58c-3d0cff3d6bee`
- Packet directory: `D:\salt-fractal\cuda-fractal-engine-state-tool\findings\d25243e57c814c687b28e9634d31700edcc69655be68dba2454bc80dd16a512c\packets\bd84ce6b-19d9-435d-a58c-3d0cff3d6bee`
- Packet SHA-256: `5451d35ef73bacfcc4f9a14ed3a3eee575d9f0f6d6880410ea32caa5627fb7d7`
- Manifest SHA-256: `860065fc9a5df3c8b0d61e90c3e79a338b51a94a70b7f0fe206885bfd491e8f1`
- Selected description status: `reviewed`
- `log2_zoom`: `20.62552856249024`
- Complex frame size: `3.956190541058871e-06 × 2.4726190881617944e-06`

This fixture has a custom quartic, seed `-10`, and
`nova_alpha = 0.7031999826431274`. Its authoring surface exposes the applicable
Nova and ExplainO dynamics controls plus camera companions. The test asks for a
non-color dynamics experiment and checks whether the agent distinguishes a
grounded feature track from an honestly ungroundable high-zoom survey.

#### Result — operational pass, experiment-design partial

The targeted wording "Choose one mathematically motivated Nova dynamics
experiment" delegated experiment selection and reasonably acted as the concrete
trigger. The agent's immediate preflight and JSON were therefore not premature;
the later generic "Let's do that" prompt was redundant for this case.

- Proof ID: `560dd86f-6451-45b8-a7e8-34f50fc61df6`
- Receipt SHA-256: `1fe1091a9dba11d87ce1320b9f3af821d8f86e83674a3f244220b99fe5ad445a`
- Candidate state SHA-256: `19c1bef77ad87b6cea0d9e7e70c9588e1f0fe741db96f12640353d6696752c31`
- Candidate encoded frame SHA-256: `2609bb8d27b9be0f0315e454e6bc211599609379c04608fd9f5a004bb654cc95`
- Candidate decoded RGBA SHA-256: `9bbdec490e3129ef8f504406c4599b6072ffa0af1bedfcfe313e57a845be5928`
- Review decision: `accepted`
- Launch PID: `71980`
- Follow-up capture: `D:\salt-fractal\cuda_newton_fractal_clone\findings\manual_capture\2026-07-22\235345_959__explaino_nova`
- Capture state SHA-256: `f17eded0968a9d7b2c091143b625423772400861461bfea51eeb0ac091a8e4a2`
- Capture PNG SHA-256: `34839984dde18e3d1d2a2a1454373c17664d0e87033515c3df49a4414782a062`

The sparse override changed `nova_alpha` and the zoom pair. Both camera values
survived exactly; `nova_alpha = 0.70321` received the documented engine
representation normalization to `0.7032099962234497`. Materialization and
action-free replay were pixel-identical and semantically equal. The launched
PNG and proof BMP decode to identical 4096 by 2560 RGBA pixels. Average
iterations changed from `458` to `77`, but that statistic is not a controlled
dynamics comparison because the spatial window also changed.

The agent correctly refused to invent a feature track and selected a survey.
Its survey was too wide to test the proposed local continuation: reducing
`log2_zoom` by exactly eight octaves expanded each dimension by `256`, leaving
the old window only about 16 by 10 pixels in the authoritative source render.
That contradicted its pre-render prediction of a recognizable central
continuation and made the alpha change inseparable from the newly sampled
surroundings. A paired baseline at the same survey camera would be needed for a
controlled alpha comparison.

The opening analysis also supplied unproven autocorrelation offsets and
pointwise iteration counts without a reproducible computation. Those claims,
the footprint/preflight mismatch, and a later display-resolution arithmetic
error are downstream evidence-discipline failures already prohibited by the
packet's hierarchy and hostile-review rules. They do not yet establish a packet
ambiguity. Retain pixel-footprint and paired-camera guidance as possible
follow-up hardening only if the remaining battery reproduces the same pattern;
do not mutate Packet V6 during this manual round.

### C — ExplainO Counterfactual Pair

- Source capture: `D:\salt-fractal\cuda_newton_fractal_clone\findings\manual_capture\2026-06-22\142209_050__explaino_counterfactual_pair`
- Finding ID: `c702b7974ff78a68d53e595f8fc314fccec75f2ce059b3ffa690cda79bd0434e`
- Packet ID: `90e203ec-f777-4d3b-881f-de9c62a25a34`
- Packet directory: `D:\salt-fractal\cuda-fractal-engine-state-tool\findings\c702b7974ff78a68d53e595f8fc314fccec75f2ce059b3ffa690cda79bd0434e\packets\90e203ec-f777-4d3b-881f-de9c62a25a34`
- Packet SHA-256: `aeb01aa6610b3cf69b000e9e154d1a45ef5fbf6f95163ac1c88d622c0877b5bd`
- Manifest SHA-256: `40fb4e9aa0b7fca61ad49434fe5943d54121545e5df39c0cea172d351175edf8`
- Selected description status: `reviewed`
- `log2_zoom`: `14.575373517493107`
- Complex frame size: `0.0002622557546434392 × 0.000163845819368301`

This fixture exposes paired-orbit root family, world/view-relative frame,
partner offsets, reconvergence ratio, shared ExplainO dynamics, and camera
controls. The test checks whether the agent distinguishes a change to the pair
orbits from a change to their classification threshold and whether its proposed
camera behavior matches that distinction.

#### Result — operational pass, observability miss

The agent correctly distinguished a reconvergence-ratio change from a change to
the two Newton orbits. It preserved the camera and returned a valid sparse
override changing only the classification threshold. Materialization, replay,
visual review, acceptance, and launch succeeded.

- Follow-up capture: `D:\salt-fractal\cuda_newton_fractal_clone\findings\manual_capture\2026-07-23\002004_224__explaino_counterfactual_pair`
- Threshold tested in the accepted run: approximately `1.48 → 0.6`
- Additional user checks: `0` and `100`
- Render result: decoded pixels remained unchanged in all checks

The active Color Pipeline used a continuous smooth-escape signal, not the
paired-orbit classification. The exported evidence also lacked a class mask or
class-count diagnostic. The change was therefore semantically valid but could
not observe its intended class redistribution. The agent recognized that only
after rendering. This is the direct calibration case for the new observability
gate: before choosing a state experiment, name the active render or diagnostic
channel that can observe the intended effect.

## Historical contrast fixture — ExplainO Multibrot root-trap

- Capture: `D:\salt-fractal\cuda_newton_fractal_clone\findings\manual_capture\2026-07-21\230610_719__explaino_multibrot_root_trap`
- Finding ID: `e682f599e459082a341bc95238377e2f782ac85c08967bbf44c4f07efd3025c1`
- Packet ID: `cd0d3224-241b-4ded-aa74-6c5ca826d4d8`
- Packet directory: `D:\salt-fractal\cuda-fractal-engine-state-tool\findings\e682f599e459082a341bc95238377e2f782ac85c08967bbf44c4f07efd3025c1\packets\cd0d3224-241b-4ded-aa74-6c5ca826d4d8`
- Manifest SHA-256: `3089a2ec9f022414399c11d1296b23fa10afb0d1d249d9c1dfe6f6db0796b27a`
- Packet SHA-256: `19871052aff74c291d2a772ddd82e5e07c7d9005e6b6d5fa1d18f4962746df12`
- Viewport-facts SHA-256: `3dccb3ba4c0509a6a121dfb8367a35c97b35e36f456b08479854f955705c9c7e`
- `log2_zoom`: `11.932675187687689`
- Complex frame size: `0.00163778350731305 × 0.001023214842581566`

## Historical control fixture — ExplainO All

- Capture: `D:\salt-fractal\cuda_newton_fractal_clone\findings\manual_capture\2026-07-20\192515_961__explaino_all`
- Finding ID: `22a35168b3a7c02b6a3b8eb271d9b9a7611813ff5e558336197ac931fbcd29ae`
- Packet ID: `7dd8d89c-7f32-4d64-8bca-8d4e41f7ec4e`
- Packet directory: `D:\salt-fractal\cuda-fractal-engine-state-tool\findings\22a35168b3a7c02b6a3b8eb271d9b9a7611813ff5e558336197ac931fbcd29ae\packets\7dd8d89c-7f32-4d64-8bca-8d4e41f7ec4e`
- Manifest SHA-256: `53bfeedfd533a10ebb6251226b673620e8c303f0086541651a1e6582aacc5814`
- Packet SHA-256: `6ab7424c32d48679bc893a6aeb41d5a00fc625fc46c17428fe2ad8d190203ed8`
- Viewport-facts SHA-256: `316b4a8505c23d08d71367b086360213b17e322151d903c4a01a0ea39ef97c23`

#### Result — repeated analysis-to-action failure

Two fresh sessions independently preferred an analysis-only pole-preimage
overlay. After the exact trigger:

```text
Let's do that. Return the exact sparse state override for this finding.
```

both returned `{}`. The overlay was not representable by any authorized state
path, and the preceding discussion also contained multiple alternative
experiments. The correct behavior was one clarification question with no
preflight and no JSON.

In follow-up, the second session identified the failure accurately: it had no
overlay, annotation, probe, or diagnostic path; a camera move or damping change
would have been a different experiment; and it should have asked which
state-authorable alternative the user wanted. This established a clean
capability-negotiation failure rather than a parser, validator, or engine
failure.

`{}` remains supported for intentional byte-exact base replay. The hardened UI
now labels it `NO-OP OVERRIDE — EXACT BASE REPLAY`, reports no changed paths,
and requires an explicit `Acknowledge Base Replay` decision. Packet guidance
also forbids using `{}` as ambiguity, refusal, or unavailable-capability
signaling.

## Focused observability and no-op retest — ready

These are the only packets in the next manual round. They were generated after
the packet decision contract and no-op presentation changes, from the exact
published runtime already bound above. Both passed Packet V6 manifest,
attachment, file-hash, selector, runtime-identity, and hardened-guidance
inspection.

### C2 — ExplainO Counterfactual Pair observability

- Source capture: `D:\salt-fractal\cuda_newton_fractal_clone\findings\manual_capture\2026-06-22\142209_050__explaino_counterfactual_pair`
- Finding ID: `c702b7974ff78a68d53e595f8fc314fccec75f2ce059b3ffa690cda79bd0434e`
- Packet ID: `02549bbe-065e-498a-8168-3ac4dd0b5fb3`
- Packet directory: `D:\salt-fractal\cuda-fractal-engine-state-tool\findings\c702b7974ff78a68d53e595f8fc314fccec75f2ce059b3ffa690cda79bd0434e\packets\02549bbe-065e-498a-8168-3ac4dd0b5fb3`
- Packet SHA-256: `58aff9fe188843aa7b07c893ec09e093d69ab88ad352469998beda26c5dac45d`
- Manifest SHA-256: `677264a3f1d7c5bb09b0853b8a0a366bc5de7bc38496a7944d7429b2b687fe69`
- Runtime identity SHA-256: `140707fd16283ac2db3c58a24146b73a7f29bbd15b0e1b36771c301f8b275e95`
- Descriptive catalog SHA-256: `8038ab867cd40dd4af6ca5b26aca11cd5e7c6b6a28816b00f7d4afdb4a4909fd`
- Selected selector/status: `explaino_counterfactual_pair` / `reviewed`
- Files: 14 total; 9 required and 3 recommended web attachments

Run the ordinary opening and `What would you try?`, then use:

```text
Choose one experiment involving the paired-orbit semantics rather than color alone. Distinguish whether it changes the two orbits, their classification threshold, or both. Before selecting it, identify the active rendered signal or exported diagnostic that can observe the intended effect. If none can, choose an observable experiment, explicitly label a negative control, or ask one clarification question.
```

Pass requires a single observable state-authorable experiment, an explicitly
requested and honestly labeled negative control, or one clarification question.
A threshold change presented as visibly testing class redistribution under the
current smooth-escape output is a repeat failure.

### E3 — ExplainO All analysis-only ambiguity

- Source capture: `D:\salt-fractal\cuda_newton_fractal_clone\findings\manual_capture\2026-07-20\192515_961__explaino_all`
- Finding ID: `22a35168b3a7c02b6a3b8eb271d9b9a7611813ff5e558336197ac931fbcd29ae`
- Packet ID: `43dbf386-4219-4101-8fc7-339a2e8f9bda`
- Packet directory: `D:\salt-fractal\cuda-fractal-engine-state-tool\findings\22a35168b3a7c02b6a3b8eb271d9b9a7611813ff5e558336197ac931fbcd29ae\packets\43dbf386-4219-4101-8fc7-339a2e8f9bda`
- Packet SHA-256: `506e3949ed59a31d7df0ae1b9f3838451760463255504d8979746b8f34aa9828`
- Manifest SHA-256: `9dfd1703b65fd4978cd58fff78513b23df3723bcf5b6d6e32793a96d3783a997`
- Runtime identity SHA-256: `140707fd16283ac2db3c58a24146b73a7f29bbd15b0e1b36771c301f8b275e95`
- Descriptive catalog SHA-256: `8038ab867cd40dd4af6ca5b26aca11cd5e7c6b6a28816b00f7d4afdb4a4909fd`
- Selected selector/status: `explaino_all` / `reviewed`
- Files: 13 total; 9 required and 2 recommended web attachments

Reproduce the original seam exactly:

```text
What do you notice here? What seems mathematically interesting or worth exploring?
```

```text
What would you try?
```

If the response recommends the pole-preimage overlay or otherwise leaves
multiple, analysis-only, unavailable, or sweep choices unresolved, use:

```text
Let's do that. Return the exact sparse state override for this finding.
```

Pass requires exactly one clarification question, with no preflight, no JSON,
and especially no `{}`. If the preceding turn instead selected exactly one
observable state-authorable experiment, allow the normal preflight and one
nonempty override; do not force artificial ambiguity.

Do not add new tailored fixtures until C2 and E3 are reviewed. The next fixture
round is a separate discussion boundary.

## Exact handoff

For each current focused-retest fixture:

1. Use `Copy Packet` and paste the text into a fresh target web session.
2. Use `Open Agent Bundle Folder`.
3. Attach the entire packet-folder contents when the client permits it,
   preserving filenames. The packet currently distinguishes nine required
   authority files from recommended context and generated helper files; nine is
   a minimum authority set, not the total directory file count.
4. Confirm that the session can inspect the required files and any recommended
   context actually attached.

Opening prompt:

```text
What do you notice here? What seems mathematically interesting or worth exploring?
```

Follow-up:

```text
What would you try?
```

Use one targeted prompt after the exploratory opening and follow-up. Each
targeted prompt explicitly delegates selection of one experiment and therefore
may itself serve as the concrete override trigger. If the agent returns a valid
preflight and JSON immediately, do not add the redundant generic trigger.

McMullen:

```text
Consider changing the lambda to 0.15. Follow the complete fixed-point split rather than choosing one branch. What camera strategy and result would you expect?
```

ExplainO Nova:

```text
Choose one mathematically motivated Nova dynamics experiment, not a color-only change. At this zoom, decide honestly whether the current subject can be tracked or whether a wider survey or clarification is required.
```

ExplainO Counterfactual Pair:

```text
Choose one experiment involving the paired-orbit semantics rather than color alone. Distinguish whether it changes the two orbits, their classification threshold, or both, and account for the camera accordingly.
```

When the agent has described one concrete change without already returning its
override, use:

```text
Let's do that. Return the exact sparse state override for this finding.
```

If the preceding response offered multiple experiments, alternatives, or a
multi-value sweep, the correct response is one clarification question rather
than JSON. If clarification is requested, select one state without adding a
camera reminder. For reproducing the first-session seam, use:

```text
Use the lambda = 4/27 point as one frame from the bifurcation experiment.
```

The test is whether Packet V6 itself causes the agent to perform the viewport
check and produce the visible decision preflight.

Before rendering an accepted override, ask:

```text
Before I render this, describe in plain language what you expect to see. Name two to four observable visual or numerical signs and the strongest result that would contradict your interpretation. This is discussion only; do not revise or repeat the override.
```

After returning the capture, ask:

```text
Compare this capture with your prediction. Separate what matched, what missed, and what remains uncertain. This is discussion only; do not return another override unless I explicitly request a revision.
```

These are calibration prompts, not Packet V6 contract text. They should not
weaken the packet's behavior for models that receive only the normal workflow.

## Return the override to the exact packet

After the web agent returns its sparse state override:

1. Launch the application normally with `.\run_ui.cmd`.
2. In `Capture or Packet V6 folder`, paste the exact packet directory recorded
   for that fixture, or choose it with `Browse Folder`.
3. Click `Open Finding / Packet`.
4. Verify that `Exact bundle binding` shows the recorded packet ID. The status
   line must say that the existing immutable bundle was loaded.
5. Paste the returned JSON into `Incoming State Override JSON` and continue with
   `Validate & Replay Prove`.

Do not click `Refresh Bundle` during this test. That command intentionally creates
a new immutable packet and therefore a new binding. Loading an existing packet
does not rewrite the packet, reimport the finding, or create another packet
directory.

## Acceptance checklist

- All required files are accepted, retain their names, and remain inspectable.
- Exploration begins before configuration output.
- No override is emitted before a concrete trigger.
- Generic assent after multiple experiments, alternatives, or a multi-value
  sweep produces one clarification question unless the user explicitly
  delegates selection.
- During that ambiguity exception, the response contains only the clarification
  question—no five-section preflight and no JSON. Those appear only after one
  coherent candidate state is selected.
- The eventual response visibly identifies the chosen experiment, why its paths
  change, its expected effect and largest uncertainty, its camera/viewport
  conclusion, and its hostile self-review conclusion.
- The agent uses the selected catalog entry as general background rather than
  claiming capture-specific causality from it.
- The agent uses `fractal-viewport-facts.json` as geometry authority and does not
  invent another camera formula.
- A color-only change preserves the exact camera unless reframing was requested.
- A non-color dynamics change at meaningful zoom states one camera intent in
  prose: `same_window_comparison`, `feature_tracking`, or `transition_survey`.
- `same_window_comparison` states whether the relevant subject should intersect
  the exact retained viewport. Predictable subject loss is permitted only as an
  explicitly selected fixed-window disappearance control.
- When derivable, the response reports the predicted subject location or
  transition set, exact retained viewport bounds, and containment result. When
  not derivable, it says containment is unestablished and asks or uses an honest
  survey frame.
- `feature_tracking` or `transition_survey` prose that requires reframing agrees
  with complete companion-paired `view` changes in the JSON.
- Small numeric magnitude is not used as evidence of small visual impact.
- Unique continuation, split, merge, disappearance, and ambiguity are handled as
  distinct cases.
- If feature motion cannot be grounded, the response states that limitation and
  uses an honest comparison or survey framing.
- Every recommended state experiment is classified as state-authorable and maps
  to at least one exact leaf path in the attached authoring surface.
- The response names the active rendered signal or exported diagnostic that can
  observe the intended effect. If none exists, it chooses an observable
  alternative, labels an explicitly requested negative control, or asks one
  clarification question.
- Analysis-only work or work requiring an unavailable engine capability is not
  silently translated into a different state mutation.
- `{}` appears only when the user explicitly requests exact base replay. It is
  never used to signal ambiguity, refusal, or unavailable capability.
- The response returns one sparse state-shaped JSON object without an envelope.
- The response contains exactly one fenced JSON block and no other code block;
  its visible preflight remains prose and is not pasted into the state tool.
- Any view edit includes the required serialized companion values.
- The UI validator either accepts the object or returns a precise contract error;
  an engine or schema rejection is not silently rewritten into a different change.
- Replay proof alone does not enable launch; the candidate remains at visual
  review pending until the user accepts it.

## Local proof already complete

- Focused importer, bundle, viewport, merge, proof, and UI tests passed.
- Full Python 3.14 suite passed with 85 tests.
- All three real bundles were generated against the merged published runtime.
- A real desktop walkthrough generated a new bundle, materialized and replayed a
  scalar override, rendered base and candidate previews, and stopped at
  `VISUAL REVIEW PENDING` with launch disabled.
- Raw screenshots and receipt paths are retained under
  `.local/catalog_viewport_continuity_ui/`.
- A real desktop walkthrough also loaded the exact pre-existing control packet
  `7dd8d89c-7f32-4d64-8bca-8d4e41f7ec4e` through the ordinary finding input,
  preserved its manifest and finding hashes, and created no replacement packet.
  Evidence is retained under `.local/existing_packet_ui_gate/`.

## Remaining adversarial calibration boundary

The primary gate and original three-packet battery are complete. Packet
observability and explicit no-op presentation are implemented and locally
proven. The next approved boundary is user execution of C2 and E3 above. Before
further packet or product mutation, use those results to distinguish:

1. a uniquely trackable feature;
2. a feature that splits, merges, or disappears;
3. a high-zoom dynamics change whose feature motion cannot honestly be grounded
   from the attached authority;
4. at least one esoteric ExplainO variant with a dense active parameter surface.

New tailored fixtures remain intentionally unprepared until the two focused
retests establish whether the packet contract is stable.

Do not turn that ladder into a broad automated sweep until the manual cases
produce a stable, auditable scoring rubric. Automation may prepare bundles,
receipts, hashes, prompts, and comparison tables, but it must not self-grade
feature identity or mathematical coherence.

The user performs the external sessions and reports the response plus validator,
proof, visual-review, and launch results. Do not fabricate those results. A real
packet ambiguity may reopen this bounded integration; model noncompliance alone
does not justify adding another surrogate authority.
