# Fixture G — Luna High Assisted Authoring and Runtime-Drift Timeout Finding

Date: 2026-08-03

## Exact paid run

- Case SHA-256: `384cf69ff0d1bdb01219581c856b750cece44701192d34799704c0a003f4fd49`
- Run: `v9-v8-g-luna-high-live-e7855b39-5695-499b-b4c2-0b7ac062b35d`
- Packet: `71bae9d2-c49b-4219-be8e-8e2699d60823`
- Finding: `649c5e1ab68b4144ac257214b239dcd3b4888d8d034a91c6efc8018caf22c66c`
- Model: `gpt-5.6-luna`, high reasoning, assisted disclosure
- Actual calculated author cost: `$0.0385442`
- Cell ceiling: `$0.0884228`

The author response selected a color-only phase test and returned a complete,
fixed-topology pipeline override. Validation accepted one changed leaf:

```text
color_pipeline_draft.lanes[2].rows[0].parameter_values[1].number_value
0 -> 0.35
```

The prediction preserved dynamics and camera and expected global recoloring
without geometry movement. This was coherent, observable, and authorized.

## Paid stop condition

Proof `3702a83c-8f9c-4844-81cb-9f5df477c010` timed out during direct-state
materialization at the packet-derived 90-second deadline. The engine emitted no
partial state or frame and no diagnostics. Model review was not dispatched.

The run ended `PROOF_FAILED`. Automatic qualification gates correctly remained
false. In addition to the missing proof/review gates, the assisted disclosure
gate reported the old expected analysis ID
`5e75bb00f9bc9efd753d0a812f37170c8506a7b7d4742185da666909ab93c47c`
while the newly published engine produced analysis ID
`80a6957a2992e4e0fcfc57284c3e01c40ec7223d3995829ae04d91a7687e1773`.
The old qualification case is therefore stale after the engine publication.

## Exact no-API classification replay

The archived override was rerun without another model call using an explicit
300-second diagnostic deadline. Proof
`8f250ee7-53ed-4f71-b7ab-396ae2f5e2f2` passed materialization and action-free
replay:

| Evidence | Result |
| --- | --- |
| Materialization elapsed | `82.86501180002233` seconds |
| Replay elapsed | `207.2055640000035` seconds |
| Candidate decoded RGBA | `b856a9d2e446b828a7cac69eed49f18c514b94fae1d30bc5fabf4a9bd17f24e4` |
| Replay decoded RGBA | `b856a9d2e446b828a7cac69eed49f18c514b94fae1d30bc5fabf4a9bd17f24e4` |
| Engine candidate state | `26f487c2ea432a4f629beba0c6572b2272047e11d209287e0e60c96d5a7f7d14` |

This proves a timeout-policy miss, not a loaded-draft or replay-authority
failure. The captured viewer timing was `15964.0263671875 ms`, but it belonged
to executable SHA-256
`ae329398693a5872faced0fa6f9cf57868788fc975b07ece5150954ac4face78`.
The proof used the newly published executable SHA-256
`17513a94d277afb6188da1683214731476eddf6649471278129e54e93eea06c3`.

## Hardening disposition

The shared timeout resolver now applies a 300-second per-stage floor only when:

```text
runtime identity drift is present
and compatibility mode is development
and no explicit timeout was supplied
```

Matching-runtime captured timing, explicit caller deadlines, the 600-second
cap, and strict-mode stop behavior remain unchanged. The synchronous CLI wrapper
now waits for the maximum possible inner adaptive policy when the caller did not
set an explicit deadline, preventing an outer wait from preempting the worker's
runtime-drift floor.

The repaired default route was exercised against the same archived override
without supplying `--timeout-seconds`. Proof
`a447ac82-66e4-42a6-a629-5cc29ae304ea` recorded a 300-second resolved timeout,
`runtime_drift_detected: true`, and `runtime_drift_floor_applied: true`. It
completed materialization in `62.199727600003826` seconds and replay in
`21.798570499988273` seconds. Candidate and replay again decoded to
`b856a9d2e446b828a7cac69eed49f18c514b94fae1d30bc5fabf4a9bd17f24e4`.
The different elapsed times across identical override proofs are direct evidence
that the old 90-second floor had insufficient margin under runtime drift.

