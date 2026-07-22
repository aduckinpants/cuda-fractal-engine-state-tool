from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Optional

from .agent_bundle import build_agent_bundle, load_agent_bundle_handoff, open_agent_bundle_folder
from .finding_workspace import SourceCaptureImporter
from .runtime_surface import DEFAULT_RUNTIME_CMD


def _bundle_summary(bundle) -> dict[str, object]:
    return {
        "packet_version": 6,
        "packet_id": bundle.packet_id,
        "finding_id": bundle.finding_id,
        "selected_fractal_type": bundle.selected_fractal_type,
        "packet_dir": str(bundle.packet_dir),
        "packet_path": str(bundle.packet_path),
        "packet_sha256": bundle.packet_sha256,
        "manifest_path": str(bundle.manifest_path),
        "manifest_sha256": bundle.manifest_sha256,
        "required_attachments": list(bundle.required_attachments),
        "recommended_attachments": list(bundle.recommended_attachments),
        "unavailable_optional_attachments": list(bundle.unavailable_optional_attachments),
    }


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Build and inspect exact Agent Bundle V6 directories")
    subparsers = parser.add_subparsers(dest="command", required=True)

    build_parser = subparsers.add_parser("build", help="Import a finding and construct a coherent Packet V6 bundle")
    build_parser.add_argument("--workspace-root", type=Path, required=True)
    build_parser.add_argument("--source", type=Path, required=True)
    build_parser.add_argument("--runtime-cmd", type=Path, default=DEFAULT_RUNTIME_CMD)
    build_parser.add_argument("--timeout-seconds", type=float, default=30.0)

    inspect_parser = subparsers.add_parser("inspect", help="Verify a published Packet V6 and print its handoff lists")
    inspect_parser.add_argument("--packet-dir", type=Path, required=True)

    open_parser = subparsers.add_parser("open-folder", help="Verify and open a Packet V6 directory in Explorer")
    open_parser.add_argument("--packet-dir", type=Path, required=True)

    args = parser.parse_args(argv)
    if args.command == "build":
        imported = SourceCaptureImporter(args.workspace_root).import_capture(args.source)
        bundle = build_agent_bundle(
            imported.finding_dir,
            args.runtime_cmd,
            timeout_seconds=args.timeout_seconds,
        )
        print(json.dumps(_bundle_summary(bundle), indent=2, sort_keys=True))
        return 0
    if args.command == "inspect":
        handoff = load_agent_bundle_handoff(args.packet_dir)
        print(
            json.dumps(
                {
                    "packet_dir": str(handoff.packet_dir),
                    "packet_sha256": handoff.packet_sha256,
                    "required_attachments": list(handoff.required_attachments),
                    "recommended_attachments": list(handoff.recommended_attachments),
                    "unavailable_optional_attachments": list(handoff.unavailable_optional_attachments),
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0
    if args.command == "open-folder":
        handoff = open_agent_bundle_folder(args.packet_dir)
        print(json.dumps({"opened_packet_dir": str(handoff.packet_dir)}, indent=2))
        return 0
    raise ValueError(f"Unknown command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
