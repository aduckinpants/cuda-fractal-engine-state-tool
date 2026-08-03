# Finding Enrichment Slice 4 — Context Partition Evidence

## Closure

Slice 4 is complete without a paid provider request. Packet V8 remains the sole
domain and authoring authority. The transport may reuse an already uploaded
file only for the same role and exact SHA-256; it does not create a shared
packet schema or infer equivalence from filenames.

The author and review routes are now bounded as:

```text
current Packet V8
+ selected enrichment-disclosure manifest and immutable outputs
-> fresh authoring context

replay-proven derived Packet V8
+ exact controller round-review ledger
+ selected enrichment-disclosure manifest and immutable outputs
-> fresh review context
```

The review request uses `previous_response_id: null`. Its compact ledger binds
the exact author response text and hash, sparse override text and hash, changed
paths, author/derived packet identities, and proof identities. It is expressly
not state authority.

## Disclosure contract

Analysis identity is independent from presentation:

- `blind`: no analysis is run or disclosed;
- `assisted`: receipted common/model/evaluation/annotation outputs are selected
  for authoring and review;
- `break_blind`: authoring remains blind and the same receipted outputs are
  selected only for review.

Each disclosure is a deterministic manifest over immutable analysis outputs.
Every selected artifact is reread and verified against the completed analysis
receipt before transport. Missing, changed, or packet-mismatched evidence fails
closed.

## Captured fixture replay

The local replay used this exact Rational Escape Packet V8:

```text
D:\salt-fractal\cuda-fractal-engine-state-tool\findings\
ffbd5143b3b8098867291cbe30ded9acd87d518877723c381e3e6aedd12ec138\packets\
6e9ca581-fcb3-45aa-8aa9-5d03997f3569
```

Published runtime:

```text
D:\salt-fractal\cuda_newton_fractal_clone\runtime\fractal_ui.exe
SHA-256 501002f174068641b9a6105e56c277e6a4080bc9dbeb5e672282e77562b96f56
```

The immutable enrichment analysis was a cache hit at:

```text
analysis_id 4db4181f7b1e8108a0c571daea99d4750f1bce5587ff5fd2f230fea3aabd27e6
```

Measured local request resources:

| Component | Resources | Exact bytes |
|---|---:|---:|
| Packet V8 | 7 | 2,253,384 |
| Assisted immutable outputs | 6 | 1,711,216 |
| Assisted disclosure manifest | 1 | 2,392 |

The binary images dominate byte size. These byte counts are not provider token
counts and do not predict an invoice. The architectural regression test proves
that review attaches only the derived packet, ledger, and selected disclosure;
it does not attach the original packet or continue its response chain. Exact
provider token counting remains the mandatory pre-generation gate when a paid
run is eventually authorized.

## Validation

Focused tests covered:

- fresh review context and round-ledger binding;
- exact role/hash file reuse and one-time cleanup;
- packet/additional-resource collision and mutation checks;
- blind, assisted, and break-blind disclosure behavior;
- receipted artifact mutation failure;
- zero-dollar rejection before enrichment or provider work;
- Tk automation-panel regression coverage.

The Slice 4 focused set passed 40 tests. The full Python 3.14 suite and final
diff checks are recorded with the slice checkpoint.

## Hostile review

- A fresh review context could have lost the locked prediction. The exact
  controller ledger closes that gap without making model history authoritative.
- File reuse could have become filename-based aliasing. Reuse requires the same
  semantic role and exact SHA-256, and run-owned cleanup deletes each provider
  file once.
- Disclosure could have contaminated analysis/cache identity. Profiles are
  separate manifests over immutable outputs and never enter analysis identity.
- Assisted mode adds a second annotated image and therefore does not guarantee
  lower raw bytes than blind mode. Its purpose is deterministic mathematical
  help; the dollar gate still decides whether any concrete request is allowed.
- A zero-dollar UI default could have performed preparation or a provider token
  count before rejection. It now stops before disclosure preparation and all
  provider work.

## Next approved boundary

Slice 5, Headless Scalar Bracket Sweep V1, is ready to begin. It is local and
requires no provider credential or paid call.
