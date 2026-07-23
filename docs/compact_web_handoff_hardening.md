# Compact Web Handoff and PNG Display Hardening

## Starting authority

- Repository: `C:\code\cuda-fractal-engine-state-tool`
- Starting main commit: `3f2bee9`
- Branch: `codex/compact-web-handoff-hardening`
- Published engine/runtime mutation: forbidden
- UI redesign and future evidence-toolset work: deferred
- Baseline: Python 3.14 full suite, 85 passing tests

The completed Packet V6 calibration established that the state-override
authority model is sound. The remaining friction is transport: too many
separate uploads, oversized source frames that a web client resizes anyway, and
BMP proof frames opening in Paint.

## Locked outcome

Packet V7 keeps every exact source and authority artifact in the immutable local
packet. It adds a smaller web-upload view:

1. `state.json`
2. `fractal-state.json`, when present
3. `fractal-viewport-facts.json`
4. `state-authoring-authorities.md`
5. `color-pipeline-authority.md`
6. `finding-context.md`
7. `web-agent-frame.png`, when a captured frame exists

`packet.md` is pasted, not counted as an uploaded attachment. Missing optional
files are stated in `finding-context.md` and `packet.md`; the required upload
set contracts naturally when an optional exact sidecar or frame is absent.

The consolidated Markdown files are deterministic transport views, not new
authority. Their sections identify the exact neighboring local artifact, role,
byte size, and SHA-256. JSON payloads are copied into fenced sections from the
already-staged immutable packet bytes; they are not independently reread from
runtime or source paths.

## Authority boundaries

- `state.json`, `fractal-state.json`, and viewport facts stay exact and
  separately attachable.
- The full parameter surface, UI schema, UI-Salt contract, descriptive catalog,
  authoring surface, finding manifest, notes, and pipeline example remain as
  individual immutable local packet artifacts.
- Proof and validation continue to consume those exact local artifacts.
- Consolidation does not alter proposal/override grammar, validation,
  applicability, pipeline semantics, viewport mathematics, or runtime proof.
- The selected catalog entry may be rendered into `finding-context.md`, but it
  remains bound to the complete local catalog hash.
- No ZIP, PDF, single giant Markdown authority dump, historical fallback, or
  engine-source scraping is introduced.

## Image contracts

### Web discussion derivative

`web-agent-frame.png` is:

- PNG;
- never upscaled;
- bounded to a provisional 2048-pixel maximum long edge;
- generated in an isolated image worker under the existing decoded-pixel,
  maximum-dimension, and timeout safety policy;
- recorded with source and derivative hashes and dimensions, resampling method,
  and explicit `discussion_derivative_not_full_resolution_authority` status.

Packet guidance says that exact pixel counts, color frequencies, and other
resolution-sensitive measurements apply only to this derivative unless the
full source frame is separately supplied and identified.

### Full candidate display derivative

The engine's authoritative `materialization/frame.bmp` and
`replay/frame.bmp` remain untouched. After proof, the tool creates a
full-resolution PNG display derivative of the engine candidate, verifies that
its decoded RGBA hash and dimensions equal the authoritative BMP, records both
encoded hashes and the shared decoded identity in the proof receipt, and opens
the PNG for visual review. A missing, changed, or decoded-inequivalent display
derivative invalidates its use.

This is a display-format improvement, not render authority or automatic visual
acceptance.

## Slice 0 — Calibration closure and clean transition

1. Record the supplied C2, E3, and ExplainO Bell results and exact proof/capture
   references.
2. Run the full suite and hostile review.
3. Commit, push, update PR 5, merge under the user's standing state-tool
   authorization, and fast-forward clean main.
4. Create this branch from exact merged main and lock this plan.

## Slice 1 — Packet V7 compact handoff

1. Add failing tests for Packet V7, preserved local authorities, deterministic
   consolidated views, exact embedded byte provenance, dynamic optional-file
   handling, and the compact upload list.
2. Build every consolidated view from bytes already copied to the staging
   directory.
3. Keep manifest records for all local files and classify files as
   `required`, `recommended`, `local_authority`, `index`, or `generated_helper`.
4. Update packet guidance and UI attachment logging without rearranging the
   accepted two-column hierarchy.
5. Prove V6 packets remain immutable historical data and V7 packets load
   normally.

## Slice 2 — PNG transport and display derivatives

1. Add failing image-policy, cache, no-upscale, identity, tamper, and UI-open
   tests.
2. Generate and bind `web-agent-frame.png`.
3. Generate a decoded-equivalent full-resolution candidate PNG after proof and
   record it in receipts.
4. Open base or candidate BMP evidence through verified PNG display derivatives
   while preserving the original files.
5. Do not alter runtime commands, engine output formats, or proof parity rules.

## Slice 3 — Validation and fresh manual gate

1. Run focused tests, full Python 3.14 suite, real bundle generation, state
   override proof, left-side UI workflow, `git diff --check`, and hostile
   review.
2. Inspect manual captures and select unused findings that exercise:
   - an ordinary scalar or viewport-authorable case;
   - a complete nontrivial Color Pipeline draft;
   - a comparatively large or visually dense source image where the bounded
     derivative materially reduces transport.
3. Generate exact immutable V7 packets and record paths, hashes, upload lists,
   prompts, and a concise user checklist.
4. Commit, push, and open a ready PR.
5. Stop. The user performs the web sessions; the execution agent does not
   simulate or grade them.

## Manual acceptance

For each selected fresh capture:

1. Paste `packet.md`.
2. Upload only the exact files listed by its Web-session handoff section.
3. Confirm preserved filenames and readable authority sections.
4. Ask the ordinary exploration and experiment-selection prompts.
5. Confirm the response treats the PNG as a bounded discussion derivative,
   identifies exact authorities correctly, and returns no override before a
   concrete trigger.
6. Run any returned override through the exact packet binding in the desktop
   tool.

If the target web client ignores or truncates consolidated authorities, stop
and revise transport only. Do not weaken the authority model or re-expand the
active prompt architecture to mask a client transport defect.

## Closure boundary

The implementation checkpoint may be described as acceptance-ready only after
all local rails pass and fresh packets exist. Product acceptance remains
pending the user's external web-session tests.
