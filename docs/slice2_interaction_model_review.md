# Slice 2 Interaction-Model Review

## Checkpoint

The active branch now contains one application surface. `app.py` is only a
compatibility entry point to `user_workflow_app.py`; the archived controller,
notebook, debug surface, and widget hierarchy were deleted from the branch.
Historical recovery is through `archive/vscode-phase3-ui` and ordinary Git
history.

Launch command:

```powershell
.\run_ui.cmd
```

## Real shell walkthrough

The final visual capture used finding
`22a35168b3a7c02b6a3b8eb271d9b9a7611813ff5e558336197ac931fbcd29ae`
with authoring base
`6d68b95d89445deef0ee1300150acb4c5283e4493212b1bb98b814e3ab72c7ef`.

The source frame was 4096×2560. The UI loaded only its cached 640×400
derivative and displayed a further fit of that derivative without reopening the
source image in Tk.

Raw screenshots and manifest:
`.local/slice2_ui_acceptance_final/`

- `EMPTY`: `75909aed93b9626b0719663bfcdf5f8519858d4e5ad60a2f2cf24591c27ead6a`
- `PACKET_READY`: `1df3ee0565a20aa9d2a748332b6e89da4089fbc717d2470bbad95ba27ed3bf8a`
- `PROPOSAL_DIRTY`: `6d3df441e87867e497f82c9727ad521eccfa457b974cfd98c945f284ba5ca79e`

The captured exact packet was
`8e27c439-44c3-4f86-808f-b6b7d374fa4a` with SHA-256
`5f6999fb07ebf9a72ede18a20081600946cdfa1449dc171d46c2c4f89ee6fe8b`.

## Async ownership finding

The first live visual run exposed a worker-thread Tk dispatch error. Raw partial
evidence remains under `.local/slice2_ui_acceptance/`. Completion dispatch now
uses a thread-safe queue polled by the Tk thread; workers never invoke
`Tk.after` or mutate widgets. The corrected and final live runs completed
finding import, preview, packet generation, proposal editing, screenshot
capture, and clean application shutdown.

The shared worker provides bounded concurrency and queue capacity, immutable
request identity, per-request child-process ownership, cancellation, exact
owned-process cleanup, stale-result suppression at the controller boundary,
and shutdown rejection of new work. Preview and future runtime proof use this
same worker abstraction.

## Review boundary

Please review:

- two-column hierarchy and direction of information flow;
- finding context and bounded preview;
- outgoing packet versus incoming proposal separation;
- empty proposal behavior;
- state indicator and control grouping;
- disabled proof, repair, and launch behavior.

After acceptance, this interaction hierarchy freezes. Slice 3 may populate the
existing proof and repair surfaces and change readiness states, but may not
substantially rearrange the screen without renewed review.
