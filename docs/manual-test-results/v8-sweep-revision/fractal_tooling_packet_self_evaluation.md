# Self-Evaluation and Recommendations for the Fractal Experiment Tooling and Intake Packets

**Generated:** 2026-08-05 16:23 (-05:00)
**Scope:** Review of the visible interaction, the sweep workflow, packet handoff behavior, proof semantics, and opportunities to improve experiment design and documentation.

---

## Executive summary

The scientific workflow was productive and ultimately strong:

- The damping sweep identified a practical transition near \(1.95\)–\(1.97\).
- Repeating the same sweep with a 1500-iteration base separated iteration-cap artifacts from the true local stability boundary near damping \(2\).
- A high-zoom follow-up exposed a central circular termination region.
- An epsilon sweep verified that the circle radius scales nearly linearly with epsilon, strongly supporting the one-step convergence interpretation.

The main process failure occurred before the first sweep. The assistant initially treated “one experiment” as though it had to be expressed as “one sparse state override” and missed the existence of a separate host-side `Local Scalar Bracket Sweep V1` input format. The original packet did not document that format, so the assistant’s confusion was understandable but still avoidable once the user’s intent was clear. The revised packet substantially fixes this gap.

The strongest tooling improvements would be:

1. Make sweep capability a first-class, machine-readable packet artifact.
2. Distinguish semantic experiment identity from execution representation.
3. Treat float32 serialization differences as representation-equivalent, not proof failures.
4. Export per-member convergence diagnostics, not only rendered images.
5. Add automated measurement and comparison helpers for obvious sweep observables.
6. Provide one-click transcript and experiment-report export.

---

## 1. What went well

### 1.1 The investigation moved from visual observation to falsifiable prediction

The strongest part of the session was the progression:

1. Observe concentric phase-colored rings.
2. Form a local damped-Newton explanation.
3. Predict how damping should move the center and alter ring spacing.
4. Predict that a low iteration cap would hide rings near damping \(2\).
5. Recapture a 1500-iteration base.
6. Verify that rings return at \(1.97\) and \(1.99\), but not at \(2.00\) and \(2.02\).
7. Zoom into the one-step preimage.
8. Predict a circular epsilon-controlled termination region.
9. Sweep epsilon and verify nearly linear radius scaling.

This is a good model for exploratory numerical work: each step narrowed uncertainty rather than merely producing more images.

### 1.2 The fixed-base sweep design was correct

The sweep runner’s rule that every member starts independently from the exact packet base was appropriate. It prevented cumulative parameter drift and made each member interpretable as a controlled comparison.

The revised packet now states this explicitly and requires `{}` as the fixed override for V1 scalar sweeps. That is a meaningful improvement.

### 1.3 The 224-versus-1500 comparison was especially informative

The first damping sweep alone could not distinguish:

- true dynamical instability, from
- unfinished orbits caused by the iteration cap.

The recaptured 1500-iteration base created a clean experiment. The result clearly showed:

- \(1.97\): hidden rings reappear;
- \(1.99\): substantial ring structure returns, though convergence remains difficult;
- \(2.00\): contraction does not return;
- \(2.02\): the local behavior remains unstable.

This was a high-information comparison and should be preserved as an example workflow in the documentation.

### 1.4 The epsilon sweep was an excellent validation test

The epsilon sweep was well chosen because it tested a quantitative prediction:

\[
r_{\text{circle}}\propto \epsilon.
\]

The result was not merely qualitatively consistent. The central disk expanded in the expected order and approximately by the expected factors. This is much stronger evidence than “the pictures look similar.”

### 1.5 The revised packet addresses the original sweep-documentation gap

The follow-up packet now includes:

- `Local Scalar Bracket Sweep V1`;
- admissible axes;
- exact current values;
- type and range restrictions;
- exact-base exclusion;
- fixed-state policy;
- required preflight labels;
- JSON wire shape;
- permitted member-failure policies.

That revision directly addresses the failure encountered earlier.

---

## 2. What did not go well

### 2.1 The assistant incorrectly collapsed “experiment” into “single state”

The user asked for the JSON for the first damping experiment. The assistant initially responded as though the user had to choose one damping value.

That was the wrong abstraction.

A sweep is one coherent scientific experiment even when it executes as multiple independent states. The response should have distinguished:

- **scientific unit:** one damping sweep;
- **execution unit:** several independently rendered members;
- **wire format:** either a sweep plan or multiple sparse overrides, depending on tool capability.

The assistant instead treated “one state” as “one experiment,” which created avoidable friction.

### 2.2 The assistant relied too heavily on the packet’s sparse-override contract

The original packet said that a sweep could not be encoded as one ordinary override. That statement was true but incomplete.

The assistant generalized it into “there is no valid sweep JSON,” which was false for the host-side sweep runner shown by the user.

