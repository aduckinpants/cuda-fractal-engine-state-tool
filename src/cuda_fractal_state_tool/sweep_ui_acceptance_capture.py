from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path
from typing import Callable, Optional

from PIL import ImageGrab

from .user_workflow_app import DEFAULT_FINDING_WORKSPACE, UserWorkflowApp, _enable_dpi_awareness


def _wait(root, predicate: Callable[[], bool], timeout_seconds: float, label: str) -> None:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        root.update()
        if predicate():
            return
        time.sleep(0.03)
    raise TimeoutError(f"Timed out waiting for {label}")


def _capture(window, path: Path) -> dict[str, object]:
    window.deiconify()
    window.lift()
    window.attributes("-topmost", True)
    window.update_idletasks()
    window.update()
    time.sleep(0.15)
    left = window.winfo_rootx()
    top = window.winfo_rooty()
    width = window.winfo_width()
    height = window.winfo_height()
    image = ImageGrab.grab(bbox=(left, top, left + width, top + height), all_screens=True)
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path)
    window.attributes("-topmost", False)
    payload = path.read_bytes()
    return {
        "path": str(path.resolve()),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "width": image.width,
        "height": image.height,
    }


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Capture the real local Scalar Bracket Sweep V1 Tk review states"
    )
    parser.add_argument("--packet-dir", type=Path, required=True)
    parser.add_argument("--workspace-root", type=Path, default=DEFAULT_FINDING_WORKSPACE)
    parser.add_argument(
        "--plan",
        type=Path,
        required=True,
        help="Exact packet-authorized Scalar Bracket Sweep V1 JSON plan",
    )
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    plan_text = args.plan.read_bytes().decode("utf-8")

    _enable_dpi_awareness()
    import tkinter as tk

    root = tk.Tk()
    app = UserWorkflowApp(root, workspace_root=args.workspace_root)
    app.open_packet_path(args.packet_dir)
    _wait(
        root,
        lambda: app.session.bundle is not None and not app._busy_kinds,
        90,
        "existing Packet V8 binding",
    )
    app.open_sweep_panel()
    app.sweep_plan_text.configure(state="normal")
    app.sweep_plan_text.delete("1.0", "end")
    app.sweep_plan_text.insert("1.0", plan_text)
    app.sweep_plan_text.edit_modified(True)
    app._sweep_plan_modified()
    app.validate_scalar_sweep()
    _wait(
        root,
        lambda: "sweep_validation" not in app._busy_kinds,
        90,
        "scalar sweep validation",
    )
    if app._sweep_validation_binding is None:
        raise AssertionError(app.session.status_text)
    validated = _capture(app.sweep_window, args.out / "01_sweep_validated.png")
    app.run_scalar_sweep()
    _wait(
        root,
        lambda: "scalar_sweep" not in app._busy_kinds,
        900,
        "local scalar sweep",
    )
    if app._sweep_result_dir is None:
        raise AssertionError(app.session.status_text)
    completed = _capture(app.sweep_window, args.out / "02_sweep_complete.png")
    receipt_path = app._sweep_result_dir / "receipt.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    manifest = {
        "packet_dir": str(args.packet_dir.resolve()),
        "packet_manifest_sha256": app.session.bundle.manifest_sha256,
        "fixed_override_editor_text_sha256": hashlib.sha256(
            app.session.override_text.encode("utf-8")
        ).hexdigest(),
        "plan_sha256": hashlib.sha256(plan_text.encode("utf-8")).hexdigest(),
        "sweep_dir": str(app._sweep_result_dir),
        "sweep_receipt_sha256": hashlib.sha256(receipt_path.read_bytes()).hexdigest(),
        "disposition": receipt.get("disposition"),
        "human_acceptance": receipt.get("presentation", {}).get("human_acceptance"),
        "screenshots": {"validated": validated, "complete": completed},
    }
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    app.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
