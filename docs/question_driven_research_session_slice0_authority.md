# Question-Driven Research Session — Slice 0 Authority Record

## Repository baseline

Recorded on 2026-08-05:

```text
repository: C:\code\cuda-fractal-engine-state-tool
starting branch: main
starting HEAD: cdfc516405080ba9604d8f16901068ed3018465a
origin/main: cdfc516405080ba9604d8f16901068ed3018465a
campaign branch: codex/question-driven-research-session-poc
Python: 3.14
baseline suite: 229 passed
```

The starting worktree had no tracked edits. The user-supplied
`docs/manual-test-results/v8-sweep-revision/` directory was untracked and is
adopted unchanged as campaign evidence rather than discarded or hidden.

The existing `stash@{0}` safety backup is unrelated and remains untouched.

## Published runtime baseline

```text
launcher: D:\salt-fractal\cuda_newton_fractal_clone\runtime\fractal_ui.cmd
launcher SHA-256: 2f532fc917362ba0db0c5e95e5ea0cd966786fabc73229e47c030ad94600012a
executable SHA-256: 26db530a4e73aa482f5752ed6bc35e7e5092dd94277aa417be25668d338c7560
runtime schema SHA-256: f4490afb2a1a1a985c97f6b70b832ae60a379d98fb6b2c06de3d8c6d06d57fb6
UI-Salt contract SHA-256: 4f38cd329e108a0321a745e3e121648f9af2547a84320200cc37548b52c8f9bb
runtime identity SHA-256: c8534d3bc26371e6e458e5b9f627b88501782950aa64b6d3e76686a7a44152ca
```

Runtime metadata is observed through `runtime_surface.build_runtime_identity`.
The engine repository is not a mutation target for this campaign.

## Canonical owner trace

| Responsibility | Existing canonical owner | Research-route rule |
| --- | --- | --- |
| Packet V8 construction and membership | `build_agent_bundle` and validated `manifest.json` | Reuse; add only deterministic active-pipeline presentation |
| Packet transport | `PacketV8ResponsesTransport` | Reuse manifest-driven resources; no hard-coded file list |
| Sparse override parse and merge | `parse_state_override`, `materialize_state_override` | Reuse unchanged |
| Proof and action-free replay | `execute_state_override_proof` through `AsyncJobRunner` / `JobContext` | Reuse unchanged |
| Proof timeout | `resolve_proof_timeout` / packet policy | Reuse unchanged |
| Full candidate PNG and comparison | proof-owned derivative and `compare_image_files` | Reuse; no new decoder or PNG writer |
| Scalar sweep | `ScalarBracketSweepService` | Reuse exact V1 service |
| Derived-finding publication | `promote_replay_proven_candidate` delegating to `SourceCaptureImporter` | Reuse only after explicit review nomination |
| Packet refresh | `build_agent_bundle` | Reuse after promotion |
| Provider files and cleanup | `PacketV8ResponsesTransport` | Reuse and receipt cleanup state |
| Pricing and count-only | existing pricing policy and transport count path | Reuse with research-stage reserves |
| Event history and current projection | `AutomatedRunStore` | Extract or extend one shared owner; do not copy atomic-write logic |
| Human acceptance and launch | manual review and launch services | Excluded from research automation |

The prior Responsibility-Compression Scanner qualification remains
`NOT_APPLICABLE` to this Python/Tk repository. Source and runtime traces, not a
fabricated scanner adapter, govern the campaign.

The research-route default is `gpt-5.6-luna`, high reasoning, assisted
enrichment disclosure, standard pricing tier, and explicit no-cache transport.
The disclosure and pricing-tier concepts remain separate.

## Golden fixture qualification

```text
source capture:
D:\salt-fractal\cuda_newton_fractal_clone\findings\manual_capture\2026-08-05\143014_930__explaino_transcendental

historical packet:
D:\salt-fractal\cuda-fractal-engine-state-tool\findings\3209208bc5ccbc09a8f36fbc60b95d125f082761e0195b8c9aaee1af80f3c2cc\packets\41de51de-0e49-4114-8c1a-0b6f86a09af3

packet manifest SHA-256:
7ae3593b628b3b1d9bbde86f9aba4fa5dd808985043167918ee27cafb14e0fb6

finding ID:
3209208bc5ccbc09a8f36fbc60b95d125f082761e0195b8c9aaee1af80f3c2cc

selector: explaino_transcendental
captured epsilon: 9.999999974752427e-07
captured maximum iterations: 1500
```

The packet's mechanically derived sweep surface contains a direct float axis:

```text
path: params.epsilon
current value: 9.999999974752427e-07
declared minimum: 1e-12
UI range: [1e-12, 0.01]
source control: epsilon
```

The captured active Color Pipeline is:

```text
Source: Phase Orbit [phase_orbit]
-> Shape: Identity [identity]
-> Palette: Phase Wheel [phase_wheel_palette]
-> Grading: Phase Finish [phase_finish]
```

All four rows are enabled and occur in deployed lane order. This chain is the
relevant observation context for the phase-colored termination rings.

The historical packet runtime identity is
`023b4dab4347a6fe8e8c3c560a5dd34dbac3ec54355094bea150b57061ce95a6`,
which differs from the current published runtime identity. It remains valid
historical evidence. Before a paid golden run, regenerate Packet V8 from the
same source capture under the then-current runtime and revalidate the epsilon
axis, base state, pipeline, and manifest binding.

## Historical evidence identities

The user-supplied Markdown was normalized only for trailing whitespace and a
single final newline so the repository diff rail remains clean. The tracked
content identities are:

| File | SHA-256 |
| --- | --- |
| `artifacts.txt` | `4c4725ccfe80f4cd32af8652d3af198a2eff9a728882957972fff10268b20e08` |
| `fractal_session_transcript(1).md` | `048a4e64e43c8251e07bfb6b98ca22174895940ada1d5487102af4ac8318e10a` |
| `fractal_tooling_packet_self_evaluation.md` | `114782a4ef2651c36cd896deb7413406c76322eb5810781e1cf928d17177430e` |

They establish the historical epsilon investigation and its process lessons;
they do not replace Packet, proof, sweep, or runtime authority.

## Rational Escape exclusion

The earlier Rational Escape idea is not the golden court. The scientifically
interesting near-critical value is `params.explaino_seed_drift`, while the
current Packet authoring projection does not truthfully expose that serialized
path as a direct sweep axis. No state-tool special case or engine mutation is
authorized here.

## Slice 0 closure gate

Slice 0 closes only after this record and the campaign contract are tracked,
the supplied evidence is preserved, focused contract checks and the complete
Python 3.14 suite pass, hostile review finds no open contract contradiction,
and the branch is committed with a clean tree.
