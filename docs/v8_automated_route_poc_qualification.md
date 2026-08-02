# Packet V8 Automated Route POC Qualification

## Disposition

```text
IMPLEMENTATION_COMPLETE
DETERMINISTIC_QUALIFICATION_PASS
REAL_ADAPTIVE_TIMEOUT_PASS
LIVE_PROVIDER_QUALIFICATION_PENDING_CREDENTIAL_AND_USER_REVIEW
```

This report qualifies the bounded automated route without fabricating the one
capped external provider session. No OpenAI API request was made during local
implementation or qualification.

Reviewed code checkpoint:

```text
codex/v8-automated-route-poc
7a550d0679597025d67aad73d4e0819a994476c4
```

The final documentation checkpoint follows this code commit without changing
the qualified runtime path.

## Deterministic Qualification Matrix

| Gate | Evidence | Result |
| --- | --- | --- |
| Two-round controller and exact model/controller gate separation | `tests/test_automated_session.py` | Pass |
| `ROUND_ADVANCE` rebinding | second override binds the derived Packet V8 | Pass |
| `ROUND_REVISE` rebinding | second override remains bound to the preceding base Packet V8 | Pass |
| Unintended `{}` | one correction turn; base-replay validator semantics unchanged | Pass |
| Malformed or repeated bad override | stops at `MANUAL_REVIEW_REQUIRED` | Pass |
| Malformed gate | no inferred or silent transition | Pass |
| Proven-round cap | third-round request stops at exactly two proven rounds | Pass |
| Auto-promotion disabled | replay proof stops before promotion; no human acceptance fabricated | Pass |
| Manifest-driven provider input | ordered roles and hashes from exact Packet V8 manifest | Pass |
| Stored-response continuation | stable instructions repeated; no packet resend on continuation | Pass |
| Provider cancellation ambiguity | durable response retained; turn never resent | Pass |
| Provider timeout ambiguity | owned files retained until manual disposition | Pass |
| Definite provider rejection | turn uploads cleaned exactly | Pass |
| Provider file cleanup debt | reported as failure rather than hidden success | Pass |
| Credential and request sanitation | secret-shaped fields redacted; token usage retained | Pass |
| Run-store recovery | stale/missing projection rebuilt from append-only events | Pass |
| Conflicting recovery projection | fails closed | Pass |
| Evidence containment and atomicity | run-local paths only; immutable manifest; atomic writes | Pass |
| Promotion authority and tampering | packet, binding, state, receipt, and PNG hashes rechecked | Pass |
| Proof-owned image reuse | exact verified `candidate-display.png` copied; no second conversion path | Pass |
| Runtime drift/tampering and launch review | existing proof/readiness suites remain unchanged | Pass |
| Per-job cancellation | automated cancel does not cancel unrelated worker work | Pass |
| Canonical service delegation | proof, promotion, and packet refresh call recorded owners | Pass |

Focused Slice 4 checks:

```text
34 passed
```

Final full suite after qualification-only coverage was added:

```text
Python 3.14
148 passed
```

## Real Fixture F Adaptive-Timeout Proof

The exact historical negative witness was rerun without regenerating its packet
or changing its override.

Packet:

```text
D:\salt-fractal\cuda-fractal-engine-state-tool\findings\529d0037634964e430ea654ea4d17d2c220e23cfc6a3844192ddcfa1f91696a3\packets\6fb115b4-8e90-46c9-ad23-8dd11da383c5
```

Packet manifest SHA-256:

```text
7b2e3d9bef02bdedb9bd39f34af0f57dd47f7df2f12c3d5f2e673a7f0d02ff8d
```

Original override SHA-256:

```text
58aacad22000153f15a60f16faec41bacb82d5609f518b6b2ccc4e94c089f765
```

Ignored proof evidence:

```text
.local/p/fixture-f-adaptive/f3d6652d-a43b-4b59-90b5-a3f5b1a2cf77/
```

Receipt SHA-256:

```text
df1c97dd5278ec437c72fc26edbbeaac8c3c4cb5b3f1d15947310be471017ee1
```

Result:

- adaptive source: captured `last_render_ms = 203542.34375`;
- resolved timeout: 438 seconds per runtime stage;
- materialization: 258.805 seconds, exit 0, not timed out;
- action-free replay: 259.535 seconds, exit 0, not timed out;
- total CLI wall time: 523 seconds;
- runtime identity: exact packet match;
- materialization/replay decoded RGBA: byte-for-pixel identical;
- replay state: semantically equal, excluding the documented volatile render
  timing receipt;
- candidate PNG: proof-owned, 4096 by 2560, decoded-equivalent to the engine
  BMP;
- terminal proof status: `replay_proven`;
- `visual_review: pending`;
- `launch_ready: false`.

Candidate display PNG SHA-256:

```text
01273fbabcc30236f82723860fb8de9c63a4975b0251dfcb74105126476df1b8
```

This closes Fixture F's original fixed-timeout failure without weakening the
proof or acceptance boundary.

## Fixture G Conversational Milestone

Fixture G remains accepted manual evidence under:

```text
docs/manual-test-results/v8_six_fixture_manual_gate_08-01-2026/
```

It proves the Packet V8 conversational workflow and Lens/SDF-backed observation
path through a capable external session. It is not relabeled as an automated
provider run. The automated controller exercises the same stage sequence with
deterministic provider scripts; the capped live session remains deliberately
pending.

## UI Qualification

The two-column manual hierarchy was rendered after the automation entry was
added. A first inline design compressed the candidate-preview surface and was
rejected during visual review. The accepted design keeps one compact
`Automated Session...` row and opens a separate child panel.

Ignored screenshots:

```text
.local/p/ui-slice4-main-refactored.png
.local/p/ui-slice4-automation-panel.png
```

Observed no-key state:

- `Credential: not configured (no API request can start)`;
- Run disabled;
- Cancel disabled;
- manual candidate-preview and review hierarchy preserved;
- no live request dispatched.

## Responsibility-Compression Conclusion

The reviewed before/after trace is in
`docs/v8_automated_route_authority_trace.md`. Manual and automated routes
converge on the same packet loader, override validator and merger, adaptive
timeout resolver, proof launcher, process owner, proof-image materializer,
workspace importer, and Packet V8 builder. Human acceptance and viewer launch
remain manual-only authority.

The Salticid Responsibility-Compression Scanner remains correctly classified
as `NOT_APPLICABLE`; no adapter, synthetic scanner input, or score was created.

## One Capped Live Gate

The next approved boundary is one user-observed session after an API credential
is available:

1. Launch `run_ui.cmd` and bind one exact Packet V8 fixture.
2. Open `Automated Session...`.
3. Use `Set OpenAI API Key...`, or launch with `OPENAI_API_KEY` already set.
4. Leave the two-round, response, token, and timeout caps unchanged.
5. Choose whether replay-proven candidates may be promoted automatically.
6. Start exactly one `gpt-5.6` high-reasoning run.
7. Observe current packet authority, budgets, controller disposition, and the
   durable result folder.
8. Do not treat automation promotion as human acceptance and do not launch a
   viewer from an automated disposition.

Cancellation, provider ambiguity, cleanup debt, budget exhaustion, proof
failure, or any unresolved authority conflict ends at a recorded non-success
disposition. It never silently retries a conversational turn.

No second paid run, wider model sweep, Packet V9 work, or merge is authorized
by this campaign checkpoint.
