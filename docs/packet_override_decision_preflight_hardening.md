# Packet Override Decision-Preflight Hardening

## Status

Approved bounded calibration campaign on
`codex/catalog-viewport-continuity-integration`, starting from clean pushed
commit `656b77e8ee6e383dfa55c8732970febd7cd7d672`.

The campaign changes generated Packet V6 guidance and its acceptance evidence
only. It does not change Packet V6 or manifest schema versions, sparse override
JSON, authoring-surface derivation, validation, merge, proof, replay, UI,
launch, the CUDA engine, or the published runtime.

## Triggering evidence

The first viewport-continuity manual session used:

- finding `cc2cb68da25f649f2de674750b04c2b15f5e1416a806a0329b09743491525e63`;
- packet `8c1d791f-5122-4fbc-9458-554a52e84db4`;
- proof `5e2ab49c-7d9e-49e4-b687-f069d7ee64cd`;
- requested `params.mcmullen_lambda = 0.14814814814814814`;
- engine-emitted `params.mcmullen_lambda = 0.14814814925193787`.

Materialization and action-free replay produced identical decoded and encoded
frames. The exact launched high-zoom result was a healthy all-black render:

```text
D:\salt-fractal\cuda_newton_fractal_clone\findings\manual_capture\2026-07-22\110321_101__mcmullen
```

Resetting the same launched state to the default view produced a healthy
McMullen render:

```text
D:\salt-fractal\cuda_newton_fractal_clone\findings\manual_capture\2026-07-22\110335_382__mcmullen
```

The exact original viewport had center Y `-0.044871019404427663`, half-height
`0.020614894096391525`, and continuous Y bounds
`[-0.065485913500819184, -0.024256125308036138]`. At the selected parabolic
threshold the relevant fixed-point neighborhood is near Y `0`, outside the
retained frame. The packet carried enough authority to identify that outcome,
but the agent selected `same_window_comparison` and returned only the dynamics
change.

Classification:

- packet transport, exact binding, override validation, engine materialization,
  replay, candidate preview, review receipt, exact launch, and renderer health:
  passed;
- experiment selection and viewport-aware decision quality: failed;
- packet contract: underspecified because it permitted an unchanged comparison
  window without requiring a subject-visibility or intentional-control finding.

## Response contract

When a concrete override is authorized, the response contains concise visible
conclusions under these labels:

```text
Chosen experiment
Why this override
Expected effect and uncertainty
Camera intent and viewport check
Hostile self-review conclusion
```

Those conclusions are followed by exactly one fenced `json` block containing
one sparse state-shaped object. They are not part of the JSON and are not pasted
into the state tool. No other code block is permitted.

The packet asks for auditable conclusions, not private chain-of-thought.

## Selection binding

One override represents one state and one coherent experiment. Generic assent
is not an unambiguous trigger when the immediately preceding response contains
multiple numbered experiments, alternatives, a multi-value sweep, unresolved
camera choices, or more than one candidate state. The agent asks one concise
clarification question unless the user explicitly delegates the selection.

A sweep cannot be encoded as one override. The exact single member must be
selected before JSON is returned.

## Camera decision gate

For `same_window_comparison`, the response reports whether the relevant subject
is predicted to intersect the retained viewport. An unchanged window is valid
only when the subject should remain meaningfully visible or the user explicitly
requested a fixed-window control where disappearance is intentional.

If the feature is predicted outside the frame, the agent provides a grounded
tracking or survey camera, asks for direction, or proposes the intentional
disappearance control before returning it. `feature_tracking` and
`transition_survey` claims must agree with actual complete companion-paired
`view` changes in the JSON.

Color-only changes report that the exact camera is preserved and return no view
paths unless the user separately requested reframing.

## Hostile self-review gate

Before returning JSON, the agent reports the conclusion of checking:

- selection ambiguity;
- path authorability;
- narrative/JSON alignment;
- likely subject displacement outside the supplied viewport;
- split, merge, disappearance, or ambiguous continuation;
- blank, irrelevant, or misleading framing;
- a multi-state experiment incorrectly compressed into one state.

Every changed JSON path is explained by the selected experiment, every promised
change appears in JSON, and the largest expected uncertainty is visible.

## Phases

- [x] Slice 0 — lock this evidence and contract, add RED packet assertions, run
  the baseline, hostile-review the scope, and checkpoint cleanly.
- [x] Slice 1 — implement the response/preflight guidance, update tests and
  active documentation, run focused/full/workflow proof, and checkpoint cleanly.
- [x] Slice 2 — regenerate the original McMullen packet, verify exact local
  authority and handoff evidence, and stop for the user-run web calibration.
- [ ] Slice 3 — after primary acceptance, regenerate the remaining fixtures,
  finish manual acceptance, close documentation, and merge the state-tool PR
  under the user's standing authorization.

## Stop conditions

Stop for plan revision rather than adding automatic feature detection,
Python-owned fractal mathematics, Python camera fitting, a proposal envelope,
another machine schema, validator changes, engine changes, or repeated packet
growth in response to explicit downstream model noncompliance.

## Slice 0–1 proof

The focused packet test first failed because the generated packet lacked the
five required decision-preflight labels. After the generator change, the
focused packet/application set passed 12 tests and the complete Python 3.14
suite passed 82 tests. `compileall` and `git diff --check` also passed.

Hostile review confirmed that the guidance does not create a second schema or
ask for hidden reasoning. It requires only visible decision conclusions, leaves
the sparse JSON unchanged, applies after the exploration phase, and makes the
existing human candidate-preview gate the final visual authority.

## Slice 2 manual calibration handoff

The hardened primary packet is:

```text
D:\salt-fractal\cuda-fractal-engine-state-tool\findings\cc2cb68da25f649f2de674750b04c2b15f5e1416a806a0329b09743491525e63\packets\2a8f4d43-a08b-487b-9ad8-49bd88b8e06f
```

- Packet SHA-256: `42042589b1c91f0a2ec2bfbf5d6c223551c9b668b17d09d800736580504f7c19`
- Manifest SHA-256: `afad5724a217f3f55ae3c09cf819d357966030e29dc15222bfcda3e0fd2cb1d6`
- Runtime identity SHA-256: `140707fd16283ac2db3c58a24146b73a7f29bbd15b0e1b36771c301f8b275e95`
- Runtime executable SHA-256: `ae329398693a5872faced0fa6f9cf57868788fc975b07ece5150954ac4face78`
- Base state SHA-256: `e68e611fd1b8014f98a59af689b53c299585bd62d8ed15dd3b81c1eadaba504d`
- Viewport-facts SHA-256: `4d40f7c64149ff112842fcefa0f49b0021e6b2a01703058c8267cc328d5eb934`

The bundle inspector and ordinary existing-packet workflow loader both accepted
the new directory, selected `mcmullen`, and recovered the exact durable finding
without refresh. All nine required and three recommended attachments are
present. The historical packet retained its recorded packet and manifest
hashes, proving that regeneration did not mutate it.

The front-loaded packet grew from 9,834 to 12,031 UTF-8 bytes (26 additional
lines). Hostile review accepted that bounded increase because it carries the
five operative decision checks without duplicating any attached authority or
adding another schema.

The execution agent stops here. The user runs the external session described in
`docs/catalog_viewport_continuity_manual_gate.md`; Slice 3 remains blocked until
that transcript and candidate result are supplied.
