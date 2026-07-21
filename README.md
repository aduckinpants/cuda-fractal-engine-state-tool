# CUDA Fractal Engine State Tool

This repository hosts a small experimental Python tool for creating and validating CUDA fractal engine state workflows without duplicating engine-state authority.

Current status:

- Phase 0 complete: runtime authority probe committed at `102c5bd`
- Phase 1 complete: bounded proposal loop, replay proof workflow, and slim desktop UI
- Phase 2 complete (bounded scope): replay-proven color triplet coverage expansion, promotion profile controls, and CLI-first execution/reporting paths
- Phase 3 in progress: runtime metadata-cache wiring plus fail-closed lane/function metadata validation is active; bounded full `color_pipeline_draft` replacement is available in proposal_v1
- Raw probe outputs live under ignored `.local/`
- Stable conclusions are tracked in `docs/runtime_authority_probe.md`
- Phase 2 closure summary is tracked in `docs/phase2_closure.md`
- Phase 3 start checkpoint is tracked in `docs/phase3_start_checkpoint.md`
- Web-session copy/paste usage guide is tracked in `USER_GUIDE_WEB_SESSION.md`

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

Summary output includes draft triage fields:

- `draft_run_count`
- `draft_lane_total`
- `latest_draft_run`

Run a proposal workflow from a proposal file (non-UI path):

```powershell
$env:PYTHONPATH = "src"
py -3.14 -m cuda_fractal_state_tool.workflow_cli --proposal .local\example_proposal.json --promotion-profile none
py -3.14 -m cuda_fractal_state_tool.workflow_cli --proposal .local\example_proposal.json --promotion-profile none --launch-viewer-on-success
```

Phase 3 draft smoke path (proposal -> workflow -> validation-runs query):

```powershell
$env:PYTHONPATH = "src"
py -3.14 -m cuda_fractal_state_tool.proposal_cli --example color-pipeline-draft --draft-lane shape --draft-function identity --out .local\proposal_draft_smoke.json
py -3.14 -m cuda_fractal_state_tool.workflow_cli --proposal .local\proposal_draft_smoke.json --promotion-profile color_pipeline_draft_only_v1 --state-id draft_smoke_cli
py -3.14 -m cuda_fractal_state_tool.validation_runs --list --promotion-profile color_pipeline_draft_only_v1 --status runtime_proof_succeeded --limit 5
```

Prompt-session harness for repeatable agent-style tests:

```powershell
$env:PYTHONPATH = "src"
py -3.14 -m cuda_fractal_state_tool.prompt_session_cli --pack .local\prompt_session_pack.json
```

Canonical fresh-agent onboarding (recommended):

```powershell
$env:PYTHONPATH = "src"
py -3.14 -m cuda_fractal_state_tool.agent_handoff_cli --baseline-manifest .local\baselines\runtime-default-v1\manifest.json --replay-state .local\runtime_probe\replay_one\state.json --out .local\agent_handoff_packet.md
```

Give the generated `.local\agent_handoff_packet.md` to a fresh agent session.
It defines terms (`state.json` vs `proposal_v1`), runtime-authoritative loop, output contract, and run commands.

Current runtime note:

- Real draft-lane prompt packs require runtime `describe-functions` metadata that includes lane/function catalog shape.
- If runtime metadata lacks lane/function entries, draft cases fail closed with `runtime_metadata_shape_unsupported`.
- Bounded scalar/triplet prompt packs run now and are suitable for immediate real-session harness validation.

Example pack schema:

```json
{
	"session_id": "draft-smoke-pack",
	"cases": [
		{
			"case_id": "draft-identity",
			"proposal_path": ".local/proposal_draft_smoke.json",
			"state_id": "draft_identity_run",
			"promotion_profile": "color_pipeline_draft_only_v1",
			"expected_status": "runtime_proof_succeeded",
			"expected_runtime_status": "runtime_success"
		}
	]
}
```

Checked-in starter pack:

- `tests/fixtures/prompt_session_pack.sample.json`

The workflow CLI JSON payload now includes `runtime_metadata_cache` copied from the validation artifact.
Use this field to verify cache hit/miss behavior and metadata provenance paths before lane-authoring decisions.

Generate proposal examples (for workflow_cli input):

```powershell
$env:PYTHONPATH = "src"
py -3.14 -m cuda_fractal_state_tool.proposal_cli --example noop --out .local\proposal_noop.json
py -3.14 -m cuda_fractal_state_tool.proposal_cli --example color-triplet --signal root_proximity --palette cyclic_escape --grading tone_map_default --out .local\proposal_triplet.json
py -3.14 -m cuda_fractal_state_tool.proposal_cli --example color-pipeline-draft --draft-lane shape --draft-function identity --out .local\proposal_draft.json
py -3.14 -m cuda_fractal_state_tool.proposal_cli --list-color-triplets
py -3.14 -m cuda_fractal_state_tool.workflow_cli --proposal .local\proposal_triplet.json --promotion-profile none
py -3.14 -m cuda_fractal_state_tool.workflow_cli --proposal .local\proposal_draft.json --promotion-profile none
```

Proposal CLI intentionally remains bounded: it emits scalar and replay-proven triplet examples only.
Bounded `color_pipeline_draft` full replacement payloads are accepted in `proposal_v1` and validated during workflow execution.

Inspect runtime metadata for lane/function catalog discovery (fail-closed parser):

```powershell
$env:PYTHONPATH = "src"
py -3.14 -m cuda_fractal_state_tool.lane_catalog_cli --describe-functions .local\runtime_probe\describe-functions.json
py -3.14 -m cuda_fractal_state_tool.lane_catalog_cli --describe-functions .local\runtime_probe\describe-functions.json --check-lane shape --check-function identity
```

When `--check-lane` and `--check-function` are provided, the CLI returns explicit fail-closed statuses for mismatch:

- `lane_unknown`
- `function_unknown`

Example bounded draft override payload in proposal_v1:

```json
{
	"proposal_version": 1,
	"base_state": {
		"id": "runtime-default-v1",
		"sha256": "<baseline sha256>"
	},
	"overrides": {
		"color_pipeline_draft": {
			"lanes": [
				{
					"lane_id": "shape",
					"function_id": "identity"
				}
			]
		}
	}
}
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

