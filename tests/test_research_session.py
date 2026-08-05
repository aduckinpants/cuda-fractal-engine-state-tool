from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from cuda_fractal_state_tool.agent_bundle import AgentBundle
from cuda_fractal_state_tool.research_protocol import ResearchBrief
from cuda_fractal_state_tool.research_run_store import ResearchRunStore
from cuda_fractal_state_tool.research_session import (
    ResearchRouteServices,
    ResearchSessionController,
    ResearchSessionState,
)


def _brief(rounds: int = 2) -> ResearchBrief:
    return ResearchBrief.from_dict(
        {
            "question": "Why does the circle change?",
            "attention_context": "Study the central circle.",
            "user_hypotheses": ["It depends on epsilon."],
            "experiment_permissions": {
                "domains": ["params"],
                "allowed_paths": ["params.epsilon"],
                "allow_scalar_sweep": True,
            },
            "fixed_conditions": {"notes": ["Keep the camera fixed."]},
            "useful_answer": {"kind": "bounded_relationship", "details": "Return evidence."},
            "maximum_experiment_rounds": rounds,
            "communication_profile": "working_session",
            "hard_dollar_budget": "0",
        }
    )


def _bundle(root: Path, packet_id: str = "packet-1") -> AgentBundle:
    packet = root / packet_id
    packet.mkdir(parents=True)
    return AgentBundle(
        packet_version=8,
        packet_id=packet_id,
        packet_dir=packet,
        packet_path=packet / "packet.md",
        packet_sha256="b" * 64,
        manifest_path=packet / "manifest.json",
        manifest_sha256=("a" if packet_id == "packet-1" else "c") * 64,
        finding_id="finding-1" if packet_id == "packet-1" else "finding-2",
        selected_fractal_type="explaino_transcendental",
        required_attachments=(),
        recommended_attachments=(),
        unavailable_optional_attachments=(),
    )


def _override_response(payload: str = '{"params":{"epsilon":0.000002}}') -> str:
    return f"""RESEARCH_ACTION: SINGLE_OVERRIDE

Chosen experiment: Raise epsilon once.
Why this experiment: Test the radius.
Locked prediction: The circle grows.
Observation channel: Phase Orbit [phase_orbit] -> Phase Wheel [phase_wheel_palette].
Disconfirmation condition: The circle does not grow.
Camera and fixed-state policy: Preserve all other state.
Hostile self-review conclusion: One authorized leaf changes.

```json
{payload}
```
"""


def _sweep_response() -> str:
    return """RESEARCH_ACTION: SCALAR_SWEEP

Selected bracket: Three epsilon values.
Why this bracket: Test an ordered radius trend.
Locked trend prediction: Radius grows with epsilon.
Observation channel: Phase Orbit [phase_orbit] -> Phase Wheel [phase_wheel_palette].
Disconfirmation condition: Radius is unordered.
Fixed-state and camera policy: Preserve every non-axis field.
Hostile self-review conclusion: The authorized axis is observable.

```json
{"sweep_version":1,"axis":{"path":"params.epsilon","values":[0.0000005,0.00000075,0.00000125]},"member_failure_policy":"continue_independent"}
```
"""


def _review(gate: str, selected: str = "none") -> str:
    return f"""RESEARCH_GATE: {gate}

Prediction outcome: The evidence is consistent with the prediction.
Evidence assessment: The replay evidence is sufficient for this gate.
Selected result: {selected}
Next research step: Continue only when requested by this gate.
Hostile self-review conclusion: The exact result and authority were checked.
"""


class _Services:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.promotions = []
        self.single_changed_paths = ("params.epsilon",)
        self.single_execution_error: Exception | None = None

    def validate_single(self, bundle, payload, output):
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text("{}\n", encoding="utf-8")
        return SimpleNamespace(changed_paths=self.single_changed_paths)

    def execute_single(self, bundle, payload):
        if self.single_execution_error is not None:
            raise self.single_execution_error
        return SimpleNamespace(
            proof_id="proof-1",
            status="replay_proven",
            receipt_sha256="d" * 64,
        )

    def validate_sweep(self, bundle, payload):
        return SimpleNamespace(plan=SimpleNamespace(axis_path="params.epsilon"))

    def execute_sweep(self, bundle, payload):
        return SimpleNamespace(
            sweep_id="sweep-1",
            disposition="COMPLETE",
            members=(
                SimpleNamespace(index=0, status="REPLAY_PROVEN", proof_id="proof-a"),
                SimpleNamespace(index=1, status="REPLAY_PROVEN", proof_id="proof-b"),
                SimpleNamespace(index=2, status="REPLAY_PROVEN", proof_id="proof-c"),
            ),
        )

    def promote(self, bundle, selection, evidence, promotion_dir):
        self.promotions.append((selection, evidence.round_plan_sha256))
        return _bundle(self.root, "packet-2")

    def contract(self):
        return ResearchRouteServices(
            self.validate_single,
            self.execute_single,
            self.validate_sweep,
            self.execute_sweep,
            self.promote,
        )


