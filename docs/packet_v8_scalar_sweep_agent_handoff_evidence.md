# Packet V8 Scalar Sweep Agent Handoff Evidence

Status: local implementation and real-workflow gates complete; bounded paid
behavioral qualification stopped at a classified provider-credit limitation.

## Implementation checkpoint

- Branch: `codex/packet-v8-sweep-web-review`
- Product checkpoint: `e23bbf1aad17efe6e65f487401c929fe26e4c599`
- Published runtime executable SHA-256:
  `17513a94d277afb6188da1683214731476eddf6649471278129e54e93eea06c3`
- Engine repository and published runtime were not modified by this campaign.

The implementation adds no second state or numeric authority. Packet sweep axes
are projected from the exact Packet V8 authoring surface. Ordinary sparse-state
override validation, runtime materialization, replay proof, timeouts, and
proof-owned candidate PNGs remain the canonical service owners.

## Fresh Packet V8

Source capture:

```text
D:\salt-fractal\cuda_newton_fractal_clone\findings\manual_capture\
2026-08-05\125750_233__explaino_transcendental
```

Generated packet:

```text
D:\salt-fractal\cuda-fractal-engine-state-tool\findings\
af56ad25187bd97210d772b629f98db90cf3e5ddc4a7dbb74cd3672e838d9c7c\
packets\3775efa2-f1f7-4641-9c88-f47be101bc28
```

- `packet.md`: 18,682 bytes;
  SHA-256 `94714b6393f3d63d5a5eabe285796ee058a9373ead8bad269ad4b93349bd4e19`
- `manifest.json`: 10,381 bytes;
  SHA-256 `9bbdeae3604a964e0a32e9c5fe2142eee598cd80a1cbb1d9170dd313f54625e9`
- Exact projected damping base:
  `params.explaino_damping = 1.899999976158142`
- The generated packet describes the mutually exclusive sparse override and
  Scalar Bracket Sweep V1 outputs, the exact plan shape, structurally admissible
  axes, fixed-base policy, prediction requirement, and failure policy.

The packet also lists `epsilon`, `explaino_warp_strength`, and `max_iter` because
they are direct numeric `params` leaves in the exact authoring surface. Their
presence is explicitly structural only and does not claim behavioral fitness.

## Real local transcendental bracket

Sweep:

```text
D:\salt-fractal\cuda-fractal-engine-state-tool\findings\
af56ad25187bd97210d772b629f98db90cf3e5ddc4a7dbb74cd3672e838d9c7c\
sweeps\6018405f-512a-4020-a029-ae585db858b6
```

Plan values:

```text
1.94, 1.97, 1.99, 2.00, 2.02
```

All five independent members completed engine materialization and action-free
replay with `REPLAY_PROVEN`. No automatic acceptance was recorded.

- `plan.json` SHA-256:
  `b32bc5cd2b563ef7b0ad69c17852935b4f5d3f189c9b52b072ed70e96d3ed261`
- `binding.json` SHA-256:
  `9ce8c0103bd8d54877be0be9f4c31d1a20f161a2ad9542ed5ac95183db533da4`
- `receipt.json` SHA-256:
  `0a2ce7f4eb8dcc6f8f30de39370d4067d69d7e9e358e696c6cf0583fbf5d76b0`
- `presentation/contact-sheet-receipt.json` SHA-256:
  `50a73c60b44acb82c6c1d1e7368d05ab8cd79532273567d1bdc182e84186aae0`

The first tile is the hash-verified full captured source, downsampled through the
same presentation renderer. It is labeled `CURRENT / CAPTURED BASE`, records the
exact serialized damping value, and states that it is neither a sweep member nor
newly replay-proven. The observed progression retains dense rings at 1.94-1.99
and collapses most of the field near 2.00-2.02. That is an observation across
these proven samples, not an automatic causal or phase-transition conclusion.

An earlier harness attempt at
`ee838138-2717-40e4-af72-4371c4a32c42` reached three proven members before the
outer test driver reached its own 180-second wait limit. It cancelled the owned
work and preserved a valid partial sweep and web bundle. This was not a product
proof timeout or CUDA failure and serves as additional cancellation evidence.

## Three-file web review

```text
web-review/
  contact-sheet.png
  sweep-evidence.json
  sweep-review.md
```

