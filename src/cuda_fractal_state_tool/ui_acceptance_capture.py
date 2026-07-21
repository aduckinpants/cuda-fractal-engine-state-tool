from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path
from typing import Callable, Optional

from PIL import ImageGrab

from .user_workflow_app import DEFAULT_FINDING_WORKSPACE, UserWorkflowApp, _enable_dpi_awareness


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(64 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _wait(root, predicate: Callable[[], bool], timeout_seconds: float, label: str) -> None:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        root.update()
        if predicate():
            return
        time.sleep(0.03)
    raise TimeoutError(f"Timed out waiting for {label}")


def _capture(root, output_path: Path) -> dict[str, object]:
    root.lift()
    root.attributes("-topmost", True)
    root.update_idletasks()
    root.update()
    time.sleep(0.15)
    left = root.winfo_rootx()
    top = root.winfo_rooty()
    width = root.winfo_width()
    height = root.winfo_height()
    image = ImageGrab.grab(bbox=(left, top, left + width, top + height), all_screens=True)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path)
    root.attributes("-topmost", False)
    return {
        "path": str(output_path.resolve()),
        "sha256": _sha256(output_path),
        "width": image.width,
        "height": image.height,
    }


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Capture the three Slice 2 interaction-review states")
    parser.add_argument("--capture-source", type=Path, required=True)
    parser.add_argument("--workspace-root", type=Path, default=DEFAULT_FINDING_WORKSPACE)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    _enable_dpi_awareness()
    import tkinter as tk

    root = tk.Tk()
    app = UserWorkflowApp(root, workspace_root=args.workspace_root)
    root.update()
    artifacts: dict[str, object] = {
        "empty": _capture(root, args.out / "01_empty.png"),
    }
    app.open_finding_path(args.capture_source, args.workspace_root)
    _wait(
        root,
        lambda: (
            app.session.finding is not None
            and app.session.packet is not None
            and "preview" not in app._busy_kinds
            and "packet" not in app._busy_kinds
        ),
        45,
        "real finding import, preview, and automatic exploration packet",
    )
    artifacts["packet_ready"] = _capture(root, args.out / "02_packet_ready.png")
    finding = app.session.finding
    assert finding is not None
    app.set_proposal_text(
        json.dumps(
            {
                "proposal_version": 1,
                "base_state": {
                    "finding_id": finding.finding_id,
                    "sha256": finding.authoring_base_sha256,
                },
                "overrides": {
                    "color_pipeline_draft": {
                        "lanes": [{"lane_id": "shape", "function_id": "repeat"}]
                    }
                },
            },
            indent=2,
        )
    )
    root.update()
    artifacts["proposal_dirty"] = _capture(root, args.out / "03_proposal_dirty.png")
    manifest = {
        "capture_source": str(args.capture_source.resolve()),
        "workspace_root": str(args.workspace_root.resolve()),
        "launch_command": ".\\run_ui.cmd",
        "states": artifacts,
        "packet_id": app.session.packet.packet_id if app.session.packet else None,
        "packet_sha256": app.session.packet.packet_sha256 if app.session.packet else None,
        "finding_id": finding.finding_id,
        "authoring_base_sha256": finding.authoring_base_sha256,
    }
    (args.out / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    app.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