A better response would have been:

> “The packet documents sparse state overrides but does not document the host sweep runner. The UI you showed appears to define a second wire format. Based on that format, the damping sweep should be encoded as follows…”

That would have separated packet authority from observed tool capability without blocking the user.

### 2.3 The proof layer mislabeled a float representation issue as failure

The damping value `1.9` materialized as `1.899999976158142`, causing a proof failure.

This is a poor user-facing classification. For a float32 control, that emitted value is the expected binary representation of the requested decimal. The system should not present it as equivalent to:

- an invalid path,
- a rejected value,
- a render failure,
- an engine mismatch,
- or a non-reproducible state.

This should be classified separately, for example:

- `REPRESENTATION_EQUIVALENT`
- `FLOAT32_CANONICALIZED`
- `VALUE_ACCEPTED_WITH_CANONICALIZATION`

The receipt should preserve both requested and emitted values and report the comparison rule used.

### 2.4 The initial contact sheet lacked enough diagnostics to explain the transition

The images were informative, but the first sweep required a second capture because the output did not directly expose:

- convergence fraction;
- max-iteration fraction;
- nonfinite termination fraction;
- derivative-degeneracy fraction;
- average and maximum iterations by member;
- residual statistics.

If these diagnostics had been included, the iteration-cap hypothesis could have been evaluated immediately.

### 2.5 Visual interpretation risk remained high

The active coloring was orbit phase. That makes the images visually rich but can obscure termination semantics.

Examples:

- a broad smooth region may be unfinished-orbit phase, not a basin;
- a gray region may be a max-iteration class, invalid state, or another rendering convention;
- alternating colors across rings may reflect phase reversal rather than separate objects.

The packet correctly warns against overclaiming, but the tool should make the active observation channel and its limitations more prominent in the contact sheet itself.

---

## 3. Recommendations for the packet files

### 3.1 Add a dedicated machine-readable sweep capability artifact

Do not rely only on prose inside `packet.md`.

Add a separate artifact such as:

`local-scalar-bracket-sweep-v1.json`

Suggested contents:

```json
{
  "schema_id": "viewer.local_scalar_bracket_sweep.v1",
  "supported": true,
  "member_count": {
    "minimum": 3,
    "maximum": 9
  },
  "fixed_override_policy": "exact_base_empty_object",
  "member_execution": "independent_non_cumulative",
  "failure_policies": [
    "continue_independent",
    "stop_on_first_failure"
  ],
  "axes": [
    {
      "path": "params.epsilon",
      "type": "float",
      "current_value": 9.999999974752427e-07,
      "minimum": 1e-12,
      "maximum": null,
      "ui_minimum": 1e-12,
      "ui_maximum": 0.01
    },
    {
      "path": "params.explaino_damping",
      "type": "float",
      "current_value": 1.899999976158142,
      "minimum": null,
      "maximum": null,
      "ui_minimum": 0.01,
      "ui_maximum": 10.0
    },
    {
      "path": "params.max_iter",
      "type": "int",
      "current_value": 1500,
      "minimum": 1,
      "maximum": null,
      "ui_minimum": 1,
      "ui_maximum": 5000
    }
  ]
}
```

Benefits:

- easy tool discovery;
- less semantic ambiguity;
- easier validation;
- fewer packet-reading errors;
- cleaner versioning.

### 3.2 Put tool execution modes near the top of the packet

The revised packet contains the right information, but it should appear immediately after the behavioral contract:

1. Sparse State Override
2. Local Scalar Bracket Sweep V1
3. Rules for choosing between them

The first paragraph should state:

> “A coherent experiment may be either one state or one scalar bracket. Do not equate experiment identity with a single render state.”

That sentence would have prevented the main misunderstanding.

### 3.3 Include a complete valid example for each admissible sweep axis

The generic example is useful, but axis-specific examples would be better:

- epsilon sweep;
- damping sweep;
- max-iteration sweep;
- warp-strength sweep.

Examples should explicitly exclude the exact base value, because that is a non-obvious V1 rule.

### 3.4 Add a “representation and canonicalization” section

The packet should define how requested numeric values are compared with engine-emitted values.

For each numeric type:

- integer: exact equality;
- float32: compare against canonical float32 materialization;
- float64: compare against canonical float64 materialization;
- optionally report ULP distance;
- distinguish semantic mismatch from representation normalization.

This should be shared by sparse overrides and sweep members.

### 3.5 Add an observable-to-axis guidance table

The packet already says experiments must be observable. Make that concrete.

Example:

| Axis | Primary expected visual effect | Best diagnostic |
|---|---|---|
| `params.epsilon` | stopping-boundary displacement | iteration bands / termination map |
| `params.explaino_damping` | ring spacing, center movement, stability | phase image + iteration stats |
| `params.max_iter` | recovery of unfinished regions | max-iteration fraction |
| `params.explaino_warp_strength` | coordinate deformation | same-window comparison, feature tracking |

