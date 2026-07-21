from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Optional

from .lane_catalog import (
    FunctionUnknownError,
    LaneUnknownError,
    RuntimeMetadataUnavailableError,
    RuntimeMetadataShapeUnsupportedError,
    load_lane_catalog_from_ui_salt_contract,
    validate_lane_function_reference,
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
        description="Inspect the deployed compiled UI-Salt lane/function contract",
        epilog="Fail-closed: unsupported metadata shapes are rejected instead of inferred.",
    )
    parser.add_argument("--ui-salt-contract", type=Path, required=True, help="Path to compiled UI-Salt contract JSON")
    parser.add_argument("--check-lane", type=str, default=None, help="Optional lane id to validate against metadata catalog")
    parser.add_argument("--check-function", type=str, default=None, help="Optional function id to validate for --check-lane")
    args = parser.parse_args(argv)

    if (args.check_lane is None) != (args.check_function is None):
        print(
            json.dumps(
                {
                    "status": "invalid_arguments",
                    "error": "--check-lane and --check-function must be provided together",
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 2

    try:
        catalog = load_lane_catalog_from_ui_salt_contract(args.ui_salt_contract)
    except RuntimeMetadataUnavailableError as exc:
        print(json.dumps({"status": "runtime_metadata_unavailable", "error": str(exc)}, indent=2, sort_keys=True))
        return 2
    except RuntimeMetadataShapeUnsupportedError as exc:
        print(json.dumps({"status": "runtime_metadata_shape_unsupported", "error": str(exc)}, indent=2, sort_keys=True))
        return 2

    entries = [{"lane_id": item.lane_id, "function_id": item.function_id} for item in catalog.entries]

    if args.check_lane is not None and args.check_function is not None:
        try:
            validate_lane_function_reference(catalog, args.check_lane, args.check_function)
        except LaneUnknownError as exc:
            print(json.dumps({"status": "lane_unknown", "error": str(exc)}, indent=2, sort_keys=True))
            return 2
        except FunctionUnknownError as exc:
            print(json.dumps({"status": "function_unknown", "error": str(exc)}, indent=2, sort_keys=True))
            return 2

    payload = {
        "status": "ok",
        "shape": catalog.shape,
        "entry_count": len(entries),
        "lane_count": len({item["lane_id"] for item in entries}),
        "lanes": _collect_lanes(entries),
        "entries": entries,
        "validated_lane": args.check_lane,
        "validated_function": args.check_function,
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
