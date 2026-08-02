# Packet V8 Automated Route Authority Trace

## Purpose

This source-grounded trace records the exact merged-main semantic owners that
the automated route must reuse. It replaces any attempt to apply the qualified
Salticid Responsibility-Compression Scanner to this Python/Tk repository.

Baseline commit:

```text
3f42290abb734ae17e8ae95f2c2c9f111d631fb4
```

## Manual Route

| Authored operation | UI/controller route | Semantic owner | Runtime/artifact authority | Classification |
| --- | --- | --- | --- | --- |
| Open capture or Packet V8 directory | `UserWorkflowApp.open_finding_path` / `open_packet_path` | `load_finding_context`, `load_existing_packet_context`, and `SourceCaptureImporter` | workspace `source/`, `workspace.json`, and immutable packet directory | Intentional entry routes converging on shared loaders |
| Build Packet V8 | `UserWorkflowApp.build_packet` | `build_agent_bundle` | staged immutable packet plus `manifest.json` | Canonical packet owner |
| Reopen or copy packet | `_activate_bundle`, `copy_packet`, `open_bundle_folder` | `load_agent_bundle_handoff`, `copy_agent_packet`, `open_agent_bundle_folder` | manifest-bound packet bytes | Intentional presentation routes |
| Parse and merge sparse override | `UserWorkflowApp.prove_override` delegates into proof | `parse_state_override` and `materialize_state_override` | exact override text, copied Packet V8 authorities, merged candidate | Canonical validator and merge owner |
| Execute materialization and replay | `prove_override` submits an owned async job | `execute_state_override_proof`; synchronous CLI uses `run_state_override_proof_sync` over the same function | runtime-emitted state/frame, replay state/frame, receipt | Canonical proof owner with two intentional callers |
| Own runtime process and cancellation | UI `_submit` and synchronous proof wrapper | `AsyncJobRunner` and `JobContext.run_process` | exact process command, PID, timeout, stdout/stderr, cleanup | Canonical process owner |
| Resolve proof timeout | UI omits the argument; CLI and proof functions expose fixed defaults | No current policy owner | default `90.0` seconds plus sync wrapper wait | Automation-blocking representation debt; Slice 1 creates one resolver and migrates all callers |
| Materialize full candidate PNG | internal proof completion | `_create_candidate_display_derivative` in `state_override_proof.py` | `materialization/candidate-display.png` plus decoded-RGBA equivalence in `receipt.json` | Canonical proof-image owner; must not be duplicated |
| Preview candidate in Tk | `_proof_completed` and `_candidate_preview_loaded` | `PreviewService` creates only bounded UI cache derivatives | proof-owned full PNG remains authority | Intentional presentation derivative |
| Record human decision | `accept_candidate` / `request_revision` | `record_state_override_review` plus `UserWorkflowSession` | `review-decision.json` | Human lifecycle authority; automation must use distinct dispositions |
| Launch accepted state | `launch_accepted_state` | `validate_state_override_launch_readiness` and `launch_state_override_candidate` | engine candidate plus review and launch receipts | Human-only route; not used by POC automation |
| Publish source finding | `load_finding_context` | `SourceCaptureImporter.import_capture` | deterministic finding ID, copied source artifacts, workspace manifest/index | Canonical workspace publication owner |
| Publish derived finding | No existing operation | One bounded derived-finding promoter must stage proven state and exact proof-owned PNG, record lineage, then delegate to `SourceCaptureImporter` | derived source bundle and importer-owned workspace artifacts | Missing owner to add once; must not reproduce importer logic |
| Refresh packet after promotion | No automated caller yet | `build_agent_bundle` | new immutable Packet V8 | Reuse canonical packet owner |

## Required Automated Route

```text
validated current Packet V8
-> manifest-driven model transport
-> protocol controller selects one override
-> parse_state_override / materialize_state_override
-> shared timeout resolver
-> execute_state_override_proof through AsyncJobRunner
-> proof-owned candidate-display.png
-> one derived-finding promoter
-> SourceCaptureImporter
-> build_agent_bundle
-> explicit ROUND_ADVANCE or ROUND_REVISE rebinding
```