This would help agents select higher-information tests.

### 3.6 Include derived mathematical landmarks when available

For this finding, the packet could optionally include transparent derived landmarks such as:

- one-step preimage estimate;
- local derivative at the preimage;
- local root multiplier \(1-\lambda\);
- predicted stability threshold.

These should be clearly marked as derived, not engine-owned state.

A small `derived-math-hints.json` artifact could prevent repeated manual derivation while keeping evidence classes separate.

### 3.7 Improve field-notes prompts

The empty field-note template should ask targeted questions:

- What visually changed?
- Which parameter was varied?
- What remained fixed?
- What result was predicted?
- What result would disconfirm the hypothesis?
- Were there proof failures or canonicalization events?
- Which regions appear unfinished?
- What follow-up base should be captured?

This would produce more useful human-authored context.

---

## 4. Recommendations for the sweep tool

### 4.1 Add a structured axis picker

The UI should allow the user to choose an admissible axis from the packet rather than typing the path manually.

Suggested fields:

- axis dropdown;
- current base value;
- allowed type and range;
- member values editor;
- failure policy;
- exact-base exclusion warning.

The raw JSON editor can remain available for advanced use.

### 4.2 Auto-generate a candidate bracket

For a selected axis, offer optional bracket templates:

- symmetric around base;
- logarithmic;
- near-threshold;
- coarse scout;
- dense follow-up.

For epsilon, a logarithmic or ratio-based bracket is usually more meaningful than equal additive spacing.

For damping near \(2\), a threshold-focused bracket is preferable.

### 4.3 Add float canonicalization-aware validation

Before running, display:

- requested value;
- canonical engine type;
- canonical emitted value;
- whether the difference is representation-only.

Do not wait until proof to mark a predictable float32 representation difference as failure.

### 4.4 Export per-member termination diagnostics

Each member should include at least:

- average iteration count;
- median iteration count;
- convergence fraction;
- max-iteration fraction;
- nonfinite fraction;
- degenerate-derivative fraction;
- average terminal residual;
- residual quantiles.

For this session, those metrics would have made the 224-step artifact immediately obvious.

### 4.5 Add optional diagnostic contact sheets

Provide selectable presentation modes:

1. active color pipeline;
2. iteration count;
3. termination reason;
4. residual magnitude;
5. root/basin classification;
6. difference from base.

The active phase image is useful, but it should not be the only summary.

### 4.6 Add automatic feature measurement

For obvious concentric structures, the tool could optionally estimate:

- common center;
- ring radii;
- radius ratios;
- central disk radius;
- linear or log-linear trend across sweep values;
- fit quality.

For the epsilon sweep, the tool could have directly reported:

\[
r = m\epsilon+b,\qquad R^2.
\]

This would convert a visual impression into review evidence while still preserving the source frames.

### 4.7 Add paired-base comparison support

The 224-versus-1500 experiment required a new captured finding and a separate sweep.

A future sweep mode could compare the same axis bracket across two immutable bases:

- Base A: `max_iter=224`
- Base B: `max_iter=1500`

The result would be a paired contact sheet with aligned members and direct difference metrics.

This should be a new versioned mode, not overloaded into V1.

### 4.8 Improve contact-sheet labeling

The newer sheet correctly labels the captured base as not a sweep member. Keep that behavior and add:

- base badge;
- member index;
- requested value;
- emitted value;
- proof status;
- canonicalization status;
- key diagnostics;
- explicit “not newly replay-proven” label for the base.

### 4.9 Add one-click report export

The sweep tool should export:

- plan JSON;
- binding metadata;
- fixed override;
- aggregate receipt;
- contact sheet;
- per-member diagnostics;
- machine-readable measurements;
- a Markdown summary template;
- session transcript link or attachment.

This would make the documentation workflow much easier.

---

## 5. Recommendations for the proof and receipt system

### 5.1 Separate failure classes

Recommended statuses:

- `REPLAY_PROVEN`
- `REPRESENTATION_EQUIVALENT`
- `NO_EFFECT_ENGINE_EMITTED_BASE`
- `PATH_REJECTED`
- `VALUE_OUT_OF_RANGE`
- `ENGINE_MATERIALIZATION_FAILED`
- `REPLAY_MISMATCH`
- `RENDER_FAILED`
- `UNSTARTED_AFTER_POLICY_STOP`

This is more informative than a generic proof failure.

### 5.2 Record requested, canonical, and emitted values

For every numeric member:

```json
{
  "requested_value": 1.9,
  "declared_type": "float",
  "canonical_value": 1.899999976158142,
  "engine_emitted_value": 1.899999976158142,
  "comparison": "representation_equivalent"
}
```

