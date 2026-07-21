from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from cuda_fractal_state_tool.finding_workspace import (
    SourceCaptureImporter,
    build_validation_run_id,
    compute_finding_id,
    compute_proposal_id,
)
from cuda_fractal_state_tool.proposal import parse_proposal_v1
from cuda_fractal_state_tool.workspace_layout import WORKSPACE_MARKER_FILENAME, initialize_workspace_root


def _write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _snapshot_tree(root: Path) -> dict[str, dict[str, object]]:
    snapshot: dict[str, dict[str, object]] = {}
    for path in sorted(root.rglob("*")):
        rel = str(path.relative_to(root)).replace("\\", "/")
        stat = path.stat()
        if path.is_dir():
            snapshot[rel] = {
                "kind": "dir",
                "mode": stat.st_mode,
                "mtime_ns": stat.st_mtime_ns,
            }
        else:
            snapshot[rel] = {
                "kind": "file",
                "mode": stat.st_mode,
                "mtime_ns": stat.st_mtime_ns,
                "size": stat.st_size,
                "content": path.read_bytes(),
            }
    return snapshot


class FindingWorkspaceTests(unittest.TestCase):
    def test_initialize_workspace_root_rejects_nonempty_unrecognized_root(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "workspace"
            root.mkdir(parents=True, exist_ok=True)
            (root / "unexpected.txt").write_text("x", encoding="utf-8")
            with self.assertRaises(ValueError):
                initialize_workspace_root(root)

    def test_initialize_workspace_root_creates_marker(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "workspace"
            marker = initialize_workspace_root(root)
            self.assertEqual(marker.name, WORKSPACE_MARKER_FILENAME)
            payload = json.loads(marker.read_text(encoding="utf-8"))
            self.assertEqual(payload["workspace_schema_version"], 1)

    def test_directory_resolution_fails_closed_on_multiple_state_candidates(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir) / "workspace"
            source_root = Path(temp_dir) / "source"
            _write_json(source_root / "one" / "state.json", {"a": 1})
            _write_json(source_root / "two" / "state.json", {"a": 2})
            importer = SourceCaptureImporter(workspace_root)
            with self.assertRaises(ValueError):
                importer.resolve_capture(source_root)

    def test_import_is_idempotent_for_same_bundle_and_same_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir) / "workspace"
            capture_root = Path(temp_dir) / "capture"
            _write_json(capture_root / "state.json", {"state_version": 3, "params": {"max_iter": 500}})
            (capture_root / "frame.bmp").write_bytes(b"frame-data")

            importer = SourceCaptureImporter(workspace_root)
            first = importer.import_capture(capture_root)
            (first.finding_dir / "proposals" / "keep.txt").write_text("keep", encoding="utf-8")
            second = importer.import_capture(capture_root)

            self.assertEqual(first.finding_id, second.finding_id)
            self.assertTrue((second.finding_dir / "proposals" / "keep.txt").exists())

    def test_import_preserves_optional_review_focused_fractal_state(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir) / "workspace"
            capture_root = Path(temp_dir) / "capture"
            _write_json(capture_root / "state.json", {"state_version": 3, "params": {"max_iter": 500}})
            review_state = {
                "schema_id": "viewer.finding_fractal_state.v1",
                "active_fractal_controls": {"max_iter": 500},
            }
            _write_json(capture_root / "fractal-state.json", review_state)

            imported = SourceCaptureImporter(workspace_root).import_capture(capture_root)
            copied = imported.finding_dir / "source" / "fractal-state.json"
            manifest = json.loads(imported.workspace_manifest_path.read_text(encoding="utf-8"))

            self.assertEqual(json.loads(copied.read_text(encoding="utf-8")), review_state)
            entry = manifest["source_artifacts"]["review_fractal_state"]
            self.assertEqual(entry["workspace_path"], "source/fractal-state.json")
            self.assertEqual(entry["sha256"], hashlib.sha256(copied.read_bytes()).hexdigest())

    def test_import_adds_optional_field_notes_without_rewriting_source(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir) / "workspace"
            capture_root = Path(temp_dir) / "capture"
            _write_json(capture_root / "state.json", {"state_version": 3, "params": {"max_iter": 500}})
            notes_bytes = b"First observation.\r\nSecond observation.\r\n"
            (capture_root / "field-notes.md").write_bytes(notes_bytes)

            imported = SourceCaptureImporter(workspace_root).import_capture(capture_root)
            copied = imported.finding_dir / "source" / "field-notes.md"
            manifest = json.loads(imported.workspace_manifest_path.read_text(encoding="utf-8"))

            self.assertEqual(copied.read_bytes(), notes_bytes)
            self.assertEqual((capture_root / "field-notes.md").read_bytes(), notes_bytes)
            entry = manifest["source_artifacts"]["field_notes"]
            self.assertEqual(entry["workspace_path"], "source/field-notes.md")
            self.assertEqual(entry["sha256"], hashlib.sha256(notes_bytes).hexdigest())

    def test_reimport_from_different_path_updates_aliases_same_finding(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir) / "workspace"
            source_one = Path(temp_dir) / "capture_a"
            source_two = Path(temp_dir) / "capture_b"
            payload = {"state_version": 3, "params": {"max_iter": 500}}
            _write_json(source_one / "state.json", payload)
            _write_json(source_two / "state.json", payload)

            importer = SourceCaptureImporter(workspace_root)
            first = importer.import_capture(source_one)
            second = importer.import_capture(source_two)

            self.assertEqual(first.finding_id, second.finding_id)
            manifest = json.loads(second.workspace_manifest_path.read_text(encoding="utf-8"))
            aliases = manifest.get("source_aliases", [])
            self.assertIn(str(source_one.resolve()), aliases)
            self.assertIn(str(source_two.resolve()), aliases)

    def test_changed_bundle_same_path_creates_new_finding_and_preserves_old(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir) / "workspace"
            capture_root = Path(temp_dir) / "capture"
            _write_json(capture_root / "state.json", {"state_version": 3, "params": {"max_iter": 500}})
            importer = SourceCaptureImporter(workspace_root)
            first = importer.import_capture(capture_root)

            _write_json(capture_root / "state.json", {"state_version": 3, "params": {"max_iter": 700}})
            second = importer.import_capture(capture_root)

            self.assertNotEqual(first.finding_id, second.finding_id)
            self.assertTrue(first.workspace_manifest_path.exists())
            self.assertTrue(second.workspace_manifest_path.exists())

    def test_import_does_not_mutate_source_bundle_contents(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir) / "workspace"
            capture_root = Path(temp_dir) / "capture"
            _write_json(capture_root / "state.json", {"state_version": 3, "params": {"max_iter": 500}})
            _write_json(capture_root / "finding.json", {"note": "meta"})
            (capture_root / "frame.bmp").write_bytes(b"frame-data")

            before = _snapshot_tree(capture_root)
            importer = SourceCaptureImporter(workspace_root)
            importer.import_capture(capture_root)
            after = _snapshot_tree(capture_root)

            self.assertEqual(before.keys(), after.keys())
            for rel in before:
                left = before[rel]
                right = after[rel]
                self.assertEqual(left["kind"], right["kind"])
                self.assertEqual(left["mode"], right["mode"])
                self.assertEqual(left["mtime_ns"], right["mtime_ns"])
                if left["kind"] == "file":
                    self.assertEqual(left["size"], right["size"])
                    self.assertEqual(left["content"], right["content"])

    def test_compute_finding_id_is_path_independent(self) -> None:
        finding_one = compute_finding_id("a", "b", "c")
        finding_two = compute_finding_id("a", "b", "c")
        finding_three = compute_finding_id("a", "b", None)
        self.assertEqual(finding_one, finding_two)
        self.assertNotEqual(finding_one, finding_three)

    def test_proposal_id_is_stable_for_equivalent_validated_overrides(self) -> None:
        text_a = (
            '{"proposal_version": 1, "base_state": {"finding_id": "fid", "sha256": "sha"}, '
            '"overrides": {"params.max_iter": 700, "params.color_signal": "iteration_count", '
            '"params.color_palette": "cyclic_escape", "params.color_grading": "escape_default"}}'
        )
        text_b = (
            '{"proposal_version": 1, "base_state": {"finding_id": "fid", "sha256": "sha"}, '
            '"overrides": {"params.color_palette": "cyclic_escape", "params.color_grading": "escape_default", '
            '"params.color_signal": "iteration_count", "params.max_iter": 700}}'
        )
        proposal_a = parse_proposal_v1(text_a, "fid", "sha")
        proposal_b = parse_proposal_v1(text_b, "fid", "sha")
        id_a = compute_proposal_id(proposal_a, "fid", "sha")
        id_b = compute_proposal_id(proposal_b, "fid", "sha")
        self.assertEqual(id_a, id_b)

    def test_validation_run_ids_are_unique(self) -> None:
        first = build_validation_run_id()
        second = build_validation_run_id()
        self.assertNotEqual(first, second)

    def test_findings_index_is_rebuildable(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir) / "workspace"
            source_root = Path(temp_dir) / "capture"
            _write_json(source_root / "state.json", {"state_version": 3, "params": {"max_iter": 500}})

            importer = SourceCaptureImporter(workspace_root)
            result = importer.import_capture(source_root)
            index_path = result.findings_index_path
            self.assertTrue(index_path.exists())

            index_path.unlink()
            self.assertFalse(index_path.exists())
            rebuilt = importer.rebuild_findings_index()
            self.assertEqual(rebuilt, index_path)
            payload = json.loads(index_path.read_text(encoding="utf-8"))
            entries = payload.get("entries", [])
            self.assertEqual(len(entries), 1)
            self.assertEqual(entries[0]["finding_id"], result.finding_id)


if __name__ == "__main__":
    unittest.main()
