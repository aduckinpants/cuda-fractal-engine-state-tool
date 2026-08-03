from __future__ import annotations

import hashlib
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from cuda_fractal_state_tool.agent_bundle import AgentBundle
from cuda_fractal_state_tool.automated_protocol import ControllerDisposition, SessionBudgets
from cuda_fractal_state_tool.automated_run_store import AutomatedRunStore, RunStoreWriteError
from cuda_fractal_state_tool.automated_session import (
    AutomatedRouteServices,
    AutomatedSessionController,
    create_job_bound_automated_route_services,
    extract_model_gate_proposal,
    extract_sparse_override,
)
from cuda_fractal_state_tool.derived_finding import DerivedFindingPromotion
from cuda_fractal_state_tool.enrichment_disclosure import DisclosureProfile
from cuda_fractal_state_tool.finding_workspace import ImportResult
from cuda_fractal_state_tool.openai_transport import (
    ProviderFailureKind,
    ProviderTransportError,
    TransportTurnResult,
)
from cuda_fractal_state_tool.state_override_proof import StateOverrideProofResult
from cuda_fractal_state_tool.workspace_layout import initialize_workspace_root
from cuda_fractal_state_tool.async_jobs import JobCancelledError


VALID_OVERRIDE_RESPONSE = """Chosen experiment: damping comparison.

Expected effect: a visible stability change.

```json
{
  "params": {
    "explaino_damping": 0.9
  }
}
```
"""


class FakeTransport:
    def __init__(self, responses: list[str]) -> None:
        self.responses = list(responses)
        self.calls: list[dict[str, object]] = []
        self.closed = False

    def send_turn(self, **kwargs) -> TransportTurnResult:
        self.calls.append(kwargs)
        if not self.responses:
            raise AssertionError("Fake transport response script exhausted")
        authorize = kwargs.get("authorize_dispatch")
        if authorize is not None:
            authorize(100)
        number = len(self.calls)
        return TransportTurnResult(
            response_id=f"resp-{number}",
            previous_response_id=kwargs.get("previous_response_id"),
            model="gpt-5.6-test",
            output_text=self.responses.pop(0),
            input_tokens=100,
            output_tokens=20,
            resources=(),
            unavailable_optional_attachments=(),
            requested_model="gpt-5.6",
            cached_input_tokens=40,
            cache_write_tokens=10,
            latency_seconds=1.25,
        )

    def close_owned_files(self, **kwargs) -> None:
        self.closed = True


class ServiceHarness:
    def __init__(self, root: Path, initial: AgentBundle, derived: list[AgentBundle]) -> None:
        self.root = root
        self.initial = initial
        self.all_derived = list(derived)
        self.derived_queue = list(derived)
        self.validation_packets: list[Path] = []
        self.proof_packets: list[Path] = []
        self.promotions = 0

    def validate(self, packet_dir, override_text, output_path, manifest_sha256):
        self.validation_packets.append(packet_dir)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text('{}\n', encoding="utf-8")
        empty = override_text.strip().replace(" ", "").replace("\n", "") == "{}"
        return SimpleNamespace(
            changed_paths=() if empty else (SimpleNamespace(path="params.explaino_damping"),),
            empty_override_byte_exact=empty,
            override_text_sha256=hashlib.sha256(override_text.encode("utf-8")).hexdigest(),
        )

    def proof(self, packet_dir, override_text, manifest_sha256):
        self.proof_packets.append(packet_dir)
        number = len(self.proof_packets)
        proof_dir = self.root / f"proof-{number}"
        proof_dir.mkdir()
        receipt = proof_dir / "receipt.json"
        binding = proof_dir / "binding.json"
        merged = proof_dir / "merged.json"
        receipt.write_text('{}\n', encoding="utf-8")
        binding.write_text('{}\n', encoding="utf-8")
        merged.write_text('{}\n', encoding="utf-8")
        return StateOverrideProofResult(
            status="replay_proven",
            proof_id=f"proof-{number}",
            message="proven",
            proof_dir=proof_dir,
            receipt_path=receipt,
            receipt_sha256=hashlib.sha256(receipt.read_bytes()).hexdigest(),
            binding_sha256=hashlib.sha256(binding.read_bytes()).hexdigest(),
            packet_dir=packet_dir,
            packet_id=packet_dir.name,
            packet_manifest_sha256=manifest_sha256,
            override_text_sha256=hashlib.sha256(override_text.encode("utf-8")).hexdigest(),
            merged_candidate_path=merged,
            merged_candidate_sha256=hashlib.sha256(merged.read_bytes()).hexdigest(),
        )

    def promote(self, proof, packet_dir, promotion_dir):
        self.promotions += 1
        promotion_dir.mkdir(parents=True)
        finding_dir = self.root / f"derived-finding-{self.promotions}"
        finding_dir.mkdir()
        imported = ImportResult(
            finding_id=self.all_derived[self.promotions - 1].finding_id,
            finding_dir=finding_dir,
            workspace_manifest_path=finding_dir / "workspace.json",
            findings_index_path=self.root / "findings_index.json",
            workspace_index_updated=True,
            authoring_base_state_sha256="d" * 64,
        )
        receipt = promotion_dir / "receipt.json"
        receipt.write_text('{}\n', encoding="utf-8")
        return DerivedFindingPromotion(
            promotion_dir=promotion_dir,
            capture_dir=promotion_dir / "capture",
            promotion_receipt_path=receipt,
            import_result=imported,
            source_packet_id=proof.packet_id,
            source_proof_id=proof.proof_id,
        )

    def build_bundle(self, finding_dir):
        return self.derived_queue.pop(0)

    def services(self) -> AutomatedRouteServices:
        return AutomatedRouteServices(
            proof=self.proof,
            promote=self.promote,
            build_bundle=self.build_bundle,
            validate=self.validate,
        )


