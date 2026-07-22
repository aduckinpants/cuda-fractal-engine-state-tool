# Catalog And Viewport Continuity Manual Gate

Status: the hardened primary McMullen calibration is the first strong
end-to-end pass. Broader adversarial calibration remains open; this pass does
not by itself close split, disappearance, or ungroundable-feature behavior.

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

## Contrast fixture — ExplainO Multibrot root-trap

- Capture: `D:\salt-fractal\cuda_newton_fractal_clone\findings\manual_capture\2026-07-21\230610_719__explaino_multibrot_root_trap`
- Finding ID: `e682f599e459082a341bc95238377e2f782ac85c08967bbf44c4f07efd3025c1`
- Packet ID: `cd0d3224-241b-4ded-aa74-6c5ca826d4d8`
- Packet directory: `D:\salt-fractal\cuda-fractal-engine-state-tool\findings\e682f599e459082a341bc95238377e2f782ac85c08967bbf44c4f07efd3025c1\packets\cd0d3224-241b-4ded-aa74-6c5ca826d4d8`
- Manifest SHA-256: `3089a2ec9f022414399c11d1296b23fa10afb0d1d249d9c1dfe6f6db0796b27a`
- Packet SHA-256: `19871052aff74c291d2a772ddd82e5e07c7d9005e6b6d5fa1d18f4962746df12`
- Viewport-facts SHA-256: `3dccb3ba4c0509a6a121dfb8367a35c97b35e36f456b08479854f955705c9c7e`
- `log2_zoom`: `11.932675187687689`
- Complex frame size: `0.00163778350731305 × 0.001023214842581566`

## Control fixture — ExplainO All

- Capture: `D:\salt-fractal\cuda_newton_fractal_clone\findings\manual_capture\2026-07-20\192515_961__explaino_all`
- Finding ID: `22a35168b3a7c02b6a3b8eb271d9b9a7611813ff5e558336197ac931fbcd29ae`
- Packet ID: `7dd8d89c-7f32-4d64-8bca-8d4e41f7ec4e`
- Packet directory: `D:\salt-fractal\cuda-fractal-engine-state-tool\findings\22a35168b3a7c02b6a3b8eb271d9b9a7611813ff5e558336197ac931fbcd29ae\packets\7dd8d89c-7f32-4d64-8bca-8d4e41f7ec4e`
- Manifest SHA-256: `53bfeedfd533a10ebb6251226b673620e8c303f0086541651a1e6582aacc5814`
- Packet SHA-256: `6ab7424c32d48679bc893a6aeb41d5a00fc625fc46c17428fe2ad8d190203ed8`
- Viewport-facts SHA-256: `316b4a8505c23d08d71367b086360213b17e322151d903c4a01a0ea39ef97c23`

## Exact handoff

For each selected fixture:

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

When the agent has described one concrete change worth testing:

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
- Full Python 3.14 suite passed with 82 tests.
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

The primary gate above passed. Before further packet or product mutation,
qualify a small ladder of real captures that distinguishes:

1. a uniquely trackable feature;
2. a feature that splits, merges, or disappears;
3. a high-zoom dynamics change whose feature motion cannot honestly be grounded
   from the attached authority;
4. at least one esoteric ExplainO variant with a dense active parameter surface.

Do not turn that ladder into a broad automated sweep until the manual cases
produce a stable, auditable scoring rubric. Automation may prepare bundles,
receipts, hashes, prompts, and comparison tables, but it must not self-grade
feature identity or mathematical coherence.

The user performs the external sessions and reports the response plus validator,
proof, visual-review, and launch results. Do not fabricate those results. A real
packet ambiguity may reopen this bounded integration; model noncompliance alone
does not justify adding another surrogate authority.
