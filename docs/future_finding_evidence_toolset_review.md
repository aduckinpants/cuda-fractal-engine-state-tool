# Future Finding-Evidence Toolset Review

Status: read-only design review complete; future work intentionally deferred.

Review date: 2026-07-23

State-tool checkpoint:
`a361cfd` on `codex/catalog-viewport-continuity-integration`

Engine checkpoint:
`09d5664b77116b716f83dd8df1085e88596498d0` on clean `master`

Published runtime:
`D:\salt-fractal\cuda_newton_fractal_clone\runtime`

Published executable SHA-256:
`ae329398693a5872faced0fa6f9cf57868788fc975b07ece5150954ac4face78`

## Purpose

This report records a bounded future-work shortlist for optional mathematical
and image-analysis tools around a captured fractal finding. It preserves the
useful ideas in the CUDA engine repository's historical Reality Toolkit work
without adopting that implementation as a new product architecture.

This is not an implementation plan and does not authorize product mutation.
The active state-tool boundary remains the user-run C2 and E3 Packet V6 retests
recorded in `docs/catalog_viewport_continuity_manual_gate.md`. Those tests must
finish before this toolset is planned or implemented.

The intended future relationship is:

```text
immutable finding
+ exact packet authorities
+ optional, explicitly requested evidence operation
-> immutable finding-evidence receipt
-> user review
-> optional new packet containing selected evidence
```

It is not:

```text
finding
-> old general analyzer
-> inferred mathematical story
-> silently modified packet
```

## Executive Decision

A finding-analysis capability is worth pursuing, but it should be a new
state-tool-owned subsystem rather than a button that runs the historical
Reality Toolkit wholesale.

The historical tools contain useful implementation and presentation ideas:

- decoded-frame statistics;
- comparison sheets;
- parameter and seed sweeps;
- root-constellation plots;
- symmetry measurements;
- runtime sampling galleries;
- structured manifests and analysis summaries.

They also contain assumptions that are not safe at the current product
boundary:

- duplicated Newton iteration and camera mathematics;
- broad-state fields treated as though they describe the selected recurrence;
- RGB clusters described as dynamical basins;
- source-parsed capability models used as authority;
- generated scenes and active experiments mixed with passive finding review;
- machine-specific external Reality Toolkit dependencies;
- insufficient separation between image evidence, serialized facts, engine
  measurements, and editorial interpretation.

The safe design is therefore:

1. keep the historical tools unchanged as review evidence;
2. build new capabilities under a dedicated state-tool namespace only after
   packet testing closes;
3. make immutable evidence receipts the shared foundation;
4. implement passive, clearly classified measurements before active
   experiments;
5. request small engine APIs only for measurements whose semantics depend on
   the selected engine recurrence or runtime field;
6. add evidence to a finding first, then deliberately create a new immutable
   packet if that evidence should be sent to an agent.

## Current Execution Boundary

No work in this report may begin before the focused packet retests are reviewed:

- C2 — ExplainO Counterfactual Pair observability;
- E3 — ExplainO All analysis-only ambiguity.

Those sessions are specifically testing whether Packet V6 can distinguish:

- a state-authorable and observable experiment;
- a state-authorable but unobservable experiment;
- analysis-only work;
- work requiring an unavailable tool;
- a legitimate clarification;
- an intentional exact-base replay.

Their results affect the future tool boundary. For example:

- If C2 shows that agents can use existing observation-channel authority
  correctly, a future observation audit can remain compact and factual.
- If C2 shows a real authority gap, a runtime field-summary API may deserve
  earlier priority.
- If E3 correctly classifies a prepole overlay as unavailable, optional
  analysis tools can be advertised without weakening capability negotiation.
- If E3 again translates unavailable analysis into an unrelated state change,
  exposing more tools before fixing that decision boundary would make the
  workflow less reliable.

Until those outcomes are known, this document is a durable design seed only.

## Repository and Authority Boundary

### State tool owns

The state tool may own:

