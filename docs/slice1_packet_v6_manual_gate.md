# Packet V6 Slice 1 Manual Transport Gate

Status: acceptance-ready; external web-session result pending.

The execution agent completed the local Packet V6 implementation and stopped before sparse-override implementation, as required by the approved rescue plan.

## Exact acceptance fixture

- Capture: `D:\salt-fractal\cuda_newton_fractal_clone\findings\manual_capture\2026-07-20\192515_961__explaino_all`
- Finding ID: `22a35168b3a7c02b6a3b8eb271d9b9a7611813ff5e558336197ac931fbcd29ae`
- Packet ID: `d1e71ba9-a302-42dc-9bd2-1e4c1936679d`
- Packet directory: `D:\salt-fractal\cuda-fractal-engine-state-tool\findings\22a35168b3a7c02b6a3b8eb271d9b9a7611813ff5e558336197ac931fbcd29ae\packets\d1e71ba9-a302-42dc-9bd2-1e4c1936679d`
- `packet.md` SHA-256: `5618c662b30b63ec527226ae925fa12585a860578cdfcb4a874924e6baf0d51d`
- `manifest.json` SHA-256: `2d05c6d4d56dadc249196276f0074a6446ea1c2945b5bf5f4e51c2fc11573d15`
- Runtime identity SHA-256: `9a65702321cdd5c73c59e87f92401b82bc78780222c59d940fa2478f953a06c8`
- Descriptive catalog SHA-256: `21184b8af87d3fe2cc7e652cba5a125b54876a265ae2fe99595dc7f4a46262c0`
- Selected selector/status: `explaino_all` / `reviewed`

## Exact handoff commands

```powershell
$packetDir = 'D:\salt-fractal\cuda-fractal-engine-state-tool\findings\22a35168b3a7c02b6a3b8eb271d9b9a7611813ff5e558336197ac931fbcd29ae\packets\d1e71ba9-a302-42dc-9bd2-1e4c1936679d'
Get-Content -Raw -LiteralPath (Join-Path $packetDir 'packet.md') | Set-Clipboard
Start-Process explorer.exe -ArgumentList $packetDir
```

Paste the clipboard text into one fresh target web session. Then attach these required files from the opened directory, preserving their filenames:

1. `state.json`
2. `fractal-state.json`
3. `fractal-parameter-surface.json`
4. `fractal_binding_surface_v1.ui_schema.json`
5. `color_pipeline_function_library.contract.v1.json`
6. `fractal-descriptive-catalog.json`
7. `state-override-authoring-surface.json`
8. `frame.png`

Also attach the available recommended context files when the client permits it:

1. `finding.json`
2. `field-notes.md`

No optional attachment is missing from this fixture.

## Exact prompt

```text
What do you notice here? What seems mathematically interesting or worth exploring?
```

## Acceptance checklist

Record pass or fail for every rule:

- The client accepts all eight required attachments together.
- The client preserves each filename exactly.
- The agent can inspect every required attachment; none is silently ignored or truncated beyond usability.
- The agent correctly identifies `state.json` as replay authority, the parameter surface as applicability authority, the UI schema as control/binding authority, the UI-Salt contract as Color Pipeline authority, and the authoring surface as the finding-specific state-override index.
- The agent uses the frame for direct observations and the selected engine-owned description for general mathematical background.
- The agent distinguishes applicable controls from state-override-authorable controls.
- The agent does not infer activity or visible contribution merely from serialized field presence or nonzero values.
- The agent does not claim basins from a continuous signal, visible symmetry from serialized root symmetry, spatial localization from global statistics, or exact self-similarity from one frame.
- The agent remains exploration-first and emits no state override without a concrete change trigger.
- The concise `packet.md` index is sufficient to navigate the attached authorities without the former embedded giant packet.

If the web client fails to transport or expose the files, classify that as a transport failure and revise transport only. Do not reinterpret the authority model and do not begin Slice 2.

## Local implementation evidence

- Focused Packet V6, finding-import, and catalog tests pass under Python 3.14.
- The full local Python 3.14 suite passes with 134 tests discovered.
- Real July 20 bundle generation and subsequent manifest inspection pass against the published runtime.
- A second real finding with a complete serialized Color Pipeline draft generated a contract-validated whole-array example at packet `af3795c1-2878-45f0-8d57-571958b0a90e` under finding `a749836d7e1b65025b6188c20079e4b619c6d4596dc36d7affaa9012ab5d7729`.

Slice 2 remains blocked until the user performs the external session and reports this checklist result.
