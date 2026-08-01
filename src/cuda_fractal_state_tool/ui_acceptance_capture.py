from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path
from typing import Callable, Optional

from PIL import ImageGrab

from .user_workflow import SessionState
from .user_workflow_app import DEFAULT_FINDING_WORKSPACE, UserWorkflowApp, _enable_dpi_awareness


DEFAULT_REVIEW_OVERRIDE = '{\n  "params": {\n    "explaino_damping": 0.9\n  }\n}\n'


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
    parser = argparse.ArgumentParser(description="Capture the Agent State Override manual-review states")
    parser.add_argument("--capture-source", type=Path, required=True)
    parser.add_argument("--workspace-root", type=Path, default=DEFAULT_FINDING_WORKSPACE)
    parser.add_argument("--override", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    override_text = (
        args.override.read_bytes().decode("utf-8") if args.override is not None else DEFAULT_REVIEW_OVERRIDE
    )
    _enable_dpi_awareness()
    import tkinter as tk

    root = tk.Tk()
    app = UserWorkflowApp(root, workspace_root=args.workspace_root)
    root.update()
    artifacts: dict[str, object] = {"empty": _capture(root, args.out / "01_empty.png")}
    app.open_finding_path(args.capture_source, args.workspace_root)
    _wait(
        root,
        lambda: (
            app.session.finding is not None
            and app.session.bundle is not None
            and "base_preview" not in app._busy_kinds
            and "bundle" not in app._busy_kinds
        ),
        90,
        "finding, base preview, and exact Agent Bundle V7",
    )
    if app.session.override_text != "":
        raise AssertionError("Incoming State Override editor did not start empty")
    artifacts["bundle_ready_empty_override"] = _capture(
        root, args.out / "02_bundle_ready_empty_override.png"
    )
    app.set_override_text(override_text)
    root.update()
    artifacts["override_dirty"] = _capture(root, args.out / "03_override_dirty.png")
    app.prove_override()
    _wait(
        root,
        lambda: (
            "proof" not in app._busy_kinds
            and "candidate_preview" not in app._busy_kinds
            and app.session.state in {SessionState.VISUAL_REVIEW_PENDING, SessionState.REJECTED}
        ),
        180,
        "engine proof and candidate preview",
    )
    if app.session.state != SessionState.VISUAL_REVIEW_PENDING:
        raise AssertionError(f"State override did not reach visual review: {app.session.status_text}")
    artifacts["visual_review_pending"] = _capture(root, args.out / "04_visual_review_pending.png")

    finding = app.session.finding
    bundle = app.session.bundle
    proof = app.session.proof_result
    assert finding is not None and bundle is not None and proof is not None
    manifest = {
        "capture_source": str(args.capture_source.resolve()),
        "workspace_root": str(args.workspace_root.resolve()),
        "launch_command": ".\\run_ui.cmd",
        "finding_id": finding.finding_id,
        "authoring_base_sha256": finding.authoring_base_sha256,
        "packet_id": bundle.packet_id,
        "packet_manifest_sha256": bundle.manifest_sha256,
        "packet_path": str(bundle.packet_path),
        "override_text_sha256": hashlib.sha256(override_text.encode("utf-8")).hexdigest(),
        "proof_id": proof.proof_id,
        "receipt_path": str(proof.receipt_path),
        "engine_candidate_sha256": proof.engine_candidate_sha256,
        "candidate_frame_sha256": proof.candidate_frame_sha256,
        "empty_override_byte_exact": proof.empty_override_byte_exact,
        "visual_review": "pending",
        "launch_ready": False,
        "states": artifacts,
    }
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    app.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
