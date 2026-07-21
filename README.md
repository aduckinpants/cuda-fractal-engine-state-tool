# CUDA Fractal Engine State Tool

This repository hosts a small experimental Python tool for creating and validating CUDA fractal engine state workflows without duplicating engine-state authority.

Current status:

- Phase 0 complete: runtime authority probe committed at `102c5bd`
- Phase 1 complete: bounded proposal loop, replay proof workflow, and slim desktop UI
- Phase 2 complete (bounded scope): replay-proven color triplet coverage expansion, promotion profile controls, and CLI-first execution/reporting paths
- UI rescue implementation is operational on `codex/user-workflow-ui-rescue`; final operational UX acceptance is pending user review. The rejected Phase 3 surface is preserved at `archive/vscode-phase3-ui`.
- Raw probe outputs live under ignored `.local/`
- Stable conclusions are tracked in `docs/runtime_authority_probe.md`
- Phase 2 closure summary is tracked in `docs/phase2_closure.md`
- Phase 3 start checkpoint is tracked in `docs/phase3_start_checkpoint.md`
- The approved five-slice rescue contract is tracked in `docs/user_workflow_ui_rescue.md`
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

Controlled Color Pipeline authority proof (compiled UI-Salt -> engine action -> action-free replay):

```powershell
$env:PYTHONPATH = "src"
py -3.14 -m cuda_fractal_state_tool.color_authority_cli --runtime-cmd D:\salt-fractal\cuda_newton_fractal_clone\runtime\fractal_ui.cmd --base-state .local\baselines\runtime-default-v1\state.json --out .local\slice1_color_authority_proof
```

Prompt-session harness for repeatable agent-style tests:

```powershell
$env:PYTHONPATH = "src"
py -3.14 -m cuda_fractal_state_tool.prompt_session_cli --pack .local\prompt_session_pack.json
```

Legacy frozen-baseline agent handoff CLI:

```powershell
$env:PYTHONPATH = "src"
py -3.14 -m cuda_fractal_state_tool.agent_handoff_cli --baseline-manifest .local\baselines\runtime-default-v1\manifest.json --replay-state .local\runtime_probe\replay_one\state.json --out .local\agent_handoff_packet.md
```

Give the generated `.local\agent_handoff_packet.md` to a fresh agent session only for the older frozen-baseline CLI workflow.
It defines terms (`state.json` vs `proposal_v1`), runtime-authoritative loop, output contract, and run commands.

Current runtime note:

- Color Pipeline lane/function authority comes from the deployed compiled UI-Salt contract, not `--describe-functions`.
- Direct sparse-draft workflow materialization fails closed with `color_pipeline_draft_requires_engine_action_workflow`; the desktop finding workflow lowers bounded row-0 selections through the engine action seam.
- Bounded scalar/triplet prompt packs run now and are suitable for immediate real-session harness validation.

Example pack schema:

```json
{
	"session_id": "noop-smoke-pack",
	"cases": [
		{
			"case_id": "noop",
			"proposal_path": ".local/proposal_noop.json",
			"state_id": "noop_run",
			"promotion_profile": "none",
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
py -3.14 -m cuda_fractal_state_tool.proposal_cli --list-color-triplets
py -3.14 -m cuda_fractal_state_tool.workflow_cli --proposal .local\proposal_triplet.json --promotion-profile none
```

`proposal_v1` remains structurally unchanged. Draft payloads use the exact packet-bound desktop workflow; the legacy direct workflow rejects them rather than writing an incomplete engine state.

Inspect the compiled UI-Salt lane/function authority (fail-closed bounded projection):

```powershell
$env:PYTHONPATH = "src"
py -3.14 -m cuda_fractal_state_tool.lane_catalog_cli --ui-salt-contract D:\salt-fractal\cuda_newton_fractal_clone\runtime\ui_salt\generated\color_pipeline_function_library.contract.v1.json
py -3.14 -m cuda_fractal_state_tool.lane_catalog_cli --ui-salt-contract D:\salt-fractal\cuda_newton_fractal_clone\runtime\ui_salt\generated\color_pipeline_function_library.contract.v1.json --check-lane shape --check-function repeat
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

Run the fresh finding-to-proof shell:

```powershell
.\run_ui.cmd
```

The active application has one two-column workflow surface. Opening a finding
automatically creates an agent exploration packet containing the exact captured
`state.json`, readable finding context, deployed UI-Salt function semantics,
parser-validated examples, and closing machine-binding metadata. The proposal
editor starts empty.

`Validate & Replay Prove` binds the exact packet and proposal text, applies
scalar overrides, lowers bounded Color Pipeline row-0 selections through the
engine action seam, captures the engine-emitted candidate, and replays that
candidate without actions. Actionable proposal rejection enables a bound repair
packet. Successful proof enables launch only for the exact rehashed candidate,
runtime, contract, packet, and proposal binding.

Durable finding artifacts are laid out under the configured workspace:

- `findings/<finding-id>/source/` — mirrored read-only capture artifacts;
- `findings/<finding-id>/packets/<packet-id>/` — exact packet and manifest;
- `findings/<finding-id>/proofs/<proof-id>/` — binding, proposal, intermediate
  base, materialization, replay, repair when actionable, proven candidate, and
  receipt.

Direct module launch (equivalent):

```powershell
$env:PYTHONPATH = "src"
py -3.14 -m cuda_fractal_state_tool.app
```

The failed notebook/controller is available only through
`archive/vscode-phase3-ui`; it is not present in the active application code.

