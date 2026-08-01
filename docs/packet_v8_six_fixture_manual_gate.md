# Packet V8 Six-Fixture Manual Gate

Date prepared: 2026-08-01

## Status and ownership

This is the user-run external web-session gate for Packet V8. The six fixtures
were selected by the user after visual and state review. The implementation
agent generated and independently reopened the immutable bundles, but must not
simulate, predict, or self-grade the web-agent sessions.

The CUDA engine repository, published runtime, and original captures were not
modified. Each packet contains exactly seven files and reports no unavailable
optional attachments.

## Handoff procedure

For each fixture:

1. Start one fresh temporary web-agent session.
2. Open the exact packet directory listed below.
3. Select all seven files, including `packet.md` and `manifest.json`, and drag
   them into the session together.
4. Confirm that all seven filenames remain visible and inspectable.
5. Use the shared opening and exploratory prompts.
6. Use the fixture-specific selection prompt. It explicitly asks for discussion
   first and does not yet authorize JSON output.
7. Ask the prediction/falsification prompt.
8. Only after one coherent experiment is selected, use the exact override
   trigger.
9. Load the same existing packet directory in the state-tool UI. Do not refresh
   it. Paste only the returned JSON, prove replay, visually review the candidate,
   and launch only after explicit acceptance.
10. Return the resulting capture and complete session transcript for review.

Copying `packet.md` separately is unnecessary for Packet V8. Dragging all seven
files is the primary transport.

## Shared prompts

Opening:

```text
What do you notice here? What seems mathematically interesting or worth exploring?
```

Exploration:

```text
What would you try?
```

Prediction and falsification, after the fixture-specific selection response:

```text
Before we run it, what exactly do you expect to change in the rendered frame, what should remain fixed, and what outcome would make you conclude that the experiment failed or that your interpretation was wrong? Do not return the override yet.
```

Exact override trigger, only after one coherent state experiment exists:

```text
Let's do that. Return the exact sparse state override for this finding.
```

Post-render comparison:

```text
Here is the fresh capture produced by the accepted override. Compare it with your prediction. Separate direct visual observations from state facts, grounded inferences, and hypotheses. What did the experiment establish, fail to establish, or leave ambiguous?
```

Session evaluation:

```text
This was a test of a new web-session agentic workflow for a fractal render engine project. Briefly evaluate your performance against the packet's authority, observability, ambiguity, camera, prediction, and sparse-override rules.
```

If the selection response still contains multiple experiments, a sweep, or an
unresolved camera choice, do not use the override trigger as generic assent.
Ask the agent to identify one exact state first. `{}` is valid only for an
explicitly requested base replay.

## Fixture A — ExplainO Fold

Source capture:

```text
D:\salt-fractal\cuda_newton_fractal_clone\findings\manual_capture\2026-07-24\093816_244__explaino_fold
```

Packet:

```text
D:\salt-fractal\cuda-fractal-engine-state-tool\findings\d0ebae039f19758575fae1407cffa14baadf260f006c047d23a6345dc695e510\packets\aff46d55-e454-4a82-9d06-91fbc0356c4f
```

- Finding ID: `d0ebae039f19758575fae1407cffa14baadf260f006c047d23a6345dc695e510`
- Packet ID: `aff46d55-e454-4a82-9d06-91fbc0356c4f`
- Packet text SHA-256: `811b4f59850048092b6e6e3d16420777b2f68af1161cde6678eb5deb76a5a2ed`
- Manifest SHA-256: `0c631954e0be33da62cb1f20860ff45a26e244e552dfc310f64c3aa4ad060a80`

Selection prompt:

```text
Select one state-authorable experiment that could help distinguish the large four-region geometry from structure introduced or emphasized by the layered Color Pipeline. Explain the active observation channel and the single comparison you chose. Do not return the override yet.
```

## Fixture B — ExplainO All, complex pipeline

Source capture:

```text
D:\salt-fractal\cuda_newton_fractal_clone\findings\manual_capture\2026-07-30\222449_767__explaino_all
```

Packet:

```text
D:\salt-fractal\cuda-fractal-engine-state-tool\findings\6676d59ebd8e1a6cb23ee7754b5ee3e7d68db6aba83be0c27215047922badb00\packets\68c848b7-ca63-418f-bce8-31a53e9e1ad0
```

