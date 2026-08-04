# Fixtures D–G — Exact Count-Only Preflight

Date: 2026-08-03

All four exact qualification cases were reopened against their immutable Packet
V8 authority before any paid dispatch. Production transport constructed and
provider-counted each author request, dispatched no response generation, and
cleaned every run-owned provider file.

| Fixture | Input tokens | Author maximum | Cell ceiling | Count-only run |
| --- | ---: | ---: | ---: | --- |
| D | 172,180 | $0.0440360 | $0.0888360 | `v9-v8-d-luna-high-exact-count-b4e633d2-604c-4199-a124-861d24280f93` |
| E | 167,680 | $0.0431360 | $0.0879360 | `v9-v8-e-luna-high-exact-count-a818d7f4-9acb-42d1-95e9-bdf75a966d60` |
| F | 169,597 | $0.0435194 | $0.0883194 | `v9-v8-f-luna-high-exact-count-67361444-ce0e-45de-bd7b-1d8e02bc4082` |
| G | 170,114 | $0.0436228 | $0.0884228 | `v9-v8-g-luna-high-exact-count-6403e893-e822-4283-bad1-b9f238e1402d` |

Each author request remained below the tracked 200,000-token per-response gate
and the 272,000-token long-context threshold. No cache discount was assumed.
Provider billing remains authoritative.

Fixture D and E were subsequently paid and passed. Fixture F was paid and
stopped at engine proof. Fixture G remains count-only because the approved panel
policy stops paid dispatch on a real defect.

## Post-engine-publication Fixture G refresh

After the Fixture F engine repair was merged and published, Fixture G's assisted
analysis identity changed with the executable authority. The G case was refreshed
to exact case SHA-256
`ba6a9bd1ca3c9c04cf0da5a2e48475831d9909cb81c6d602d3c5d56353b14e93`
and reopened against the same immutable Packet V8.

Production count-only transport again constructed and provider-counted the exact
author request without response generation:

| Fixture | Input tokens | Author maximum | Cell ceiling | Count-only run |
| --- | ---: | ---: | ---: | --- |
| G refreshed | 170,119 | $0.0436238 | $0.0884228 | `v9-v8-g-luna-high-post-engine-count-20923c75-4050-4fb0-a956-dd64086afaef` |

The count-only receipt SHA-256 is
`c9fe4ded58a9fbcc86171082eabd832faed16863fce5590f2cb8ffacbf8baf48`.
The request remains below the 200,000-token case gate and the 272,000-token
long-context threshold. No second paid G dispatch is authorized by this receipt.
