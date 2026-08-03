# Finding Enrichment Slice 6 — Local Scalar Sweep Manual Gate

## Acceptance-ready state

The thin local-sweep UI is implemented over the same Packet V8 parser,
authoring surface, override materializer, timeout resolver, proof launcher, and
proof-image owner used by the ordinary override route. It adds no provider call
and records no human acceptance automatically.

The accepted UI hierarchy remains intact. **Local Scalar Sweep...** opens a
separate bounded window containing:

- an editable Scalar Bracket Sweep V1 plan;
- exact packet/fixed-override binding and validation;
- per-member progress through the shared async runner;
- cancellation that preserves completed evidence;
- an aggregate contact-sheet preview explicitly labelled as non-acceptance;
- direct access to the immutable sweep folder and full contact sheet.

## Launch and fixture

From `C:\code\cuda-fractal-engine-state-tool`:

```powershell
.\run_ui.cmd
```

Load this existing Packet V8 folder directly:

```text
D:\salt-fractal\cuda-fractal-engine-state-tool\findings\
68eae29408ef2c533d7cf27c452bf7e5f93e51d9b611c2e4a6d7636c31a11963\packets\
72980336-bc21-44b0-bb00-754182718ef5
```

Open **Local Scalar Sweep...**. The default plan is the locked five-member
vortex bracket:

```json
{
  "sweep_version": 1,
  "axis": {
    "path": "params.vortex_strength",
    "values": [0, 0.25, 0.5, 0.75, 1]
  },
  "member_failure_policy": "continue_independent"
}
```

The existing override editor is the optional fixed sparse override. It must not
also contain `params.vortex_strength`.

## Preserved real UI proof

The actual Tk route produced this immutable sweep:

```text
D:\salt-fractal\cuda-fractal-engine-state-tool\findings\
68eae29408ef2c533d7cf27c452bf7e5f93e51d9b611c2e4a6d7636c31a11963\sweeps\
b74ae953-47c8-4458-9bb4-4029d098fa13
```

Evidence identities:

```text
aggregate receipt SHA-256
2c0f93264574115aea0246bff00be22a686c9de5874efec6353fc4e73382766c

contact-sheet PNG SHA-256
de58f32f2d0d8d257db02690977999ec89ac16b6c02d44bd9696858918e3c3b4

presentation receipt SHA-256
5112a4854ed1ce6e6e590f0a915461ef5e6821924b4f17f2e1203eda37d9fcaf
```

All five members are independently `REPLAY_PROVEN`. The contact sheet is
byte-identical to the one derived from the preceding headless sweep, despite
distinct proof IDs. This demonstrates deterministic presentation of the same
five proof-owned images; it does not establish mathematical causality or human
acceptance.

Principal UI screenshots are preserved locally at:

```text
C:\code\cuda-fractal-engine-state-tool\.local\slice6-sweep-ui\
01_sweep_validated.png
02_sweep_complete.png
```

## User review checklist

1. Load the packet and open the local sweep without changing the accepted main
   two-column hierarchy.
2. Confirm validation is required before **Run Local Sweep** is enabled.
3. Confirm plan or fixed-override edits invalidate the validation binding.
4. Run the bracket and confirm member progress remains readable during the
   approximately five-minute local proof sequence.
5. Confirm the full contact sheet shows the five ordered axis values and no
   result is labelled accepted.
6. Confirm **Open Sweep Folder** and **Open Contact Sheet** expose the durable
   evidence.
7. Optionally cancel a separate run and verify no new member starts after the
   owned in-flight proof resolves or is terminated, while earlier evidence is
   retained.

## Closure boundary

This gate is the only remaining approved action. No paid model call is needed.
All preplanned implementation slices are exhausted. Record the user's manual
review disposition before authorizing further product mutation or merge.
