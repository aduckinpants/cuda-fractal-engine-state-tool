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