- evidence-operation selection and orchestration;
- exact input hashing and immutable receipts;
- decoded image measurements;
- comparisons between exact frames or findings;
- presentation images, tables, and Markdown summaries;
- joining already exported packet authorities;
- invoking published runtime commands;
- bounded active experiments constructed from the exact finding-specific
  state-override authoring surface;
- durable analysis storage;
- deliberate packet refresh with selected evidence.

### CUDA engine owns

The CUDA engine remains the authority for:

- the selected fractal recurrence or field;
- family-specific iteration and classification semantics;
- generated-root semantics;
- exact camera and viewport mapping;
- runtime field values;
- convergence, basin, pair-class, pole, or feature identities;
- any headless measurement whose correctness depends on the active runtime
  implementation.

If a future evidence tool needs one of those facts and the published runtime
does not expose it, the state tool must report that limitation. It must not
reimplement the engine formula in Python merely to keep moving.

Any required engine change must use the engine repository's native authority,
planning, validation, publication, and merge protocols. This report grants no
engine mutation authority.

### Packet owns transport authority

Packet V6 remains the exact agent transport boundary. An analysis operation
must not mutate an existing packet directory.

The preferred lifecycle is:

```text
finding
-> Generate Evidence
-> findings/<finding-id>/analyses/<analysis-id>/
-> user inspects evidence
-> Refresh Bundle With Evidence
-> new immutable packet ID
```

The existing packet remains readable and unchanged. A new packet records the
selected evidence files and hashes in its manifest.

## Evidence Classification

Every future measurement and every human-readable conclusion must identify its
evidence class.

### Direct frame observation

Computed only from decoded pixels:

- dimensions;
- channel distributions;
- luminance;
- saturation;
- gradients;
- edge density;
- spatial frequencies;
- image-space symmetry;
- image-space differences.

These measurements may describe the rendered image. They do not establish
basins, recurrence terms, root identity, causal contribution, or exact
self-similarity.

### Serialized finding fact

Read directly from an exact finding artifact:

- selected fractal type;
- captured parameters;
- captured roots when the engine declares them authoritative;
- active Color Pipeline draft;
- frame and render dimensions;
- runtime-generated review sidecars.

Presence in broad replay state does not prove that a field applies to the
selected fractal. Applicable-parameter and descriptive-catalog authorities
continue to govern interpretation.

### Engine-derived measurement

Produced by the exact published runtime from the exact state:

- viewport facts;
- runtime sampling;
- selected-field values;
- class histograms;
- convergence or pair classifications;
- recurrence-dependent point or region probes.

The receipt must bind runtime identity, command, state hash, and output hash.

### Proven comparison

Established by a controlled pair or series:

- exact state changes;
- same-camera A/B comparisons;
- decoded-pixel equality or difference;
- parameter-sweep results;
- repeated runtime stability;
- observation-channel comparison.

A difference establishes that the controlled intervention changed the output.
It does not, by itself, prove a complete mathematical explanation.

### Hypothesis or editorial interpretation

Reasoned from one or more evidence classes but not directly established:

- a line is a caustic;
- a feature is a basin boundary;
- a motif is exactly self-similar;
- an apparent symmetry is caused by conjugate roots;
- a color plateau represents one engine classification.

Tools may help formulate such hypotheses. They must not silently promote them
to measured facts.

## Review of Existing Reality Toolkit Work

The files reviewed live primarily under:

```text
C:\code\cuda_newton_fractal_clone\tools\reality_toolkit\fractal_explorer
```

The review also considered:

```text
C:\code\cuda_newton_fractal_clone\tools\explaino_rtk_v3_measurement_lane.py
```

The published runtime does not include these Python sources. A production state
tool must not import them from the adjacent engine checkout or depend on that
checkout being present.

### `finding_analyzer.py` and `finding_charts.py`

Useful seeds:

- root geometry summaries;
- decoded-frame metrics;
- image-space symmetry measurements;
- charts and CSV output;
- a Markdown summary;
- a structured output manifest.

Unsafe product assumptions:

- an ordinary Newton model is recomputed in Python;
- polynomial coefficients and captured roots can be interpreted too broadly
  for non-Newton selected families;
- analysis damping and iteration behavior can diverge from the selected engine
  recurrence;
- convergence charts may describe a full root extent rather than the captured
  viewport;
- RGB clustering is presented with basin language;
- image-space symmetry is connected too readily to dynamical symmetry;
- boundary language is stronger than the actual image measurement;
- chart annotations and narrative highlights can overstate causality.

Disposition:

```text
retain as historical reference
extract ideas, not imports
do not expose as an intake-packet analyzer
```

### `fractal_extensions.py`

This is a manifest-driven composite experiment runner. It can create multiple
scenes, collect runtime sampling sidecars, and optionally invoke the finding
analyzer.

Its orchestration and receipt ideas are useful, but it generates experiments
rather than passively explaining an immutable finding. It would make the
packet's capability boundary harder to understand if exposed as one general
button.

Disposition:

```text
reference for orchestration patterns only
do not expose the composite runner directly
```

### `explaino_param_sensitivity.py`

This builds selected ExplainO parameter grids and evaluates runtime sampling
statistics such as:

- mean iterations;
- escape fraction;
- converged fraction;
- non-finite fraction;
- pole fraction;
- root-index entropy.

This is closer to a useful controlled experiment because the runtime performs
the sampling. It is nevertheless an active sweep with a specialized parameter
model, not passive finding evidence.

Disposition:

```text
seed for a later schema-derived controlled sweep
do not retain its hard-coded parameter surface
```

### `param_probe_sweep.py`

This provides a broader parameter-modulation and sample/capture sweep. It
contains useful batching ideas but also predeclared path and probe registries
that would duplicate the packet's finding-specific authoring authority.

Disposition:

```text
seed for sweep execution and reporting
replace all handwritten authorability with packet-derived authority
```

### `explaino_slime_trace_runner.py`

This performs deterministic non-root ExplainO parameter traversals with
manifests and measurement streams. Its trace presentation may inspire later
continuation work, but it constructs state mutations in Python and is too
specialized to define the general finding-analysis boundary.

Disposition:

```text
retain as a specialized historical experiment
do not generalize it into the first toolset
```

### `seed_sweep.py`

This runs real runtime captures across seed values, archives frames, and
computes image metrics and deltas.

It is a good seed for:

- exact per-frame receipts;
- contact sheets;
- frame-to-frame difference measurements;
- active series presentation.

It remains an active experiment and should follow, not precede, passive evidence
tools.

Disposition:

```text
strong implementation reference for later controlled sweeps
not an intake default
```

### `generic_sampler_gallery.py`

This converts `generic.sample` responses into image galleries and manifests.
It is a presentation layer for a runtime sampling response, not a finding
analysis.

Disposition:

```text
reuse concepts for runtime-measurement galleries
keep generic sampling clearly separate from selected-fractal semantics
```

### `generic_equation_pack.py`

This is a separate formula and AST workbench around generic sampling. It does
not belong in the finding-to-agent workflow because it introduces a different
authoring problem and a different mathematical authority.

Disposition:

```text
out of scope
```

### `explaino_capability_atlas.py`

This parses engine source to build a static capability atlas and documents
analyzer limitations. It is useful inside the engine repository as audit
evidence, but source parsing cannot become state-tool runtime authority.

Disposition:

```text
engine-internal audit reference
never consume it from the state tool as a published contract
```

### `explaino_rtk_v3_measurement_lane.py`

This stages FITS data into an external Reality Toolkit workflow and harvests
ghost, entropy, and invariance artifacts. It is machine-path dependent, heavy,
and designed for a separate scientific campaign.

Disposition:

```text
keep separate
do not attach it to ordinary finding packets
```

## Candidate Shortlist

The shortlist contains eleven candidates. They are ordered by dependency and
product value, not by implementation estimate.

### 1. Finding Evidence Receipt Core

Purpose:

