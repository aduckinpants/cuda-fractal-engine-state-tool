from __future__ import annotations

import json
import unittest
from pathlib import Path

from cuda_fractal_state_tool.agent_bundle import load_existing_agent_bundle
from cuda_fractal_state_tool.model_qualification import load_qualification_case
from cuda_fractal_state_tool.pricing_policy import load_pricing_policy


class V9PanelContractTests(unittest.TestCase):
    def test_panel_binds_all_seven_historical_packets_and_transcripts_when_available(self) -> None:
        root = Path(__file__).resolve().parents[1]
        panel = json.loads(
            (root / "docs" / "v9_v8_panel_qualification.v1.json").read_text(
                encoding="utf-8"
            )
        )
        fixtures = panel["fixtures"]
        self.assertEqual([item["fixture_id"] for item in fixtures], list("ABCDEFG"))
        self.assertEqual(panel["execution_policy"]["first_fixture"], "A")
        self.assertEqual(panel["execution_policy"]["authorized_fixtures"], list("ABCDEFG"))
        self.assertFalse(panel["execution_policy"]["full_panel_automation_authorized"])
        self.assertFalse(panel["execution_policy"]["bracketed_questions_authorized"])
        self.assertEqual(
            panel["prepared_first_case"]["case_sha256"],
            "7c83fa206468ec14b44bc02b4775700526219bfd89832063242b7852cdaf7d72",
        )
        self.assertEqual(panel["prepared_first_case"]["maximum_cell_cost_usd"], "0.0886872")
        available_packet_dirs = [
            Path(item["packet_dir"]) for item in fixtures if Path(item["packet_dir"]).is_dir()
        ]
        self.assertIn(len(available_packet_dirs), {0, 7})
        for item in fixtures:
            packet_dir = Path(item["packet_dir"])
            self.assertRegex(item["packet_id"], r"^[0-9a-f-]{36}$")
            self.assertRegex(item["finding_id"], r"^[0-9a-f]{64}$")
            self.assertRegex(item["manifest_sha256"], r"^[0-9a-f]{64}$")
            self.assertTrue((root / item["historical_transcript"]).is_file())
            if not packet_dir.is_dir():
                continue
            bundle = load_existing_agent_bundle(packet_dir)
            self.assertEqual(bundle.packet_version, 8)
            self.assertEqual(bundle.packet_id, item["packet_id"])
            self.assertEqual(bundle.finding_id, item["finding_id"])
            self.assertEqual(bundle.manifest_sha256, item["manifest_sha256"])
            self.assertEqual(bundle.selected_fractal_type, item["selector"])

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
            [
                "packet_v8_only",
                "enrichment_only",
                "controller_comparison_only",
                "packet_v8_and_enrichment",
                "packet_v8_and_controller_comparison",
                "all_three",
            ],
        )

    def test_fixture_a_spot_check_case_reopens_against_exact_authority(self) -> None:
        root = Path(__file__).resolve().parents[1]
        case_path = root / "docs" / "v9_v8_fixture_a_luna_high_assisted_case.v1.json"
        serialized = json.loads(case_path.read_text(encoding="utf-8"))
        self.assertEqual(
            serialized["sha256"],
            "7c83fa206468ec14b44bc02b4775700526219bfd89832063242b7852cdaf7d72",
        )
        packet_dir = Path(
            "D:/salt-fractal/cuda-fractal-engine-state-tool/findings/"
            "d0ebae039f19758575fae1407cffa14baadf260f006c047d23a6345dc695e510/"
            "packets/ea1f8e62-a8ff-4b3d-ae0c-ee019e4314d5"
        )
        if not packet_dir.is_dir():
            return
        case = load_qualification_case(
            case_path,
            packet_dir=packet_dir,
            pricing_policy=load_pricing_policy(),
        )
        self.assertEqual(
            case.sha256,
            "7c83fa206468ec14b44bc02b4775700526219bfd89832063242b7852cdaf7d72",
        )
        self.assertEqual(case.expected_analysis_id, "7b0a7eeba2ad7102c9f3b9f82cf57fa31808d5943f28fefb2127f4c446d82fa4")

    def test_fixture_a_live_comparison_ledger_is_bound_and_pending_human_review(self) -> None:
        root = Path(__file__).resolve().parents[1]
        result_root = (
            root
            / "docs"
            / "manual-test-results"
            / "v9_v8_panel_luna_high_assisted_08-03-2026"
        )
        ledger = json.loads(
            (result_root / "Fixture-A-comparison-ledger.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(ledger["fixture_id"], "A")
        self.assertEqual(
            ledger["qualification_case_sha256"],
            "7c83fa206468ec14b44bc02b4775700526219bfd89832063242b7852cdaf7d72",
        )
        self.assertEqual(ledger["cost"]["actual_calculated_usd"], "0.0752966")
        self.assertEqual(ledger["workflow_result"]["proof_status"], "replay_proven")
        self.assertEqual(ledger["workflow_result"]["model_gate"], "ROUND_ADVANCE")
        self.assertEqual(ledger["human_disposition"], "pending")
        support_classes = {item["support_class"] for item in ledger["enrichment_use"]}
        self.assertEqual(
            support_classes,
            {
                "packet_v8_only",
                "enrichment_only",
                "controller_comparison_only",
                "packet_v8_and_enrichment",
                "packet_v8_and_controller_comparison",
            },
        )

        reevaluation = json.loads(
            (result_root / "Fixture-A-gate-reevaluation.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertTrue(reevaluation["original_receipt_preserved"])
        self.assertTrue(reevaluation["automatic_gates_passed"])
        terminal = next(
            item for item in reevaluation["gates"] if item["gate_id"] == "terminal_controller"
        )
        self.assertEqual(
            terminal,
            {
                "gate_id": "terminal_controller",
                "passed": True,
                "detail": "bounded_round_limit_after_ROUND_ADVANCE",
            },
        )

    def test_fixtures_b_and_c_cases_and_result_ledgers_are_exactly_bound(self) -> None:
        root = Path(__file__).resolve().parents[1]
        panel = json.loads(
            (root / "docs" / "v9_v8_panel_qualification.v1.json").read_text(
                encoding="utf-8"
            )
        )
        expected = {
            "B": {
                "case": "docs/v9_v8_fixture_b_luna_high_assisted_case.v1.json",
                "sha256": "8744a3cc7c7308e8bb5a9078803ca9827f78aaee9f150cb1a0c18d1996487379",
                "ceiling": "0.0897892",
                "actual": "0.0758634",
                "packet": Path(panel["fixtures"][1]["packet_dir"]),
            },
            "C": {
                "case": "docs/v9_v8_fixture_c_luna_high_assisted_case.v1.json",
                "sha256": "f0da6ce081b145419f2f0000fa5e9408656ae41a3602bebb6285c4977756db96",
                "ceiling": "0.0891732",
                "actual": "0.0753274",
                "packet": Path(panel["fixtures"][2]["packet_dir"]),
            },
        }
        prepared = {item["fixture_id"]: item for item in panel["prepared_next_cases"]}
        result_root = (
            root
            / "docs"
            / "manual-test-results"
            / "v9_v8_panel_luna_high_assisted_08-03-2026"
        )
        for fixture_id, values in expected.items():
            self.assertEqual(prepared[fixture_id]["case_sha256"], values["sha256"])
            self.assertEqual(prepared[fixture_id]["maximum_cell_cost_usd"], values["ceiling"])
            case_payload = json.loads((root / values["case"]).read_text(encoding="utf-8"))
            self.assertEqual(case_payload["sha256"], values["sha256"])
            self.assertEqual(
                case_payload["budgets"]["maximum_calculated_cost_usd"],
                values["ceiling"],
            )
            if values["packet"].is_dir():
                case = load_qualification_case(
                    root / values["case"],
                    packet_dir=values["packet"],
                    pricing_policy=load_pricing_policy(),
                )
                self.assertEqual(case.sha256, values["sha256"])
            ledger = json.loads(
                (result_root / f"Fixture-{fixture_id}-comparison-ledger.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(ledger["qualification_case_sha256"], values["sha256"])
            self.assertEqual(ledger["cost"]["actual_calculated_usd"], values["actual"])
            self.assertEqual(ledger["workflow_result"]["proof_status"], "replay_proven")
            self.assertEqual(ledger["workflow_result"]["model_gate"], "ROUND_ADVANCE")
            self.assertEqual(ledger["human_disposition"], "pending")

    def test_fixtures_d_through_g_cases_reopen_against_exact_authority(self) -> None:
        root = Path(__file__).resolve().parents[1]
        panel = json.loads(
            (root / "docs" / "v9_v8_panel_qualification.v1.json").read_text(
                encoding="utf-8"
            )
        )
        expected = {
            "D": ("2414489f4fe0eee1a7e0a1ede78b0b0551c37e62fe1941aaaa113746931d4f35", "0.088836"),
            "E": ("942cc72cd918f51c4a32752ff389b0a6b364689a9ff0fab71d6b54dfa0367ecd", "0.087936"),
            "F": ("9c7bdf4da7bdc84ad85ce6bdd3e1dc526f377c03201a4ec233f827ef4fb06847", "0.0883194"),
            "G": ("ba6a9bd1ca3c9c04cf0da5a2e48475831d9909cb81c6d602d3c5d56353b14e93", "0.0884228"),
        }
        prepared = {item["fixture_id"]: item for item in panel["prepared_next_cases"]}
        fixtures = {item["fixture_id"]: item for item in panel["fixtures"]}
        for fixture_id, (case_sha256, ceiling) in expected.items():
            item = prepared[fixture_id]
            self.assertEqual(item["case_sha256"], case_sha256)
            self.assertEqual(item["maximum_cell_cost_usd"], ceiling)
            case_path = root / item["case_path"]
            payload = json.loads(case_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["sha256"], case_sha256)
            self.assertEqual(payload["budgets"]["maximum_calculated_cost_usd"], ceiling)
            packet_dir = Path(fixtures[fixture_id]["packet_dir"])
            if packet_dir.is_dir():
                case = load_qualification_case(
                    case_path,
                    packet_dir=packet_dir,
                    pricing_policy=load_pricing_policy(),
                )
                self.assertEqual(case.sha256, case_sha256)

    def test_fixtures_d_through_f_result_ledgers_preserve_pass_and_failure(self) -> None:
        root = Path(__file__).resolve().parents[1]
        result_root = (
            root
            / "docs"
            / "manual-test-results"
            / "v9_v8_panel_luna_high_assisted_08-03-2026"
        )
        expected = {
            "D": ("0.0758272", "replay_proven", "ROUND_ADVANCE", "BUDGET_EXHAUSTED"),
            "E": ("0.0733474", "replay_proven", "ROUND_ADVANCE", "BUDGET_EXHAUSTED"),
            "F": ("0.0373346", "rejected", "not_reached", "PROOF_FAILED"),
        }
        for fixture_id, values in expected.items():
            ledger = json.loads(
                (result_root / f"Fixture-{fixture_id}-comparison-ledger.json").read_text(
                    encoding="utf-8"
                )
            )
            actual_cost, proof_status, model_gate, controller_disposition = values
            self.assertEqual(ledger["cost"]["actual_calculated_usd"], actual_cost)
            self.assertEqual(ledger["workflow_result"]["proof_status"], proof_status)
            self.assertEqual(ledger["workflow_result"]["model_gate"], model_gate)
            self.assertEqual(
                ledger["workflow_result"]["controller_disposition"],
                controller_disposition,
            )
            self.assertEqual(ledger["human_disposition"], "pending")


if __name__ == "__main__":
    unittest.main()
