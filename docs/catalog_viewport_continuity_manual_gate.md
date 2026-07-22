# Catalog And Viewport Continuity Manual Gate

Status: acceptance-ready; downstream web-session review is pending user execution.

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
3. Attach all nine required files listed by the packet, preserving filenames.
4. Attach recommended context files when the client permits it.

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

Do not add a camera reminder to that trigger. The test is whether Packet V6 itself
causes the agent to apply the continuity rule.

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
- The agent uses the selected catalog entry as general background rather than
  claiming capture-specific causality from it.
- The agent uses `fractal-viewport-facts.json` as geometry authority and does not
  invent another camera formula.
- A color-only change preserves the exact camera unless reframing was requested.
- A non-color dynamics change at meaningful zoom states one camera intent in
  prose: `same_window_comparison`, `feature_tracking`, or `transition_survey`.
- Small numeric magnitude is not used as evidence of small visual impact.
- Unique continuation, split, merge, disappearance, and ambiguity are handled as
  distinct cases.
- If feature motion cannot be grounded, the response states that limitation and
  uses an honest comparison or survey framing.
- The response returns one sparse state-shaped JSON object without an envelope.
- Any view edit includes the required serialized companion values.
- The UI validator either accepts the object or returns a precise contract error;
  an engine or schema rejection is not silently rewritten into a different change.
- Replay proof alone does not enable launch; the candidate remains at visual
  review pending until the user accepts it.

## Local proof already complete

- Focused importer, bundle, viewport, merge, proof, and UI tests passed.
- Full Python 3.14 suite passed with 81 tests.
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

## Stop condition

The user performs the external sessions and reports the response plus validator,
proof, visual-review, and launch results. Do not fabricate those results. A real
packet ambiguity may reopen this bounded integration; model noncompliance alone
does not justify adding another surrogate authority.
