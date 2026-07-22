# Agent State Override Rescue

## Authority and boundary

- Starting commit: `035dd9771a7d8dcac1df225a804f175e13590919`
- Branch: `codex/agent-state-override-rescue`
- Mutation owner: this repository only
- Runtime authority: `D:\salt-fractal\cuda_newton_fractal_clone\runtime`
- Python validation interpreter: 3.14

The active product becomes:

```text
Exact Finding Bundle
+ Sparse Agent State Override
-> Deterministic Merged Candidate
-> Engine Materialization
-> Action-Free Replay
-> Candidate Preview
-> User Accept / Revise
-> Exact-Candidate Launch
```

The CUDA engine repository and published runtime are read-only inputs. Historical
workspace artifacts are preserved as data and are never rewritten or deleted.

## Slice 0 - contract lock and audit

The failed proposal architecture is not a compatibility requirement. The active
dependencies to retire after the atomic UI cutover are:

- `proposal.py`, proposal examples, and the handwritten color tuple allowlist;
- proposal/materializer/finding/state workflow CLIs and prompt-session harnesses;
- capability-profile interpretation and agent-supplied binding envelopes;
- Color Pipeline action lowering and the reduced lane/function catalog;
- repair packets and proposal-oriented UI/session states;
- active tests and documentation that advertise those paths.

Reusable lower-level seams are runtime identity/command construction, finding
import, async job ownership, bounded preview generation, exact JSON duplicate
detection, descriptive-catalog loading, and state/frame comparison.

## Packet V6 contract

Packet construction stages one coherent authority snapshot in a temporary
directory, derives all indexes and examples from the copied bytes, rechecks the
live runtime identities, and only then atomically publishes the immutable packet
directory. A V6 packet contains the exact finding artifacts, deployed UI schema,
deployed UI-Salt contract, full runtime parameter-surface export, full descriptive
catalog, a finding-specific `state-override-authoring-surface.json`, concise
`packet.md`, and a manifest that hashes every sibling artifact.

The authoring surface is a deterministic index into the copied authorities. It
is not a surrogate schema. Applicability does not imply state authorability: an
entry is emitted only when exact metadata resolves unambiguously to a present
serialized `params` or `view` path.

The manual handoff is explicit:

```text
Copy Packet
-> paste packet.md
-> Open Agent Bundle Folder
-> attach every required authority file and frame
```

Copying the Markdown alone is never described as transporting the authorities.

## State override contract

The remote document is one sparse state-shaped JSON object. It contains no
version, finding/hash envelope, capability profile, action list, or receipt data.
Objects merge recursively, scalars replace, and arrays replace completely.
`null`, duplicate keys, non-finite numbers, unknown paths, absent optional paths,
and read-only/derived paths fail closed.

An empty override copies the exact base `state.json` bytes. A non-empty override
uses UTF-8 without BOM, two-space indentation, LF newlines, retained base object
ordering, contract/capture ordering for Color Pipeline structures, and exactly
one trailing newline.

Allowed V1 domains are `params`, mechanically supported `view` fields, and an
existing complete `color_pipeline_draft`. `state_version`, `fractal_type`,
`render`, `lens`, statistics, sidecars, automation, and absent fields are not
authorable.

Camera high-precision values are companion-only: `center_hp_x` requires
`center_x`, `center_hp_y` requires `center_y`, and `log2_zoom` requires `zoom` in
the same override. Python neither synthesizes nor proves their relationship.

For Color Pipeline authoring, the captured draft owns topology and the copied
UI-Salt contract owns functions and parameter metadata. Lane/row identity,
ordering, count, labels, enablement, and `next_row_id` remain fixed. Existing
rows may replace their function and complete parameter list. Python maintains no
parallel function, parameter, default, range, enum, compatibility, or coercion
table.

## Execution gates

1. Slice 0 closes with this tracked contract, dependency audit, full suite,
   hostile review, clean commit, and clean tree.
2. Slice 1 builds Packet V6 and closes at a manual web-session transport gate.
3. Slices 2-5 remain blocked until the user reports that the target web client
   exposed all required attachments correctly.
4. Every later slice runs focused tests, the full Python 3.14 suite, its real
   workflow proof, hostile review, diff checks, a coherent commit, and a clean
   tree.
5. The final rescue checkpoint is pushed and PR-ready but is not merged without
   separate authorization.

## Final closure

All execution gates above were subsequently passed. The user accepted the final
Color Pipeline candidate, launched the exact engine-emitted state, and recaptured
byte-identical decoded pixels. Pull request #2 merged the completed rescue to
`main` at `781cd0dc9375f8bfefb2c92fbd8af6384127c005`. This document remains the
historical contract for that completed campaign, not an active list of pending
work.
