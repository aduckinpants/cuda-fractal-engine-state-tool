from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Optional

from .state_override import materialize_state_override


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate and deterministically merge one exact agent-packet state override"
    )
    parser.add_argument("--packet-dir", type=Path, required=True)
    parser.add_argument("--override", type=Path, required=True, help="Exact UTF-8 state override JSON")
    parser.add_argument("--out", type=Path, required=True, help="Merged candidate output path")
    parser.add_argument("--manifest-sha256")
    args = parser.parse_args(argv)

    try:
        override_text = args.override.read_bytes().decode("utf-8")
        result = materialize_state_override(
            args.packet_dir,
            override_text,
            args.out,
            expected_manifest_sha256=args.manifest_sha256,
        )
    except (OSError, UnicodeError, ValueError) as exc:
        print(
            json.dumps(
                {
                    "status": "override_rejected",
                    "error": str(exc),
                },
                indent=2,
                ensure_ascii=False,
            )
        )
        return 2
    print(
        json.dumps(
            {
                "status": "override_accepted",
                "output_path": str(result.output_path),
                "override_text_sha256": result.override_text_sha256,
                "base_state_sha256": result.base_state_sha256,
                "merged_candidate_sha256": result.merged_candidate_sha256,
                "empty_override_byte_exact": result.empty_override_byte_exact,
                "requested_paths": list(result.requested_paths),
                "changed_paths": [
                    {
                        "path": change.path,
                        "base_value": change.base_value,
                        "merged_value": change.merged_value,
                        "conceptual_domain": change.conceptual_domain,
                    }
                    for change in result.changed_paths
                ],
                "conceptual_domains": list(result.conceptual_domains),
                "camera_edits": list(result.camera_edits),
            },
            indent=2,
            ensure_ascii=False,
            allow_nan=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
