from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Optional

from .runtime_surface import DEFAULT_RUNTIME_CMD
from .state_override_proof import run_state_override_proof_sync


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Prove one Packet V6 state override through engine materialization and action-free replay"
    )
    parser.add_argument("--packet-dir", type=Path, required=True)
    parser.add_argument("--override", type=Path, required=True, help="Exact UTF-8 state override JSON")
    parser.add_argument("--runtime-cmd", type=Path, default=DEFAULT_RUNTIME_CMD)
    parser.add_argument("--proofs-root", type=Path)
    parser.add_argument("--manifest-sha256")
    parser.add_argument("--timeout-seconds", type=float, default=90.0)
    args = parser.parse_args(argv)
    try:
        override_text = args.override.read_bytes().decode("utf-8")
        result = run_state_override_proof_sync(
            args.packet_dir,
            override_text,
            args.runtime_cmd,
            proofs_root=args.proofs_root,
            expected_manifest_sha256=args.manifest_sha256,
            timeout_seconds=args.timeout_seconds,
        )
    except (OSError, UnicodeError, ValueError, TimeoutError) as exc:
        print(json.dumps({"status": "proof_error", "error": str(exc)}, indent=2, ensure_ascii=False))
        return 2
    print(
        json.dumps(
            {
                "status": result.status,
                "message": result.message,
                "proof_id": result.proof_id,
                "proof_dir": str(result.proof_dir),
                "receipt_path": str(result.receipt_path),
                "engine_candidate_path": str(result.engine_candidate_path) if result.engine_candidate_path else None,
                "candidate_frame_path": str(result.candidate_frame_path) if result.candidate_frame_path else None,
                "visual_review": "pending" if result.status == "replay_proven" else "not_available",
                "launch_ready": False,
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0 if result.status == "replay_proven" else 2


if __name__ == "__main__":
    raise SystemExit(main())