Provide the immutable identity, storage, and classification foundation shared
by every later evidence operation.

Inputs:

- finding ID and directory;
- exact source artifact hashes;
- requested operation and version;
- runtime identity when invoked;
- tool configuration;
- optional comparison-finding identity.

Outputs:

```text
findings/<finding-id>/analyses/<analysis-id>/
  request.json
  receipt.json
  evidence.json
  evidence.md
  artifacts/
```

Required receipt fields:

- analysis schema and operation version;
- analysis ID;
- finding ID;
- exact input file hashes;
- state and frame identities;
- runtime identity and command when applicable;
- tool-code or package identity;
- evidence-class labels;
- warnings and unavailable measurements;
- output file roles, sizes, and hashes;
- completion status;
- no volatile absolute paths in portable evidence.

Key rule:

An operation may fail partially, but it may not quietly omit a requested
measurement. Missing authority is reported as unavailable.

Priority:

```text
required foundation
```

### 2. Frame Facts Report

Purpose:

Produce conservative, reproducible facts about one decoded frame.

Candidate measurements:

- encoded and decoded hashes;
- dimensions and color mode;
- per-channel minimum, maximum, mean, standard deviation, and quantiles;
- luminance and saturation distributions;
- clipped-black and clipped-white fractions;
- edge-energy and gradient-orientation summaries;
- coarse spatial-frequency summaries;
- dominant RGB clusters, labeled only as color clusters;
- alpha-channel behavior when present.

Candidate artifacts:

- `frame-facts.json`;
- `frame-facts.md`;
- luminance histogram;
- saturation histogram;
- edge-orientation plot;
- optional color-cluster swatch image.

Forbidden claims:

- basin identity;
- root classification;
- recurrence activity;
- causal attribution to configured parameters;
- exact self-similarity.

Priority:

```text
first passive measurement
state-tool only
```

### 3. Finding Comparison Report

Purpose:

Compare two exact findings, or a base and proven candidate, without relying on
visual memory.

Candidate measurements:

- exact state-path changes;
- frame dimension and camera compatibility;
- encoded and decoded hashes;
- changed-pixel fraction;
- absolute and signed channel differences;
- luminance and edge-map differences;
- region-based difference summaries;
- unchanged-region estimates;
- optional structural-similarity measurement, clearly labeled as an image
  statistic rather than semantic equivalence.

Candidate artifacts:

- side-by-side contact sheet;
- absolute-difference image;
- amplified-difference image;
- comparison JSON and Markdown;
- exact input identities.

Existing state-tool overlap:

The proof path already records exact frame hashes, decoded RGBA equality, state
hashes, and changed paths. This tool should extend that evidence instead of
duplicating a second proof system.

Priority:

```text
early passive comparison
state-tool only
```

### 4. Observation-Channel Audit

Purpose:

Explain what the current render can observe before an agent chooses an
experiment.

Inputs:

- copied `state.json`;
- copied `fractal-state.json` when present;
- applicable-parameter surface;
- selected descriptive-catalog entry;
- active Color Pipeline draft;
- copied UI-Salt contract;
- any engine-exported diagnostic identities.

Outputs:

- active source signal;
- downstream pipeline functions;
- relevant engine-side consumer facts already present in the review sidecar;
- which proposed semantic effects are directly observable;
- which are only indirectly reflected;
- which lack an attached observation channel;
- explicit negative-control limits.

This tool must not decide whether an image actually shows an effect. It
describes the configured observation path and its authority.

Value:

This directly addresses the Counterfactual Pair calibration failure in which a
classification-threshold change was rendered through a signal that did not
display the intended class redistribution.

Priority:

```text
early authority summary
prefer existing exports
```

### 5. Captured-Root and Viewport Projection

Purpose:

Place already authoritative captured points into exact engine viewport
geometry.

Permitted inputs:

- captured roots or points that the selected runtime contract declares
  authoritative;
- `fractal-viewport-facts.json`;
- exact frame dimensions;
- optional user-selected point labels.

Candidate outputs:

