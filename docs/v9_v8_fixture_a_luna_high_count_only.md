# V9 V8 Fixture A Luna/High Count-Only Preflight

## Exact Cell

```text
fixture: A - ExplainO Fold
packet ID: ea1f8e62-a8ff-4b3d-ae0c-ee019e4314d5
finding ID: d0ebae039f19758575fae1407cffa14baadf260f006c047d23a6345dc695e510
packet manifest SHA-256: 8c809bf64ea0944dfb9b157f55eda03683661bdd5741582124659ee6e32e70c4
model: gpt-5.6-luna
reasoning: high
disclosure: assisted
initial analysis ID: 7b0a7eeba2ad7102c9f3b9f82cf57fa31808d5943f28fefb2127f4c446d82fa4
case SHA-256: 7c83fa206468ec14b44bc02b4775700526219bfd89832063242b7852cdaf7d72
```

The immutable case is `docs/v9_v8_fixture_a_luna_high_assisted_case.v1.json`.

## Provider Count Receipt

The exact author request was submitted to the provider input-token count endpoint. No response generation was requested.

```text
run directory:
D:\salt-fractal\cuda-fractal-engine-state-tool\automated-runs\v9-v8-a-luna-high-tight-count-a361ac05-7c9e-4711-b5c8-90f6b6aa2e5d

input tokens: 171436
maximum author output tokens: 8000
maximum author cost: $0.0438872
within case budget: true
provider-file cleanup receipt: present
```

The review request cannot be counted exactly until the model has authored an override, the engine has produced a replay-proven result, and the derived packet and comparison records exist. Its hard bounds remain 200,000 input tokens and 4,000 output tokens, or `$0.0448` under the tracked policy. Therefore the full cell is capped at:

```text
$0.0438872 author maximum
+ $0.0448 review maximum
= $0.0886872 full-cell hard maximum
```

The executable case ceiling is exactly `$0.0886872`; it does not retain the looser `$0.10` planning allowance. This count-only receipt does not itself authorize response generation.

## Next Boundary

The first panel spot check is ready. A live run requires separate user authorization for this exact case and hard maximum. After it completes, its result must be compared with the historical Fixture A transcript and recorded through the panel comparison ledger before another fixture is dispatched.
