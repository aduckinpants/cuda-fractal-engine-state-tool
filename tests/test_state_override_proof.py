from __future__ import annotations

import hashlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from cuda_fractal_state_tool.agent_bundle import (
    derive_state_override_authoring_surface,
    serialize_state_override_authoring_surface,
)
from cuda_fractal_state_tool.process_utils import ProcessResult
from cuda_fractal_state_tool.runtime_surface import (
    build_materialization_command,
    build_runtime_identity,
    runtime_identity_summary,
    runtime_identity_summary_sha256,
)
from cuda_fractal_state_tool.state_override_proof import (
    execute_state_override_proof,
    launch_state_override_candidate,
    record_state_override_review,
    validate_state_override_launch_readiness,
)


def _json_bytes(value: object) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


class FakeProofJob:
    def __init__(self, *, contradict_requested: bool = False, alter_replay: bool = False) -> None:
        self.commands: list[list[str]] = []
        self.timeout_seconds: list[float | None] = []
        self.contradict_requested = contradict_requested
        self.alter_replay = alter_replay

    def run_process(self, command, cwd, timeout_seconds=None, env=None):
        command = list(command)
        self.commands.append(command)
        self.timeout_seconds.append(timeout_seconds)
        source = Path(command[command.index("--load-state-json") + 1])
        output = Path(command[command.index("--diagnostics-out-dir") + 1])
        output.mkdir(parents=True, exist_ok=True)
        state = json.loads(source.read_text(encoding="utf-8"))
        if "--apply-loaded-color-pipeline-draft" in command:
            grading_row = state["color_pipeline_draft"]["lanes"][0]["rows"][0]
            state["params"]["color_saturation"] = grading_row["parameter_values"][0][
                "number_value"
            ]
        requested = state["params"]["explaino_damping"]
        if len(self.commands) == 1:
            state["params"]["explaino_damping"] = 1.0 if self.contradict_requested else float(requested) - 2.0e-8
        elif self.alter_replay:
            state["params"]["explaino_damping"] = 0.75
        state["stats"] = {"last_render_ms": 12.0 + len(self.commands)}
        (output / "state.json").write_bytes(_json_bytes(state))
        color = (40, 80, 120) if len(self.commands) == 1 or not self.alter_replay else (4, 8, 12)
        Image.new("RGB", (6, 4), color).save(output / "frame.bmp")
        return ProcessResult(
            command=command,
            cwd=str(cwd),
            pid=100 + len(self.commands),
            exit_code=0,
            timed_out=False,
            elapsed_seconds=0.01,
            stdout="runtime stdout",
            stderr="",
            observed_process_tree=[],
        )


class FailingProofJob:
    def run_process(self, command, cwd, timeout_seconds=None, env=None):
        return ProcessResult(
            command=list(command),
            cwd=str(cwd),
            pid=911,
            exit_code=1,
            timed_out=False,
            elapsed_seconds=0.01,
            stdout="",
            stderr="",
            observed_process_tree=[],
        )


class RuntimeMutatingProofJob(FakeProofJob):
    def __init__(self, executable: Path) -> None:
        super().__init__()
        self.executable = executable

    def run_process(self, command, cwd, timeout_seconds=None, env=None):
        result = super().run_process(command, cwd, timeout_seconds, env)
        if len(self.commands) == 1:
            self.executable.write_bytes(b"runtime changed during proof")
        return result


class FakeLaunchedProcess:
    pid = 4321