The model transport owns provider exchange only. The protocol controller owns
automation state and legal transitions only. Neither may reinterpret packet,
state, proof, runtime, image, or workspace facts.

## Automation-Blocking Compression

Only these baseline findings authorize implementation work:

1. Proof timeout is a repeated numeric default rather than a canonical policy.
2. Derived-finding promotion has no owner; one service is needed to stage
   provenance and delegate publication to the existing importer.
3. The UI currently owns manual session presentation. Automated lifecycle state
   must live in a separate controller/run store and remain callable without Tk.

The following are intentional and must not be compressed:

- UI and CLI as separate entry routes into the same proof service;
- full proof PNG and bounded UI preview as different representations;
- human review/launch disposition and automation promotion disposition;
- engine materialization and action-free replay as distinct proof stages.

## Slice 5 Comparison Requirement

Repeat this trace after implementation and prove:

```text
same authored operations
-> same validator and merge owner
-> same timeout resolver
-> same proof launcher and process owner
-> same proof-image owner
-> same packet builder
-> one derived-finding promoter delegating to the same importer
-> distinct human and automation lifecycle dispositions
```

Pre-existing nonblocking multiplicity remains visible; a lower finding count is
not itself a success criterion.

## Post-Implementation Trace

Reviewed implementation commit:

```text
7a550d0679597025d67aad73d4e0819a994476c4
```

| Semantic responsibility | Manual entry route | Automated entry route | Canonical owner after implementation | Disposition |
| --- | --- | --- | --- | --- |
| Packet membership and exact resource bytes | UI bundle binding/copy/open | `PacketV8ResponsesTransport` prepares the current packet | `load_agent_bundle_handoff` plus validated Packet V8 `manifest.json` | One owner; transport follows manifest order and does not own a file count |
| Sparse override syntax and state authorability | `prove_override` | `AutomatedSessionController` override stage | `parse_state_override` and `materialize_state_override` | One validator/merge owner; controller adds only experiment-outcome policy for `{}` |
| Proof timeout | UI and proof CLI omit or explicitly override policy input | production automated services call the same proof owner | `resolve_proof_timeout` / `resolve_packet_proof_timeout` | Baseline numeric duplication removed |
| Runtime materialization and replay | async UI proof / synchronous proof CLI | job-bound automated service | `execute_state_override_proof` with `JobContext.run_process` | One proof and process owner |
| Candidate PNG | manual candidate preview reads the proof derivative | promotion consumes the proof derivative | `_create_candidate_display_derivative` inside `state_override_proof.py` | One decoder and full-PNG writer; promotion copies exact verified bytes |
| Finding publication | capture import | replay-proven candidate promotion | `SourceCaptureImporter` | `promote_replay_proven_candidate` only checks lineage and stages exact proof artifacts before delegation |
| Packet refresh | manual `Refresh Bundle` | post-promotion round refresh | `build_agent_bundle` | One Packet V8 builder |
| Human review and launch | `record_state_override_review`, readiness recheck, launcher | unavailable to automation | manual UI/service route only | Deliberately distinct lifecycle authority |
| Automation lifecycle | unavailable | Tk starts one worker-bound controller | `AutomatedSessionController` plus `AutomatedRunStore` | New orchestration owner only; no domain authority duplicated |
| Cancellation | reset/shutdown or proof job cancellation | per-automated-job cancel | `AsyncJobRunner` and owned `JobContext` | One process owner; per-job cancellation does not cancel unrelated work |

### Before/after conclusion

```text
same authored operation
-> same packet authority
-> same validator and deterministic merge
-> same timeout resolver
-> same proof launcher and process owner
-> same proof-image owner
-> same packet builder
-> one promotion seam delegating to the existing importer
-> distinct human and automation dispositions
```

No second validator, proof launcher, timeout policy, BMP decoder, PNG writer,
packet generator, or workspace importer was introduced. The automated route's
new responsibilities are limited to provider transport, bounded protocol
transitions, durable orchestration history, explicit current-packet rebinding,
and non-human promotion disposition.

The qualified Salticid Responsibility-Compression Scanner remains
`NOT_APPLICABLE`. This comparison is source- and runtime-grounded and does not
claim a scanner score.
