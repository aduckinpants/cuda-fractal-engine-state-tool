from __future__ import annotations

import json
import hashlib
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from PIL import Image

import tests.test_state_override as state_override_fixture

from cuda_fractal_state_tool.async_jobs import JobCancelledError
from cuda_fractal_state_tool.scalar_sweep import (
    PacketSweepBinding,
    ScalarBracketSweepService,
    ScalarSweepPlanError,
    parse_scalar_sweep_plan,
)
from cuda_fractal_state_tool.sweep_presentation import (
    CapturedBaseReference,
    render_scalar_sweep_web_review,
)


def _plan(policy: str = "continue_independent") -> str:
    return json.dumps(
        {
            "sweep_version": 1,
            "axis": {
                "path": "params.explaino_damping",
                "values": [0.5, 0.9, 1.5],
            },
            "member_failure_policy": policy,
        }
    )


class FakeJob:
    def __init__(self) -> None:
        self.cancelled = False

    def raise_if_cancelled(self) -> None:
        if self.cancelled:
            raise JobCancelledError("cancelled")


class ScalarSweepTests(unittest.TestCase):
    def _packet(self, root: Path) -> Path:
        packet, *_ = state_override_fixture.StateOverrideTests()._packet(root)
        return packet

    def _service(self, statuses, *, identity_values=None, after_proof=None):
        queue = list(statuses)
        identities = list(identity_values or ["runtime-a"] * 20)

        def proof(packet_dir, override_text, runtime_cmd_path, job, **kwargs):
            status = queue.pop(0)
            index = len(statuses) - len(queue)
            proof_dir = packet_dir.parent / f"proof-{index}"
            proof_dir.mkdir()
            receipt = proof_dir / "receipt.json"
            receipt_document = (
                {
                    "status": "rejected",
                    "errors": [
                        "Engine reverted requested value at params.explaino_damping: "
                        "requested test value, emitted exact base"
                    ],
                }
                if status == "no_effect"
                else {}
            )
            receipt.write_text(json.dumps(receipt_document) + "\n", encoding="utf-8")
            display = proof_dir / "candidate-display.png"
            Image.new("RGB", (16, 10), (index * 30, 0, 0)).save(display)
            merged = proof_dir / "merged_candidate.json"
            emitted = proof_dir / "materialization" / "state.json"
            merged_sha = ""
            emitted_sha = ""
            if status == "no_effect":
                base_document = json.loads((packet_dir / "state.json").read_text(encoding="utf-8"))
                merged_document = json.loads(json.dumps(base_document))
                requested = json.loads(override_text)["params"]["explaino_damping"]
                merged_document["params"]["explaino_damping"] = requested
                merged.write_text(json.dumps(merged_document), encoding="utf-8")
                emitted.parent.mkdir()
                emitted.write_text(json.dumps(base_document), encoding="utf-8")
                merged_sha = hashlib.sha256(merged.read_bytes()).hexdigest()
                emitted_sha = hashlib.sha256(emitted.read_bytes()).hexdigest()
            if after_proof is not None:
                after_proof(index, job)
            return SimpleNamespace(
                status="rejected" if status == "no_effect" else status,
                proof_id=f"proof-{index}",
                message=status,
                receipt_path=receipt,
                receipt_sha256=(
                    hashlib.sha256(receipt.read_bytes()).hexdigest()
                    if status == "no_effect"
                    else "a" * 64
                ),
                merged_candidate_path=merged,
                merged_candidate_sha256=merged_sha,
                engine_candidate_path=emitted if status == "no_effect" else None,
                engine_candidate_sha256=emitted_sha if status == "no_effect" else "b" * 64,
                candidate_frame_sha256="c" * 64,
                candidate_display_path=display if status == "replay_proven" else None,
                candidate_display_sha256=(
                    hashlib.sha256(display.read_bytes()).hexdigest()
                    if status == "replay_proven"
                    else None
                ),
            )

        def snapshot(_runtime):
            return {"runtime_identity_sha256": identities.pop(0)}

        def binding(packet_dir):
            manifest = packet_dir / "manifest.json"
            return PacketSweepBinding(
                packet_id=packet_dir.name,
                finding_id="fixture-finding",
                manifest_sha256=hashlib.sha256(manifest.read_bytes()).hexdigest(),
                authority_identities={},
            )

        def captured_base(packet_dir, axis_path):
            path = packet_dir.parent / "captured-base.png"
            if not path.exists():
                Image.new("RGB", (32, 20), (4, 8, 12)).save(path)
            return CapturedBaseReference(
                source_path=path,
                source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                axis_value=1.0,
                packet_id=packet_dir.name,
                finding_id="fixture-finding",
            )

        return ScalarBracketSweepService(
            proof=proof,
            runtime_snapshot=snapshot,
            packet_binding=binding,
            captured_base_reference=captured_base,
        )

    def test_plan_parser_rejects_duplicates_nonfinite_and_unsupported_shapes(self) -> None:
        with self.assertRaisesRegex(ScalarSweepPlanError, "duplicate"):
            parse_scalar_sweep_plan(
                '{"sweep_version":1,"axis":{"path":"params.x","values":[0,0.0,1]},'
                '"member_failure_policy":"continue_independent"}'
            )
        with self.assertRaisesRegex(ScalarSweepPlanError, "finite"):
            parse_scalar_sweep_plan(
                '{"sweep_version":1,"axis":{"path":"params.x","values":[0,NaN,1]},'
                '"member_failure_policy":"continue_independent"}'
            )
        with self.assertRaisesRegex(ScalarSweepPlanError, "direct scalar"):
            parse_scalar_sweep_plan(
                '{"sweep_version":1,"axis":{"path":"view.zoom","values":[1,2,3]},'
                '"member_failure_policy":"continue_independent"}'
            )

    def test_collision_and_range_failure_abort_before_proof_or_sweep_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            packet = self._packet(root)
            service = self._service([])
            with self.assertRaisesRegex(ScalarSweepPlanError, "already contains"):
                service.execute(
                    packet_dir=packet,
                    fixed_override_text='{"params":{"explaino_damping":1.0}}',
                    plan_text=_plan(),
                    runtime_cmd_path=root / "runtime.cmd",
                    job=FakeJob(),
                    sweeps_root=root / "sweeps",
                )
            bad = _plan().replace("1.5", "3.0")
            with self.assertRaisesRegex(ScalarSweepPlanError, "deployed maximum"):
                service.execute(
                    packet_dir=packet,
                    fixed_override_text="{}",
                    plan_text=bad,
                    runtime_cmd_path=root / "runtime.cmd",
                    job=FakeJob(),
                    sweeps_root=root / "sweeps",
                )
            self.assertFalse((root / "sweeps").exists())

    def test_blank_fixed_override_is_the_empty_override(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            packet = self._packet(root)
            result = self._service(["replay_proven"] * 3).execute(
                packet_dir=packet,
                fixed_override_text="  \r\n",
                plan_text=_plan(),
                runtime_cmd_path=root / "runtime.cmd",
                job=FakeJob(),
                sweeps_root=root / "sweeps",
            )
            self.assertEqual(result.disposition, "COMPLETE")

    def test_exact_captured_base_value_is_rejected_before_proof(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            packet = self._packet(root)
            plan = json.loads(_plan())
            plan["axis"]["values"] = [0.5, 1.0, 1.5]
            with self.assertRaisesRegex(ScalarSweepPlanError, "exactly repeats captured base"):
                self._service([]).execute(
                    packet_dir=packet,
                    fixed_override_text="{}",
                    plan_text=json.dumps(plan),
                    runtime_cmd_path=root / "runtime.cmd",
                    job=FakeJob(),
                    sweeps_root=root / "sweeps",
                )
            self.assertFalse((root / "sweeps").exists())

    def test_continue_independent_preserves_failed_member_and_completes_remaining(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            packet = self._packet(root)
            result = self._service(["replay_proven", "rejected", "replay_proven"]).execute(
                packet_dir=packet,
                fixed_override_text="{}",
                plan_text=_plan(),
                runtime_cmd_path=root / "runtime.cmd",
                job=FakeJob(),
                sweeps_root=root / "sweeps",
            )
            self.assertEqual(result.disposition, "PARTIAL_MEMBER_FAILURES")
            self.assertEqual([item.status for item in result.members], [
                "REPLAY_PROVEN", "PROOF_FAILED", "REPLAY_PROVEN"
            ])
            self.assertTrue(result.receipt_path.is_file())
            self.assertEqual((result.sweep_dir / "fixed-override.json").read_bytes(), b"{}")
            self.assertTrue((result.sweep_dir / "presentation" / "index.md").is_file())
            self.assertIsNotNone(result.web_review_dir)
            self.assertEqual(
                {path.name for path in result.web_review_dir.iterdir()},
                {"sweep-review.md", "sweep-evidence.json", "contact-sheet.png"},
            )
            first = {
                path.name: path.read_bytes() for path in result.web_review_dir.iterdir()
            }
            regenerated = render_scalar_sweep_web_review(sweep_dir=result.sweep_dir)
            self.assertEqual(
                first,
                {path.name: path.read_bytes() for path in regenerated.web_review_dir.iterdir()},
            )
            review = regenerated.review_path.read_text(encoding="utf-8")
            self.assertIn("Current / captured base reference", review)
            self.assertIn("not a sweep member and is not newly replay-proven", review)
            self.assertNotIn(str(root), review)
            evidence = json.loads(regenerated.evidence_path.read_text(encoding="utf-8"))
            self.assertFalse(evidence["human_acceptance"])
            self.assertTrue(
                all(not Path(source["path"]).is_absolute() for source in evidence["sources"])
            )
            (result.sweep_dir / "presentation" / "contact-sheet.png").write_bytes(b"corrupt")
            with self.assertRaisesRegex(ValueError, "differs"):
                render_scalar_sweep_web_review(sweep_dir=result.sweep_dir)

    def test_engine_emitted_exact_base_is_a_distinct_no_effect_member_status(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            packet = self._packet(root)
            result = self._service(["replay_proven", "no_effect", "replay_proven"]).execute(
                packet_dir=packet,
                fixed_override_text="{}",
                plan_text=_plan(),
                runtime_cmd_path=root / "runtime.cmd",
                job=FakeJob(),
                sweeps_root=root / "sweeps",
            )
            self.assertEqual(result.disposition, "PARTIAL_MEMBER_FAILURES")
            self.assertEqual(result.members[1].status, "NO_EFFECT_ENGINE_EMITTED_BASE")
            self.assertIn("exact captured base value", result.members[1].message)
            review = (result.web_review_dir / "sweep-review.md").read_text(encoding="utf-8")
            self.assertIn("not a CUDA or image-render failure", review)

    def test_progress_reports_validation_members_and_terminal_disposition(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            packet = self._packet(root)
            events = []
            self._service(["replay_proven"] * 3).execute(
                packet_dir=packet,
                fixed_override_text="{}",
                plan_text=_plan(),
                runtime_cmd_path=root / "runtime.cmd",
                job=FakeJob(),
                sweeps_root=root / "sweeps",
                on_progress=events.append,
            )
            self.assertEqual(events[0]["event"], "PLAN_VALIDATED")
            self.assertEqual(
                [event["event"] for event in events].count("MEMBER_STARTED"), 3
            )
            self.assertEqual(events[-1]["event"], "SWEEP_COMPLETED")
            self.assertEqual(events[-1]["disposition"], "COMPLETE")

    def test_strict_failure_stops_before_later_members(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            packet = self._packet(root)
            result = self._service(["rejected"]).execute(
                packet_dir=packet,
                fixed_override_text="{}",
                plan_text=_plan("stop_on_first_failure"),
                runtime_cmd_path=root / "runtime.cmd",
                job=FakeJob(),
                sweeps_root=root / "sweeps",
            )
            self.assertEqual(result.disposition, "STOPPED_AFTER_MEMBER_FAILURE")
            self.assertEqual([item.status for item in result.members], [
                "PROOF_FAILED", "NOT_STARTED_AFTER_FAILURE", "NOT_STARTED_AFTER_FAILURE"
            ])

    def test_cancelled_member_stops_and_preserves_completed_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            packet = self._packet(root)

            def cancel_after_first(index, job):
                if index == 1:
                    job.cancelled = True

            result = self._service(
                ["replay_proven"], after_proof=cancel_after_first
            ).execute(
                packet_dir=packet,
                fixed_override_text="{}",
                plan_text=_plan(),
                runtime_cmd_path=root / "runtime.cmd",
                job=FakeJob(),
                sweeps_root=root / "sweeps",
            )
            self.assertEqual(result.disposition, "CANCELLED")
            self.assertEqual([item.status for item in result.members], [
                "REPLAY_PROVEN", "NOT_STARTED_AFTER_CANCEL", "NOT_STARTED_AFTER_CANCEL"
            ])

    def test_runtime_drift_stops_remaining_members_even_in_continue_mode(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            packet = self._packet(root)
            result = self._service(
                ["replay_proven"], identity_values=["runtime-a", "runtime-a", "runtime-b"]
            ).execute(
                packet_dir=packet,
                fixed_override_text="{}",
                plan_text=_plan(),
                runtime_cmd_path=root / "runtime.cmd",
                job=FakeJob(),
                sweeps_root=root / "sweeps",
            )
            self.assertEqual(result.disposition, "AUTHORITY_DRIFT")
            self.assertEqual(result.members[1].status, "NOT_STARTED_AFTER_AUTHORITY_DRIFT")


if __name__ == "__main__":
    unittest.main()
