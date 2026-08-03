# V9-on-V8 Fixtures B and C — Luna High Count-Only Receipts

Date: 2026-08-03

Both exact author requests were submitted to the provider input-token count endpoint without response generation. Both used `gpt-5.6-luna`, high reasoning, assisted disclosure, and explicit no-cache transport.

## Fixture B

```text
packet: bb430c93-1747-490d-92a0-59f998fe451c
analysis: 3e0ce82af48deb2d114680323ec1caa8145115bebf604114a9b408f403812a42
case SHA-256: 8744a3cc7c7308e8bb5a9078803ca9827f78aaee9f150cb1a0c18d1996487379
input tokens: 176946
author maximum: $0.0449892
review maximum: $0.0448000
exact cell ceiling: $0.0897892
```

Durable count-only run:

```text
D:\salt-fractal\cuda-fractal-engine-state-tool\automated-runs\v9-v8-b-luna-high-exact-count-9a972b84-0c1f-4d3e-990e-f5869cc34b47
```

Count receipt SHA-256: `393ce1fbf685c35dffe0a690addee35a3ac4ce712563c5f29d3a578cebdf442e`.

## Fixture C

```text
packet: 06dc4aef-7a5e-4c62-9eab-76b7ddcb6eed
analysis: 00c6500153501d13d958214548df23d4a6858cb9c0d7bee90f6b06b9d3c21779
case SHA-256: f0da6ce081b145419f2f0000fa5e9408656ae41a3602bebb6285c4977756db96
input tokens: 173866
author maximum: $0.0443732
review maximum: $0.0448000
exact cell ceiling: $0.0891732
```

Durable count-only run:

```text
D:\salt-fractal\cuda-fractal-engine-state-tool\automated-runs\v9-v8-c-luna-high-exact-count-5ef63630-3a0b-4904-a91f-ae6ac9b94365
```

Count receipt SHA-256: `3cd71ec0a4c63f85b05879022897cd6ee92b3b6ae62da7b32368b4633f871995`.

Both requests remained below the 200,000-token short-context gate. Provider cleanup completed with no remaining run-owned file IDs. Provider billing remains authoritative.
