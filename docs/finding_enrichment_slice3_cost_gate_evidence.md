# Slice 3 Evidence — Exact-Count Dollar Dispatch Gate

Date: 2026-08-03

Branch: `codex/finding-enrichment-v9-sweep`

Paid generation calls: **none**

## Outcome

Automated generation now has an explicit USD run budget in addition to the
existing response, round, and token limits. The UI initializes the run budget
to `0.00`; a user must enter a non-negative amount deliberately.

The dispatch sequence is:

```text
bind and upload exact manifest resources
-> call Responses input-token count endpoint
-> price the exact counted input conservatively plus maximum output
-> compare with remaining run budget
-> generate only when the controller authorizes dispatch
```

A rejection occurs before `responses.create`. Files uploaded for the rejected
turn are deleted through the existing owned-file cleanup path.

## Locked pricing input

The packaged default is
`src/cuda_fractal_state_tool/openai_pricing_policy.v1.json`. Its exact bytes are
hashed into the run projection and its identity is written into the run
manifest and every estimate/actual-cost receipt. A caller can select another
exact V1 file with:

```powershell
$env:CUDA_FRACTAL_OPENAI_PRICING_POLICY = "C:\path\pricing-policy.v1.json"
```

Unknown models, duplicate aliases, malformed rates, non-USD currency, and
non-standard service tiers fail closed. The local policy is not billing
authority and includes the disclaimer in receipts.

The 2026-08-03 default records the then-current standard short/long GPT-5.6
Sol, Terra, and Luna rates from:

- <https://developers.openai.com/api/docs/pricing>

The cache accounting and exact count path were checked against:

- <https://developers.openai.com/api/docs/guides/prompt-caching>
- <https://api.openai.com/v1/responses/input_tokens>

The policy's 272,000-token context boundary is an explicit versioned local
input. Re-entry must replace or reconfirm the policy rather than treating this
tracked file as perpetually current.

## Conservative estimate

Before generation, the exact counted input is priced entirely at the greatest
applicable input-side rate among ordinary input, cache read, and cache write.
Maximum requested output is added at the applicable output rate. This avoids
assuming a cache hit before the provider reports one.

After a response, calculated cost separates:

```text
ordinary input
cached input reads
cache writes
output
```

`cache_write_tokens` is retained independently from `cached_tokens`. The run
also records the pre-dispatch count, provider-reported input, and their delta.
Provider billing remains authoritative.

## Focused proof

The focused tests prove:

- exact pricing-policy parsing, hashing, aliases, rates, and tier selection;
- conservative short/long estimates;
- usage-derived read/write/input/output calculation;
- environment-selected exact policy bytes;
- exact input counting before generation;
- a `$0.42` gate rejection before a fake provider response is consumed;
- rejected-turn provider-file cleanup;
- cache-write usage propagation into transport evidence, controller events,
  active projection, and UI text;
- malformed or unknown pricing authority fails closed.

Commands:

```powershell
$env:PYTHONPATH = (Resolve-Path .\src).Path
py -3.14 -m unittest tests.test_pricing_policy tests.test_automated_protocol `
  tests.test_openai_transport tests.test_automated_session tests.test_app_controller -v
py -3.14 -m unittest discover -s tests
git diff --check
```

## Hostile review

The first implementation used a fixed maximum-input assumption. That was not
strong enough: an old review turn had already exceeded the proposed bound.
The implementation was revised to use the provider's input-token count
endpoint on the exact constructed request before generation. No local byte-to-
token heuristic remains in the dispatch decision.

The count request itself is a provider control call, not a model generation.
Its failure stops the turn and cleans owned uploads. This slice made no live
provider request of either kind; all provider behavior was mocked.

## Closure

Slice 3 is complete. The next approved boundary is Slice 4: split stable
authority from per-round context, begin review in a fresh provider context,
and add disclosure-controlled enrichment without a paid call.
