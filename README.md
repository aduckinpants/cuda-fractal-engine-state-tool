# CUDA Fractal Engine State Tool

This repository hosts a small experimental Python tool for creating and validating CUDA fractal engine state workflows without duplicating engine-state authority.

Current status:

- Phase 0 in progress: runtime authority probe
- No main UI yet
- Raw probe outputs live under ignored `.local/`
- Stable conclusions are tracked in `docs/runtime_authority_probe.md`

## Phase 0 goals

1. Resolve and observe the published runtime launcher.
2. Capture runtime identity.
3. Probe no-input diagnostic capture behavior.
4. Compare repeated captures both raw and semantically.
5. Replay at least one captured state.
6. Observe describe-metadata surfaces.
7. Document what the runtime actually proves.

## Local commands

Run tests:

```powershell
$env:PYTHONPATH = "src"
py -3 -m unittest discover -s tests
```

Run the runtime probe:

```powershell
py -3 -m cuda_fractal_state_tool.runtime_probe --runtime-cmd "D:\salt-fractal\cuda_newton_fractal_clone\runtime\fractal_ui.cmd" --output-root ".local\runtime_probe"
```
