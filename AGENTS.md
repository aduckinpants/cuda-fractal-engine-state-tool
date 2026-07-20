# CUDA Fractal State Tool Agent Rules

This repository exists to prove a narrow workflow:

engine-observed baseline
+ constrained proposal
-> transport candidate
-> authoritative runtime replay
-> evidence

Rules:

1. Authoritative engine behavior wins over duplicated assumptions.
2. Inspect the runtime and source before changing code.
3. No implicit fallback. Unknown inputs and unsupported paths must fail clearly.
4. Do not invent contracts the runtime has not proven.
5. Work in small coherent slices with focused tests first.
6. Run focused tests, then the full local test suite, then exercise the affected workflow.
7. Preserve raw machine outputs under `.local/`; preserve stable conclusions in tracked docs.
8. If a needed runtime fact cannot be established without patching the engine, record the limitation and stop or continue according to whether it blocks the current slice.
9. Perform hostile self-review before closing a slice.
10. Completion reports must make a firm closure determination. Report what changed, what proof ran, what remains, whether remaining work is already covered by the approved or checked-in plan, whether planned sliced work remains or is exhausted, the repository and checkpoint state, and the single next approved execution boundary when one exists. Do not end with optional menus, speculative enhancements, or offers to begin work that is already part of the approved plan. When the approved plan is exhausted, say so explicitly and stop for replanning before further product mutation.
