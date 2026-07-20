from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Optional

from .lane_catalog import (
    RuntimeMetadataUnavailableError,
    RuntimeMetadataShapeUnsupportedError,
    load_lane_catalog_from_describe_functions,
)


def _collect_lanes(entries: list[dict[str, str]]) -> dict[str, list[str]]:
    lanes: dict[str, list[str]] = {}
    for entry in entries:
        lane_id = entry["lane_id"]
        function_id = entry["function_id"]
        lanes.setdefault(lane_id, []).append(function_id)
    for lane_id in list(lanes.keys()):
        lanes[lane_id] = sorted(set(lanes[lane_id]))
    return dict(sorted(lanes.items()))


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Inspect runtime-derived lane/function catalog from describe-functions JSON",
        epilog="Fail-closed: unsupported metadata shapes are rejected instead of inferred.",
    )
    parser.add_argument("--describe-functions", type=Path, required=True, help="Path to describe-functions.json")
    args = parser.parse_args(argv)

    try:
        catalog = load_lane_catalog_from_describe_functions(args.describe_functions)
    except RuntimeMetadataUnavailableError as exc:
        print(json.dumps({"status": "runtime_metadata_unavailable", "error": str(exc)}, indent=2, sort_keys=True))
        return 2
    except RuntimeMetadataShapeUnsupportedError as exc:
        print(json.dumps({"status": "runtime_metadata_shape_unsupported", "error": str(exc)}, indent=2, sort_keys=True))
        return 2

    entries = [{"lane_id": item.lane_id, "function_id": item.function_id} for item in catalog.entries]
    payload = {
        "status": "ok",
        "shape": catalog.shape,
        "entry_count": len(entries),
        "lane_count": len({item["lane_id"] for item in entries}),
        "lanes": _collect_lanes(entries),
        "entries": entries,
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
