from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from cuda_fractal_state_tool.runtime_probe import build_runtime_identity, resolve_launcher


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

            resolution = resolve_launcher(cmd)

            self.assertEqual(resolution.active_entry, "fractal_ui.exe")
            self.assertTrue(str(runtime / "fractal_ui.exe").endswith("fractal_ui.exe"))
            self.assertEqual(resolution.repo_root_hint, "C:\\example\\repo")
            self.assertTrue((runtime / "ui" / "fractal_binding_surface_v1.ui_schema.json").exists())

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

            identity = build_runtime_identity(cmd, runtime)

            self.assertIsNotNone(identity["launcher_sha256"])
            self.assertIsNotNone(identity["resolved_executable_sha256"])
            self.assertIsNotNone(identity["source_schema_sha256"])


if __name__ == "__main__":
    unittest.main()