class StateOverrideProofTests(unittest.TestCase):
    def test_materialization_command_applies_loaded_pipeline_draft_only_when_requested(self) -> None:
        runtime = Path(r"C:\runtime\fractal_ui.cmd")
        candidate = Path(r"C:\proof\merged_candidate.json")
        output = Path(r"C:\proof\materialization")
        ordinary = build_materialization_command(runtime, candidate, output, apply_loaded_draft=False)
        pipeline = build_materialization_command(runtime, candidate, output, apply_loaded_draft=True)
        self.assertNotIn("--apply-loaded-color-pipeline-draft", ordinary)
        self.assertIn("--apply-loaded-color-pipeline-draft", pipeline)
        self.assertLess(
            pipeline.index("--apply-loaded-color-pipeline-draft"),
            pipeline.index("--capture-diagnostic"),
        )

    def _runtime(self, root: Path) -> Path:
        runtime = root / "runtime"
        (runtime / "ui").mkdir(parents=True)
        (runtime / "ui_salt" / "generated").mkdir(parents=True)
        launcher = runtime / "fractal_ui.cmd"
        launcher.write_text("@echo off\n", encoding="utf-8")
        (runtime / "fractal_ui_active.txt").write_text("fractal_ui.exe\n", encoding="utf-8")
        (runtime / "fractal_ui.exe").write_bytes(b"test runtime")
        return launcher

    def _packet(
        self,
        root: Path,
        runtime: Path,
        *,
        with_pipeline: bool = False,
        last_render_ms: float | None = None,
    ) -> Path:
        packet = root / "finding" / "packets" / "packet-test"
        packet.mkdir(parents=True)
        state = {
            "state_version": 3,
            "fractal_type": "explaino_all",
            "view": {
                "center_x": 0.0,
                "center_hp_x": 0.0,
                "center_y": 0.0,
                "center_hp_y": 0.0,
                "zoom": 1.0,
                "log2_zoom": 0.0,
            },
            "params": {"explaino_damping": 1.0},
            "render": {"width": 6, "height": 4, "device_id": 0},
        }
        if last_render_ms is not None:
            state["stats"] = {"last_render_ms": last_render_ms}
        surface = {
            "version": 1,
            "lanes": [
                {
                    "fractal_id": "explaino_all",
                    "controls": [
                        {
                            "control_id": "explaino_damping",
                            "owner_lane": "explaino_all",
                            "binding_path": "fractal.params.explaino_damping",
                            "control_type": "slider_double",
                            "value_type": "double",
                            "default_value": "1",
                            "candidate_value": "0.9",
                            "runtime_binding_kind": "double",
                            "binding_resolves": True,
                            "state_io_key": "explaino_damping",
                            "has_validation_range": True,
                            "animatable": True,
                            "visibility_surface_id": "default",
                            "default_visible": True,
                        }
                    ],
                }
            ],
        }
        schema = {
            "schema_version": 1,
            "namespace": "fractal",
            "panels": [
                {
                    "id": "fractal",
                    "label": "Fractal",
                    "controls": [
                        {
                            "id": "explaino_damping",
                            "type": "slider_double",
                            "label": "Damping",
                            "help": "Damping.",
                            "value_type": "double",
                            "ui_min": 0.01,
                            "ui_max": 10.0,
                            "step": 0.01,
                            "default": 1.0,
                            "binding": {"kind": "param", "path": "fractal.params.explaino_damping"},
                            "visible_if": {
                                "op": "eq",
                                "path": "fractal.view.fractal_type",
                                "value": "explaino_all",
                            },
                        }
                    ],
                }
            ],
        }
        contract = {"function_library": {"lanes": []}}
        if with_pipeline:
            state["params"]["color_saturation"] = 1.0
            state["color_pipeline_draft"] = {
                "next_row_id": 2,
                "lanes": [
                    {
                        "lane_id": "grading",
                        "label": "Grading",
                        "rows": [
                            {
                                "ui_row_id": 1,
                                "enabled": True,
                                "function_id": "neutral_finish",
                                "parameter_values": [
                                    {
                                        "path": "grade.saturation",
                                        "type": "float",
                                        "number_value": 1.0,
                                    }
                                ],
                            }
                        ],
                    }
                ],
            }
            contract = {
                "function_library": {
                    "lanes": [
                        {
                            "id": "grading",
                            "functions": [
                                {
                                    "id": "neutral_finish",
                                    "params": [
                                        {
                                            "path": "grade.saturation",
                                            "type": "float",
                                            "min": 0.0,
                                            "max": 4.0,
                                        }
                                    ],
                                }
                            ],
                        }
                    ]
                }
            }
        catalog = {"schema_version": 1, "entries": []}
        state_bytes = _json_bytes(state)
        surface_bytes = _json_bytes(surface)
        schema_bytes = _json_bytes(schema)
        contract_bytes = _json_bytes(contract)
        catalog_bytes = _json_bytes(catalog)
        viewport_facts_bytes = _json_bytes(
            {
                "schema_version": 1,
                "mapping_id": "cuda_fractal_renderer_pixel_center_v1",
                "selected_fractal_type": "explaino_all",
            }
        )
        frame_buffer = io.BytesIO()
        Image.new("RGB", (6, 4), (40, 80, 120)).save(frame_buffer, format="PNG")
        frame_bytes = frame_buffer.getvalue()
        authoring_bytes = serialize_state_override_authoring_surface(
            derive_state_override_authoring_surface(state_bytes, surface_bytes, schema_bytes)
        )
        (runtime.parent / "ui" / "fractal_binding_surface_v1.ui_schema.json").write_bytes(schema_bytes)
        (
            runtime.parent
            / "ui_salt"
            / "generated"
            / "color_pipeline_function_library.contract.v1.json"
        ).write_bytes(contract_bytes)
        files = {
            "packet.md": b"# Packet V6 fixture\n",
            "state.json": state_bytes,
            "fractal-parameter-surface.json": surface_bytes,
            "fractal_binding_surface_v1.ui_schema.json": schema_bytes,
            "color_pipeline_function_library.contract.v1.json": contract_bytes,
            "fractal-descriptive-catalog.json": catalog_bytes,
            "fractal-viewport-facts.json": viewport_facts_bytes,
            "state-override-authoring-surface.json": authoring_bytes,
            "frame.png": frame_bytes,
        }
        for name, payload in files.items():
            (packet / name).write_bytes(payload)
        identity = build_runtime_identity(runtime, runtime.parent)
        summary = runtime_identity_summary(identity)
        manifest = {
            "bundle_manifest_version": 2,
            "packet_version": 6,
            "packet_id": packet.name,
            "finding_id": "finding-test",
            "runtime_identity": summary,
            "runtime_identity_sha256": runtime_identity_summary_sha256(summary),
            "authority_identities": {
                "state_sha256": _sha256(state_bytes),
                "parameter_surface_sha256": _sha256(surface_bytes),
                "ui_schema_sha256": _sha256(schema_bytes),
                "ui_salt_contract_sha256": _sha256(contract_bytes),
                "fractal_descriptive_catalog_sha256": _sha256(catalog_bytes),
                "fractal_viewport_facts_sha256": _sha256(viewport_facts_bytes),
                "state_override_authoring_surface_sha256": _sha256(authoring_bytes),
            },
            "required_attachments": [name for name in files if name != "packet.md"],
            "recommended_attachments": [],
            "unavailable_optional_attachments": [],
            "files": [
                {
                    "path": name,
                    "role": "captured_visual_evidence" if name == "frame.png" else "fixture",
                    "sha256": _sha256(payload),
                    "size_bytes": len(payload),
                    "web_handoff": "index" if name == "packet.md" else "required",
                }
                for name, payload in files.items()
            ],
        }
        (packet / "manifest.json").write_bytes(_json_bytes(manifest))
        return packet

    def test_direct_state_proof_records_normalization_replay_and_pending_review(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            runtime = self._runtime(root)
            packet = self._packet(root, runtime)
            override = '{\n  "params": {\n    "explaino_damping": 0.9\n  }\n}\n'
            job = FakeProofJob()
            result = execute_state_override_proof(
                packet, override, runtime, job, proofs_root=root / "proofs"
            )
            self.assertEqual(result.status, "replay_proven")
            self.assertFalse(result.empty_override_byte_exact)
            self.assertEqual(len(job.commands), 2)
            self.assertEqual(job.timeout_seconds, [90.0, 90.0])
            self.assertNotIn("--color-pipeline-action", job.commands[0])
            self.assertNotIn("--apply-loaded-color-pipeline-draft", job.commands[0])
            receipt = json.loads(result.receipt_path.read_text(encoding="utf-8"))
            self.assertEqual(receipt["status"], "replay_proven")
            self.assertEqual(receipt["visual_review"], "pending")
            self.assertFalse(receipt["launch_ready"])
            viewport_hash = receipt["binding"]["authority_identities"][
                "fractal_viewport_facts_sha256"
            ]
            self.assertEqual(
                viewport_hash,
                hashlib.sha256((packet / "fractal-viewport-facts.json").read_bytes()).hexdigest(),
            )
            self.assertEqual(
                receipt["requested_value_receipts"][0]["classification"],
                "representation_normalization",
            )
            self.assertTrue(receipt["replay"]["frame_comparison"]["decoded_equal"])
            self.assertTrue(
                receipt["materialization"]["base_to_candidate_frame_comparison"]["decoded_equal"]
            )
            self.assertEqual(
                {path.name for path in result.proof_dir.iterdir()},
                {
                    "binding.json",
                    "override.json",
                    "merged_candidate.json",
                    "materialization",
                    "replay",
                    "receipt.json",
                },
            )

    def test_proof_uses_adaptive_packet_timeout_and_records_resolution(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            runtime = self._runtime(root)
            packet = self._packet(root, runtime, last_render_ms=203542.34375)
            job = FakeProofJob()

            result = execute_state_override_proof(
                packet,
                '{"params":{"explaino_damping":0.9}}',
                runtime,
                job,
                proofs_root=root / "proofs",
            )

            self.assertEqual(result.status, "replay_proven")
            self.assertEqual(job.timeout_seconds, [438.0, 438.0])
            receipt = json.loads(result.receipt_path.read_text(encoding="utf-8"))
            self.assertEqual(receipt["proof_timeout"]["timeout_seconds"], 438.0)
            self.assertEqual(
                receipt["proof_timeout"]["source"], "captured_last_render_ms"
            )

    def test_development_runtime_drift_applies_shared_300_second_floor(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            runtime = self._runtime(root)
            packet = self._packet(root, runtime, last_render_ms=15964.0263671875)
            (runtime.parent / "fractal_ui.exe").write_bytes(b"published runtime changed")
            job = FakeProofJob()

            result = execute_state_override_proof(
                packet,
                '{"params":{"explaino_damping":0.9}}',
                runtime,
                job,
                proofs_root=root / "proofs",
                runtime_compatibility_mode="development",
            )

            self.assertEqual(result.status, "replay_proven")
            self.assertEqual(job.timeout_seconds, [300.0, 300.0])
            receipt = json.loads(result.receipt_path.read_text(encoding="utf-8"))
            self.assertTrue(receipt["binding"]["runtime_compatibility"]["drift_detected"])
            self.assertTrue(receipt["proof_timeout"]["runtime_drift_detected"])
            self.assertTrue(receipt["proof_timeout"]["runtime_drift_floor_applied"])

    def test_empty_override_result_is_explicit_exact_base_replay(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            runtime = self._runtime(root)
            packet = self._packet(root, runtime)
            base_bytes = (packet / "state.json").read_bytes()
            result = execute_state_override_proof(
                packet, " { }\r\n", runtime, FakeProofJob(), proofs_root=root / "proofs"
            )

            self.assertEqual(result.status, "replay_proven")
            self.assertTrue(result.empty_override_byte_exact)
            self.assertEqual(result.merged_candidate_path.read_bytes(), base_bytes)
            self.assertEqual(result.merged_candidate_sha256, _sha256(base_bytes))
            receipt = json.loads(result.receipt_path.read_text(encoding="utf-8"))
            self.assertTrue(receipt["merged_candidate"]["empty_override_byte_exact"])
            self.assertEqual(receipt["override"]["changed_paths"], [])
            self.assertEqual(receipt["override"]["requested_paths"], [])
            record_state_override_review(result, "accepted", "Explicit exact-base replay acknowledgement.")
            self.assertEqual(
                validate_state_override_launch_readiness(result, packet, " { }\r\n", runtime),
                [],
            )

    def test_pipeline_override_uses_engine_apply_operation_only_for_materialization(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            runtime = self._runtime(root)
            packet = self._packet(root, runtime, with_pipeline=True)
            state = json.loads((packet / "state.json").read_text(encoding="utf-8"))
            lanes = state["color_pipeline_draft"]["lanes"]
            lanes[0]["rows"][0]["parameter_values"][0]["number_value"] = 0.25
            override = json.dumps({"color_pipeline_draft": {"lanes": lanes}})
            job = FakeProofJob()
            result = execute_state_override_proof(
                packet, override, runtime, job, proofs_root=root / "proofs"
            )
            self.assertEqual(result.status, "replay_proven")
            self.assertIn("--apply-loaded-color-pipeline-draft", job.commands[0])
            self.assertNotIn("--apply-loaded-color-pipeline-draft", job.commands[1])
            receipt = json.loads(result.receipt_path.read_text(encoding="utf-8"))
            self.assertEqual(receipt["proof_receipt_version"], 5)
            self.assertTrue(receipt["override"]["apply_loaded_color_pipeline_draft"])
            self.assertTrue(receipt["materialization"]["applied_loaded_color_pipeline_draft"])
            self.assertEqual(
                json.loads(result.engine_candidate_path.read_text(encoding="utf-8"))["params"][
                    "color_saturation"
                ],
                0.25,
            )
            self.assertTrue(receipt["replay"]["frame_comparison"]["decoded_equal"])
            self.assertEqual(result.candidate_display_path.name, "candidate-display.png")
            self.assertTrue(result.candidate_display_path.is_file())
            display = receipt["materialization"]["display_derivative"]
            self.assertTrue(display["decoded_equal"])
            self.assertEqual(
                display["source_frame"]["decoded_rgba_sha256"],
                display["display_frame"]["decoded_rgba_sha256"],
            )
            self.assertNotEqual(
                display["source_frame"]["encoded_sha256"],
                display["display_frame"]["encoded_sha256"],
            )
            self.assertTrue(
                receipt["materialization"]["base_to_candidate_frame_comparison"]["decoded_equal"]
            )
            self.assertEqual(
                {path.name for path in result.proof_dir.iterdir()},
                {
                    "binding.json",
                    "override.json",
                    "merged_candidate.json",
                    "materialization",
                    "replay",
                    "receipt.json",
                },
            )

    def test_runtime_contradiction_and_replay_instability_are_rejected(self) -> None:
        for job, expected in (
            (FakeProofJob(contradict_requested=True), "reverted requested value"),
            (FakeProofJob(alter_replay=True), "changed stable authoring state"),
        ):
            with self.subTest(expected=expected), tempfile.TemporaryDirectory() as temp_dir:
                root = Path(temp_dir)
                runtime = self._runtime(root)
                packet = self._packet(root, runtime)
                result = execute_state_override_proof(
                    packet,
                    '{"params":{"explaino_damping":0.9}}',
                    runtime,
                    job,
                    proofs_root=root / "proofs",
                )
                self.assertEqual(result.status, "rejected")
                self.assertIn(expected, result.message)
                receipt = json.loads(result.receipt_path.read_text(encoding="utf-8"))
                self.assertFalse(receipt["launch_ready"])

    def test_runtime_drift_warns_and_attempts_in_development_but_strict_stops(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            runtime = self._runtime(root)
            packet = self._packet(root, runtime)
            (runtime.parent / "fractal_ui.exe").write_bytes(b"newer compatible runtime")
            override = '{"params":{"explaino_damping":0.9}}'

            development_job = FakeProofJob()
            development = execute_state_override_proof(
                packet,
                override,
                runtime,
                development_job,
                proofs_root=root / "development-proofs",
                runtime_compatibility_mode="development",
            )
            self.assertEqual(development.status, "replay_proven")
            self.assertEqual(len(development_job.commands), 2)
            development_binding = json.loads(
                (development.proof_dir / "binding.json").read_text(encoding="utf-8")
            )
            compatibility = development_binding["runtime_compatibility"]
            self.assertEqual(compatibility["mode"], "development")
            self.assertTrue(compatibility["drift_detected"])
            self.assertEqual(compatibility["disposition"], "warning_attempt_current_runtime")
            self.assertTrue(compatibility["differences"])
            self.assertNotEqual(
                compatibility["packet_runtime_identity_sha256"],
                compatibility["proof_runtime_identity_sha256"],
            )

            strict_job = FakeProofJob()
            strict = execute_state_override_proof(
                packet,
                override,
                runtime,
                strict_job,
                proofs_root=root / "strict-proofs",
                runtime_compatibility_mode="strict",
            )
            self.assertEqual(strict.status, "rejected")
            self.assertEqual(strict_job.commands, [])
            self.assertIn("strict runtime compatibility mode", strict.message)
            strict_receipt = json.loads(strict.receipt_path.read_text(encoding="utf-8"))
            self.assertEqual(
                strict_receipt["binding"]["runtime_compatibility"]["disposition"],
                "warning_strict_stop_before_materialization",
            )

    def test_runtime_change_during_proof_and_after_proof_always_invalidates(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            runtime = self._runtime(root)
            packet = self._packet(root, runtime)
            executable = runtime.parent / "fractal_ui.exe"
            override = '{"params":{"explaino_damping":0.9}}'

            changed_during = execute_state_override_proof(
                packet,
                override,
                runtime,
                RuntimeMutatingProofJob(executable),
                proofs_root=root / "changed-during",
                runtime_compatibility_mode="development",
            )
            self.assertEqual(changed_during.status, "rejected")
            self.assertIn("changed during proof", changed_during.message)

            stable_packet = self._packet(root / "stable", runtime)
            proven = execute_state_override_proof(
                stable_packet,
                override,
                runtime,
                FakeProofJob(),
                proofs_root=root / "stable-proofs",
                runtime_compatibility_mode="development",
            )
            self.assertEqual(proven.status, "replay_proven")
            record_state_override_review(proven, "accepted")
            executable.write_bytes(b"runtime changed after proof")
            errors = validate_state_override_launch_readiness(
                proven, stable_packet, override, runtime
            )
            self.assertIn("Published runtime identity changed after proof", errors)

    def test_runtime_failure_retains_exit_and_missing_artifact_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            runtime = self._runtime(root)
            packet = self._packet(root, runtime)
            result = execute_state_override_proof(
                packet,
                '{"params":{"explaino_damping":0.9}}',
                runtime,
                FailingProofJob(),
                proofs_root=root / "proofs",
            )
            self.assertEqual(result.status, "rejected")
            self.assertIn("exit code 1", result.message)
            self.assertIn("missing artifacts: state.json, frame.bmp", result.message)
            self.assertIn("runtime emitted no stdout or stderr", result.message)
            receipt = json.loads(result.receipt_path.read_text(encoding="utf-8"))
            attempt = receipt["runtime_attempts"]["materialization"]
            self.assertEqual(attempt["exit_code"], 1)
            self.assertEqual(attempt["missing_artifacts"], ["state.json", "frame.bmp"])

    def test_review_acceptance_is_required_and_all_bindings_are_rechecked_for_launch(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            runtime = self._runtime(root)
            packet = self._packet(root, runtime)
            override = '{"params":{"explaino_damping":0.9}}'
            result = execute_state_override_proof(
                packet, override, runtime, FakeProofJob(), proofs_root=root / "proofs"
            )
            self.assertIn(
                "Visual review is still pending",
                validate_state_override_launch_readiness(result, packet, override, runtime),
            )
            decision = record_state_override_review(result, "accepted", "Candidate matches the requested exploration.")
            self.assertTrue(decision.is_file())
            self.assertEqual(validate_state_override_launch_readiness(result, packet, override, runtime), [])

            calls: list[tuple] = []

            def fake_launcher(*args, **kwargs):
                calls.append((args, kwargs))
                return FakeLaunchedProcess()

            launched = launch_state_override_candidate(
                result, packet, override, runtime, launcher=fake_launcher
            )
            self.assertEqual(launched.pid, 4321)
            self.assertEqual(len(calls), 1)
            launch = json.loads((result.proof_dir / "launch.json").read_text(encoding="utf-8"))
            self.assertEqual(launch["engine_candidate_sha256"], result.engine_candidate_sha256)
            self.assertEqual(launch["launch_receipt_version"], 3)
            self.assertEqual(launch["launch_status"], "launcher_process_created")
            self.assertEqual(launch["launcher_process_pid"], 4321)
            self.assertEqual(launch["pid"], 4321)
            self.assertFalse(launch["viewer_health_verified"])
            self.assertIn("process creation only", launch["viewer_health_note"])

    def test_revision_and_tampering_never_become_launch_ready(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            runtime = self._runtime(root)
            packet = self._packet(root, runtime)
            override = '{"params":{"explaino_damping":0.9}}'
            revision = execute_state_override_proof(
                packet, override, runtime, FakeProofJob(), proofs_root=root / "proofs"
            )
            record_state_override_review(revision, "revision_needed")
            self.assertTrue(validate_state_override_launch_readiness(revision, packet, override, runtime))

            accepted = execute_state_override_proof(
                packet, override, runtime, FakeProofJob(), proofs_root=root / "proofs"
            )
            record_state_override_review(accepted, "accepted")
            accepted.engine_candidate_path.write_text("{}\n", encoding="utf-8")
            errors = validate_state_override_launch_readiness(accepted, packet, override, runtime)
            self.assertIn("Engine launch candidate changed after proof", errors)

            display_tampered = execute_state_override_proof(
                packet, override, runtime, FakeProofJob(), proofs_root=root / "proofs"
            )
            record_state_override_review(display_tampered, "accepted")
            display_tampered.candidate_display_path.write_bytes(b"changed")
            display_errors = validate_state_override_launch_readiness(
                display_tampered, packet, override, runtime
            )
            self.assertIn("Candidate PNG display derivative changed after proof", display_errors)

            receipt_tampered = execute_state_override_proof(
                packet, override, runtime, FakeProofJob(), proofs_root=root / "proofs"
            )
            receipt_tampered.receipt_path.write_text("{}\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Proof receipt changed"):
                record_state_override_review(receipt_tampered, "accepted")


if __name__ == "__main__":
    unittest.main()