class ResearchSessionControllerTests(unittest.TestCase):
    def _controller(self, root: Path, *, rounds: int = 2):
        brief = _brief(rounds)
        bundle = _bundle(root / "packets")
        store = ResearchRunStore.create(
            root / "workspace",
            run_id="research-1",
            protocol_snapshot={"schema": "question_research_protocol.v1"},
            initial_packet={
                "packet_id": bundle.packet_id,
                "manifest_sha256": bundle.manifest_sha256,
                "finding_id": bundle.finding_id,
            },
            research_brief=brief.to_dict(),
        )
        services = _Services(root / "promoted")
        return ResearchSessionController(
            brief=brief,
            run_store=store,
            initial_bundle=bundle,
            services=services.contract(),
        ), services, store

    def test_single_attempt_is_consumed_only_when_execution_starts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            controller, services, store = self._controller(Path(temp_dir))
            controller.prepare_planner_response(_override_response())

            self.assertEqual(controller.attempts_consumed, 0)
            self.assertEqual(controller.state, ResearchSessionState.PLAN_READY)
            self.assertTrue((store.run_dir / "attempts/001/round-plan.json").is_file())

            evidence = controller.execute_prepared()
            self.assertEqual(controller.attempts_consumed, 1)
            self.assertEqual(evidence.proof.proof_id, "proof-1")
            controller.apply_review(_review("COMPLETE_RESEARCH"))
            self.assertEqual(controller.state, ResearchSessionState.READY_FOR_SYNTHESIS)
            self.assertEqual(services.promotions, [])

    def test_failed_planner_payload_allows_exactly_one_correction_without_attempt(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            controller, _services, _store = self._controller(Path(temp_dir))
            with self.assertRaisesRegex(ValueError, "outside research permission"):
                controller.prepare_planner_response(
                    _override_response('{"params":{"explaino_damping":1.5}}')
                )
            self.assertEqual(controller.attempts_consumed, 0)

            controller.prepare_planner_response(_override_response(), correction=True)
            with self.assertRaisesRegex(RuntimeError, "not legal|No executable correction"):
                controller.prepare_planner_response(_override_response(), correction=True)

    def test_sweep_promotion_requires_exact_replay_proven_member(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            controller, services, _store = self._controller(Path(temp_dir))
            controller.prepare_planner_response(_sweep_response())
            controller.execute_prepared()
            controller.apply_review(
                _review("CONTINUE_PROMOTE_RESULT", "sweep:sweep-1:1")
            )

            self.assertEqual(controller.state, ResearchSessionState.PLANNING)
            self.assertEqual(controller.current_packet.packet_id, "packet-2")
            self.assertEqual(len(services.promotions), 1)

    def test_final_attempt_cannot_continue_or_promote(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            controller, services, _store = self._controller(Path(temp_dir), rounds=1)
            controller.prepare_planner_response(_override_response())
            controller.execute_prepared()
            with self.assertRaisesRegex(RuntimeError, "final experiment attempt"):
                controller.apply_review(
                    _review("CONTINUE_PROMOTE_RESULT", "single:proof-1")
                )
            self.assertEqual(services.promotions, [])
            self.assertFalse(
                (
                    controller.run_store.run_dir
                    / "attempts/001/review-decision.json"
                ).exists()
            )

    def test_materializer_no_effect_is_rejected_before_attempt(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            controller, services, _store = self._controller(Path(temp_dir))
            services.single_changed_paths = ()
            with self.assertRaisesRegex(ValueError, "UNINTENDED_NO_EFFECT"):
                controller.prepare_planner_response(_override_response())
            self.assertEqual(controller.attempts_consumed, 0)

    def test_execution_failure_consumes_attempt_and_reaches_review(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            controller, services, _store = self._controller(Path(temp_dir))
            services.single_execution_error = RuntimeError("runtime failed")
            controller.prepare_planner_response(_override_response())
            evidence = controller.execute_prepared()
            self.assertEqual(controller.attempts_consumed, 1)
            self.assertEqual(evidence.execution_error, "runtime failed")
            self.assertEqual(controller.state, ResearchSessionState.REVIEW_READY)

    def test_answer_ready_consumes_no_attempt(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            controller, _services, _store = self._controller(Path(temp_dir))
            controller.prepare_planner_response(
                """RESEARCH_ACTION: ANSWER_READY

Proposed answer: The packet already contains enough evidence.
Evidence basis: Captured state and engine description.
Uncertainty: No causal comparison was run.
Hostile self-review conclusion: This remains provisional until synthesis.
"""
            )
            self.assertEqual(controller.attempts_consumed, 0)
            self.assertEqual(controller.state, ResearchSessionState.READY_FOR_SYNTHESIS)


if __name__ == "__main__":
    unittest.main()
