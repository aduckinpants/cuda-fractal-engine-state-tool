# Packet V8 Seven-Fixture Manual Results

## Purpose

This ledger reviews the user-run Packet V8 external-session evidence prepared
on 2026-08-01. The historical directory name contains `six_fixture` because
the gate began with six selected fixtures. Fixture G was added after Fixture F
reached a valid override but the local proof process timed out. The accepted
evidence set is therefore seven fixtures, A through G.

The transcripts and the user's contemporaneous notebook are tracked under the
following historical directory name. Their wording and ordering are preserved;
only trailing Markdown whitespace was normalized to satisfy repository diff
checks.

```text
docs/manual-test-results/v8_six_fixture_manual_gate_08-01-2026/
```

## Reviewed Results

| Fixture | Selected fractal | Workflow result | Stable conclusion |
| --- | --- | --- | --- |
| A | ExplainO Fold | Successful state-authoring and render comparison | Packet authority and Color Pipeline authoring were usable. A later duplicate-launch attempt exposed a lifecycle issue, not a packet or proof failure. |
| B | ExplainO All, complex pipeline | Successful | The workflow remained authority-disciplined; prediction calibration was the principal weakness. |
| C | ExplainO All, gold field | Successful but diagnostically weak first frame | The state override executed. The fixed high-zoom camera made the first dynamics comparison too conservative, leaving a camera-strategy lesson rather than a packet-contract failure. |
| D | ExplainO Mult, high zoom | Successful | The color-only experiment preserved dynamics and camera. The transcript records a formatting defect and overconfident prediction without an authority failure. |
| E | ExplainO Mult, automatic iteration context | Successful | The experiment isolated one authorized dynamics change and preserved the automatic-iteration caveat. |
| F | ExplainO Balance Void | Valid workflow attempt; proof timed out | Packet use, experiment selection, prediction, and override generation succeeded. The fixed proof timeout expired before state or frame artifacts appeared. The captured `last_render_ms` makes adaptive proof timeout the next grounded implementation seam. |
| G | ExplainO Tension, lens/SDF observation | Successful | The Lens/SDF-backed observation path worked through the same Packet V8 and sparse-override workflow. Prediction calibration remained imperfect but did not invalidate the route. |

## Acceptance Judgment

Packet V8 passed its manual authority and transport gate for the seven reviewed
fixtures. The results do not establish that every model prediction is correct
or that every chosen experiment is maximally diagnostic. They do establish
that a fresh agent can use the compact packet to discuss a finding, select a
state-authorable experiment, return a sparse override, and evaluate the result
without reviving the removed proposal architecture.

Fixture F is retained as a first-class negative execution result. It is not
replaced by Fixture G and is not counted as a conversational or packet failure.
It authorizes one shared adaptive-timeout owner for manual and automated proof.

The seven results also preserve two later concerns without expanding this
campaign:

- candidate relaunch behavior should remain visibly separate from proof and
  acceptance authority;
- future automated sessions should select more discriminating dynamics and
  camera tests rather than converging on repeated simple color comparisons.

## Closure

The Packet V8 seven-file compaction campaign is accepted and its planned work
is exhausted. The next separately approved campaign is the bounded Packet V8
automated-route POC. It must reuse the existing packet, override, proof-image,
finding-promotion, and lifecycle owners rather than introducing parallel
implementations.
