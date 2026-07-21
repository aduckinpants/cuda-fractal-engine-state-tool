# Web Session Quickstart (Python UI)

This is the shortest path to success when you are copy/pasting workflow in a web chat.

## 60-second version

1. Start UI:

```powershell
./run_ui.cmd
```

2. In the UI:
- Keep Example: No-Op loaded (default).
- Choose Promotion profile (`none` is fine).
- Leave State id as generated.

3. In Web Session Workflow panel:
- Click Step 1: Save Proposal
- Click Step 2: Copy Commands
- Paste/run those commands in terminal or web session
- After run, click Step 3: Copy Evidence
- Paste evidence into web chat

If you already have a captured engine state path:

- Paste it into Captured state.json path
- Click Build Proposal From state.json
- Then continue Step 1/2/3 as above

That is the core loop.

## Exact click order (first real run)

1. Open UI with `./run_ui.cmd`.
2. Confirm top status line shows baseline loaded.
3. Click Example: No-Op (if unsure).
4. In Web Session Workflow, check Proposal file path.
5. Click Step 1: Save Proposal.
6. Click Step 2: Copy Commands.
7. Paste commands into terminal and run.
8. Back in UI, click Step 3: Copy Evidence.
9. Paste evidence into web chat.

## Concept bridge: where files actually go

In the UI, use Output Folder Map (Concept Bridge). It shows these groups:

1. capture_finding_output_folder
This is the capture/probe output root (typically `.local/runtime_probe`).

2. local_files_root
This is the main local workspace data root (typically `.local`).

3. local_baseline_group
Frozen baseline artifacts (typically `.local/baselines`).

4. next_working_state_subfolder
The exact per-run working subfolder that will be created for the current State id.

5. next_validation_run_subfolder
The exact per-run validation subfolder that will be created for the current State id.

6. last_working_state_subfolder / last_validation_run_subfolder
Appears after a run and points to the most recent created run folders.

Use these UI actions:

- Refresh Output Map
- Copy Output Map
- Open Local Files Root

You also get a tree view now:

- Capture Finding Output
- Baseline
- Session Inputs
- Next Run Folders
- Last Run

Select any row to see a plain-English explanation and exact path.

## What success looks like

You should see these values in evidence:

- status: runtime_proof_succeeded
- runtime_status: runtime_success
- validation_path: <path>
- validation_run_manifest_path: <path>
- validation_runs_index_path: <path>

## state.json vs proposal.json (critical)

`state.json`:

- Full engine snapshot with many fields.
- Comes from runtime capture/output folders.
- Not directly the same thing as a bounded proposal.

`proposal.json`:

- Sparse override document relative to frozen baseline.
- Only allowed proposal_v1 paths are accepted.
- This is what workflow_cli and replay proof consume.

Bridge action in UI:

- Build Proposal From state.json converts full captured state to bounded proposal overrides (fail-closed if out of contract).

## Fresh agent entrypoint (use this, not random snippets)

If you are starting a brand-new agent session, generate one canonical handoff packet:

```powershell
$env:PYTHONPATH = "src"
py -3.14 -m cuda_fractal_state_tool.agent_handoff_cli --baseline-manifest .local\baselines\runtime-default-v1\manifest.json --replay-state .local\runtime_probe\replay_one\state.json --out .local\agent_handoff_packet.md
```

Then give that single file to the fresh agent:

- `.local\agent_handoff_packet.md`

That packet tells the agent:

1. What a full state is.
2. What a proposal is.
3. What replay proof means.
4. What output format to return.
5. Which commands to run.

## If it fails

### Proposal validation failure

- Cause: proposal JSON is out of contract.
- Fix: click Example: No-Op and retry.

### Runtime metadata shape unsupported (draft cases)

- Cause: current runtime describe-functions does not expose lane/function catalog shape needed for draft lane validation.
- Fix: run bounded scalar/triplet/no-op cases for real sessions; keep draft lane cases parked until runtime exposes expected catalog shape.

### Runtime proof failed

- Run:

```powershell
$env:PYTHONPATH = "src"
py -3.14 -m cuda_fractal_state_tool.validation_runs --latest
```

- Paste latest output into web session for triage.

## Copy/paste templates

### Template A: run what UI prepared

```text
Use the saved proposal path and state_id from my UI.
Run the workflow commands exactly, then paste back:
1) status/runtime_status
2) validation_path
3) validation_run_manifest_path
4) validation_runs_index_path
5) git status --short
```

### Template B: fast retry

```text
Repeat the same run with a new state_id suffix _retry1.
Keep promotion profile unchanged.
Return only status/runtime_status and validation paths.
```

## Optional CLI-only path (no UI)

```powershell
$env:PYTHONPATH = "src"
py -3.14 -m cuda_fractal_state_tool.proposal_cli --example noop --baseline-manifest .local\baselines\runtime-default-v1\manifest.json --out .local\proposal_noop.json
py -3.14 -m cuda_fractal_state_tool.workflow_cli --proposal .local\proposal_noop.json --baseline-manifest .local\baselines\runtime-default-v1\manifest.json --working-root .local\working_states --state-id cli_noop_run --promotion-profile none
py -3.14 -m cuda_fractal_state_tool.validation_runs --latest
```

## End of slice checklist

```powershell
git status --short
```

Expected: no output.
