# Finding Exploration and State Override Workflow

## 1. Open the finding

Launch the desktop tool, select a captured finding directory or artifact, and
open it into the durable workspace. Inspect the finding summary and bounded base
preview.

## 2. Hand the exact bundle to the web agent

After Agent Bundle V6 finishes:

1. Click `Copy Packet` and paste `packet.md` into a fresh web session.
2. Click `Open Agent Bundle Folder`.
3. Attach every file shown under `Attach required` plus any useful recommended
   context files.
4. Ask the normal exploration question.

Copying `packet.md` alone does not transmit the state, schemas, contracts,
catalog, authoring surface, or frame.

The agent should begin with curiosity-driven discussion. It should return no
override until you request a concrete change. Once requested, it returns one
sparse state-shaped JSON object, for example:

```json
{
  "params": {
    "explaino_damping": 0.9
  }
}
```

The object has no envelope, version, finding ID, hash, capability profile, or
action list. A path is usable only when the exact packet's
`state-override-authoring-surface.json` authorizes it.

## 3. Prove the returned override

Paste the JSON into the empty `Incoming State Override JSON` editor and click
`Validate & Replay Prove`.

The tool:

1. rechecks the immutable Packet V6 and published runtime identity;
2. validates the sparse override from the packet's copied authorities;
3. deterministically merges it into the exact base state;
4. loads that complete state through the engine without actions;
5. captures the engine-emitted candidate state and frame;
6. replays the emitted state without actions;
7. requires stable authoring state and identical decoded replay pixels.

Small runtime numeric representation changes are shown explicitly. Missing,
reverted, or materially contradictory values reject the proof.

## 4. Review the candidate

Replay success does not authorize launch. Compare the base and candidate
previews, or open either full frame explicitly.

- `Accept Candidate` writes an immutable accepted review decision and enables
  launch only after fresh hash and authority checks.
- `Revision Needed` preserves the proof and decision, keeps launch disabled,
  and lets you edit or replace the override for a new attempt.

## 5. Launch only the accepted engine state

`Launch Accepted State` rechecks the bundle, exact override text, merged state,
engine-emitted state, candidate frame, replay evidence, proof receipt, review
decision, and current runtime identity. It then launches the exact
engine-emitted state in a new viewer and writes `launch.json`.

## Safety boundaries

- `fractal_type`, render, lens, diagnostics, and absent optional state are not
  authorable.
- Camera high-precision companions are pair-only and are never synthesized by
  Python.
- Color Pipeline arrays replace completely; lane/row topology and enablement are
  fixed by the captured draft.
- Preview failure does not weaken proof or cause full-resolution Tk decoding.
- Reset cancels only session-owned work and preserves durable evidence.
- Historical proposal artifacts are data only and cannot be pasted into the
  active editor as a compatibility input.
