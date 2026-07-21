from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path
from typing import Callable, Optional

from PIL import ImageGrab

from .user_proof import ProofResult, validate_launch_readiness
from .user_workflow import SessionState
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


def _proposal(finding_id: str, base_sha256: str, function_id: str) -> str:
    return json.dumps(
        {
            "proposal_version": 1,
            "base_state": {"finding_id": finding_id, "sha256": base_sha256},
            "overrides": {
                "color_pipeline_draft": {
                    "lanes": [{"lane_id": "shape", "function_id": function_id}]
                }
            },
        },
        indent=2,
    )


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Capture the complete morning operational workflow")
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
        60,
        "finding, preview, and automatic packet",
    )
    if app.session.proposal_text != "":
        raise AssertionError("Incoming proposal editor did not start empty")
    artifacts["packet_ready_empty_proposal"] = _capture(root, args.out / "02_packet_ready_empty_proposal.png")

    finding = app.session.finding
    packet = app.session.packet
    assert finding is not None and packet is not None
    accepted_text = _proposal(finding.finding_id, finding.authoring_base_sha256, "repeat")
    app.set_proposal_text(accepted_text)
    artifacts["proposal_dirty"] = _capture(root, args.out / "03_proposal_dirty.png")
    app.prove_proposal()
    _wait(
        root,
        lambda: "proof" not in app._busy_kinds and app.session.state in {SessionState.PROVEN, SessionState.REJECTED},
        180,
        "accepted proposal proof",
    )
    if app.session.state != SessionState.PROVEN or not isinstance(app.session.proof_result, ProofResult):
        raise AssertionError(f"Accepted proposal did not prove: {app.session.status_text}")
    accepted_result = app.session.proof_result
    readiness_errors = validate_launch_readiness(accepted_result, packet, accepted_text, app.runtime_cmd_path)
    if readiness_errors:
        raise AssertionError(f"Proven candidate was not launch-ready: {readiness_errors}")
    artifacts["proven_launch_ready"] = _capture(root, args.out / "04_proven_launch_ready.png")

    rejected_text = _proposal(finding.finding_id, finding.authoring_base_sha256, "definitely_missing")
    app.set_proposal_text(rejected_text)
    app.prove_proposal()
    _wait(
        root,
        lambda: "proof" not in app._busy_kinds and app.session.state == SessionState.REJECTED,
        60,
        "rejected proposal and repair packet",
    )
    rejected_result = app.session.proof_result
    if not isinstance(rejected_result, ProofResult) or not rejected_result.repair_packet_text:
        raise AssertionError("Actionable rejection did not produce a repair packet")
    artifacts["rejected_repair_ready"] = _capture(root, args.out / "05_rejected_repair_ready.png")

    manifest = {
        "capture_source": str(args.capture_source.resolve()),
        "workspace_root": str(args.workspace_root.resolve()),
        "launch_command": ".\\run_ui.cmd",
        "finding_id": finding.finding_id,
        "authoring_base_sha256": finding.authoring_base_sha256,
        "packet_id": packet.packet_id,
        "packet_sha256": packet.packet_sha256,
        "packet_path": str(packet.packet_path),
        "packet_size_bytes": len(packet.packet_text.encode("utf-8")),
        "accepted_proposal_sha256": accepted_result.proposal_text_sha256,
        "accepted_receipt_path": str(accepted_result.receipt_path),
        "candidate_path": str(accepted_result.candidate_path),
        "candidate_sha256": accepted_result.candidate_sha256,
        "launch_readiness_errors": readiness_errors,
        "rejected_proposal_sha256": rejected_result.proposal_text_sha256,
        "rejection_receipt_path": str(rejected_result.receipt_path),
        "repair_packet_available": True,
        "states": artifacts,
    }
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    app.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
