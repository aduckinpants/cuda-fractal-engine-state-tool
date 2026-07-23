# Packet Observability and No-Op Hardening

Status: implementation complete; focused user-run retesting pending.

Branch: `codex/catalog-viewport-continuity-integration`

Starting commit: `ebe625fd8e329aac11d20e8533e539a877c83cbb`

## Goal

Close two experimentally demonstrated decision failures without expanding the
state-authoring contract:

```text
state-authorable experiment
+ observable intended effect
+ one concrete candidate state
-> sparse override with at least one authorized leaf change
```

An intentional unchanged-state replay remains:

```text
explicit base-replay request
-> {}
-> byte-exact base candidate
-> visibly classified no-op proof
-> explicit user acknowledgement
```

The implementation stops with focused Counterfactual Pair and ExplainO All
retest material ready for user-run web sessions. New tailored fixtures are a
later discussion boundary.

## Evidence lock

The completed manual battery established:

1. McMullen feature-tracking and ExplainO Nova dynamics cases can produce useful
   authorized overrides.
2. ExplainO Counterfactual Pair transported, materialized, replayed, and
   launched a valid classification-threshold change, but the selected
   `smooth_escape` signal could not display the changed pair class. The agent
   recognized that limitation and still selected a low-information experiment.
3. ExplainO Multibrot root-trap produced a clean one-path iteration continuation
   and exact launched-capture match.
4. Two fresh ExplainO All sessions selected an analysis-only prepole-overlay
   experiment. After the user requested the exact sparse override, each returned
   `{}` instead of asking the clarification already required by Packet V6.
5. The second agent later identified the failure as a capability-negotiation
   error: no authorized state path represented an overlay, and substituting a
   camera or dynamics edit would have changed the experiment.

These results justify packet and presentation hardening. They do not justify an
engine change, an overlay feature, a diagnostic API, or another proposal
envelope.

## Contract lock

### Experiment classification

Before presenting a recommendation as an executable state experiment, the
agent distinguishes:

- `state-authorable`: one candidate state maps to at least one exact leaf path
  in `state-override-authoring-surface.json`;
- `analysis-only`: mathematical analysis, measurement, comparison, or external
  image work that does not mutate the captured state;
- `requires unavailable capability`: an overlay, probe, annotation, diagnostic,
  automation, or other operation absent from the attached authoring surface.

Curiosity-driven discussion may include all three categories. Acceptance of an
analysis-only or unavailable operation does not make it state-authorable.

At the output trigger, the agent must map the selected experiment to one
candidate state and at least one authorized leaf change before emitting the
decision preflight. If that mapping fails, the ambiguity exception applies:
return one clarification question and no preflight or JSON.

### Observability

Before selecting a state experiment, the agent identifies the active rendered
signal or exported diagnostic that can observe the intended effect.

If the intended effect is not observable through attached evidence, the agent
must:

- choose an observable state experiment;
- explicitly label a user-requested negative control and its limited
  interpretation; or
- ask one clarification question.

Changing a semantic classification while the active signal ignores that
classification must not be presented as a visual test of the hidden class.

The existing `Expected effect and uncertainty` preflight label becomes:

```text
Expected effect, observation channel, and uncertainty
```

It names the intended effect, the exact observation channel, the expected
information gain, and the largest uncertainty. The preflight remains five
concise visible sections.

### Empty override

`{}` remains a valid state-shaped document and preserves the exact base
`state.json` bytes. It is not a refusal, ambiguity fallback, capability signal,
or substitute for an unrepresentable experiment.

The packet states:

> An empty override is an explicit exact-base-replay operation. Return `{}` only
> when the user explicitly requests unchanged-state replay or verification. If
> no authorized leaf change implements the selected experiment, ask one
> clarification question instead.

No envelope, intent flag, capability profile, or proposal metadata is added.

### UI classification

The proof receipt remains authoritative and continues to record
`empty_override_byte_exact`.

For a replay-proven empty override, the desktop UI must visibly state:

```text
NO-OP OVERRIDE — EXACT BASE REPLAY
Changed paths: none
Merged input is byte-identical to the authoritative base state
```

The ordinary `Accept Candidate` control becomes an explicit
`Acknowledge Base Replay` control for that proof. Launch readiness may follow
only after that acknowledgement and the existing hash/binding rechecks. The
engine-emitted launch candidate may still differ from the base in documented
volatile diagnostics, so the UI must not claim that the emitted state bytes are
identical. A non-empty same-value override is not an empty override and retains
existing deterministic serialization semantics.

## Non-goals

- engine or published-runtime changes;
- overlays, probes, annotations, diagnostics, or image-analysis automation;
- rejection or removal of byte-exact `{}` replay;
- a proposal envelope or conversation-intent metadata;
- automatic semantic grading of web-agent prose;
- new Color Pipeline, camera, or state authoring authority;
- broad automated model sweeps;
- new tailored manual fixtures before the focused retest review.

