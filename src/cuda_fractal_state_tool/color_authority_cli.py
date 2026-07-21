from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Optional

from .color_authority import ColorAuthorityProofError, run_controlled_color_authority_proof
from .runtime_surface import DEFAULT_RUNTIME_CMD


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Prove bounded Color Pipeline authoring through engine authority")
    parser.add_argument("--runtime-cmd", type=Path, default=DEFAULT_RUNTIME_CMD)
    parser.add_argument("--base-state", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--timeout-seconds", type=float, default=90.0)
    args = parser.parse_args(argv)
    try:
        result = run_controlled_color_authority_proof(
            args.runtime_cmd,
            args.base_state,
            args.out,
            timeout_seconds=args.timeout_seconds,
        )
    except (ColorAuthorityProofError, ValueError) as exc:
        print(json.dumps({"status": "failed", "error": str(exc)}, indent=2, sort_keys=True))
        return 2
    print(
        json.dumps(
            {
                "status": result.status,
                "receipt_path": str(result.receipt_path),
                "controlled_base_state_path": str(result.controlled_base_state_path),
                "materialized_state_path": str(result.materialized_state_path),
                "replay_state_path": str(result.replay_state_path),
                "selected_lane_id": result.selected_lane_id,
                "selected_function_id": result.selected_function_id,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
