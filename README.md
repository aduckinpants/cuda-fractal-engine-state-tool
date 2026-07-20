# CUDA Fractal Engine State Tool

This repository hosts a small experimental Python tool for creating and validating CUDA fractal engine state workflows without duplicating engine-state authority.

Current status:

- Phase 0 complete: runtime authority probe committed at `102c5bd`
- Phase 1 complete: bounded proposal loop, replay proof workflow, and slim desktop UI
- Phase 2 complete (bounded scope): replay-proven color triplet coverage expansion, promotion profile controls, and CLI-first execution/reporting paths
- Phase 3 decision pending: whether to keep the bounded scalar+triplet contract or begin `color_pipeline_draft` authoring work
- Raw probe outputs live under ignored `.local/`
- Stable conclusions are tracked in `docs/runtime_authority_probe.md`
- Phase 2 closure summary is tracked in `docs/phase2_closure.md`

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

Run the Phase 1 integration workflow tests:

```powershell
$env:PYTHONPATH = "src"
py -3 -m unittest discover -s tests
```

Inspect validation runs (summary/list/latest with filters):

```powershell
$env:PYTHONPATH = "src"
py -3.14 -m cuda_fractal_state_tool.validation_runs
py -3.14 -m cuda_fractal_state_tool.validation_runs --list --status runtime_proof_succeeded
py -3.14 -m cuda_fractal_state_tool.validation_runs --list --status runtime_proof_succeeded --limit 5
py -3.14 -m cuda_fractal_state_tool.validation_runs --latest --promotion-profile observed_runtime_enrichment_v1
py -3.14 -m cuda_fractal_state_tool.validation_runs --list --since 2026-07-20T00:00:00+00:00 --until 2026-07-21T00:00:00+00:00
```

Run a proposal workflow from a proposal file (non-UI path):

```powershell
$env:PYTHONPATH = "src"
py -3.14 -m cuda_fractal_state_tool.workflow_cli --proposal .local\example_proposal.json --promotion-profile none
py -3.14 -m cuda_fractal_state_tool.workflow_cli --proposal .local\example_proposal.json --promotion-profile none --launch-viewer-on-success
```

Generate proposal examples (for workflow_cli input):

```powershell
$env:PYTHONPATH = "src"
py -3.14 -m cuda_fractal_state_tool.proposal_cli --example noop --out .local\proposal_noop.json
py -3.14 -m cuda_fractal_state_tool.proposal_cli --example color-triplet --signal root_proximity --palette cyclic_escape --grading tone_map_default --out .local\proposal_triplet.json
py -3.14 -m cuda_fractal_state_tool.proposal_cli --list-color-triplets
py -3.14 -m cuda_fractal_state_tool.workflow_cli --proposal .local\proposal_triplet.json --promotion-profile none
```

Run the minimal UI:

```powershell
./run_ui.cmd
```

The UI includes a promotion profile selector used by Replay Prove (`none`, single-key profiles, and combined observed enrichment).

Direct module launch (equivalent):

```powershell
$env:PYTHONPATH = "src"
py -3.14 -m cuda_fractal_state_tool.app
```