- Finding ID: `6676d59ebd8e1a6cb23ee7754b5ee3e7d68db6aba83be0c27215047922badb00`
- Packet ID: `68c848b7-ca63-418f-bce8-31a53e9e1ad0`
- Packet text SHA-256: `9cb7b87159c095341b691557fd81c330bb8af0bde08387be68a24aa6affe7de5`
- Manifest SHA-256: `c848f44c7dae3adbdda75ed4595b2ebbf2fa95f7eeccbe5980a6c9ead40b3804`

Selection prompt:

```text
Select one coherent state-authorable experiment that tests a specific interpretation of this unusually layered Color Pipeline without collapsing several comparisons into one state. State which current function or signal makes the result observable. Do not return the override yet.
```

## Fixture C — ExplainO All, gold field

Source capture:

```text
D:\salt-fractal\cuda_newton_fractal_clone\findings\manual_capture\2026-07-30\155813_114__explaino_all
```

Packet:

```text
D:\salt-fractal\cuda-fractal-engine-state-tool\findings\1f3c878c60b13b9e66aeddcc107eea85672a6d85882b07d66903feda9f580f41\packets\6514085a-27a2-4ebf-9d0e-c78885e773f8
```

- Finding ID: `1f3c878c60b13b9e66aeddcc107eea85672a6d85882b07d66903feda9f580f41`
- Packet ID: `6514085a-27a2-4ebf-9d0e-c78885e773f8`
- Packet text SHA-256: `2565b9b783e1b5fc06c79b37ceaf128098b5e964548f0eddbfd17fbc8f0e54f5`
- Manifest SHA-256: `5a93d3a764bf6d718870827987168fc258c893515cbbacdb04d918b2cca0a01d`

Selection prompt:

```text
Select one mathematically motivated state-authorable dynamics experiment rather than a color-only change. Decide whether it is a same-window comparison, feature-tracking change, or transition survey, and explain how the active signal can reveal its effect. Do not return the override yet.
```

## Fixture D — ExplainO Mult, high zoom and multi-source color

Source capture:

```text
D:\salt-fractal\cuda_newton_fractal_clone\findings\manual_capture\2026-07-26\210614_504__explaino_mult
```

Packet:

```text
D:\salt-fractal\cuda-fractal-engine-state-tool\findings\15d62ebd7b1fbd9195c0e3aa4cb3610b4699645c1f8a2b4cd3b5b5be1d0ee03a\packets\6c84cdeb-fd7d-4c4c-84aa-188528cd5248
```

- Finding ID: `15d62ebd7b1fbd9195c0e3aa4cb3610b4699645c1f8a2b4cd3b5b5be1d0ee03a`
- Packet ID: `6c84cdeb-fd7d-4c4c-84aa-188528cd5248`
- Packet text SHA-256: `5d9e74eb848a4c67b8f96ed83251de7c534f960b41c8fe3f829d9e5800302d3b`
- Manifest SHA-256: `bcfd402f93e7f7e79169a7f51483b5fae4f5e515e1df529651903e667c1fc1b9`

Selection prompt:

```text
At this high zoom, select one state-authorable experiment with a clearly observable outcome. If it changes dynamics, justify the camera intent using the exact viewport facts; if it changes color only, preserve the camera and dynamics exactly. Do not return the override yet.
```

## Fixture E — ExplainO Mult, auto-iteration capture

Source capture:

```text
D:\salt-fractal\cuda_newton_fractal_clone\findings\manual_capture\2026-07-31\103522_405__explaino_mult
```

Packet:

```text
D:\salt-fractal\cuda-fractal-engine-state-tool\findings\e125c0b066fb7318379545561b0e93090e9347c4b5d32e196b84e2b71e54bed1\packets\f6eb6330-8327-4e80-9069-f7b9f57680da
```

- Finding ID: `e125c0b066fb7318379545561b0e93090e9347c4b5d32e196b84e2b71e54bed1`
- Packet ID: `f6eb6330-8327-4e80-9069-f7b9f57680da`
- Packet text SHA-256: `1e08db50e6312d6740491d937fecbf12cdae2ad1824525fc51d870a09b671c93`
- Manifest SHA-256: `6f97e170d31c7748f5b77c8c2a5ca1a19c7c08d22ea111df1d64ca5f508f4d27`