### 5.3 Include proof tolerance policy in receipts

Receipts should state:

- exact equality or canonicalized equality;
- float width;
- ULP tolerance if any;
- relative/absolute tolerance if any;
- whether textual decimal preservation is required.

### 5.4 Preserve unsuccessful members without visually conflating them

An unsuccessful member is valuable evidence. The contact sheet should distinguish:

- no image because the member never rendered;
- rendered but failed replay proof;
- rendered and canonicalized;
- rendered and proven;
- emitted base/no effect.

---

## 6. Recommendations for agent behavior

### 6.1 Ask what wire format the user is targeting only when truly unknown

When the user asks for “the sweep JSON” and a sweep runner is known or visible, provide the sweep plan.

Do not force a single-member clarification merely because the ordinary override format supports only one state.

### 6.2 Distinguish packet authority from observed UI capability

A good phrasing pattern:

> “The packet documents sparse overrides, while the UI shows a separate sweep-plan schema. I will use the UI’s sweep format and note that the packet currently omits it.”

This is precise without blocking progress.

### 6.3 Treat the user’s experiment as the semantic unit

The agent should reason in three layers:

1. hypothesis;
2. experiment;
3. execution representation.

That prevents the mistake of equating one experiment with one state.

### 6.4 Prefer falsifiable predictions

The strongest responses in this session specified:

- expected center movement;
- expected ring spacing trend;
- expected recovery below damping \(2\);
- expected failure at and above \(2\);
- expected linear circle-radius scaling with epsilon.

Continue using this style.

### 6.5 State uncertainty at the right level

Good distinctions:

- observed: rings return at \(1.97\);
- inferred: the old disappearance was iteration-cap driven;
- mathematically predicted: local contraction vanishes at \(2\);
- not yet established: exact global self-similarity or basin structure.

---

## 7. Recommended next experiments

### 7.1 Iteration-band recolor

Purpose:

- directly reveal stopping-count regions;
- verify that the central disk is the one-step region;
- separate phase-wheel appearance from iteration geometry.

This is the best immediate visualization test.

### 7.2 Max-iteration sweep at damping \(1.99\)

Suggested values:

\[
500,\ 1000,\ 1500,\ 2500,\ 4000.
\]

Questions:

- Does the gray core shrink monotonically?
- Does it disappear?
- Does a persistent nonconvergent structure remain?

Best diagnostics:

- max-iteration fraction;
- convergence fraction;
- residual quantiles.

### 7.3 Denser epsilon sweep near the base

A tighter bracket around \(10^{-6}\) could quantify linearity and systematic offset:

\[
6\times10^{-7},\ 8\times10^{-7},\ 1.2\times10^{-6},\ 1.4\times10^{-6},\ 1.8\times10^{-6}.
\]

The current result is already strong, so this is optional.

### 7.4 Sample-probe validation

Probe:

- the predicted one-step preimage;
- a point just inside the central circle;
- a point just outside;
- points on opposite sides at the same radius.

Expected:

- inside: one-step convergence;
- outside: two or more steps;
- equal radius: similar stopping count;
- angular position: phase follows angle.

### 7.5 Compare phase and iteration-band images

Use identical dynamics and camera, changing only the color pipeline.

This would produce a clean explanatory pair for documentation:

- phase image: direction information;
- iteration-band image: stopping-time structure.

---

## 8. Suggested documentation language

A concise result statement:

> A damped Newton render of \(e^z-1\) at damping \(1.9\) exhibits concentric stopping-time shells around a one-step preimage of the root. A damping sweep showed that ring spacing compresses as damping approaches \(2\). Repeating the sweep with the iteration cap increased from 224 to 1500 recovered rings at damping \(1.97\) and \(1.99\), demonstrating that the earlier apparent transition was largely iteration-cap truncation. A high-zoom epsilon sweep showed that the central one-step convergence disk grows approximately linearly with epsilon, strongly supporting the local linearization model.

A concise tooling result statement:

> The original packet did not document the host-side scalar sweep schema, causing ambiguity between sparse state overrides and sweep plans. The revised packet now includes `Local Scalar Bracket Sweep V1`, admissible axes, fixed-base semantics, and validation rules. Remaining improvements should focus on float canonicalization, per-member termination diagnostics, and automated sweep measurements.

---

## 9. Final assessment

The experimental method was successful and produced a coherent chain of evidence.

The largest tooling flaw was not mathematical; it was **capability handoff ambiguity**. The revised packet resolves much of that issue. The next most important improvements are:

1. float representation-aware proof semantics;
2. termination diagnostics;
3. automated measurements;
4. stronger report export.

The combination of immutable bases, independent sweep members, proof receipts, and derived contact sheets is already a strong foundation. With the recommendations above, the system could support much faster and more reliable numerical investigations with substantially less conversational friction.
