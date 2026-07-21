from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Optional

from .finding_workspace import SourceCaptureImporter


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Manage mirrored findings workspace imports and index rebuild",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    import_parser = subparsers.add_parser("import", help="Import a capture bundle into the mirrored findings workspace")
    import_parser.add_argument("--workspace-root", type=Path, required=True, help="Durable findings workspace root")
    import_parser.add_argument("--source", type=Path, required=True, help="Capture folder or artifact path")

    rebuild_parser = subparsers.add_parser("rebuild-index", help="Rebuild findings_index.json by scanning per-finding manifests")
    rebuild_parser.add_argument("--workspace-root", type=Path, required=True, help="Durable findings workspace root")

    args = parser.parse_args(argv)
    importer = SourceCaptureImporter(args.workspace_root)

    if args.command == "import":
        result = importer.import_capture(args.source)
        payload = {
            "command": "import",
            "workspace_root": str(args.workspace_root.resolve()),
            "source": str(args.source.resolve()),
            "finding_id": result.finding_id,
            "finding_dir": str(result.finding_dir.resolve()),
            "workspace_manifest_path": str(result.workspace_manifest_path.resolve()),
            "findings_index_path": str(result.findings_index_path.resolve()),
            "workspace_index_updated": result.workspace_index_updated,
            "authoring_base_state_sha256": result.authoring_base_state_sha256,
        }
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0

    if args.command == "rebuild-index":
        index_path = importer.rebuild_findings_index()
        payload = {
            "command": "rebuild-index",
            "workspace_root": str(args.workspace_root.resolve()),
            "findings_index_path": str(index_path.resolve()),
        }
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0

    raise ValueError(f"Unknown command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
