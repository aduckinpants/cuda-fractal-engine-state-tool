from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from cuda_fractal_state_tool.runtime_probe import build_runtime_identity, resolve_launcher
from cuda_fractal_state_tool.runtime_probe import run_probe
from cuda_fractal_state_tool.process_utils import ProcessResult


class RuntimeProbeTests(unittest.TestCase):
    def test_resolve_launcher_reads_active_executable_and_repo_hint(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            runtime = root / "runtime"
            runtime.mkdir()
            cmd = runtime / "fractal_ui.cmd"
            cmd.write_text("@echo off\n", encoding="utf-8")
            (runtime / "fractal_ui_active.txt").write_text("fractal_ui.exe\n", encoding="utf-8")
            (runtime / "fractal_ui.exe").write_text("binary", encoding="utf-8")
            (runtime / "fractal_ui_repo_root.txt").write_text("C:\\example\\repo\n", encoding="utf-8")
            (runtime / "ui").mkdir()
            (runtime / "ui" / "fractal_binding_surface_v1.ui_schema.json").write_text("{}", encoding="utf-8")
            contract = runtime / "ui_salt" / "generated" / "color_pipeline_function_library.contract.v1.json"
            contract.parent.mkdir(parents=True)
            contract.write_text("{}", encoding="utf-8")

            resolution = resolve_launcher(cmd)

            self.assertEqual(resolution.active_entry, "fractal_ui.exe")
            self.assertTrue(str(runtime / "fractal_ui.exe").endswith("fractal_ui.exe"))
            self.assertEqual(resolution.repo_root_hint, "C:\\example\\repo")
            self.assertTrue((runtime / "ui" / "fractal_binding_surface_v1.ui_schema.json").exists())
            self.assertEqual(resolution.ui_salt_contract_path, str(contract))

    def test_build_runtime_identity_includes_hashes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            runtime = root / "runtime"
            runtime.mkdir()
            cmd = runtime / "fractal_ui.cmd"
            cmd.write_text("@echo off\n", encoding="utf-8")
            (runtime / "fractal_ui_active.txt").write_text("fractal_ui.exe\n", encoding="utf-8")
            (runtime / "fractal_ui.exe").write_text("binary", encoding="utf-8")
            (runtime / "fractal_ui_repo_root.txt").write_text(str(root) + "\n", encoding="utf-8")
            (root / "ui").mkdir()
            (root / "ui" / "fractal_binding_surface_v1.ui_schema.json").write_text("{}", encoding="utf-8")
            contract = runtime / "ui_salt" / "generated" / "color_pipeline_function_library.contract.v1.json"
            contract.parent.mkdir(parents=True)
            contract.write_text("{}", encoding="utf-8")

            identity = build_runtime_identity(cmd, runtime)

            self.assertIsNotNone(identity["launcher_sha256"])
            self.assertIsNotNone(identity["resolved_executable_sha256"])
            self.assertIsNotNone(identity["source_schema_sha256"])
            self.assertIsNotNone(identity["ui_salt_contract_sha256"])

    def test_run_probe_summary_classifies_supported_statuses(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            runtime = root / "runtime"
            runtime.mkdir()
            cmd = runtime / "fractal_ui.cmd"
            cmd.write_text("@echo off\n", encoding="utf-8")
            (runtime / "fractal_ui_active.txt").write_text("fractal_ui.exe\n", encoding="utf-8")
            (runtime / "fractal_ui.exe").write_text("binary", encoding="utf-8")
            (runtime / "fractal_ui_repo_root.txt").write_text(str(root) + "\n", encoding="utf-8")
            (root / "ui").mkdir()
            (root / "ui" / "fractal_binding_surface_v1.ui_schema.json").write_text("{}", encoding="utf-8")

            def fake_run_command(command, cwd, timeout_seconds=None, env=None):
                output_root = Path(command[-1]).parent if command[-1].endswith(".json") else None
                if "--describe-parameter-surface-json" in command:
                    Path(command[-1]).write_text("{}", encoding="utf-8")
                elif "--describe-functions-json" in command:
                    Path(command[-1]).write_text("{}", encoding="utf-8")
                elif "--capture-diagnostic" in command and "invalid_capture" in command[-1]:
                    pass
                elif "--capture-diagnostic" in command:
                    capture_dir = Path(command[command.index("--diagnostics-out-dir") + 1])
                    capture_dir.mkdir(parents=True, exist_ok=True)
                    (capture_dir / "state.json").write_text("{\"state_version\":3,\"fractal_type\":\"newton\",\"view\":{},\"params\":{},\"render\":{}}", encoding="utf-8")
                    (capture_dir / "frame.bmp").write_text("bmp", encoding="utf-8")
                if "invalid_capture" in command[-1]:
                    return ProcessResult(command=list(command), cwd=str(cwd), pid=123, exit_code=1, timed_out=False, elapsed_seconds=0.1, stdout="", stderr="invalid", observed_process_tree=[])
                return ProcessResult(command=list(command), cwd=str(cwd), pid=123, exit_code=0, timed_out=False, elapsed_seconds=0.1, stdout="ok", stderr="", observed_process_tree=[])

            with patch("cuda_fractal_state_tool.runtime_probe.run_command", side_effect=fake_run_command):
                summary = run_probe(cmd, root / "probe")

            self.assertGreaterEqual(summary["command_status_counts"]["runtime_success"], 1)
            self.assertGreaterEqual(summary["command_status_counts"]["runtime_rejected_input"], 1)


if __name__ == "__main__":
    unittest.main()