Selection prompt:

```text
Select one state-authorable experiment that uses the visible basin structure as an observation channel without treating its symmetry or repetition as proven causality. Account for the captured automatic-iteration context when describing what the comparison can establish. Do not return the override yet.
```

## Fixture F — ExplainO Balance Void, red iteration-collapse diagnostic

Source capture:

```text
D:\salt-fractal\cuda_newton_fractal_clone\findings\manual_capture\2026-07-24\090604_402__explaino_balance_void
```

Packet:

```text
D:\salt-fractal\cuda-fractal-engine-state-tool\findings\529d0037634964e430ea654ea4d17d2c220e23cfc6a3844192ddcfa1f91696a3\packets\e07545db-94a9-4862-90b5-995957ebb7a3
```

- Finding ID: `529d0037634964e430ea654ea4d17d2c220e23cfc6a3844192ddcfa1f91696a3`
- Packet ID: `e07545db-94a9-4862-90b5-995957ebb7a3`
- Packet text SHA-256: `2d17522ce9a2b0e60707a3d156d47ecafa9a793c7d1fa01a495de55c97361703`
- Manifest SHA-256: `b7aac4e45e94e6907b875f71571150f63d5150488dcb23d6055576da7d3ddbe5`

Selection prompt:

```text
Treat the nearly red frame as an observation, not proof of its cause. Select one state-authorable single-state diagnostic that can test whether useful variation is being compressed by the current iteration-derived color measurement. Distinguish a color-measurement experiment from a dynamics experiment and do not claim this one frame isolates either cause. Do not return the override yet.
```

## Shared identities and local proof

All six packets bind:

- runtime identity SHA-256:
  `140707fd16283ac2db3c58a24146b73a7f29bbd15b0e1b36771c301f8b275e95`;
- published executable SHA-256:
  `ae329398693a5872faced0fa6f9cf57868788fc975b07ece5150954ac4face78`;
- UI-Salt contract SHA-256:
  `4f38cd329e108a0321a745e3e121648f9af2547a84320200cc37548b52c8f9bb`;
- descriptive catalog SHA-256:
  `8038ab867cd40dd4af6ca5b26aca11cd5e7c6b6a28816b00f7d4afdb4a4909fd`.

Independent Packet V8 inspection passed for all six. Each directory contains
exactly the manifest-declared seven files, all embedded authority records parse
and hash correctly, the drag-all list equals the physical directory, and no
optional attachment is missing.

## Acceptance checklist

- All seven files remain attached with their original names and are inspectable.
- The agent begins with exploration rather than configuration output.
- It distinguishes visual observations, serialized facts, grounded inference,
  and hypotheses.
- It uses the selected engine description as background, not capture-specific
  causal proof.
- It classifies proposed work as state-authorable, analysis-only, or requiring
  unavailable capability.
- It selects one exact state experiment rather than a sweep or several bundled
  comparisons.
- It asks one clarification question instead of emitting JSON when selection
  remains ambiguous.
- It identifies an active rendered signal or exported diagnostic that can
  observe the intended effect.
- Its prediction names both an expected visible change and an invariant.
- Its falsification condition is concrete rather than ceremonial.
- Dynamics changes use an honest camera intent and the exact viewport facts.
- Color-only changes preserve camera and dynamics.
- Every promised change appears in the sparse JSON and every JSON change is
  explained by the experiment.
- It returns exactly one fenced JSON object only after the trigger.
- It never uses `{}` for ambiguity, refusal, or unavailable capability.
- The state tool validates and replays the override without silently changing
  the experiment.
- Replay proof stops at visual review; launch remains disabled until explicit
  user acceptance.
- The post-render comparison admits failed predictions and does not upgrade one
  image into causal or self-similarity proof.

## Stop boundary

The implementation agent stops here. The user performs the six external
sessions and returns transcripts, overrides, proof results, and resulting
captures. Further packet behavior changes, fixture expansion, or merge work
requires review of that evidence and a new approved boundary.