## Evidence hashes

- Paid run `events.ndjson`:
  `59f7980f1807908851f8c197d12488e50c8dd254c2aad59f7699b106096e68d6`
- Paid run `active-turn.json`:
  `68609be1b3ad04b5530a690dc25796debf9bcc36000e08ca090ff15fe73ac84f`
- Paid automatic gates:
  `fe14e7c4a9aee8e17a16594672a8ed715bb24c1d58bcef01f1c7a432ed7a7f9c`
- Timed-out proof receipt:
  `870b5a1ddca8a3aafcb2e85fc5806010aeda17ba5ea6ed1a398b8b97c01aa18f`
- Successful no-API proof receipt:
  `4f51e8522c16386246f1edb2ad01a76aec3de21229c24e8c405f55c9a247ae95`
- Repaired-default proof receipt:
  `c842dfd560c74f76288ceca7df2fdae733dc1d50339deae35099fc423fd6f601`

## Boundary

Fixture G is not accepted as a completed qualification cell. The replacement
case is now bound to post-publication analysis ID
`80a6957a2992e4e0fcfc57284c3e01c40ec7223d3995829ae04d91a7687e1773`
with case SHA-256
`ba6a9bd1ca3c9c04cf0da5a2e48475831d9909cb81c6d602d3c5d56353b14e93`.
Its exact count-only preflight passed at 170,119 input tokens and a conservative
`$0.0436238` author maximum under the existing `$0.0884228` cell ceiling.
Stop for separate paid-rerun authorization.

## Authorized refreshed qualification result

The user separately authorized one refreshed paid Fixture G cell. It completed
under:

- run: `v9-v8-g-luna-high-post-engine-live-dba1a920-3123-424f-bd46-7f1bfe6db968`;
- case SHA-256:
  `ba6a9bd1ca3c9c04cf0da5a2e48475831d9909cb81c6d602d3c5d56353b14e93`;
- calculated cost: `$0.0740508` under `$0.0884228`;
- automatic gates: 10 of 10 passed;
- human acceptance: not recorded.

The model changed only `palette.seed_phase` from `0` to `0.15`. Proof
`ec54493b-295c-4a9c-9f97-d94b8bdb9306` materialized in `42.3782` seconds and
replayed in `22.9861` seconds under the 300-second runtime-drift floor. Candidate
and replay decoded to the same RGBA SHA-256:
`06f7cc72314c06425a431f517a789034105c38243965126fa0b894f051a2708e`.

The controller comparison found a large RGB response with no alpha difference.
The fresh review correctly identified global recoloring with fixed geometry,
camera, and dynamics, then proposed `ROUND_ADVANCE`. The exact one-round limit
ended as the expected successful bounded `BUDGET_EXHAUSTED` disposition.

This is a valid completed qualification cell, but it selected a simpler
experiment than the historical targeted Fixture G prompt. The historical session
changed from continuous lens-field coloring to categorical `root_index` to test
geometry interpretation. The automated generic prompt instead tested active
palette responsiveness. It therefore establishes robust authority, proof,
camera, and review behavior—not exact historical experiment-selection parity.

Evidence SHA-256:

- `events.ndjson`:
  `8ce38590384fcec3b8173489d52243d54801596e0e1bfdc53564df4cd4a99d69`;
- `active-turn.json`:
  `b8a25246edf1665a3f7b7b60b82e71c2c7ccc8c6e68e6db23f52ac708b6675aa`;
- automatic gates:
  `d52a5ca860c2f483063f70a2c3d04d8d9b4716808df5e324a383060fb383636e`;
- round-review ledger:
  `e4fd9c707592487c8dfd417f2a4440291c469e9cdeae2761d38e18673999c2e8`;
- round-review comparison:
  `13104c825d8a3d557dbb762132540346415c51d9a1f45eb60990e60f8c164452`;
- proof receipt:
  `cfc7557d17231272b03637df9be189d4a092609eeef682e914185f73754746c4`.

Fixture G's automated qualification boundary is complete. Formal human
disposition remains pending independent review.
