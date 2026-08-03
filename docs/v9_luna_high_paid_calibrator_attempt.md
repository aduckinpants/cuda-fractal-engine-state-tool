# V9 Luna/High Paid Calibrator Attempt

Date: 2026-08-03

Status: blocked before model generation by provider credit exhaustion

## Authorized scope

Exactly one paid hard-calibrator cell was authorized under the locked case and
`$0.10` cell ceiling:

```text
case SHA-256:
b191c64149e434612e710de626edd88f938eddefd6879ca885b37830a08e202a
model profile SHA-256:
dbf174b6e03c074b26588e606e6ddb4a27eb5d36bcbb70184863116e39e268b7
model: gpt-5.6-luna
reasoning: high
disclosure: assisted
packet: 6e9ca581-fcb3-45aa-8aa9-5d03997f3569
cell ceiling: $0.10
```

The repository was clean at merged main
`115b55e69d42d6048cf24da335a3769e31a7057f`. The published runtime executable
SHA-256 remained
`501002f174068641b9a6105e56c277e6a4080bc9dbeb5e672282e77562b96f56`.

## Outcome

The production controller prepared the exact assisted disclosure, uploaded the
manifest-driven resources, and repeated the provider input count. It reported
the expected 176,676 tokens and authorized dispatch under the local `$0.10`
gate. Response creation then failed with:

```text
HTTP 429
type: insufficient_quota
code: credit_balance_exhausted
message: You have no credits remaining. Add credits to continue using the API.
```

The controller classified the run as `TRANSPORT_FAILED`. No model response was
created, no override or proof was attempted, and no automatic retry occurred.

```text
model responses: 0
proven rounds: 0
calculated generation cost: $0
provider cleanup: complete
remaining provider file IDs: none
```

The provider's billing state is authoritative. A previously observed local or
console balance must not be used to override this response; the organization or
project selected by the stored credential may differ or may not yet reflect a
credit update.

## Durable evidence

```text
D:\salt-fractal\cuda-fractal-engine-state-tool\automated-runs\
v9-luna-high-hard-a5cafea3-ff16-40ad-b78c-e796d274379b
```

| Artifact | SHA-256 |
| --- | --- |
| `active-turn.json` | `0babc3bad37ec39d05bc38739686979a466d7260ace85d9a5de6a44b13ccd81e` |
| `events.ndjson` | `0054e62c60f38db4b575d45d5568529d90a47295bf7ea11f80c82c8f2ea6d3af` |
| `qualification/automatic-gates.json` | `b397e2997d1410ba9f32331e9c43083c2bf61737e521243ad5168c3fab3a52b3` |
| `transport/provider-file-cleanup.json` | `1e7a62503a12943f8a2b6c7c2f365b3636cc9f141d3323a5043151a0b5ba8867` |
| `transport/turn-0001/input-token-count.json` | `ec7c72453bbbd76d0fc3f7e2421d2922f7a48ac4bf8b7f813c1e5e142d0962e3` |
| `transport/turn-0001/request.json` | `de5052b48ba9dabd08980acdf06b45a831735ac1f8048b2dac1cd752bef6da13` |

The automatic-gate receipt correctly fails terminal, model, disclosure-count,
proof, and immutable-completion gates while passing exact initial packet
binding, cost ceiling, and no-fabricated-human-acceptance gates. Cleanup has no
failures.

## Boundary

Slice 4 is not complete. The blocker is external provider billing state, not the
packet, model profile, controller budget gate, engine runtime, or proof path.
Do not retry automatically. After usable credits are confirmed for the exact
credential's organization or project, obtain fresh authorization for one retry
of the unchanged hard-calibrator cell.
