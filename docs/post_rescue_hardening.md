# Post-Rescue Hardening

## Authority and starting point

- Starting commit: `781cd0dc9375f8bfefb2c92fbd8af6384127c005`
- Branch: `codex/post-rescue-hardening`
- Runtime and CUDA-engine repositories remain read-only.
- Python validation interpreter: 3.14.

The Agent State Override rescue is complete. This campaign does not expand its
authoring surface or workflow. It closes five bounded post-merge weaknesses:

1. authenticate cached preview derivatives and regenerate invalid cache pairs;
2. run the local suite in Windows CI and declare the actually supported Python
   line;
3. label superseded slice conclusions so historical checkpoints cannot be read
   as current product state;
4. return structured errors from every Agent Bundle CLI operation;
5. describe launch evidence as successful launcher-process creation rather than
   unverified viewer health.

## Non-goals

- no engine or published-runtime mutation;
- no state-authoring expansion;
- no family switching, render/lens authoring, or pipeline-topology editing;
- no automated aesthetic or viewer-health judgment;
- no proof, packet, or historical-workspace migration;
- no remote-agent integration.

## Validation and closure

Each implementation slice receives focused tests first. Closure requires the
full Python 3.14 suite, compile checks, `git diff --check`, stale-wording and
architecture audits, hostile self-review, a clean pushed checkpoint, and a
ready pull request. Merge remains a separate user authorization boundary.
