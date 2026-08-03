# V9 Luna/High Count-Only Preflight

Date: 2026-08-03

Status: passed; no response generation dispatched

## Exact cell

```text
case SHA-256:
b191c64149e434612e710de626edd88f938eddefd6879ca885b37830a08e202a
model profile SHA-256:
dbf174b6e03c074b26588e606e6ddb4a27eb5d36bcbb70184863116e39e268b7
model: gpt-5.6-luna
reasoning: high
disclosure: assisted
packet: 6e9ca581-fcb3-45aa-8aa9-5d03997f3569
packet manifest SHA-256:
9b01378f8cee99bfbb01619f238400e262c94e610c15da02d8d5f67af6caf8ea
analysis ID:
4db4181f7b1e8108a0c571daea99d4750f1bce5587ff5fd2f230fea3aabd27e6
prompt cache policy: explicit_no_cache
```

## Provider count

The production transport uploaded the exact Packet V8 resources and exact
assisted disclosure resources, constructed the normal first-author request,
called the provider input-token count endpoint once, rejected dispatch at the
authorization callback, and deleted every run-owned provider file.

```text
input tokens: 176,676
author output ceiling: 8,000
per-response input gate: 200,000
conservative author maximum: $0.0449352
generation dispatched: false
provider cleanup: complete
```

The author request is 23,324 tokens below its hard input gate and remains in the
tracked short-context tier. The count is provider-reported; provider billing
remains authoritative.

The review request cannot exist until the paid author response has produced an
override, proof, promotion, and refreshed result packet. Its hard 200,000-input
and 4,000-output bounds produce a conservative `$0.0448` maximum. Combining the
measured author request with the bounded review request gives:

```text
author maximum:       $0.0449352
review hard maximum:  $0.0448000
cell hard maximum:    $0.0897352
cell ceiling:         $0.1000000
remaining margin:     $0.0102648
```

## Durable evidence

```text
D:\salt-fractal\cuda-fractal-engine-state-tool\automated-runs\
v9-count-luna-high-a06bc497-9b58-4cc2-9f8b-984ef6645429
```

| Artifact | SHA-256 |
| --- | --- |
| `transport/count-author-0001/request.json` | `09b171f25eb037493b7c4b6ff6658392891fbce1a95e4a11cd56067367139d98` |
| `transport/count-author-0001/input-token-count.json` | `ec7c72453bbbd76d0fc3f7e2421d2922f7a48ac4bfb8b7f813c1e5e142d0962e3` |
| `transport/provider-file-cleanup.json` | `e8e103b3726a768d6d8ee023c8b0328db1e2b6664a0ab5fc88a7a0e2b8f9e980` |
| `qualification/count-only-receipt.json` | `0f0275d91ad0a0fa2d71478055eb65894a99e25208c8bbd364b64a2638c9937e` |

Cleanup reports no failures and no remaining provider file IDs. Event evidence
contains `qualification_count_started`, the exact assisted disclosure binding,
and `qualification_count_completed`; it contains no `model_response` event.

## Credential compatibility finding

The first local attempt stopped before run creation because the current
resolver checked only the newer `api_key` username while the established
Windows credential was stored under the older `OPENAI_API_KEY` username. The
resolver now prefers the current username and uses the legacy username as a
fallback. Writes remain on the current username; explicit deletion removes both
recognized entries. The key was neither printed nor migrated. Focused tests
cover primary precedence, legacy fallback, absence, set, and delete behavior.

## Hostile review and boundary

- Input counting proves request size and the local cost gate, not model quality.
- The calculated maximum assumes the tracked pricing policy; provider billing
  is final authority.
- The exact review request is not available before the author/proof/promotion
  path runs, so its 200,000-token gate remains deliberately conservative.
- No cache discount is assumed.
- The count-only receipt is not a model-session pass and records no human
  acceptance.
- Count-only provider uploads were temporary and fully cleaned.

Slice 3 is complete. Slice 4 is one paid Luna/high hard-calibrator cell under
the exact case and `$0.10` ceiling. Response generation remains unauthorized
until separately approved.
