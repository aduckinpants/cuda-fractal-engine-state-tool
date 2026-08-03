# Fixture F — Luna High Assisted Automated Session and Stop Condition

## Authority and paid result

- Case SHA-256: `9c7bdf4da7bdc84ad85ce6bdd3e1dc526f377c03201a4ec233f827ef4fb06847`
- Run: `v9-v8-f-luna-high-live-4d246de2-c6fc-4741-a9f9-d4e58aa93056`
- Packet: `6fb115b4-8e90-46c9-ad23-8dd11da383c5`
- Actual calculated cost: `$0.0373346`
- Input/output tokens: `169597 / 2846`
- Override validation: `AUTHORIZED_CHANGE`, one changed path
- Controller disposition: `PROOF_FAILED`
- Human disposition: `pending`

Raw run evidence:

```text
D:\salt-fractal\cuda-fractal-engine-state-tool\automated-runs\v9-v8-f-luna-high-live-4d246de2-c6fc-4741-a9f9-d4e58aa93056
```

## Selected experiment

The model made one color-only pipeline edit:

```text
palette.band_emphasis: 1.5 -> 1.8
```

It returned the complete captured lane array, preserved dynamics and camera, and
predicted stronger color separation in existing band transitions. The sparse
override validator accepted the exact change under the copied Packet V8 UI-Salt
contract.

The current published runtime rejected the materialization in `0.043` seconds,
before rendering:

```text
Loaded Color Pipeline draft applied in isolation, but the live runtime cannot
provide authoritative draft readback.
```

Rejected proof:

```text
D:\salt-fractal\cuda-fractal-engine-state-tool\findings\529d0037634964e430ea654ea4d17d2c220e23cfc6a3844192ddcfa1f91696a3\proofs\f4721969-1aba-4912-b8eb-addc4f24cfa7
receipt SHA-256: 5f95ead343923e82acaaa572c7dea853c57cb19538dfcbd64d9c3dc371ec3329
```

## Exact-base control

An independent no-API `{}` control used the same packet and current runtime. It
correctly did not request loaded-draft application, then completed both expensive
captures under the adaptive timeout:

```text
materialization: 217.5586779 seconds
replay:          223.7255140 seconds
decoded pixels:  identical
semantic state:  stable
status:          replay_proven
```

Control proof:

```text
D:\salt-fractal\cuda-fractal-engine-state-tool\findings\529d0037634964e430ea654ea4d17d2c220e23cfc6a3844192ddcfa1f91696a3\proofs\df123ce6-8edf-49e5-968e-d144468981fa
receipt SHA-256: f38e71782f426bad1471d7174bf7e8aa7f80acfd0bdccd6107b76cdef17a648f
```

An earlier diagnostic wrapper stopped itself at 60 seconds and left incomplete
directory `0494f5bb-50ba-4398-928e-bac511c13da9`; it has no receipt and is not
used as evidence.

## Classification

This is not the historical fixed-timeout failure. The receipt-derived timeout
was `438` seconds, and the exact-base control proves that the current runtime can
materialize and replay the expensive packet. The failure is specifically the
engine-authoritative loaded-draft path for this otherwise contract-valid palette
parameter change.

The packet was captured under executable SHA-256
`ae329398693a5872faced0fa6f9cf57868788fc975b07ece5150954ac4face78`.
The development-mode proof warned and attempted current executable SHA-256
`501002f174068641b9a6105e56c277e6a4080bc9dbeb5e672282e77562b96f56`.
The UI schema and UI-Salt contract hashes remained identical. This makes the
source-to-runtime difference important evidence, but does not by itself prove
which engine revision introduced the readback limitation.

Under the approved sequential stop-on-defect policy, Fixture G was not dispatched.
