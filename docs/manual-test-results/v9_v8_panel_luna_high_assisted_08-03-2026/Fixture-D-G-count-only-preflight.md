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