def _bundle(root: Path, name: str, finding: str, marker: str) -> AgentBundle:
    packet_dir = root / name
    packet_dir.mkdir()
    packet = packet_dir / "packet.md"
    manifest = packet_dir / "manifest.json"
    packet.write_text(f"# {marker}\n", encoding="utf-8")
    manifest.write_text(f'{{"marker":"{marker}"}}\n', encoding="utf-8")
    return AgentBundle(
        packet_version=8,
        packet_id=name,
        packet_dir=packet_dir,
        packet_path=packet,
        packet_sha256=hashlib.sha256(packet.read_bytes()).hexdigest(),
        manifest_path=manifest,
        manifest_sha256=hashlib.sha256(manifest.read_bytes()).hexdigest(),
        finding_id=finding,
        selected_fractal_type="explaino_all",
        required_attachments=("packet.md", "manifest.json"),
        recommended_attachments=(),
        unavailable_optional_attachments=(),
    )


class AutomatedSessionTests(unittest.TestCase):
    def _store(self, root: Path, initial: AgentBundle) -> AutomatedRunStore:
        workspace = root / "workspace"
        initialize_workspace_root(workspace)
        return AutomatedRunStore.create(
            workspace,
            run_id="run-1",
            protocol_snapshot={"schema": "agent_session_protocol.v1"},
            initial_packet={"packet_id": initial.packet_id},
        )

    @staticmethod
    def _round_script(gate: str, override: str = VALID_OVERRIDE_RESPONSE) -> list[str]:
        return [
            override,
            f"Comparison and hostile audit.\nGATE_DECISION: {gate}\n",
        ]

    def test_one_round_pass_keeps_model_gate_distinct_from_controller_disposition(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            initial = _bundle(root, "packet-base", "finding-base", "base")
            derived = _bundle(root, "packet-derived", "finding-derived", "derived")
            services = ServiceHarness(root, initial, [derived])
            transport = FakeTransport(self._round_script("SESSION_PASS"))
            store = self._store(root, initial)
            result = AutomatedSessionController(
                transport=transport,
                run_store=store,
                initial_bundle=initial,
                services=services.services(),
            ).run()

            self.assertEqual(result.disposition, ControllerDisposition.SESSION_PASSED)
            self.assertEqual(result.proven_rounds, 1)
            self.assertEqual(result.current_packet.packet_id, "packet-derived")
            self.assertTrue(transport.closed)
            self.assertEqual(len(transport.calls), 2)
            self.assertEqual(transport.calls[0]["packet_dir"], initial.packet_dir)
            self.assertEqual(transport.calls[1]["packet_dir"], derived.packet_dir)
            self.assertIsNone(transport.calls[0]["previous_response_id"])
            self.assertIsNone(transport.calls[1]["previous_response_id"])
            review_resources = transport.calls[1]["additional_resources"]
            self.assertEqual(
                [resource.role for resource in review_resources],
                ["controller_round_review_ledger", "enrichment_disclosure_manifest"],
            )
            ledger = review_resources[0]
            self.assertEqual(ledger.filename, "round-review-ledger.json")
            self.assertTrue(ledger.local_path.is_file())
            events = store.read_events()
            reviews = [
                event for event in events if event["event_type"] == "review_conversation_started"
            ]
            self.assertEqual(len(reviews), 1)
            self.assertTrue(reviews[0]["payload"]["provider_chain_reset"])
            gate = [event for event in events if event["event_type"] == "model_gate_proposal"][-1]
            disposition = [event for event in events if event["event_type"] == "session_disposition"][-1]
            self.assertEqual(gate["payload"]["model_gate_proposal"], "SESSION_PASS")
            self.assertEqual(disposition["payload"]["disposition"], "SESSION_PASSED")
            responses = [event for event in events if event["event_type"] == "model_response"]
            self.assertEqual(responses[0]["payload"]["requested_model"], "gpt-5.6")
            self.assertEqual(responses[0]["payload"]["resolved_model"], "gpt-5.6-test")
            self.assertEqual(responses[0]["payload"]["cached_input_tokens"], 40)
            self.assertEqual(responses[0]["payload"]["uncached_input_tokens"], 60)
            self.assertEqual(result.usage.cumulative_cached_input_tokens, 80)
            self.assertEqual(result.usage.cumulative_cache_write_tokens, 20)
            self.assertEqual(result.usage.cumulative_uncached_input_tokens, 120)
            self.assertGreater(result.usage.cumulative_calculated_cost_usd, Decimal("0"))
            estimates = [
                event for event in events if event["event_type"] == "provider_dispatch_estimated"
            ]
            self.assertEqual(len(estimates), 2)
            self.assertEqual(
                Decimal(estimates[0]["payload"]["estimate"]["cost_usd"]),
                Decimal("0.720625"),
            )
            self.assertEqual(
                responses[0]["payload"]["calculated_call_cost"]["cache_write_tokens"], 10
            )

    def test_dollar_gate_rejects_before_transport_dispatch(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            initial = _bundle(root, "packet-base", "finding-base", "base")
            transport = FakeTransport([VALID_OVERRIDE_RESPONSE])
            store = self._store(root, initial)
            result = AutomatedSessionController(
                transport=transport,
                run_store=store,
                initial_bundle=initial,
                services=ServiceHarness(root, initial, []).services(),
                budgets=SessionBudgets(maximum_calculated_cost_usd=Decimal("0.42")),
            ).run()
            self.assertEqual(result.disposition, ControllerDisposition.BUDGET_EXHAUSTED)
            self.assertEqual(len(transport.calls), 1)
            self.assertEqual(len(transport.responses), 1)
            self.assertEqual(result.usage.model_responses, 0)
            rejected = [
                event for event in store.read_events() if event["event_type"] == "provider_dispatch_rejected"
            ]
            self.assertEqual(rejected[-1]["payload"]["reason"], "maximum_calculated_cost_usd")
            self.assertEqual(
                Decimal(rejected[-1]["payload"]["estimate"]["cost_usd"]),
                Decimal("0.720625"),
            )

    def test_zero_dollar_budget_stops_before_context_or_provider_work(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            initial = _bundle(root, "packet-base", "finding-base", "base")
            transport = FakeTransport([VALID_OVERRIDE_RESPONSE])
            disclosure_calls = []
            harness = ServiceHarness(root, initial, [])
            services = AutomatedRouteServices(
                proof=harness.proof,
                promote=harness.promote,
                build_bundle=harness.build_bundle,
                validate=harness.validate,
                disclosure=lambda *args: disclosure_calls.append(args),
            )
            result = AutomatedSessionController(
                transport=transport,
                run_store=self._store(root, initial),
                initial_bundle=initial,
                services=services,
                budgets=SessionBudgets(maximum_calculated_cost_usd=Decimal("0")),
                disclosure_profile="assisted",
            ).run()
            self.assertEqual(result.disposition, ControllerDisposition.BUDGET_EXHAUSTED)
            self.assertEqual(transport.calls, [])
            self.assertEqual(disclosure_calls, [])

    def test_break_blind_discloses_only_during_fresh_review(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            initial = _bundle(root, "packet-base", "finding-base", "base")
            controller = AutomatedSessionController(
                transport=FakeTransport([]),
                run_store=self._store(root, initial),
                initial_bundle=initial,
                services=ServiceHarness(root, initial, []).services(),
                disclosure_profile="break_blind",
            )
            self.assertEqual(
                controller._phase_disclosure_profile("author"), DisclosureProfile.BLIND
            )
            self.assertEqual(
                controller._phase_disclosure_profile("review"), DisclosureProfile.BREAK_BLIND
            )

    def test_round_revise_rebinds_second_override_to_preceding_packet(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            initial = _bundle(root, "packet-base", "finding-base", "base")
            first_derived = _bundle(root, "packet-derived-1", "finding-derived-1", "one")
            second_derived = _bundle(root, "packet-derived-2", "finding-derived-2", "two")
            services = ServiceHarness(root, initial, [first_derived, second_derived])
            script = self._round_script("ROUND_REVISE") + self._round_script("SESSION_PASS")
            transport = FakeTransport(script)
            result = AutomatedSessionController(
                transport=transport,
                run_store=self._store(root, initial),
                initial_bundle=initial,
                services=services.services(),
            ).run()

            self.assertEqual(result.disposition, ControllerDisposition.SESSION_PASSED)
            self.assertEqual(result.proven_rounds, 2)
            self.assertEqual(services.proof_packets, [initial.packet_dir, initial.packet_dir])
            self.assertEqual(transport.calls[2]["packet_dir"], initial.packet_dir)
            self.assertIsNone(transport.calls[2]["previous_response_id"])

    def test_round_advance_rebinds_second_override_to_derived_packet(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            initial = _bundle(root, "packet-base", "finding-base", "base")
            first_derived = _bundle(root, "packet-derived-1", "finding-derived-1", "one")
            second_derived = _bundle(root, "packet-derived-2", "finding-derived-2", "two")
            services = ServiceHarness(root, initial, [first_derived, second_derived])
            transport = FakeTransport(
                self._round_script("ROUND_ADVANCE") + self._round_script("SESSION_PASS")
            )
            result = AutomatedSessionController(
                transport=transport,
                run_store=self._store(root, initial),
                initial_bundle=initial,
                services=services.services(),
            ).run()
            self.assertEqual(result.disposition, ControllerDisposition.SESSION_PASSED)
            self.assertEqual(services.proof_packets, [initial.packet_dir, first_derived.packet_dir])

    def test_unintended_noop_gets_one_correction_without_changing_validator_semantics(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            initial = _bundle(root, "packet-base", "finding-base", "base")
            derived = _bundle(root, "packet-derived", "finding-derived", "derived")
            services = ServiceHarness(root, initial, [derived])
            no_op = "```json\n{}\n```"
            script = self._round_script("SESSION_PASS", override=no_op)
            script.insert(1, VALID_OVERRIDE_RESPONSE)
            transport = FakeTransport(script)
            store = self._store(root, initial)
            result = AutomatedSessionController(
                transport=transport,
                run_store=store,
                initial_bundle=initial,
                services=services.services(),
            ).run()
            self.assertEqual(result.disposition, ControllerDisposition.SESSION_PASSED)
            self.assertEqual(len(transport.calls), 3)
            validated = [event for event in store.read_events() if event["event_type"] == "override_validated"]
            self.assertTrue(validated[-1]["payload"]["correction_used"])

    def test_two_invalid_override_attempts_stop_at_manual_review(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            initial = _bundle(root, "packet-base", "finding-base", "base")
            services = ServiceHarness(root, initial, [])
            script = ["no json", "still no json"]
            transport = FakeTransport(script)
            result = AutomatedSessionController(
                transport=transport,
                run_store=self._store(root, initial),
                initial_bundle=initial,
                services=services.services(),
            ).run()
            self.assertEqual(result.disposition, ControllerDisposition.MANUAL_REVIEW_REQUIRED)
            self.assertEqual(services.promotions, 0)

    def test_third_round_request_stops_at_exact_proven_round_budget(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            initial = _bundle(root, "packet-base", "finding-base", "base")
            first_derived = _bundle(root, "packet-derived-1", "finding-derived-1", "one")
            second_derived = _bundle(root, "packet-derived-2", "finding-derived-2", "two")
            services = ServiceHarness(root, initial, [first_derived, second_derived])
            transport = FakeTransport(
                self._round_script("ROUND_ADVANCE") + self._round_script("ROUND_ADVANCE")
            )
            result = AutomatedSessionController(
                transport=transport,
                run_store=self._store(root, initial),
                initial_bundle=initial,
                services=services.services(),
            ).run()
            self.assertEqual(result.disposition, ControllerDisposition.BUDGET_EXHAUSTED)
            self.assertEqual(result.proven_rounds, 2)
            self.assertEqual(len(transport.calls), 4)

    def test_malformed_gate_stops_without_silently_selecting_a_transition(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            initial = _bundle(root, "packet-base", "finding-base", "base")
            derived = _bundle(root, "packet-derived", "finding-derived", "derived")
            services = ServiceHarness(root, initial, [derived])
            script = self._round_script("SESSION_PASS")
            script[-1] = "I think this passes, but I omitted the gate contract."
            result = AutomatedSessionController(
                transport=FakeTransport(script),
                run_store=self._store(root, initial),
                initial_bundle=initial,
                services=services.services(),
            ).run()
            self.assertEqual(result.disposition, ControllerDisposition.MANUAL_REVIEW_REQUIRED)
            self.assertIsNone(result.model_gate_proposal)

    def test_shared_worker_cancellation_never_promotes_a_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            initial = _bundle(root, "packet-base", "finding-base", "base")
            derived = _bundle(root, "packet-derived", "finding-derived", "derived")
            services = ServiceHarness(root, initial, [derived])

            def cancelled_proof(*_args):
                raise JobCancelledError("proof cancelled")

            bound = services.services()
            bound = AutomatedRouteServices(
                proof=cancelled_proof,
                promote=bound.promote,
                build_bundle=bound.build_bundle,
                validate=bound.validate,
            )
            transport = FakeTransport([VALID_OVERRIDE_RESPONSE])
            result = AutomatedSessionController(
                transport=transport,
                run_store=self._store(root, initial),
                initial_bundle=initial,
                services=bound,
            ).run()
            self.assertEqual(result.disposition, ControllerDisposition.CANCELLED)
            self.assertEqual(services.promotions, 0)

    def test_auto_promote_can_stop_at_replay_proof_without_fabricating_acceptance(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            initial = _bundle(root, "packet-base", "finding-base", "base")
            derived = _bundle(root, "packet-derived", "finding-derived", "derived")
            services = ServiceHarness(root, initial, [derived])
            transport = FakeTransport([VALID_OVERRIDE_RESPONSE])
            result = AutomatedSessionController(
                transport=transport,
                run_store=self._store(root, initial),
                initial_bundle=initial,
                services=services.services(),
                auto_promote=False,
            ).run()
            self.assertEqual(result.disposition, ControllerDisposition.MANUAL_REVIEW_REQUIRED)
            self.assertEqual(result.proven_rounds, 1)
            self.assertEqual(services.promotions, 0)

    def test_persistent_run_store_failure_is_not_reported_as_runtime_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            initial = _bundle(root, "packet-base", "finding-base", "base")
            services = ServiceHarness(root, initial, [])
            store = self._store(root, initial)
            original = AutomatedRunStore.record_transition

            def fail_after_author_response(store_self, event_type, payload, projection):
                if event_type == "controller_transition":
                    raise RunStoreWriteError(
                        "ACTIVE_TURN_PROJECTION_WRITE_FAILED_AFTER_EVENT_APPEND",
                        "forced projection failure",
                        event_appended=True,
                        event_sequence=4,
                    )
                return original(store_self, event_type, payload, projection)

            with patch.object(
                AutomatedRunStore,
                "record_transition",
                autospec=True,
                side_effect=fail_after_author_response,
            ):
                result = AutomatedSessionController(
                    transport=FakeTransport([VALID_OVERRIDE_RESPONSE]),
                    run_store=store,
                    initial_bundle=initial,
                    services=services.services(),
                ).run()

            self.assertEqual(result.disposition, ControllerDisposition.RUN_STORE_FAILED)
            self.assertIn("ACTIVE_TURN_PROJECTION_WRITE_FAILED_AFTER_EVENT_APPEND", result.message)
            self.assertEqual(services.proof_packets, [])

    def test_controller_separates_definite_and_ambiguous_provider_failures(self) -> None:
        class FailingTransport(FakeTransport):
            def __init__(self, *, ambiguous: bool) -> None:
                super().__init__([])
                self.ambiguous = ambiguous

            def send_turn(self, **kwargs) -> TransportTurnResult:
                self.calls.append(kwargs)
                raise ProviderTransportError(
                    ProviderFailureKind.TIMEOUT if self.ambiguous else ProviderFailureKind.AUTHENTICATION,
                    "provider failure",
                    remote_completion_ambiguous=self.ambiguous,
                )

        for ambiguous, expected in (
            (False, ControllerDisposition.TRANSPORT_FAILED),
            (True, ControllerDisposition.MANUAL_REVIEW_REQUIRED),
        ):
            with self.subTest(ambiguous=ambiguous), tempfile.TemporaryDirectory() as temp_dir:
                root = Path(temp_dir)
                initial = _bundle(root, "packet-base", "finding-base", "base")
                services = ServiceHarness(root, initial, [])
                transport = FailingTransport(ambiguous=ambiguous)
                result = AutomatedSessionController(
                    transport=transport,
                    run_store=self._store(root, initial),
                    initial_bundle=initial,
                    services=services.services(),
                ).run()
                self.assertEqual(result.disposition, expected)
                self.assertEqual(len(transport.calls), 1)
                self.assertEqual(services.promotions, 0)

    def test_cumulative_token_budget_exhaustion_is_controller_owned(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            initial = _bundle(root, "packet-base", "finding-base", "base")
            services = ServiceHarness(root, initial, [])
            result = AutomatedSessionController(
                transport=FakeTransport(["observation"]),
                run_store=self._store(root, initial),
                initial_bundle=initial,
                services=services.services(),
                budgets=SessionBudgets(
                    maximum_cumulative_input_tokens=50,
                    maximum_cumulative_output_tokens=24_000,
                ),
            ).run()
            self.assertEqual(result.disposition, ControllerDisposition.BUDGET_EXHAUSTED)
            self.assertEqual(result.usage.model_responses, 0)
            self.assertEqual(services.promotions, 0)

    def test_parsers_require_one_json_block_and_one_gate_line(self) -> None:
        parsed = extract_sparse_override(VALID_OVERRIDE_RESPONSE)
        self.assertIn('"explaino_damping": 0.9', parsed)
        with self.assertRaisesRegex(ValueError, "exactly one"):
            extract_sparse_override("```json\n{}\n```\n```text\nextra\n```")
        self.assertEqual(
            extract_model_gate_proposal("done\nGATE_DECISION: SESSION_PASS\n").value,
            "SESSION_PASS",
        )
        with self.assertRaisesRegex(ValueError, "exactly one"):
            extract_model_gate_proposal("SESSION_PASS")
        with self.assertRaisesRegex(ValueError, "exactly one"):
            extract_model_gate_proposal(
                "GATE_DECISION: SESSION_PASS\nThis must not follow the gate.\n"
            )

    def test_production_service_factory_delegates_to_canonical_owners(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            runtime = root / "runtime" / "fractal_ui.cmd"
            runtime.parent.mkdir()
            runtime.write_text("@echo off\n", encoding="utf-8")
            workspace = root / "workspace"
            workspace.mkdir()
            packet = root / "packet"
            finding = root / "finding"
            packet.mkdir()
            finding.mkdir()
            job = SimpleNamespace(job_id="job-1")
            proof_result = SimpleNamespace(status="replay_proven")
            promotion_result = SimpleNamespace(import_result=SimpleNamespace(finding_dir=finding))
            bundle_result = SimpleNamespace(packet_version=8)
            with (
                patch(
                    "cuda_fractal_state_tool.automated_session.execute_state_override_proof",
                    return_value=proof_result,
                ) as proof_owner,
                patch(
                    "cuda_fractal_state_tool.automated_session.promote_replay_proven_candidate",
                    return_value=promotion_result,
                ) as promotion_owner,
                patch(
                    "cuda_fractal_state_tool.automated_session.build_agent_bundle",
                    return_value=bundle_result,
                ) as packet_owner,
            ):
                services = create_job_bound_automated_route_services(
                    runtime_cmd_path=runtime,
                    workspace_root=workspace,
                    job=job,
                    runtime_compatibility_mode="development",
                )
                self.assertIs(services.proof(packet, "{}", "a" * 64), proof_result)
                self.assertIs(services.promote(proof_result, packet, root / "promotion"), promotion_result)
                self.assertIs(services.build_bundle(finding), bundle_result)

            proof_owner.assert_called_once_with(
                packet,
                "{}",
                runtime.resolve(),
                job,
                expected_manifest_sha256="a" * 64,
                runtime_compatibility_mode="development",
            )
            promotion_owner.assert_called_once_with(
                proof=proof_result,
                packet_dir=packet,
                workspace_root=workspace.resolve(),
                promotion_dir=root / "promotion",
            )
            packet_owner.assert_called_once_with(finding, runtime.resolve(), job=job)


if __name__ == "__main__":
    unittest.main()
