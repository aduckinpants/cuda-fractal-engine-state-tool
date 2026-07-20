# Runtime Authority Probe

Status: Phase 0 authority probe implemented and exercised against the configured published runtime. Raw manifests, command transcripts, hashes, and emitted artifacts live under ignored `.local/runtime_probe/`.

## Runtime Surface

- Configured launcher form: local published runtime launcher, represented here as `<published-runtime>\fractal_ui.cmd`.
- Controlled working directory: the probe runs the launcher from its published runtime directory rather than from the tool repository.
- Resolved launcher behavior for argument-bearing commands: the launcher reads an active-executable file, resolves the active executable in the same runtime directory, and invokes it directly when arguments are present.
- Resolved launcher behavior for no-argument launch: the launcher starts a detached viewer process and returns.
- Runtime identity method: launcher sha256, resolved executable sha256 when resolvable, runtime-schema sha256 when present, source-schema sha256 when discoverable from runtime metadata, describe-output hashes, and invocation working directory.
- File-version metadata: the resolved executable did not surface a usable Windows file-version string during the probe.

## Process Lineage

- Exact launched PID tracking: implemented in the probe helper.
- Exact-root process-tree cleanup: proven safely with a local child-process fixture.
- Real headless runtime commands were too short-lived for useful process-tree snapshots; their observed process-tree payloads were empty.
- A direct no-argument launcher observation did create a new viewer process. The observed viewer process was a detached `fractal_ui.exe` child in the published runtime directory.
- The wrapper process chain for detached launch is transient enough that the probe should treat detailed launcher lineage as observed-but-limited rather than fully characterizable from the short-lived wrapper alone.
- Safe conclusion: exact-PID cleanup is appropriate for tool-owned helper processes and explicitly observed viewer processes; no broader process-name cleanup is justified.

## Baseline Capture Findings

- Two no-input `--capture-diagnostic` runs succeeded when given absolute isolated output directories.
- Each run emitted `state.json` and `frame.bmp` into the requested output directory.
- Raw comparison result: the two emitted `state.json` files were not byte-identical.
- Semantic comparison result: the files were semantically equal over the loader-relevant top-level state sections used by the current tool comparison logic.
- Observed difference in the repeated captures: `stats.last_render_ms` only.
- Replay of at least one captured state succeeded through `--load-state-json <captured-state> --capture-diagnostic`.
- Baseline candidate conclusion: a no-input capture is a viable baseline candidate for the experiment, but it should still be treated as one frozen replay-proven file rather than as proof that all repeated no-input captures are byte-stable.

## Replay Artifact Findings

- During Phase 0, capture-emitted `state.json` is treated as a runtime replay artifact, not automatically as canonical working state.
- A replay artifact was successfully produced from one captured no-input baseline candidate.
- Replay-artifact promotion policy remains unproven and is intentionally deferred.
- The first tool loop should preserve both the transport candidate and the replay artifact and diff them rather than replacing one with the other automatically.

## Metadata Outputs

- `--describe-parameter-surface-json <abs-path>` succeeded.
- `--describe-functions-json <abs-path>` succeeded.
- Both surfaces write JSON successfully when given absolute output paths.
- Earlier failures with relative output paths were a probe bug, not a runtime limitation: the launcher executed from the published runtime directory, so relative output paths targeted the runtime tree instead of the tool workspace.
- Output hashes are recorded under the ignored runtime-identity manifest in `.local/runtime_probe/`.

## Schema Provenance

- The published runtime contains a runtime-side `ui/fractal_binding_surface_v1.ui_schema.json` candidate.
- The runtime also provides a repo-root hint pointing back to the authoritative source checkout.
- A source-side schema file is therefore discoverable from runtime metadata.
- The runtime-side schema hash and source-side schema hash differed in the probe run.
- Safe conclusion: runtime metadata and source schema must be labeled separately as mixed provenance unless a stronger alignment proof is established.

## Failure Signatures

- Invalid JSON passed through `--load-state-json ... --capture-diagnostic` produced a nonzero exit code.
- That invalid-JSON run produced no useful stdout or stderr phase marker and did not create the requested diagnostics output directory.
- Safe conclusion: current runtime-status classification must remain coarse. The tool may reliably distinguish success from bounded runtime failure for this path, but it may not yet distinguish loader rejection from later replay failure from output-path failure solely from the observed command outputs.

## Limitations

- If a requested fact would require patching the fractal engine to establish, Phase 0 must record that limitation rather than broadening into engine changes.
- The current probe does not yet prove which replay-artifact fields, if any, are authoritative normalizations versus capture-conditioned or environment-conditioned values.
- The current semantic comparison is intentionally conservative and keyed to the known loader-relevant top-level sections; it does not yet classify all replay-artifact-only fields into a full policy table.
- Detailed detached-launch wrapper lineage is only partially observed because the wrapper exits too quickly to give stable per-command tree snapshots.

## Conclusions Safe To Rely On

- The published launcher is usable for Phase 0 and Phase 1 when invoked from its runtime directory.
- Absolute output paths should be used for all probe and validation artifacts.
- No-input capture is replayable and semantically stable enough to serve as a baseline candidate for the first experiment.
- `--describe-parameter-surface` and `--describe-functions` are available from the published runtime.
- Runtime-side schema and source-side schema should be treated as distinct provenance surfaces for now.
- Invalid JSON currently yields only a coarse nonzero-failure signal on the capture path.
- Automatic promotion of replay-artifact state remains unjustified at the end of Phase 0.
