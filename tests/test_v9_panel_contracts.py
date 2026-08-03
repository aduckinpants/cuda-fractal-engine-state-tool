from __future__ import annotations

import json
import unittest
from pathlib import Path

from cuda_fractal_state_tool.agent_bundle import load_existing_agent_bundle
from cuda_fractal_state_tool.model_qualification import load_qualification_case
from cuda_fractal_state_tool.pricing_policy import load_pricing_policy


class V9PanelContractTests(unittest.TestCase):
    def test_panel_binds_all_seven_historical_packets_and_transcripts(self) -> None:
        root = Path(__file__).resolve().parents[1]
        panel = json.loads(
            (root / "docs" / "v9_v8_panel_qualification.v1.json").read_text(
                encoding="utf-8"
            )
        )
        fixtures = panel["fixtures"]
        self.assertEqual([item["fixture_id"] for item in fixtures], list("ABCDEFG"))
        self.assertEqual(panel["execution_policy"]["first_fixture"], "A")
        self.assertFalse(panel["execution_policy"]["full_panel_automation_authorized"])
        self.assertFalse(panel["execution_policy"]["bracketed_questions_authorized"])
        self.assertEqual(
            panel["prepared_first_case"]["case_sha256"],
            "4ecddf7109ecedb23fc5573e7b7aa9f33ac13ebc6222a145f05a19a187f8b2f2",
        )
        self.assertEqual(panel["prepared_first_case"]["maximum_cell_cost_usd"], "0.0886872")
        for item in fixtures:
            bundle = load_existing_agent_bundle(Path(item["packet_dir"]))
            self.assertEqual(bundle.packet_version, 8)
            self.assertEqual(bundle.packet_id, item["packet_id"])
            self.assertEqual(bundle.finding_id, item["finding_id"])
            self.assertEqual(bundle.manifest_sha256, item["manifest_sha256"])
            self.assertEqual(bundle.selected_fractal_type, item["selector"])
            self.assertTrue((root / item["historical_transcript"]).is_file())

    def test_comparison_ledger_requires_explicit_enrichment_attribution(self) -> None:
        root = Path(__file__).resolve().parents[1]
        schema = json.loads(
            (root / "docs" / "v9_v8_panel_comparison_ledger.schema.v1.json").read_text(
                encoding="utf-8"
            )
        )
        required = set(schema["required"])
        self.assertIn("historical_comparison", required)
        self.assertIn("enrichment_use", required)
        support_values = schema["properties"]["enrichment_use"]["items"]["properties"][
            "support_class"
        ]["enum"]
        self.assertEqual(
            support_values,
            ["packet_v8_only", "enrichment_only", "packet_v8_and_enrichment"],
        )

    def test_fixture_a_spot_check_case_reopens_against_exact_authority(self) -> None:
        root = Path(__file__).resolve().parents[1]
        case = load_qualification_case(
            root / "docs" / "v9_v8_fixture_a_luna_high_assisted_case.v1.json",
            packet_dir=Path(
                "D:/salt-fractal/cuda-fractal-engine-state-tool/findings/"
                "d0ebae039f19758575fae1407cffa14baadf260f006c047d23a6345dc695e510/"
                "packets/ea1f8e62-a8ff-4b3d-ae0c-ee019e4314d5"
            ),
            pricing_policy=load_pricing_policy(),
        )
        self.assertEqual(
            case.sha256,
            "4ecddf7109ecedb23fc5573e7b7aa9f33ac13ebc6222a145f05a19a187f8b2f2",
        )
        self.assertEqual(case.expected_analysis_id, "7b0a7eeba2ad7102c9f3b9f82cf57fa31808d5943f28fefb2127f4c446d82fa4")


if __name__ == "__main__":
    unittest.main()
