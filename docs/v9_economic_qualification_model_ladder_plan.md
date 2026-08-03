# V9 Economic Qualification and Minimum-Acceptable Model Ladder

Status: approved through zero-provider-call cost hardening. Provider count and
generation remain behind the separate approvals defined below.

Date: 2026-08-03

```text
planning branch: codex/v9-economic-qualification-plan
state-tool main: 027a7419085dc28fe2af0a9108754b8c4030c3c4
engine master:   deca3d93fac92ad93742e8d47714f91329808ead
published exe:   D:\salt-fractal\cuda_newton_fractal_clone\runtime\fractal_ui.exe
exe SHA-256:     501002f174068641b9a6105e56c277e6a4080bc9dbeb5e672282e77562b96f56
```

## Decision

The next campaign should answer one question:

> What is the least expensive supported model-and-reasoning profile that still
> performs the bounded Packet V8 author/prove/review workflow acceptably?

Cost is the dominant blocker to a reusable automated battery. The merged
repository already provides the necessary prerequisites:

- exact Packet V8 authority and canonical sparse-override proof;
- fresh review contexts with a controller-owned prediction/proof ledger;
- exact provider input-token counting before generation;
- a versioned pricing policy and hard run-dollar gate;
- requested/resolved model and usage receipts;
- a zero-dollar UI default;
- deterministic local scalar sweeps requiring no model call.

The pre-spend hardening evidence is tracked in
`docs/v9_cost_hardening_evidence.md`. It locks explicit no-cache requests,
8,000/4,000 stage output caps, a count-only transport seam, and an `$8.00`
conservative campaign envelope. The user's larger willingness is not treated
as a spending target or blanket dispatch authorization.

This campaign does not reopen engine diagnostics, Packet design, enrichment
providers, evidence tooling, or sweep semantics.

## Provider facts to reverify at execution

Official documentation on 2026-08-03 identifies `gpt-5.6-sol` as flagship,
`gpt-5.6-terra` as the balanced tier, and `gpt-5.6-luna` as the high-volume
tier. Standard short-context prices per million tokens are:

| Profile | Input | Cached input | Cache write | Output |
|---|---:|---:|---:|---:|
| Sol | $5.00 | $0.50 | $6.25 | $30.00 |
| Terra | $2.00 | $0.20 | $2.50 | $12.00 |
| Luna | $0.20 | $0.02 | $0.25 | $1.20 |

Sol and Terra requests above 272,000 input tokens use documented long-context
rates. The tracked pricing policy currently matches, but live docs remain
re-entry authority:

- <https://developers.openai.com/api/docs/pricing>
- <https://developers.openai.com/api/docs/guides/prompt-caching>
- <https://developers.openai.com/api/docs/guides/upgrading-to-gpt-5p6-sol.md>

The last user-reported account credit was approximately `$0.42`. That is a
historical, volatile statement, not provider-verified tool state. No paid cell
may run until the user confirms funding and approves its exact ceiling.

## Locked comparison method

### Golden evidence

Existing successful Sol/high manual sessions and automated runs are the
behavioral golden reference. They are not an exact A/B control for the final
fresh-review architecture because some predate it.

Do not pay to rerun Sol merely to make a symmetrical table. A new Sol/high cell
is allowed only if a candidate cannot otherwise be adjudicated and the user
approves that exact estimated maximum cost.

### Candidate ladder

Search from the inexpensive end while preserving the current route's explicit
`high` reasoning before testing one lower effort:

```text
Luna / high
  pass -> Luna / medium on the same calibrator
  fail -> Terra / high on the same calibrator

Terra / high
  pass -> Terra / medium on the same calibrator
  fail -> stop; do not silently fall back to Sol
```

If Luna/medium passes, it is the provisional minimum. If it fails but
Luna/high passes, Luna/high is provisional. The same rule applies to Terra.
Only a provisional profile proceeds to the small confirmation set.

### No hidden routing

Every cell records:

```text
requested and resolved model
reasoning effort and pricing tier
pricing-policy identity
exact request input count and estimated maximum cost
provider-reported usage and calculated cost
latency, packet, disclosure, and prompt identities
controller and proof dispositions
```

The controller rejects an incompatible resolved family. Aliases remain visible
and never silently authorize a different price or quality tier.

## Qualification fixtures

Slice 0 selects and hashes three existing immutable Packet V8 directories:

1. **Hard calibrator — feature proximity, motion, or merger.** Prefer the
   existing ExplainO Rational Escape critical-seed case with the receipted
   polynomial enrichment in `assisted` mode. It requires one coherent
   experiment, precise camera-aware prediction, honest containment/ambiguity,
   and correct use of deterministic enrichment without turning it into state
   authority.
2. **Dynamics/iteration-horizon confirmation.** Requires distinguishing a
   finite-iteration effect from stable geometry and selecting one observable
   dynamics change. Prefer an existing ExplainO Inertial fixture.
3. **Observation-channel or typed-pipeline confirmation.** Requires a complete
   schema-valid pipeline array or precise observation change without inventing
   dynamics. Prefer an existing complex Color Pipeline fixture.

The first paid cell uses only fixture 1, one proven round, and one fresh review.
Fixtures 2 and 3 remain blocked until a profile passes fixture 1 and the user
approves the confirmation budget.

Every model cell for a given fixture uses the same exact packet, disclosure
profile, prompts, image detail, output limit, and controller budgets. Disclosure
is not ablated in the same comparison as model or reasoning effort.

This is a minimum product gate for this workflow, not a broad model benchmark.

## Evaluation contract

### Automatic hard gates

A cell fails automatically for:

- transport, count, pricing, cleanup, run-store, or controller failure;
- wrong resolved model family or unapproved reasoning profile;
- malformed, missing, empty, unknown, or unauthorized override;
- proof failure caused by the proposed change;
- fabricated human acceptance;
- review bound to the wrong packet or proof ledger;
- cost above the approved cell or campaign ceiling;
- missing immutable request, response, usage, proof, or cleanup evidence.

Engine rejection of an apparently valid override remains separately classified.
It becomes a model-quality failure only when the packet supplied enough
authority for the model to avoid it.

### Human-scored gates

Use one stable rubric, blind to candidate labels when practical:

- evidence hierarchy and mathematical restraint;
- executable and observable experiment selection;
- exactly one coherent state;
- falsifiable prediction and honest uncertainty;
- camera/feature-continuity handling where applicable;
- narrative/JSON alignment;
- result review against the locked prediction;
- legal and useful controller gate proposal;
- concise output without omitted evidence.

Each item is `PASS`, `PARTIAL`, or `FAIL` with a short source-grounded note. No
weighted aesthetic score or automatic winner is introduced.

### Acceptance rule

A profile is acceptable only when all automatic gates pass, no human item is
`FAIL`, any `PARTIAL` is explicitly accepted as nonblocking, and the actual
cost per successful fixture is materially below comparable historical Sol
evidence. The provisional target is at least a 70% reduction. Report deviations
honestly rather than forcing the target.

## Contracts

### Model profile V1

```json
{
  "profile_version": 1,
  "model": "gpt-5.6-luna",
  "reasoning_effort": "high",
  "pricing_tier": "standard",
  "prompt_cache_policy": "explicit_no_cache"
}
```

- model identities derive from the exact pricing policy;
- reasoning values are an explicit transport capability, not Packet authority;
- V1 supports the tracked standard pricing table only;
- V1 preserves the current request behavior and does not add an API
  `service_tier` field; pricing classification and request routing are not
  conflated;
- profile identity enters run, count, request, and response receipts;
- changing it invalidates pre-dispatch authorization;
- qualification cells use request-wide explicit cache mode with no cache
  breakpoint; any reported cache activity fails closed;
- author output is capped at 8,000 tokens and review/correction output at
  4,000 tokens;
- Sol/high remains the operational default until qualification is accepted.

### Qualification case V1

A case binds its role, exact Packet V8 identities, disclosure profile and
manifest, model profile, one-round budgets, prompt/protocol identities,
pricing-policy identity, and rubric version. It references canonical artifacts
and services; it does not duplicate packet, proof, or state authority.

Each cell owns an ordinary automated run plus a compact qualification receipt
referencing transport, cost, proof, controller, cleanup, automatic-gate, and
human-rubric evidence. Historical run evidence is never rewritten.

## Implementation slices

### Slice 0 — Authority, pricing, fixture, and rubric lock

- Start from exact clean merged `main`; create an implementation branch only
  after plan approval.
- Reverify instructions, runtime, official pricing/model/cache guidance,
  credential availability, and user-confirmed funding.
- Record Slice 6 acceptance and PR #10 merge.
- Select and hash the three Packet V8 fixtures.
- Lock the rubric and case schema.
- Inventory model, effort, pricing, UI, prompt, parser, and receipt surfaces;
  do not change prompts.
