# Phase 3 User Workflow Status - 2026-07-20

## Scope Of This Status Record

This document captures the exact repository state at the end of the current implementation pass, including:

1. What is implemented on disk right now.
2. What verification was run and passed.
3. The active UX gaps and the explicit user frustration context from this session.
4. What remains unresolved despite passing tests.

## Verified On-Disk Change Set

### Modified files

- `src/cuda_fractal_state_tool/__init__.py`
- `src/cuda_fractal_state_tool/app.py`
- `tests/test_app_controller.py`

### Added files

- `src/cuda_fractal_state_tool/finding_workspace_cli.py`
- `src/cuda_fractal_state_tool/finding_workflow_cli.py`
- `tests/test_finding_workspace_cli.py`
- `tests/test_finding_workflow_cli.py`

## Current Implemented Behavior

### Mirrored finding workspace + identity workflow (implemented)

- Import of findings into durable workspace root via `SourceCaptureImporter` is implemented.
- Deterministic finding identity, proposal identity, and run identity helpers are present.
- Per-finding `workspace.json` authoritative manifest model is present.
- Rebuildable root index path (`findings_index.json`) support is present.
- Atomic write patterns for workspace/index persistence are present.

### CLI surface (implemented)

- `finding_workspace_cli`:
  - `import` command
  - `rebuild-index` command
- `finding_workflow_cli`:
  - proposal replay/proof execution for imported finding flows

### UI surface (implemented, but still contentious)

- `User Workflow` and `Debug Surface` are separated by tabs.
- User tab includes step-state indicators and the following actions:
  - `Open Finding`
  - `Copy Intake Packet`
  - `Validate & Prove`
  - `Copy Repair Packet`
  - `Open Viewer`
  - `Reset Session`
  - `Open Working Folder`
  - `Open Finding Folder`
- Intake packet for imported-finding flow was upgraded from a minimal placeholder to a bound, actionable contract packet with:
  - strict base-state binding (`finding_id`, `sha256`)
  - proposal envelope template
  - bounded allowed override list
  - hard constraints

## Verification Evidence

### Full automated suite

Command:

```powershell
py -3.14 -m unittest
```

Result:

- `Ran 108 tests`
- `OK`

No failing tests at this checkpoint.

## Explicit Frustration Context (As Reported In Session)

The user repeatedly reported that the delivered UI did not match the previously provided, detailed workflow specification.

### Frustration signals that were explicitly raised

- "I still have no idea what I am looking at."
- "It does not match the outline."
- "There are multiple places asking for one thing."
- "The intake packet looked like a joke."
- "Usability is still a disaster for what should be simple."
- "I described the UI and workflow in detail already; this does not match it at all."

### Interpretation of the core problem

The implementation repeatedly drifted into tool/infrastructure-oriented framing instead of faithfully mirroring the requested user-first flow and language. Even when controls were simplified, the interaction model still felt inconsistent with the requested concrete outline.

## Current Truth

1. The code is functionally stable under tests.
2. The imported-finding workflow infrastructure is in place.
3. The UI has been iterated significantly but has not yet achieved trusted alignment with the user's exact intended interaction shape.
4. The highest risk is no longer runtime correctness; it is UX contract mismatch and confidence erosion.

## Immediate Constraint At This Checkpoint

This document is a closure snapshot of current status and user frustration context only. It does not claim UX acceptance. It claims implementation state + test verification + unresolved usability alignment risk.
