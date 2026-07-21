from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

import cuda_fractal_state_tool.fractal_descriptive_catalog as catalog_module

from cuda_fractal_state_tool.fractal_descriptive_catalog import (
    load_selected_fractal_description,
)


def _entry(selector: str, status: str = "reviewed") -> dict[str, object]:
    description = None
    if status == "reviewed":
        description = {
            "math_summary": f"Reviewed summary for {selector}.",
            "recurrence_or_field_model": "A reviewed recurrence model.",
            "state_order": "The reviewed state order.",
            "termination_or_classification": "The reviewed termination rule.",
            "interpretation_notes": "A reviewed interpretation boundary.",
            "source_refs": ["ui_app/src/example.cpp#Example"],
        }
    return {
        "selector_id": selector,
        "display_name": selector.replace("_", " ").title(),
        "category": "explaino",
        "family": "explaino",
        "formula_growth_surface": "native_2d_formula",
        "capability_flags": ["schema_control_surface"],
        "runtime_flags": ["escape_time"],
        "description_status": status,
        "description": description,
    }


class FractalDescriptiveCatalogTests(unittest.TestCase):
    def _runtime(self, root: Path, entries: list[dict[str, object]]) -> tuple[Path, Path]:
        runtime = root / "runtime"
        runtime.mkdir()
        command = runtime / "fractal_ui.cmd"
        command.write_text(
            "@echo off\n"
            'if /I "%1"=="--describe-fractal-catalog-json" (\n'
            '  copy /y "%~dp0catalog.fixture.json" "%~2" >nul\n'
            "  exit /b 0\n"
            ")\n"
            "exit /b 2\n",
            encoding="utf-8",
        )
        (runtime / "fractal_ui_active.txt").write_text("fractal_ui.exe\n", encoding="utf-8")
        (runtime / "fractal_ui.exe").write_bytes(b"engine-one")
        catalog_path = runtime / "catalog.fixture.json"
        catalog_path.write_text(
            json.dumps({"schema_version": 1, "entries": entries}, separators=(",", ":")),
            encoding="utf-8",
        )
        return command, catalog_path

    def test_loads_reviewed_entry_and_caches_exact_bytes_by_runtime_and_catalog_hash(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            command, fixture = self._runtime(
                root,
                [_entry("explaino_all"), _entry("newton", "unavailable")],
            )
            result = load_selected_fractal_description(
                command,
                root / "workspace",
                "explaino_all",
                "a" * 64,
            )
            expected_hash = hashlib.sha256(fixture.read_bytes()).hexdigest()
            self.assertEqual(result.catalog_sha256, expected_hash)
            self.assertEqual(result.entry["selector_id"], "explaino_all")
            self.assertEqual(result.entry["description_status"], "reviewed")
            self.assertEqual(result.cache_path.read_bytes(), fixture.read_bytes())
            self.assertEqual(
                result.cache_path,
                (
                    root
                    / "workspace"
                    / "cache"
                    / "fractal-descriptive-catalog-v1"
                    / ("a" * 64)
                    / expected_hash
                    / "catalog.json"
                ).resolve(),
            )

    def test_valid_unavailable_entry_fails_soft(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            command, _ = self._runtime(root, [_entry("newton", "unavailable")])
            result = load_selected_fractal_description(command, root / "workspace", "newton", "b" * 64)
            self.assertEqual(result.entry["description_status"], "unavailable")
            self.assertIsNone(result.entry["description"])

    def test_duplicate_selector_and_missing_selected_identity_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            command, catalog_path = self._runtime(root, [_entry("explaino_all"), _entry("explaino_all")])
            with self.assertRaisesRegex(ValueError, "duplicate selector_id"):
                load_selected_fractal_description(command, root / "workspace", "explaino_all", "c" * 64)
            catalog_path.write_text(
                json.dumps({"schema_version": 1, "entries": [_entry("newton", "unavailable")]}),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "does not contain selected selector"):
                load_selected_fractal_description(command, root / "workspace", "explaino_all", "c" * 64)

    def test_cache_identity_changes_with_runtime_or_catalog_identity(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            command, catalog_path = self._runtime(root, [_entry("explaino_all")])
            first = load_selected_fractal_description(command, root / "workspace", "explaino_all", "d" * 64)
            second = load_selected_fractal_description(command, root / "workspace", "explaino_all", "e" * 64)
            self.assertNotEqual(first.cache_path, second.cache_path)
            catalog_path.write_text(
                json.dumps({"schema_version": 1, "entries": [_entry("explaino_all"), _entry("newton", "unavailable")]}),
                encoding="utf-8",
            )
            third = load_selected_fractal_description(command, root / "workspace", "explaino_all", "e" * 64)
            self.assertNotEqual(second.catalog_sha256, third.catalog_sha256)
            self.assertNotEqual(second.cache_path, third.cache_path)

    def test_loader_has_no_historical_side_folder_fallback(self) -> None:
        source = Path(catalog_module.__file__).read_text(encoding="utf-8").lower()
        self.assertNotIn("salt-output", source)
        self.assertNotIn("fractal_catalog_current", source)

    def test_reviewed_source_refs_must_be_repository_relative(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            invalid = _entry("explaino_all")
            invalid["description"]["source_refs"] = ["../outside.cpp#Symbol"]  # type: ignore[index]
            command, catalog_path = self._runtime(root, [invalid])
            with self.assertRaisesRegex(ValueError, "non-repository-relative source_ref"):
                load_selected_fractal_description(command, root / "workspace", "explaino_all", "f" * 64)

            invalid["description"]["source_refs"] = ["https://example.invalid/source.cpp"]  # type: ignore[index]
            catalog_path.write_text(
                json.dumps({"schema_version": 1, "entries": [invalid]}),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "non-repository-relative source_ref"):
                load_selected_fractal_description(command, root / "workspace", "explaino_all", "f" * 64)


if __name__ == "__main__":
    unittest.main()
