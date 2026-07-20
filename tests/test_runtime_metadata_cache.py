from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from cuda_fractal_state_tool.runtime_metadata_cache import runtime_cache_dir, runtime_identity_cache_key
from cuda_fractal_state_tool.runtime_probe import run_probe


class RuntimeMetadataCacheTests(unittest.TestCase):
    def test_runtime_identity_cache_key_is_stable(self) -> None:
        identity_a = {
            "launcher_path": "C:/runtime/fractal_ui.cmd",
            "launcher_sha256": "launcher",
            "working_directory": "C:/runtime",
            "resolved_executable_path": "C:/runtime/fractal_ui.exe",
            "resolved_executable_sha256": "exe",
            "resolved_executable_file_version": "1.0.0",
            "runtime_schema_path": "C:/runtime/ui/fractal_binding_surface_v1.ui_schema.json",
            "runtime_schema_sha256": "runtime-schema",
            "source_schema_path": "C:/repo/ui/fractal_binding_surface_v1.ui_schema.json",
            "source_schema_sha256": "source-schema",
        }
        identity_b = {
            "source_schema_sha256": "source-schema",
            "runtime_schema_sha256": "runtime-schema",
            "runtime_schema_path": "C:/runtime/ui/fractal_binding_surface_v1.ui_schema.json",
            "resolved_executable_file_version": "1.0.0",
            "resolved_executable_sha256": "exe",
            "resolved_executable_path": "C:/runtime/fractal_ui.exe",
            "working_directory": "C:/runtime",
            "launcher_sha256": "launcher",
            "launcher_path": "C:/runtime/fractal_ui.cmd",
            "source_schema_path": "C:/repo/ui/fractal_binding_surface_v1.ui_schema.json",
        }

        self.assertEqual(runtime_identity_cache_key(identity_a), runtime_identity_cache_key(identity_b))

    def test_run_probe_uses_cached_outputs_when_runtime_identity_matches(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            output_root = root / "runtime_probe"
            cache_root = output_root.parent / "cache" / "runtime"
            identity = {
                "launcher_path": "C:/runtime/fractal_ui.cmd",
                "launcher_sha256": "launcher",
                "working_directory": "C:/runtime",
                "resolved_executable_path": "C:/runtime/fractal_ui.exe",
                "resolved_executable_sha256": "exe",
                "resolved_executable_file_version": "1.0.0",
                "runtime_schema_path": "C:/runtime/ui/fractal_binding_surface_v1.ui_schema.json",
                "runtime_schema_sha256": "runtime-schema",
                "source_schema_path": "C:/repo/ui/fractal_binding_surface_v1.ui_schema.json",
                "source_schema_sha256": "source-schema",
                "describe_parameter_surface_sha256": None,
                "describe_functions_sha256": None,
            }
            cache_dir = runtime_cache_dir(cache_root, identity)
            cache_dir.mkdir(parents=True)
            (cache_dir / "launcher_resolution.json").write_text(
                '{"runtime_cmd_path":"C:/runtime/fractal_ui.cmd","launcher_directory":"C:/runtime","active_file_path":null,"active_entry":null,"resolved_executable_path":"C:/runtime/fractal_ui.exe","repo_root_hint":"C:/repo","runtime_schema_path":"C:/runtime/ui/fractal_binding_surface_v1.ui_schema.json"}',
                encoding="utf-8",
            )
            (cache_dir / "runtime_identity.json").write_text(
                '{"launcher_path":"C:/runtime/fractal_ui.cmd","launcher_sha256":"launcher","working_directory":"C:/runtime","resolved_executable_path":"C:/runtime/fractal_ui.exe","resolved_executable_sha256":"exe","resolved_executable_file_version":"1.0.0","runtime_schema_path":"C:/runtime/ui/fractal_binding_surface_v1.ui_schema.json","runtime_schema_sha256":"runtime-schema","source_schema_path":"C:/repo/ui/fractal_binding_surface_v1.ui_schema.json","source_schema_sha256":"source-schema","describe_parameter_surface_sha256":null,"describe_functions_sha256":null}',
                encoding="utf-8",
            )
            for name in ("describe_parameter_surface", "describe_functions", "capture_one", "capture_two", "invalid_json_capture", "replay_one"):
                (cache_dir / f"{name}.json").write_text(
                    '{"name":"%s","command":["cmd.exe","/d","/c","C:/cache/%s.json"],"cwd":"C:/runtime","pid":123,"exit_code":0,"timed_out":false,"elapsed_seconds":0.1,"stdout_path":"C:/cache/%s.stdout.txt","stderr_path":"C:/cache/%s.stderr.txt","process_tree":[]}' % (name, name, name, name),
                    encoding="utf-8",
                )
                (cache_dir / f"{name}.stdout.txt").write_text("cached stdout\n", encoding="utf-8")
                (cache_dir / f"{name}.stderr.txt").write_text("", encoding="utf-8")
            (cache_dir / "capture_one").mkdir(parents=True)
            (cache_dir / "capture_two").mkdir(parents=True)
            (cache_dir / "replay_one").mkdir(parents=True)
            (cache_dir / "capture_one" / "state.json").write_text("{}", encoding="utf-8")
            (cache_dir / "capture_two" / "state.json").write_text("{}", encoding="utf-8")
            (cache_dir / "replay_one" / "state.json").write_text("{}", encoding="utf-8")
            (cache_dir / "summary.json").write_text("{}", encoding="utf-8")

            def fail_run_command(*args, **kwargs):
                raise AssertionError("run_command should not be invoked when a matching cache exists")

            from unittest.mock import patch

            with patch("cuda_fractal_state_tool.runtime_probe.build_runtime_identity", return_value=identity), patch(
                "cuda_fractal_state_tool.runtime_probe.run_command",
                side_effect=fail_run_command,
            ):
                summary = run_probe(Path(r"C:\runtime\fractal_ui.cmd"), output_root)

            self.assertTrue(summary["cache_hit"])
            self.assertEqual(summary["cache_key"], runtime_identity_cache_key(identity))
            self.assertTrue((output_root / "summary.json").exists())
            self.assertTrue((output_root / "runtime_identity.json").exists())
            self.assertEqual(Path(summary["commands"][0]["command"][-1]), output_root.resolve() / "describe_parameter_surface.json")
            self.assertNotIn("C:/cache", summary["commands"][0]["command"][-1])


if __name__ == "__main__":
    unittest.main()