- point coordinates and source authority;
- in-frame, margin, or out-of-frame classification;
- pixel coordinates from the engine-owned mapping;
- distances and bounding boxes;
- annotated frame;
- root or point constellation plot.

Important limits:

- do not solve a generic polynomial as a substitute for selected-family roots;
- do not infer a basin from the point marker;
- do not infer visible symmetry from root symmetry;
- do not duplicate the viewport formula;
- reject ambiguous point authority.

Priority:

```text
early passive geometry
state-tool orchestration over exported engine facts
```

### 6. Multiscale Image-Structure Report

Purpose:

Make visual claims about repeated filaments, bead chains, apparent symmetry,
or scale persistence more auditable.

Candidate measurements:

- crop pyramid at declared image coordinates;
- edge-orientation fields;
- radial and directional frequency summaries;
- image-space autocorrelation;
- cross-scale patch comparison;
- feature-density changes across scales;
- horizontal, vertical, and rotational image-space symmetry scores.

The report must use language such as:

```text
image-space repetition
scale-correlated texture
approximate reflection score
```

It must not say:

```text
exact self-similarity
dynamical symmetry
basin boundary
caustic
```

unless separate engine or controlled-comparison evidence establishes the
stronger claim.

Priority:

```text
later passive analysis
state-tool only
```

### 7. Observation-Channel Comparison

Purpose:

Hold dynamics and camera fixed while comparing two valid observation channels.

Example:

```text
iteration bands
versus
root proximity
```

Required controls:

- exact same base state;
- exact same camera;
- only Color Pipeline source and required compatible downstream changes;
- both candidates validated through the copied UI-Salt contract;
- both candidates materialized and replayed by the runtime;
- exact change and frame-difference receipts;
- explicit acknowledgment that the channels measure different quantities.

This is an active experiment, not a passive packet attachment. It should be
user-triggered and reviewed before its evidence is added to a new packet.

Priority:

```text
first active evidence experiment
no engine change expected if existing channels suffice
```

### 8. Runtime Field or Classification Summary

Purpose:

Expose selected-family scalar or categorical distributions without inferring
them from RGB.

Potential measurements:

- class counts;
- root-index counts;
- pair classifications;
- convergence and escape categories;
- root-proximity distribution;
- pole or non-finite counts;
- selected runtime field quantiles.

This tool exists only if the engine can identify:

- the field;
- its selected-family meaning;
- valid sampling geometry;
- categorical versus continuous semantics;
- unavailable cases.

The state tool may invoke and present the export but must not calculate the
field from a copied recurrence.

Priority:

```text
high-value engine-assisted option
requires an independently approved engine contract if not already exported
```

### 9. Runtime Point or Region Probe

Purpose:

Ground a question spatially: what does an engine-owned field report at this
point or bounded region?

Potential modes:

- exact complex coordinate;
- exact pixel mapped by viewport facts;
- rectangular image region;
- declared line segment;
- sparse engine-generated grid.

Potential outputs:

- sampled scalar or category;
- summary over the region;
- missing or invalid sample classification;
- optional heatmap whose legend is engine-defined;
- exact mapping and runtime receipt.

The operation should not become an unrestricted remote diagnostic API. V1
would need a small, declared set of runtime-owned fields and bounded sample
sizes.

Priority:

```text
engine-assisted spatial evidence
later than summary statistics
```

### 10. Controlled Parameter Sweep

Purpose:

Turn one authorized leaf and a bounded set of values into a reproducible
runtime series.

Required authority:

- one path from the exact packet-derived authoring surface;
- explicit finite values or a bounded mechanically generated sequence;
- exact base state;
- declared camera policy;
- runtime materialization and replay for every member;
- no family switching;
- no handwritten Python parameter registry.

Candidate outputs:

- one receipt per candidate;
- series manifest;
- frames and contact sheet;
- state and frame comparison table;
- selected engine or frame measurements;
- failed-point evidence;
- no automatic aesthetic winner.

