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

## Implementation closure

All five hardening items are implemented:

- Preview cache schema V2 records and verifies the generated derivative hash.
  Invalid, incomplete, or tampered cache pairs are removed and regenerated from
  the exact source frame.
- Pull requests and pushes to `main` run the supported Python 3.14 workflow on a
  GitHub-hosted Windows runner.
- Package metadata now declares Python `>=3.14,<3.15`.
- Historical slice documents identify their superseding acceptance evidence,
  and the active web-session guide describes current engine-owned Color
  Pipeline application.
- Agent Bundle CLI failures use structured JSON, while launch receipt V2 and
  the desktop UI distinguish launcher-process creation from unverified viewer
  health.

Validation:

- focused preview, bundle, proof, controller, and workflow tests: 23 passed;
- complete Python 3.14 suite: 73 passed;
- editable package installation: passed;
- Python source compilation: passed;
- `git diff --check`: passed;
- hosted Windows/Python 3.14 run `29891026768`: passed;
- engine repository and published runtime: unchanged.

Pull request #3 is the clean review boundary. No additional product mutation or
merge is authorized by this campaign.
