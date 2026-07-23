from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from cuda_fractal_state_tool.agent_bundle import (
    derive_state_override_authoring_surface,
    serialize_state_override_authoring_surface,
)
from cuda_fractal_state_tool.state_override import materialize_state_override, parse_state_override
from cuda_fractal_state_tool.state_override_cli import main as state_override_cli_main


def _json_bytes(value: object, *, sort_keys: bool = False) -> bytes:
    return (
        json.dumps(value, indent=2, sort_keys=sort_keys, ensure_ascii=False, allow_nan=False) + "\n"
    ).encode("utf-8")


class StateOverrideTests(unittest.TestCase):
    def _packet(self, root: Path) -> tuple[Path, dict, dict, dict]:
        packet = root / "packet"
        packet.mkdir()
        state = {
            "state_version": 3,
            "fractal_type": "explaino_all",
            "view": {
                "center_x": -0.5,
                "center_hp_x": -0.5,
                "center_y": 0.0,
                "center_hp_y": 0.0,
                "zoom": 4.0,
                "log2_zoom": 2.0,
            },
            "params": {
                "explaino_damping": 1.0,
                "mode": "normal",
                "feature_enabled": False,
                "read_only_but_present": 7,
            },
            "render": {"width": 640, "height": 480},
            "color_pipeline_draft": {
                "next_row_id": 5,
                "lanes": [
                    {
                        "lane_id": "source",
                        "label": "Source",
                        "rows": [
                            {
                                "ui_row_id": 1,
                                "enabled": True,
                                "function_id": "identity",
                                "parameter_values": [],
                            }
                        ],
                    },
                    {
                        "lane_id": "shape",
                        "label": "Shape",
                        "rows": [
                            {
                                "ui_row_id": 2,
                                "enabled": True,
                                "function_id": "identity",
                                "parameter_values": [],
                            }
                        ],
                    },
                    {
                        "lane_id": "palette",
                        "label": "Palette",
                        "rows": [
                            {
                                "ui_row_id": 3,
                                "enabled": True,
                                "function_id": "heatmap",
                                "parameter_values": [
                                    {
                                        "path": "palette.blend_mode",
                                        "type": "enum",
                                        "enum_value": "normal",
                                    }
                                ],
                            }
                        ],
                    },
                    {
                        "lane_id": "grading",
                        "label": "Grading",
                        "rows": [
                            {
                                "ui_row_id": 4,
                                "enabled": True,
                                "function_id": "contrast_lift",
                                "parameter_values": [
                                    {"path": "grade.exposure", "type": "float", "number_value": 1.0},
                                    {"path": "grade.saturation", "type": "float", "number_value": 1.0},
                                ],
                            }
                        ],
                    },
                ],
            },
        }
        schema = {
            "schema_version": 1,
            "panels": [
                {
                    "id": "fractal",
                    "controls": [
                        {
                            "id": "explaino_damping",
                            "value_type": "float",
                            "min": 0.01,
                            "max": 2.0,
                            "binding": {"kind": "param", "path": "fractal.params.explaino_damping"},
                        },
                        {
                            "id": "mode",
                            "value_type": "enum",
                            "options": [{"id": "normal"}, {"id": "alternate"}],
                            "binding": {"kind": "param", "path": "fractal.params.mode"},
                        },
                        {
                            "id": "feature_enabled",
                            "value_type": "bool",
                            "binding": {"kind": "param", "path": "fractal.params.feature_enabled"},
                        },
                        {
                            "id": "center_x",
                            "value_type": "float",
                            "binding": {"kind": "param", "path": "fractal.view.center_x"},
                        },
                        {
                            "id": "center_y",
                            "value_type": "float",
                            "binding": {"kind": "param", "path": "fractal.view.center_y"},
                        },
                        {
                            "id": "zoom",
                            "value_type": "float",
                            "min": 0.000001,
                            "binding": {"kind": "param", "path": "fractal.view.zoom"},
                        },
                    ]
                }
            ],
        }
        surface = {
            "version": 1,
            "lanes": [
                {
                    "fractal_id": "explaino_all",
                    "controls": [
                        {
                            "control_id": "explaino_damping",
                            "binding_path": "fractal.params.explaino_damping",
                            "binding_resolves": True,
                            "state_io_key": "explaino_damping",
                            "default_visible": True,
                        },
                        {
                            "control_id": "mode",
                            "binding_path": "fractal.params.mode",
                            "binding_resolves": True,
                            "state_io_key": "mode",
                            "default_visible": True,
                        },
                        {
                            "control_id": "feature_enabled",
                            "binding_path": "fractal.params.feature_enabled",
                            "binding_resolves": True,
                            "state_io_key": "feature_enabled",
                            "default_visible": True,
                        },
                    ],
                }
            ],
        }
        contract = {
            "schema_version": 1,
            "function_library": {
                "lanes": [
                    {"id": lane, "functions": [{"id": "identity", "params": []}]}
                    for lane in ("source", "shape")
                ]
                + [
                    {
                        "id": "palette",
                        "functions": [
                            {"id": "identity", "params": []},
                            {
                                "id": "heatmap",
                                "params": [
                                    {
                                        "path": "palette.blend_mode",
                                        "type": "enum",
                                        "options": ["normal", "multiply"],
                                    }
                                ],
                            },
                        ],
                    },
                    {
                        "id": "grading",
                        "functions": [
                            {"id": "identity", "params": []},
                            {
                                "id": "contrast_lift",
                                "params": [
                                    {
                                        "path": "grade.exposure",
                                        "type": "float",
                                        "min": 0.1,
                                        "max": 3.0,
                                    },
                                    {
                                        "path": "grade.saturation",
                                        "type": "float",
                                        "min": 0.0,
                                        "max": 2.0,
                                    },
                                ],
                            },
                        ],
                    }
                ]
            },
        }
        self._write_packet(packet, state, surface, schema, contract)
        return packet, state, surface, schema

    def _write_packet(self, packet: Path, state: dict, surface: dict, schema: dict, contract: dict) -> None:
        state_bytes = json.dumps(state, indent=4, ensure_ascii=False).replace("\n", "\r\n").encode("utf-8") + b"\r\n"
        surface_bytes = _json_bytes(surface)
        schema_bytes = _json_bytes(schema)
        authoring = derive_state_override_authoring_surface(state_bytes, surface_bytes, schema_bytes)
        files = {
            "packet.md": b"# fixture packet\n",
            "state.json": state_bytes,
            "fractal-parameter-surface.json": surface_bytes,
            "fractal_binding_surface_v1.ui_schema.json": schema_bytes,
            "color_pipeline_function_library.contract.v1.json": _json_bytes(contract),
            "state-override-authoring-surface.json": serialize_state_override_authoring_surface(authoring),
        }
        for name, payload in files.items():
            (packet / name).write_bytes(payload)
        required = [name for name in files if name != "packet.md"]
        manifest = {
            "bundle_manifest_version": 2,
            "packet_version": 6,
            "required_attachments": required,
            "recommended_attachments": [],
            "unavailable_optional_attachments": [],
            "files": [
                {
                    "path": name,
                    "role": "test_fixture",
                    "sha256": hashlib.sha256(payload).hexdigest(),
                    "size_bytes": len(payload),
                    "web_handoff": "index" if name == "packet.md" else "required",
                }
                for name, payload in files.items()
            ],
        }
        (packet / "manifest.json").write_bytes(_json_bytes(manifest, sort_keys=True))

    def _pipeline_override(self, state: dict) -> dict:
        return {"color_pipeline_draft": {"lanes": json.loads(json.dumps(state["color_pipeline_draft"]["lanes"]))}}

    def test_parser_rejects_duplicates_nonfinite_null_envelopes_and_non_objects(self) -> None:
        invalid = [
            '{"params":{"x":1,"x":2}}',
            '{"params":{"x":NaN}}',
            '{"params":{"x":Infinity}}',
            '{"params":{"x":null}}',
            '{"proposal_version":1}',
            '{"state_version":3}',
            '{"fractal_type":"multibrot"}',
            '{"render":{}}',
            '{"lens":{}}',
            '{"stats":{}}',
            '[]',
            '{"params":1}',
        ]
        for text in invalid:
            with self.subTest(text=text), self.assertRaises(ValueError):
                parse_state_override(text)

    def test_empty_override_copies_exact_base_bytes_and_hash(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            packet, _, _, _ = self._packet(Path(temp_dir))
            output = Path(temp_dir) / "candidate.json"
            result = materialize_state_override(packet, "{ }\r\n", output)
            base_bytes = (packet / "state.json").read_bytes()
            self.assertEqual(output.read_bytes(), base_bytes)
            self.assertTrue(result.empty_override_byte_exact)
            self.assertEqual(result.base_state_sha256, result.merged_candidate_sha256)
            self.assertEqual(result.changed_paths, ())

    def test_nonempty_scalar_merge_is_deterministic_and_preserves_base_order(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            packet, _, _, _ = self._packet(Path(temp_dir))
            output = Path(temp_dir) / "candidate.json"
            override = '{\n  "params": {\n    "explaino_damping": 0.9\n  }\n}\n'
            base_bytes = (packet / "state.json").read_bytes()
            result = materialize_state_override(packet, override, output)
            payload = output.read_bytes()
            self.assertFalse(result.empty_override_byte_exact)
            self.assertFalse(payload.startswith(b"\xef\xbb\xbf"))
            self.assertNotIn(b"\r", payload)
            self.assertTrue(payload.endswith(b"\n"))
            self.assertFalse(payload.endswith(b"\n\n"))
            merged = json.loads(payload)
            self.assertEqual(list(merged), ["state_version", "fractal_type", "view", "params", "render", "color_pipeline_draft"])
            self.assertEqual(merged["params"]["explaino_damping"], 0.9)
            self.assertEqual((packet / "state.json").read_bytes(), base_bytes)
            self.assertEqual(result.requested_paths, ("params.explaino_damping",))
            self.assertEqual([change.path for change in result.changed_paths], ["params.explaino_damping"])
            self.assertEqual(result.conceptual_domains, ("params.explaino_damping",))
            self.assertEqual(result.override_text_sha256, hashlib.sha256(override.encode()).hexdigest())

            second = Path(temp_dir) / "candidate-two.json"
            second_result = materialize_state_override(packet, override, second)
            self.assertEqual(second.read_bytes(), payload)
            self.assertEqual(second_result.merged_candidate_sha256, result.merged_candidate_sha256)

    def test_same_value_nonempty_override_uses_documented_serializer(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            packet, _, _, _ = self._packet(Path(temp_dir))
            output = Path(temp_dir) / "candidate.json"
            result = materialize_state_override(packet, '{"params":{"explaino_damping":1.0}}', output)
            self.assertFalse(result.empty_override_byte_exact)
            self.assertNotEqual(output.read_bytes(), (packet / "state.json").read_bytes())
            self.assertEqual(result.changed_paths, ())

    def test_params_reject_unknown_read_only_bad_types_ranges_and_enums(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            packet, _, _, _ = self._packet(Path(temp_dir))
            cases = {
                "unknown": '{"params":{"missing":1}}',
                "read-only": '{"params":{"read_only_but_present":8}}',
                "range": '{"params":{"explaino_damping":4.0}}',
                "numeric-type": '{"params":{"explaino_damping":true}}',
                "enum": '{"params":{"mode":"unknown"}}',
                "bool": '{"params":{"feature_enabled":1}}',
                "absent-nested": '{"params":{"missing":{"value":1}}}',
            }
            for label, text in cases.items():
                with self.subTest(label=label), self.assertRaises(ValueError):
                    materialize_state_override(packet, text, Path(temp_dir) / f"{label}.json")

    def test_camera_companions_are_pair_only_and_one_conceptual_edit(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            packet, _, _, _ = self._packet(Path(temp_dir))
            invalid = [
                '{"view":{"center_x":-0.4}}',
                '{"view":{"center_hp_x":-0.4}}',
                '{"view":{"zoom":8.0}}',
                '{"view":{"log2_zoom":3.0}}',
                '{"view":{"zoom":0.0,"log2_zoom":0.0}}',
                '{"view":{"center_x":-0.4,"center_hp_x":"-0.4"}}',
            ]
            for index, text in enumerate(invalid):
                with self.subTest(index=index), self.assertRaises(ValueError):
                    materialize_state_override(packet, text, Path(temp_dir) / f"bad-{index}.json")

            result = materialize_state_override(
                packet,
                '{"view":{"center_x":-0.4,"center_hp_x":-0.40000000000000002}}',
                Path(temp_dir) / "camera.json",
            )
            self.assertEqual(result.camera_edits, ("view.center_x",))
            self.assertEqual(result.conceptual_domains, ("view.center_x",))
            self.assertEqual(len(result.changed_paths), 2)

    def test_pipeline_draft_authoring_uses_copied_contract_and_preserves_topology(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            packet, state, _, _ = self._packet(Path(temp_dir))
            override = self._pipeline_override(state)
            grading = override["color_pipeline_draft"]["lanes"][3]["rows"][0]
            grading["parameter_values"][1]["number_value"] = 1.5
            output = Path(temp_dir) / "pipeline.json"
            result = materialize_state_override(packet, json.dumps(override), output)
            merged = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(
                merged["color_pipeline_draft"]["lanes"][3]["rows"][0]["parameter_values"][1]["number_value"],
                1.5,
            )
            self.assertIn("color_pipeline_draft", result.conceptual_domains)

            unchanged = self._pipeline_override(state)
            with self.assertRaisesRegex(ValueError, "must change at least one"):
                materialize_state_override(
                    packet,
                    json.dumps(unchanged),
                    Path(temp_dir) / "unchanged-pipeline.json",
                )

            topology_changes = []
            changed_label = self._pipeline_override(state)
            changed_label["color_pipeline_draft"]["lanes"][0]["label"] = "Changed"
            topology_changes.append(changed_label)
            changed_row_id = self._pipeline_override(state)
            changed_row_id["color_pipeline_draft"]["lanes"][0]["rows"][0]["ui_row_id"] = 99
            topology_changes.append(changed_row_id)
            changed_enablement = self._pipeline_override(state)
            changed_enablement["color_pipeline_draft"]["lanes"][0]["rows"][0]["enabled"] = False
            topology_changes.append(changed_enablement)
            added_row = self._pipeline_override(state)
            added_row["color_pipeline_draft"]["lanes"][0]["rows"].append(
                json.loads(json.dumps(added_row["color_pipeline_draft"]["lanes"][0]["rows"][0]))
            )
            topology_changes.append(added_row)
            for index, invalid in enumerate(topology_changes):
                with self.subTest(index=index), self.assertRaisesRegex(ValueError, "topology"):
                    materialize_state_override(
                        packet,
                        json.dumps(invalid),
                        Path(temp_dir) / f"bad-topology-{index}.json",
                    )

            wrong_parameters = self._pipeline_override(state)
            wrong_parameters["color_pipeline_draft"]["lanes"][3]["rows"][0]["parameter_values"].reverse()
            with self.assertRaisesRegex(ValueError, "contract order"):
                materialize_state_override(
                    packet,
                    json.dumps(wrong_parameters),
                    Path(temp_dir) / "bad-parameters.json",
                )

    def test_copied_schema_change_changes_validation_without_python_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            packet, state, surface, schema = self._packet(Path(temp_dir))
            output = Path(temp_dir) / "accepted.json"
            materialize_state_override(packet, '{"params":{"explaino_damping":1.5}}', output)

            schema["panels"][0]["controls"][0]["max"] = 1.0
            contract = json.loads((packet / "color_pipeline_function_library.contract.v1.json").read_text())
            self._write_packet(packet, state, surface, schema, contract)
            with self.assertRaisesRegex(ValueError, "deployed maximum"):
                materialize_state_override(
                    packet,
                    '{"params":{"explaino_damping":1.5}}',
                    Path(temp_dir) / "rejected.json",
                )

    def test_manifest_binding_and_candidate_target_are_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            packet, _, _, _ = self._packet(Path(temp_dir))
            actual_hash = hashlib.sha256((packet / "manifest.json").read_bytes()).hexdigest()
            materialize_state_override(
                packet,
                "{}",
                Path(temp_dir) / "ok.json",
                expected_manifest_sha256=actual_hash,
            )
            with self.assertRaisesRegex(ValueError, "manifest hash"):
                materialize_state_override(
                    packet,
                    "{}",
                    Path(temp_dir) / "bad.json",
                    expected_manifest_sha256="0" * 64,
                )
            with self.assertRaisesRegex(ValueError, "immutable agent-packet"):
                materialize_state_override(packet, "{}", packet / "state.json")
            with self.assertRaisesRegex(ValueError, "immutable agent-packet"):
                materialize_state_override(packet, "{}", packet / "new-candidate.json")

    def test_older_unsafe_authoring_surface_requires_packet_rebuild(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            packet, _, _, _ = self._packet(Path(temp_dir))
            surface_path = packet / "state-override-authoring-surface.json"
            surface = json.loads(surface_path.read_text(encoding="utf-8"))
            surface["surface_version"] = 1
            surface_bytes = _json_bytes(surface)
            surface_path.write_bytes(surface_bytes)

            manifest_path = packet / "manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            record = next(
                item
                for item in manifest["files"]
                if item["path"] == "state-override-authoring-surface.json"
            )
            record["sha256"] = hashlib.sha256(surface_bytes).hexdigest()
            record["size_bytes"] = len(surface_bytes)
            manifest_path.write_bytes(_json_bytes(manifest, sort_keys=True))

            with self.assertRaisesRegex(ValueError, "unsafe or unsupported version; rebuild"):
                materialize_state_override(
                    packet,
                    '{"params":{"explaino_damping":0.9}}',
                    Path(temp_dir) / "candidate.json",
                )

    def test_cli_emits_changed_path_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            packet, _, _, _ = self._packet(root)
            override_path = root / "override.json"
            override_path.write_text('{"params":{"mode":"alternate"}}\n', encoding="utf-8")
            output = root / "candidate.json"
            stdout = StringIO()
            with redirect_stdout(stdout):
                code = state_override_cli_main(
                    [
                        "--packet-dir",
                        str(packet),
                        "--override",
                        str(override_path),
                        "--out",
                        str(output),
                    ]
                )
            self.assertEqual(code, 0)
            payload = json.loads(stdout.getvalue())
            self.assertEqual(payload["status"], "override_accepted")
            self.assertEqual(payload["changed_paths"][0]["path"], "params.mode")
            self.assertTrue(output.is_file())

    def test_cli_rejection_is_structured_and_does_not_write_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            packet, _, _, _ = self._packet(root)
            override_path = root / "override.json"
            override_path.write_text('{"params":{"missing":1}}\n', encoding="utf-8")
            output = root / "candidate.json"
            stdout = StringIO()
            with redirect_stdout(stdout):
                code = state_override_cli_main(
                    [
                        "--packet-dir",
                        str(packet),
                        "--override",
                        str(override_path),
                        "--out",
                        str(output),
                    ]
                )
            self.assertEqual(code, 2)
            payload = json.loads(stdout.getvalue())
            self.assertEqual(payload["status"], "override_rejected")
            self.assertIn("absent from the base state", payload["error"])
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