This can generalize the useful parts of the existing ExplainO sensitivity,
parameter-probe, and seed-sweep tools without inheriting their parallel
authoring models.

Priority:

```text
later active experiment
only after one-value override behavior is stable
```

### 11. Feature-Continuity Survey

Purpose:

Investigate whether a mathematically identified subject persists, moves,
splits, merges, disappears, or becomes ambiguous across a bounded series.

Possible subjects:

- a captured root;
- fixed point;
- periodic point;
- critical point;
- pole;
- cusp;
- engine-defined transition set.

Required safeguards:

- the feature identity must come from engine authority or transparent
  mathematics supported by attached evidence;
- each step records whether continuation is unique;
- a split or merge tracks the complete declared branch set;
- camera containment uses exact engine viewport facts;
- ungrounded identity becomes `unknown`, not a nearest-image-feature guess;
- human review remains the decision boundary;
- no automatic claim that a visually similar feature is the same dynamical
  object.

This is the hardest option and should not be the first implementation target.
It is nevertheless scientifically valuable because the manual McMullen,
ExplainO Nova, and high-zoom tests have repeatedly exposed continuity and camera
questions.

Priority:

```text
late research tool
likely needs engine support and a separate approved plan
```

## Recommended Initial Product Cut

When planning eventually resumes, the smallest coherent product cut is:

1. Finding Evidence Receipt Core;
2. Frame Facts Report;
3. Finding Comparison Report;
4. Observation-Channel Audit;
5. Captured-Root and Viewport Projection.

This cut is preferred because it:

- adds useful evidence without inventing a new recurrence model;
- supports the current finding-to-discussion workflow;
- improves comparisons already being performed manually;
- gives unavailable analysis an honest product destination;
- creates the receipts and storage model needed by later tools;
- does not require an automatic experiment-selection system;
- does not require a broad engine mutation.

The Multiscale Image-Structure Report can follow after the evidence vocabulary
is proven. Observation-channel comparison and parameter sweeps begin the active
experiment tier. Runtime field summaries, probes, and feature continuity remain
explicit engine-contract or research boundaries.

## Proposed Future Module Boundary

If implementation is later approved, the preferred state-tool namespace is:

```text
src/cuda_fractal_state_tool/finding_evidence/
```

Possible internal separation:

```text
finding_evidence/
  contracts.py
  receipts.py
  storage.py
  frame_facts.py
  comparisons.py
  observation_audit.py
  viewport_projection.py
  runtime_measurements.py
  reports.py
```

These names are illustrative, not locked. The important boundary is that
evidence operations do not become methods on the Tk widget and do not reuse the
failed proposal-era controller architecture.

The UI could later expose one bounded action such as:

```text
Generate Finding Evidence
```

That action would open a small operation chooser or use one explicit selected
operation. It must not run every tool automatically.

## Packet Integration Model

Evidence should be generated outside the packet:

```text
findings/<finding-id>/analyses/<analysis-id>/
```

After review, a deliberate packet refresh may copy selected portable evidence
to a new packet. A compact first contract could use:

```text
finding-evidence.json
finding-evidence.md
finding-evidence-frame.png   optional
```

If multiple evidence operations are selected, either:

- produce one deterministic evidence index referencing copied files; or
- add a bounded `finding-evidence/` packet subdirectory if the web transport is
  proven to preserve it.

That transport decision is intentionally deferred. The current web-client
workflow has already shown that file count, filenames, and attachment
visibility matter. It should be tested with real clients before introducing a
large evidence attachment set.

Every included evidence artifact must have:

- an exact role in the packet manifest;
- size and SHA-256;
- producing analysis ID;
- evidence classification;
- runtime identity when applicable;
- no dependency on the original analysis directory after copying.

`Copy Packet` still copies only `packet.md`. The packet must list evidence files
that require attachment and must not imply that generated analysis traveled
with the Markdown.

## Controls Against a New Surrogate Authority

The future toolset must not maintain:

- a parallel fractal recurrence catalog;
- a Python basin or convergence implementation;
- another camera mapping;
- a handwritten path-authorability registry;
- a parallel Color Pipeline function library;
- a source-parsed runtime capability atlas;
- generic claims that every serialized field is active;
- a mapping from RGB colors to engine classes without runtime evidence;
- automatic feature identity from visual similarity;
- a prompt-authored analysis DSL that bypasses declared operations.

New evidence contracts should be narrow and versioned. Unknown selectors,
fields, or operation versions fail clearly.

## Explicit Quarantine List

The following are not candidates for direct promotion:

- the current general Python Newton-basin analyzer;
- automatic polynomial-root fallback for non-legacy findings;
- automatic prepole overlays detached from an engine authority;
- the composite Reality Toolkit runner as a single packet option;
- the source-parsing ExplainO capability atlas as a state-tool dependency;
- external FITS/RTK-v3 measurement campaigns;
- the generic equation/AST workbench;
- automated aesthetic scoring;
- automatic “most interesting feature” selection;
- broad background sweeps;
- agent-requested arbitrary code or analysis execution.

The historical files remain useful and should not be deleted as part of a
future state-tool campaign. They simply do not control the new design.

## Future Planning Questions

After C2 and E3 are reviewed, the next planning round should answer:

1. Did either packet test expose missing measurement authority, or only model
   compliance behavior?
2. Is the first product objective better framed as passive evidence for the
   agent, or as a user-facing comparison workbench?
3. Which two or three passive reports provide enough value for the first slice?
4. Should finding evidence be generated from a capture, an existing Packet V6
   directory, or both?
5. Which exact existing state-tool receipt primitives can be reused without
   coupling analysis to proof-session state?
6. What is the maximum safe image size and resource policy for analysis?
7. Which calculations require full-resolution decode, and which can use a
   bounded derivative?
8. Should the first packet integration carry one summary pair
   (`finding-evidence.json` and `.md`) or multiple files?
9. Which evidence files are required versus recommended web attachments?
10. Does observation-channel audit require any new engine export?
11. Is captured-root projection valid for all intended selectors, or must it be
    explicitly unavailable for some?
12. What manual fixtures can falsify each proposed evidence claim?

Those questions belong in a future bounded phased plan. They are not resolved
by this report.

## Candidate Acceptance Principles

Any later implementation plan should require:

- focused tests before the full suite;
- one real finding per supported operation;
- exact input and output hashes;
- explicit evidence classification;
- fail-closed authority handling;
- bounded concurrency and cancellation for UI operations;
- no packet mutation;
- no engine-process leakage;
- measurements checked against hand-computable fixtures where possible;
- engine-backed fixtures for recurrence-dependent outputs;
- hostile review of every generated human-readable claim;
- real packet transport testing before evidence attachments are declared
  usable;
- a user review stop before expanding from passive measurements to active
  experiment automation.

## Recommended Sequencing Hypothesis

This is a planning hypothesis, not an approved campaign:

```text
finish C2 and E3
-> classify packet outcomes
-> lock evidence vocabulary and receipt contract
-> implement passive frame/comparison tools
-> prove optional packet transport
-> add observation and viewport summaries
-> review user value
-> consider active channel comparison
-> consider schema-derived parameter sweeps
-> add engine measurement APIs only for demonstrated gaps
-> consider feature-continuity research last
```

## Closure

This review identifies a useful future direction without reopening the current
rescue scope.

Firm conclusions:

- A dedicated finding-evidence toolset is preferable to exposing the existing
  Reality Toolkit directly.
- The state-tool repository can own most orchestration, image measurement,
  receipts, reports, and packet integration.
- The engine must continue to own recurrence-dependent and field-dependent
  truth.
- Existing packets remain immutable; reviewed evidence enters only a new
  packet.
- The first future product cut should be passive and receipt-first.
- Active sweeps and feature-continuity work are later tiers.
- C2 and E3 manual packet testing remains the only current execution boundary.

No implementation, product mutation, new packet attachment, or engine change is
authorized by this report.