- `contact-sheet.png`: 919,575 bytes;
  SHA-256 `26b54452e749a94bba6bedecbe5d9522f9d15458079fb9e52d1e401f14cc198d`
- `sweep-evidence.json`: 24,963 bytes;
  SHA-256 `46ebe0fd3da71c30d0529190fdfb83ab941f6390bf3d6861dafc63da76dd1d0c`
- `sweep-review.md`: 2,773 bytes;
  SHA-256 `b470e4a41d35d50be5f5d64d7c0158671c5d10977bc8485bfd997ab79a4ca3b9`

The readable review uses logical member evidence references and contains no
machine-local absolute path. The JSON projection retains the original parsed
documents, relative paths, roles, byte sizes, and hashes; immutable granular
files remain authority. Repeated generation from unchanged source artifacts is
byte-identical. Contact-sheet corruption, source-frame mutation, missing base
provenance, partial members, cancellation, and no-effect classification have
focused coverage.

## Validation

Focused command:

```powershell
$env:PYTHONPATH = (Resolve-Path .\src).Path
py -3.14 -m unittest tests.test_agent_bundle tests.test_scalar_sweep `
  tests.test_sweep_presentation tests.test_app_controller
```

Result: 35 passing tests.

Full command:

```powershell
$env:PYTHONPATH = (Resolve-Path .\src).Path
py -3.14 -m unittest discover -s tests
```

Result: 228 passing tests.

Hostile review found and removed the last generic hard-coded
`params.vortex_strength` plan from the screenshot acceptance helper. That helper
now requires an explicit packet-authorized plan. The review also tightened
`NO_EFFECT_ENGINE_EMITTED_BASE` so it requires exact base/emitted equality plus
the proof receipt's single exact-axis revert error; unrelated proof failures
cannot receive the no-effect label.

## Bounded paid qualification

Cell 1 used the exact Packet V8 above and the tracked Luna High qualification
profile:

```text
model: gpt-5.6-luna
reasoning effort: high
prompt cache: explicit no-cache
model-profile SHA-256:
dbf174b6e03c074b26588e606e6ddb4a27eb5d36bcbb70184863116e39e268b7
maximum output: 4,000 tokens
```

Qualification prompt:

```text
Identify the two tool-assisted state execution modes described by this exact
packet. Then select a Local Scalar Bracket Sweep V1 over
params.explaino_damping to examine the visible collapse near 2 while preserving
the exact packet base, camera, color, and iteration cap. Choose 3 to 5 non-base
values spanning the informative near-2 transition. Return the exact sweep
preflight and one valid sweep-plan JSON block, not a sparse override.
```

The exact count-only request completed before dispatch:

```text
input tokens: 167,293
context tier: short
conservative maximum cost: $0.0382586
per-cell ceiling: $0.12
campaign ceiling: $1.00
```

The one authorized generation request reached the same 167,293-token
pre-dispatch count, then the provider rejected it with:

```text
HTTP 429
code: credit_balance_exhausted
message: You have no credits remaining. Add credits to continue using the API.
```

The provider created no model response and returned no usage receipt. This
report therefore does not infer a billed amount. All uploaded provider files
were deleted successfully. There was no retry and the three-file result-review
cell was not dispatched. Raw sanitized request, count, failure, and cleanup
evidence is preserved under:

```text
.local/packet_v8_scalar_sweep_agent_handoff_qualification/cell1/
```

The paid gate is `PROVIDER_CREDIT_BLOCKED`, not a model-behavior pass or failure.
The campaign's decisive closure explicitly permits a classified limitation.

Hostile review confirmed that the failure occurred after the exact count and
dispatch authorization but before any model response, so it cannot be used to
judge the packet prompt. The transport classified the provider's 429 through
its generic rate-limit category; the stable campaign conclusion records the
more specific provider error code. The review also confirmed exact owned-file
cleanup and rejected a retry, a second-cell dispatch, or a claim of zero billed
cost without a provider usage receipt.

## Closure boundary

Complete repository closure without claiming paid behavioral acceptance. A
future paid rerun requires restored provider credit and a separately confirmed
execution boundary; it must begin again with exact count-only preflight and may
not reuse this failed turn as conversational history.