- Preserve the historical token/cache audit and prove the explicit no-cache
  request contract offline.
- Run all rails, hostile review, commit, and clean tree.

Exit: fixtures, rubric, pricing, and funding status are known. No provider call.

### Slice 1 — Profile plumbing and zero-call harness

- Add validated profiles to the existing controller, transport, UI, run
  manifest, projections, events, and receipts.
- Keep Sol/high as the default.
- Add a narrow headless qualification runner invoking the existing controller;
  it must not duplicate transport, validation, proof, timeout, or cleanup.
- Add automatic hard-gate evaluation over existing receipts.
- Support recorded-response fixtures so controller/scoring paths run offline.
- Prove profile changes invalidate earlier dispatch estimates.

Exit: candidate cells can be prepared and tested with zero API usage.

### Slice 2 — Offline golden calibration and paid-gate preparation

- Apply the rubric to selected existing Sol/high evidence.
- Mark exact comparisons separately from historical behavioral references.
- Generate the Luna/high case manifest and one-round ceiling.
- Present exact fixture, profile, prompt identities, budgets, and cost method.
- Run focused/full tests, screenshots, hostile review, commit, push, clean tree.

Exit: stop for authorization of a count-only live preflight. No generation.

### Slice 3 — Count-only preflight and funding gate

After explicit authorization, use the shared count-only transport seam to
upload only manifest resources, count exact input tokens, compute the
policy-aware maximum cost, clean owned files without generation, and stop for
approval of that exact Luna/high ceiling.

If count, cost, or funding fails, stop. Do not silently shrink context, change
detail, lower effort, or substitute a model.

### Slice 4 — One paid calibrator cell

After exact approval, run one Luna/high author/prove/review cell on fixture 1,
preserve all evidence, apply automatic gates, and stop for user review.

Only the verdict selects the next separately approved cell:

- Luna/high pass -> Luna/medium;
- Luna/high fail -> Terra/high;
- infrastructure failure -> repair and repeat the same profile;
- insufficient funding -> stop.

No batch preauthorization is inferred.

### Slice 5 — Minimum-profile confirmation

After one profile passes and confirmation funding is approved:

- run it on fixtures 2 and 3;
- preserve identical prompts, case schema, budgets, and scoring;
- compare cost per success with historical Sol evidence;
- prove all profiles reuse canonical controller/domain owners;
- publish the acceptance ledger and recommendation or negative result;
- run all rails, commit, push, and stop for final acceptance.

Do not change the production default here. An accepted default change is a
later tiny configuration/documentation checkpoint.

## Validation rails

Every product slice runs focused tests followed by:

```powershell
$env:PYTHONPATH = (Resolve-Path .\src).Path
py -3.14 -m unittest discover -s tests
git diff --check
```

Each slice exercises its real workflow, performs hostile review, commits one
coherent checkpoint, and closes cleanly. Paid slices additionally prove exact
request/pricing identities, cleanup, resolved-model compatibility, context
tier, actual-versus-estimated cost, and no progression beyond the approved cell.

## Non-goals

- engine or runtime changes;
- Packet redesign or prompt rewrite before measured failure;
- cache-prefix or cache-breakpoint optimization before measured reusable-prefix
  evidence;
- one growing conversation across fixtures;
- Pro, multi-agent, Batch, Flex, Fast, or explicit provider-tier changes;
- more than one proven round per case;
- diagnostic mosaics or additional enrichment providers;
- generalized eval platform or model router;
- sweep expansion or agent turns per sweep member;
- automatic aesthetics, causal claims, or human acceptance;
- paid Sol reruns without separate justification and approval.

## Hostile planning review

- Cheap valid JSON is insufficient; the rubric also gates mathematical and
  experimental quality.
- Historical Sol evidence is not mislabeled as exact current A/B evidence.
- The profile control is explicit and receipted, not an automatic router.
- Standard pricing is not mislabeled as an API routing field; request-tier
  behavior stays unchanged.
- Local pricing remains an estimate; official docs and provider billing win.
- Count-only activity is not generation authorization and owns cleanup.
- One cell cannot turn into retries or a battery without another approval.
- Identical case resources prevent savings through silent context weakening.
- Three roles and one ladder prevent drift into a general eval framework.

## Approval boundary

Plan approval authorizes Slices 0-2 only: zero-paid-call repository preparation.
It does not authorize a provider count call or paid generation.

Slice 3 requires count-only approval. Every Slice 4 or Slice 5 generation cell
requires an exact separately stated dollar ceiling and explicit approval.
