from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Optional

from .finding_enrichment import FindingEnrichmentService


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Derive immutable finding-enrichment evidence from one exact Packet V8 bundle"
    )
    parser.add_argument("--workspace-root", type=Path, required=True)
    parser.add_argument("--packet-dir", type=Path, required=True)
    parser.add_argument("--runtime-executable", type=Path)
    parser.add_argument("--runtime-compatibility", choices=("development", "strict"))
    parser.add_argument("--runtime-timeout-seconds", type=float, default=30.0)
    args = parser.parse_args(argv)
    try:
        result = FindingEnrichmentService(workspace_root=args.workspace_root).analyze(
            args.packet_dir,
            runtime_executable=args.runtime_executable,
            runtime_compatibility_mode=args.runtime_compatibility,
            runtime_timeout_seconds=args.runtime_timeout_seconds,
        )
        print(
            json.dumps(
                {
                    "status": "complete",
                    "analysis_id": result.analysis_id,
                    "analysis_dir": str(result.analysis_dir),
                    "cache_hit": result.cache_hit,
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0
    except (OSError, UnicodeError, ValueError, RuntimeError) as exc:
        print(
            json.dumps(
                {
                    "status": "enrichment_error",
                    "error": str(exc),
                },
                indent=2,
                ensure_ascii=False,
            )
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