## Slice 0 — Plan and contract checkpoint

1. Reverify branch, exact HEAD, upstream parity, clean tree, and runtime boundary.
2. Preserve the completed battery transcripts and proof directories as external
   calibration evidence; do not copy mutable session transcripts into packet
   production paths.
3. Check in this plan before product mutation.
4. Run `git diff --check`, focused documentation checks if present, hostile
   review, commit, push, and clean-tree proof.

## Slice 1 — Packet decision hardening

1. Add concise experiment-classification, observability, and empty-override
   rules to the generated Packet V6 behavioral contract.
2. Preserve the evidence hierarchy, output trigger, ambiguity exception,
   five-section preflight, sparse state shape, and exact authority attachments.
3. Update the preflight label to include the observation channel and information
   gain.
4. Add focused packet tests proving:
   - state-authorable versus analysis-only/unavailable classification;
   - an unobservable intended effect requires an observable alternative,
     explicit negative-control qualification, or clarification;
   - accepted unrepresentable work still requires clarification;
   - `{}` is reserved for explicit exact-base replay;
   - no envelope, metadata field, or new authoring authority appears.
5. Regenerate a real packet and inspect its complete front-loaded contract.
6. Run focused tests, the full Python 3.14 suite, hostile review, commit, push,
   and clean-tree proof.

## Slice 2 — Explicit no-op proof and acknowledgement

1. Carry the existing `empty_override_byte_exact` result into the UI proof
   result without reparsing conversation intent.
2. Render the no-op status distinctly from an ordinary accepted override.
3. Show merged-input exact-base identity and zero changed paths prominently
   without overclaiming engine-emitted-state byte identity.
4. Require the existing visual-review action to be an explicit
   `Acknowledge Base Replay` action for no-op proofs.
5. Preserve review, launch, tamper, binding, runtime, and exact-hash rechecks.
6. Add focused tests for:
   - exact `{}` classification;
   - explicit acknowledgement label and gating;
   - ordinary non-empty override behavior unchanged;
   - same-value non-empty override not misclassified;
   - revision, edits, reset, stale completion, and tampering invalidate the
     no-op proof identically to other proofs;
   - receipt and launch artifacts retain exact identities.
7. Run focused tests, the full Python 3.14 suite, UI screenshot capture, hostile
   review, commit, push, and clean-tree proof.

## Slice 3 — Focused retest preparation and stop

1. Regenerate or rebind immutable Packet V6 fixtures for:
   - ExplainO Counterfactual Pair, exercising the observability decision;
   - ExplainO All, reproducing the analysis-only prepole-overlay transition.
2. Record exact packet, manifest, authority, runtime, selector, and source
   identities.
3. Provide exact opening, exploratory, targeted, prediction, comparison, and
   evaluation prompts.
4. The ExplainO All test must retain the ambiguity seam:

```text
What would you try?
```

followed, after multiple or unrepresentable recommendations, by:

```text
Let's do that. Return the exact sparse state override for this finding.
```

The expected compliant response is one clarification question, not `{}`.

5. The Counterfactual Pair test must require the agent to state which active
   signal or diagnostic observes the intended semantic effect before choosing a
   change.
6. Run all local tests and workflow proofs that do not require a web session.
7. Update the manual gate, commit, push, and stop.

The execution agent must not fabricate or self-grade the external sessions.
After the user supplies both retest results, reassess packet behavior and only
then discuss new tailored fixtures or a wider battery.

## Validation

Use Python 3.14:

```powershell
$env:PYTHONPATH = (Resolve-Path .\src).Path
py -3.14 -m unittest discover -s tests
```

Each implementation slice also runs its focused tests, affected real workflow,
`git diff --check`, hostile self-review, and clean-tree proof.

## Acceptance-ready closure

```text
Packet observability, executable-experiment negotiation, and explicit no-op
base-replay handling are implemented and locally proven.
The focused Counterfactual Pair and ExplainO All retests are prepared at exact
immutable packet bindings.
Repository clean at <commit>; branch pushed.
User-run web-session retesting is the next approved boundary.
No engine mutation, new fixture campaign, or broader product work is authorized.
```

## Execution receipt

- Plan checkpoint: `9ae3107`
- Packet decision hardening: `7b68ea6`
- Explicit base-replay presentation: `9646796`
- Focused packet tests: 9 passed
- Merge/proof/workflow/UI focused tests: 29 passed
- Full Python 3.14 suite: 85 passed
- Real no-op UI workflow: replay proven, captured-base pixels identical, launch
  disabled at visual review pending, and `Acknowledge Base Replay` presented
- C2 packet: `02549bbe-065e-498a-8168-3ac4dd0b5fb3`
- E3 packet: `43dbf386-4219-4101-8fc7-339a2e8f9bda`

The exact packet paths, hashes, prompts, and pass criteria are recorded in
`docs/catalog_viewport_continuity_manual_gate.md`. External-session results are
intentionally absent until supplied by the user.
