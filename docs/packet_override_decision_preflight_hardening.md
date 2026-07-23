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

Ambiguity exception: while selection remains ambiguous, the response is exactly
one clarification question with no preflight sections and no JSON. The visible
five-section preflight applies only after one coherent candidate state has been
selected.

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

Whenever attached authority and transparent mathematics permit it, the camera
conclusion reports the predicted subject location or transition set, the exact
retained viewport bounds, and the containment result. If containment cannot be
established, it says so and chooses clarification or an honest survey frame.

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
- [ ] Slice 3 (in progress) — the hardened primary calibration passed end to end. Qualify and
  run the remaining adversarial fixtures, close documentation, and merge the
  state-tool PR under the user's standing authorization.

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
D:\salt-fractal\cuda-fractal-engine-state-tool\findings\cc2cb68da25f649f2de674750b04c2b15f5e1416a806a0329b09743491525e63\packets\4101a8d0-5b87-4bf0-af61-b7b1a8149483
```

- Packet SHA-256: `c2a47a21bf4ef1a4980f6e27b72b52de0907cf2e2ddd7ef6a7a9e62e4e49d75f`
- Manifest SHA-256: `411e0d8999e4acc07a4269d3ea88d5c6ae40bbe43d20b8b8fd33fa9b66dc1ceb`
- Runtime identity SHA-256: `140707fd16283ac2db3c58a24146b73a7f29bbd15b0e1b36771c301f8b275e95`
- Runtime executable SHA-256: `ae329398693a5872faced0fa6f9cf57868788fc975b07ece5150954ac4face78`
- Base state SHA-256: `e68e611fd1b8014f98a59af689b53c299585bd62d8ed15dd3b81c1eadaba504d`
- Viewport-facts SHA-256: `4d40f7c64149ff112842fcefa0f49b0021e6b2a01703058c8267cc328d5eb934`

The bundle inspector and ordinary existing-packet workflow loader both accepted
the new directory, selected `mcmullen`, and recovered the exact durable finding
without refresh. All nine required and three recommended attachments are
present. The historical packet retained its recorded packet and manifest
hashes, proving that regeneration did not mutate it.

The final front-loaded packet grew from 9,834 to 12,798 UTF-8 bytes. Hostile
review accepted that bounded increase because it carries the
five operative decision checks without duplicating any attached authority or
adding another schema.

Packet `2a8f4d43-a08b-487b-9ad8-49bd88b8e06f` preserves the intermediate text
before the ambiguity exception was made explicit. It is not an acceptance input.

## Slice 2 primary calibration result

The user completed the hardened McMullen session and accepted proof
`96ab8393-97e2-4576-85cd-5039123a28d5`. The exact requested dynamics and camera
paths survived engine materialization, materialization and action-free replay
were pixel-identical, and the user accepted and launched the exact candidate.
The independent viewer capture at
`D:\salt-fractal\cuda_newton_fractal_clone\findings\manual_capture\2026-07-22\180102_222__mcmullen`
decoded to the same RGBA hash as the proof frame.

This is the first strong all-around pass of the hardened decision-preflight
workflow. It closes Slice 2's primary gate without claiming broad model
acceptance. Slice 3 remains active for a small adversarial ladder covering a
split or disappearance, an honestly ungroundable high-zoom change, and an
esoteric ExplainO case. No packet or product mutation is authorized from this
result alone; fixture qualification and further manual evidence come first.

## Slice 3 three-packet battery handoff

Fixture qualification selected exactly three current captures. Their immutable
packets were generated and independently re-inspected against the published
runtime without changing Packet V6 or product code:

1. reverse McMullen split — packet
   `e0eb0a99-5353-44df-bb24-b6f8fc2cfb01`;
2. ExplainO Nova high-zoom dynamics — packet
   `bd84ce6b-19d9-435d-a58c-3d0cff3d6bee`;
3. ExplainO Counterfactual Pair — packet
   `90e203ec-f777-4d3b-881f-de9c62a25a34`.

Every manifest file matched its recorded size and SHA-256, every generated
authoring-surface authority reference matched the neighboring copied state,
parameter-surface, and UI-schema bytes, and all three packets bind runtime
identity `140707fd16283ac2db3c58a24146b73a7f29bbd15b0e1b36771c301f8b275e95`.
Exact directories, hashes, prompts, and evaluator boundaries are recorded in
`docs/catalog_viewport_continuity_manual_gate.md`.

The deeper Nova reserve, additional old captures, and a new custom fixture are
deferred to a later round. Slice 3 now stops at the user-run three-session
manual battery. No packet tweak is authorized unless those sessions reveal a
genuine packet ambiguity rather than downstream model noncompliance.

### Battery result A — reverse McMullen split

The first blind session passed using the self-contained prompt "Consider
changing the lambda to 0.15" rather than the history-dependent phrase "Reverse
the preceding transition." Proof `7f1caa34-d9d3-42af-b65f-5f78abf4736e`
preserved all requested dynamics and camera values, replayed with identical
pixels, received explicit user acceptance, and launched the exact candidate.
The independent capture `2026-07-22\232401_164__mcmullen` decoded to the same
RGBA hash as the proof frame and reduced average iterations from `4838` to `87`.

The session correctly followed both conjugate branches and selected a survey
camera containing them. Its initial intentionality claim about the nearest
binary32 representation of `4/27` and its unmeasured pixel-perfect symmetry
claim are retained as downstream calibration misses. They do not justify a
packet change or the suggested new per-family math sidecar. Battery fixtures B
and C remain pending user execution.

### Battery result B — ExplainO Nova

The targeted "Choose one" prompt reasonably delegated selection and served as
the concrete trigger, so immediate JSON did not violate the workflow. Proof
`560dd86f-6451-45b8-a7e8-34f50fc61df6` accepted the sparse Nova/zoom override,
reported the engine's representation normalization, replayed with identical
pixels, received user acceptance, and launched the exact candidate. The fresh
capture `2026-07-22\235345_959__explaino_nova` decoded to the same RGBA hash as
the proof frame.

Operationally this passed. Scientifically it was partial: the agent correctly
selected an honest survey instead of inventing feature tracking, but widened
the view by 256 per dimension and reduced the original subject to about 16 by
10 authoritative render pixels while still predicting recognizability. The
camera and dynamics changed together without a same-camera survey baseline.
Unsupported quantitative claims in the opening analysis were also downstream
evidence-discipline violations. Existing packet rules already prohibit those
failures, so no Packet V6 change is authorized before Battery C determines
whether the pattern repeats.
