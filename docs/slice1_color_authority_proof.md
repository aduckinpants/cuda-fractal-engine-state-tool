# Slice 1 Controlled Color Authority Proof

## Closure

Slice 1 passed against the published runtime without changing the engine
repository. The deployed compiled UI-Salt contract is now the lane/function
authority. The callable `--describe-functions` registry is no longer accepted
as Color Pipeline metadata.

The archived sparse-draft workflow is explicitly unavailable until the exact
packet-bound engine-action workflow lands after interaction-model acceptance.
It fails with `color_pipeline_draft_requires_engine_action_workflow` instead of
writing an incomplete draft into `state.json`.

## Real proof

Command:

```powershell
$env:PYTHONPATH = "src"
py -3.14 -m cuda_fractal_state_tool.color_authority_cli --runtime-cmd D:\salt-fractal\cuda_newton_fractal_clone\runtime\fractal_ui.cmd --base-state .local\baselines\runtime-default-v1\state.json --out .local\slice1_color_authority_proof_retry
```

Raw receipt:
`.local/slice1_color_authority_proof_retry/receipt.json`

- launcher SHA-256: `2f532fc917362ba0db0c5e95e5ea0cd966786fabc73229e47c030ad94600012a`
- executable SHA-256: `ea5216d33fc18b04fa9411627fecc456346fda8c32a0d53e1e703172ace08ec3`
- UI-Salt contract SHA-256: `4f38cd329e108a0321a745e3e121648f9af2547a84320200cc37548b52c8f9bb`
- controlled base SHA-256: `5c3c3abe2eeb5c5d128f42f9394f2045a58be95932ddc0afb705b68ebb64b23c`
- controlled base: two action-free captures were byte- and pixel-identical
- selected change: `select_function:shape:0:repeat`
- rendered effect: decoded pixels differed from the controlled `identity` base
- replay: two action-free replays preserved the requested selection
- parity: materialization and both replays had the same encoded frame hash
- launchability: the complete engine-emitted state loaded and captured twice

The first persisted run is retained under
`.local/slice1_color_authority_proof/`. It failed before validation because the
tool had not created the engine report directory. The service now creates that
directory before invoking the runtime, and the regression fixture asserts this
ownership requirement.

## Bounded implementation

The Python projection reads only lane order, lane ID, default function ID, and
function IDs from `function_library.lanes`. It rejects duplicate lanes,
duplicate functions, missing defaults, and callable-registry shapes. It does
not model parameters, recipes, row stacking, or generalized compatibility.

Runtime identity and metadata-cache identity now include the deployed UI-Salt
contract path and hash, preventing a changed contract from reusing stale
authority evidence.
