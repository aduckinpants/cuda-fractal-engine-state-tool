# V9 Provider-Cost Hardening Evidence

Status: zero-generation implementation checkpoint in progress

Date: 2026-08-03

This note records the pre-spend audit and the request-policy hardening applied
before the V9 model ladder may use provider generation.

## Authority

Current official inputs:

- <https://developers.openai.com/api/docs/pricing>
- <https://developers.openai.com/api/docs/guides/prompt-caching#prompt-cache-breakpoints>

The tracked standard-rate policy remains
`openai-standard-2026-08-03`. Provider billing remains authoritative over the
local estimate.

No provider generation or input-token count call was made during this
hardening slice.

## Historical evidence

Sixteen preserved response receipts across four V8 automated runs show:

```text
maximum observed output tokens: 5,167
average observed output tokens: 1,803.88
maximum observed chained input: 330,248
total observed cache-write tokens: 1,974,529
```

The successful two-round Sol runs cost approximately `$6.66` and `$6.72`
under the current standard policy. Their review requests retained the original
conversation and added a refreshed Packet V8, exceeded the 272,000-token
short-context boundary, and paid long-context rates.

The merged controller already removes that multiplier by starting:

```text
author: fresh Packet V8 context
review: fresh derived Packet V8 + compact prediction/proof ledger
```

That final two-call architecture has not yet been exercised by a paid live
request and must not be described as provider-qualified.

Historical raw responses also show that a fresh roughly 165,000-token request
using the provider's implicit cache policy wrote almost its complete input into
cache. Fresh author and review requests do not reuse those exact prefixes, so
the write premium produced no demonstrated economic return.

## Packet and image observations

The locked Rational Escape calibration Packet V8 contains about 611 KiB of
text authority plus a 2048 by 1280 web PNG. The largest text owner is the
341,463-byte state-authoring authority container. Packet V8 remains the domain
contract; this slice does not remove or summarize authority merely to obtain a
lower token count.

The request continues to use the bounded `web-agent-frame.png` at explicit
`high` image detail. Lower detail could erase the fine structure being tested.
The deterministic assisted annotation is another 2048 by 1280 image and will
therefore be measured by the exact count gate before assisted generation.

## Locked request hardening

### Cache policy

GPT-5.6 requests now use:

```json
{
  "prompt_cache_options": {
    "mode": "explicit"
  }
}
```

No content block receives a cache breakpoint. Under the documented GPT-5.6
contract this disables the implicit breakpoint and therefore disables cache
reads and billable cache writes for these one-off contexts.

The request, estimate, projection, event, and response evidence record
`explicit_no_cache`. A response reporting cached or cache-write tokens under
that policy fails closed.

An explicit reusable prefix is deliberately deferred. Author-to-review packet
comparison found only the Color Pipeline authority byte-identical; all earlier
Packet V8 resources differed. Reordering the authority solely to manufacture a
cache prefix would change the transport presentation before qualification.

### Output caps

Historical output supports the following stage caps:

```text
author response:     8,000 tokens
review response:     4,000 tokens
correction response: 4,000 tokens
cumulative session: 48,000 tokens
```

The author cap retains about 55 percent headroom over the historical maximum.
The review cap is more than three times the historical review maximum. These
caps include hidden reasoning tokens and are hard request limits, not expected
usage.

### Exact count-only seam

`PacketV8ResponsesTransport.count_turn_input` prepares and uploads the same
manifest-driven resources, constructs the same request, asks the provider for
the exact input-token count, records evidence, rejects before generation, and
cleans only the files uploaded for that preflight.

The preflight remains an external provider action and still requires explicit
authorization. It is not generation authorization.

## Conservative one-round ceilings

These ceilings assume both author and review independently reach the existing
200,000 input-token limit and reach their entire 8,000 and 4,000 output caps.
Requests exceeding 200,000 input tokens stop before generation.

| Profile | Author maximum | Review maximum | One-round maximum |
| --- | ---: | ---: | ---: |
| Luna | $0.0496 | $0.0448 | $0.0944 |
| Terra | $0.4960 | $0.4480 | $0.9440 |
| Sol | $1.2400 | $1.1200 | $2.3600 |

At the same hard caps, implicit full-prefix cache-write pricing would bound a
round at `$0.1144`, `$1.1440`, or `$2.8600` respectively. Explicit no-cache
saves up to `$0.02`, `$0.20`, or `$0.50` per round before exact counting.

## Campaign envelope

The current ladder's conservative worst useful path is:

```text
Luna/high calibrator
+ Terra/high and Terra/medium escalation
+ two Terra confirmation fixtures
+ one optional Sol adjudication
+ one Terra infrastructure repeat
= less than $7.20 at the hard per-call limits
```

Most paths are substantially cheaper. The appropriate initial campaign budget
is therefore `$8.00`, not `$30.00`. The user's `$30.00` willingness remains
uncommitted emergency headroom. Every cell still requires its exact count and a
separate ceiling approval before generation.

## Remaining cost gates

Before the first paid model cell:

1. finish model-profile and qualification-case plumbing offline;
2. select and hash the Rational Escape calibrator and disclosure artifacts;
3. run the count-only preflight for Luna/high after explicit approval;
4. compare the exact count with the 200,000-token boundary;
5. present the exact cell ceiling and stop for generation approval;
6. verify the first live response reports zero cached and zero cache-write
   tokens under `explicit_no_cache`.

Packet compaction, lower image detail, resource reordering, or explicit cache
breakpoints require measured evidence and a separate behavior-preserving plan.

## Hostile review

- **Could no-cache understate cost?** The estimator uses ordinary input rates
  only because the request explicitly disables caching. Any nonzero provider
  cache read or write makes the response invalid instead of silently changing
  its price partition.
- **Could an older model ignore the field?** The route is restricted to the
  tracked GPT-5.6 family. Unsupported request fields fail as provider errors;
  there is no implicit-policy fallback.
- **Could count-only accidentally generate?** Its authorization callback always
  rejects immediately after the exact count. Tests prove no response-create
  call and exact uploaded-file cleanup.
- **Could reduced output caps truncate a valid hard case?** The author cap has
  measured headroom over every preserved response. Incomplete provider output
  remains a failed cell, not a parser workaround. The first live count and cell
  are still review gates.
- **Could the savings come from weakened evidence?** Packet bytes, prompts,
  image detail, disclosure profile, validator, proof, and review semantics are
  unchanged.
- **Could `$8.00` authorize a batch?** No. It is a campaign envelope used for
  planning. Count-only and every generation cell retain separate approval.

Conclusion: the zero-call hardening is coherent and does not justify provider
dispatch by itself. The next allowed external boundary remains one explicitly
approved Luna/high count-only preflight after offline profile/case preparation.
