# Descriptive Catalog And Packet Calibration Acceptance

## Current boundary

Left-side descriptive-catalog integration and packet-calibration implementation
is acceptance-ready. Manual downstream acceptance is pending the user's four
temporary sessions. Returned-proposal operational behavior was not advanced by
this campaign.

## Engine handoff

- merged engine commit: `b8c19dfa94c7eef136dc4e5eee6a1df67d57daba`;
- published runtime executable SHA-256:
  `133555472c40bb837dd6112da108c337d62219d173575eeaa446e52dabc8946e`;
- descriptive-catalog SHA-256:
  `21184b8af87d3fe2cc7e652cba5a125b54876a265ae2fe99595dc7f4a46262c0`;
- repeated stdout/file exports: 28,487 bytes and byte-identical;
- published-runtime tests: 4/4 passed;
- strict catalog smoke: 43/43 passed;
- engine rearward review: green for the merge commit.

The engine export contains 51 live-selector rows. `explaino_all` and
`explaino_magnet_root_well` are reviewed; the remaining 49 rows explicitly
report `description_status: unavailable` with a null description.

## Packet V5 contract

Packet V5 queries the configured published runtime, validates the complete
catalog and unique selector identities, chooses exactly `state.json.fractal_type`,
and caches the exact bytes at:

```text
<workspace>/cache/fractal-descriptive-catalog-v1/
  <runtime-identity-sha256>/<catalog-sha256>/catalog.json
```

The manifest records the catalog hash, selected selector, and selected
description status. A valid unavailable description produces a clear notice and
continues. Malformed authority, duplicate selectors, or missing selected
identity fail closed. There is no historical side-folder fallback.

The packet contains one front-loaded `Selected fractal — engine-owned
mathematical background` section and preserves this evidence order:

1. attached frame;
2. selected engine-owned description;
3. engine-generated applicable-parameter projection;
4. exact `fractal-state.json` review sidecar;
5. exact `state.json` replay authority;
6. proven comparisons.

Its high-priority contract explicitly blocks six observed overinterpretations:
continuous-signal basin language, visible-symmetry claims from serialized root
geometry, visible-cause claims from nonzero controls, broadened help text,
spatialized global iteration statistics, and exact self-similarity claims from
one frame.

Captured color values are distinguished from allowed replacements. The packet
also states the scalar tuple rail, scalar Shape rail, row-zero draft rail, and
the one-authoring-rail-per-conceptual-lane rule. The proposal envelope and
validator were not changed.

## Stable fixture packets

Acceptance root:

```text
C:\code\cuda-fractal-engine-state-tool\.local\manual_downstream_acceptance
```

### Fixture A — categorical

- selector: `explaino_all` (`reviewed`);
- pipeline: `root_index → identity → joy → basin_default`;
- packet ID: `75feceaa-2b1b-4407-a8dd-be1abc425733`;
- packet SHA-256:
  `9783d7d69616724a99660b7ca0c3e102ec84a8bdfc5c3594986d24bb23450f49`;
- packet: `.local/manual_downstream_acceptance/fixture-a-explaino-all/packet.txt`;
- frame: `.local/manual_downstream_acceptance/fixture-a-explaino-all/frame.png`.

### Fixture B — continuous

- selector: `explaino_magnet_root_well` (`reviewed`);
- pipeline: `root_proximity → log_compress → cyclic_escape → glow_default`;
- packet ID: `783d0cac-448b-4e92-bd96-1586844e1320`;
- packet SHA-256:
  `f151ec383025d6c6526cce4cdc1226963fe01bbe2824a38c1f6ac59590242aa1`;
- packet:
  `.local/manual_downstream_acceptance/fixture-b-explaino-magnet-root-well/packet.txt`;
- frame:
  `.local/manual_downstream_acceptance/fixture-b-explaino-magnet-root-well/frame.png`.

Both manifests bind runtime identity
`0ef0e1d44df011d7eac0d67531c33c0d15ee8f60e7656f5c1e44c5bf3ca77bdd`
and the same exact catalog hash.

## Exact prompts

Opening:

```text
What do you notice here? What seems mathematically interesting or worth exploring?
```

Follow-up:

```text
What would you try?
```

## Manual result ledger

| Fixture | Session class | Result | Transcript/review |
|---|---|---|---|
| A | strong temporary web agent | pending user execution | pending |
| A | basic Windows Copilot | pending user execution | pending |
| B | strong temporary web agent | pending user execution | pending |
| B | basic Windows Copilot | pending user execution | pending |

For every row, require exploration-first behavior, no proposal after either
prompt, correct evidence hierarchy, and no violation of the six interpretation
rules. The execution agent must not simulate or self-grade these sessions.
