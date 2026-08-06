from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from .model_profile import ModelProfileV1
from .json_utils import loads_strict_no_duplicates
from .openai_transport import (
    DispatchAuthorizationRejected,
    PacketV8ResponsesTransport,
    TransportCancelled,
    TransportInputCountResult,
    TransportResource,
    TransportTurnResult,
)
from .pricing_policy import calculate_usage_cost, decimal_text
from .research_cost import (
    ResearchCostController,
    ResearchDispatchBudgetDecision,
    ResearchProviderStage,
)
from .research_run_store import ResearchRunStore


RESEARCH_PROVIDER_INSTRUCTIONS = """You are participating in a bounded fractal research session.
Use only the attached Packet V8 and controller evidence as authority.
Answer only the requested stage contract. Never equate replay proof or automated promotion with human acceptance.
Do not provide private chain-of-thought; provide the concise conclusions and exact structured artifact requested.
"""

DEFAULT_RESEARCH_PROVIDER_MINIMUM_SPACING_SECONDS = 65.0


@dataclass(frozen=True)
class ResearchCountGate:
    count: TransportInputCountResult
    budget: ResearchDispatchBudgetDecision
    conservative_adaptive_ceiling_usd: str


class ResearchProviderDispatcher:
    """Fresh-context provider dispatch with one exact dollar gate per call."""

    def __init__(
        self,
        *,
        transport: PacketV8ResponsesTransport,
        run_store: ResearchRunStore,
        cost: ResearchCostController,
        model_profile: ModelProfileV1,
        cancelled: Callable[[], bool] = lambda: False,
        minimum_generation_spacing_seconds: float = DEFAULT_RESEARCH_PROVIDER_MINIMUM_SPACING_SECONDS,
    ) -> None:
        if cost.model_profile != model_profile:
            raise ValueError("Research provider dispatcher model profile disagrees with cost authority")
        self.transport = transport
        self.run_store = run_store
        self.cost = cost
        self.model_profile = model_profile
        self.cancelled = cancelled
        if minimum_generation_spacing_seconds < 0:
            raise ValueError("Research provider spacing cannot be negative")
        self.minimum_generation_spacing_seconds = float(minimum_generation_spacing_seconds)
        self._last_provider_response_monotonic: float | None = None
        self._finalized_turns: dict[str, TransportTurnResult] = {}

    def _pace_generation_dispatch(self, turn_id: str) -> None:
        completed = self._last_provider_response_monotonic
        if completed is None or self.minimum_generation_spacing_seconds <= 0:
            return
        deadline = completed + self.minimum_generation_spacing_seconds
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return
        self._append_event(
            "research_provider_pacing",
            {
                "turn_id": turn_id,
                "minimum_spacing_seconds": self.minimum_generation_spacing_seconds,
                "planned_wait_seconds": round(remaining, 6),
                "provider_dispatch_started": False,
            },
        )
        while True:
            if self.cancelled():
                raise TransportCancelled(
                    "Research provider dispatch was cancelled during pre-dispatch pacing"
                )
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return
            time.sleep(min(0.25, remaining))

    @staticmethod
    def _output_text_from_raw_response(raw: object) -> str:
        if not isinstance(raw, dict):
            return ""
        parts: list[str] = []
        output = raw.get("output")
        if not isinstance(output, list):
            return ""
        for item in output:
            if not isinstance(item, dict) or item.get("type") != "message":
                continue
            content = item.get("content")
            if not isinstance(content, list):
                continue
            for block in content:
                if isinstance(block, dict) and block.get("type") == "output_text":
                    text = block.get("text")
                    if isinstance(text, str):
                        parts.append(text)
        return "\n".join(parts).strip()

    def _load_durable_turn(self, turn_id: str) -> TransportTurnResult | None:
        response_path = self.run_store.run_dir / "transport" / turn_id / "response.json"
        if not response_path.is_file():
            incomplete_path = (
                self.run_store.run_dir
                / "transport"
                / turn_id
                / "incomplete-response.json"
            )
            if incomplete_path.is_file():
                raise RuntimeError(
                    f"Durable incomplete provider response forbids redispatch: {turn_id}"
                )
            return None
        value = loads_strict_no_duplicates(response_path.read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            raise ValueError(f"Durable provider response is not an object: {turn_id}")
        output_text = value.get("output_text")
        if not isinstance(output_text, str) or not output_text.strip():
            output_text = self._output_text_from_raw_response(value.get("response"))
        if not output_text:
            raise ValueError(f"Durable provider response has no output text: {turn_id}")
        if value.get("requested_model") != self.model_profile.model:
            raise ValueError(f"Durable provider response model binding changed: {turn_id}")
        if value.get("reasoning_effort") != self.model_profile.reasoning_effort:
            raise ValueError(f"Durable provider response reasoning binding changed: {turn_id}")
        if value.get("model_profile_sha256") != self.model_profile.sha256:
            raise ValueError(f"Durable provider response profile binding changed: {turn_id}")
        if value.get("prompt_cache_policy") != self.model_profile.prompt_cache_policy.value:
            raise ValueError(f"Durable provider response cache policy changed: {turn_id}")
        response_id = value.get("response_id")
        resolved_model = value.get("resolved_model")
        if not isinstance(response_id, str) or not response_id:
            raise ValueError(f"Durable provider response identity is missing: {turn_id}")
        if not isinstance(resolved_model, str) or not resolved_model:
            raise ValueError(f"Durable provider resolved model is missing: {turn_id}")
        return TransportTurnResult(
            response_id=response_id,
            previous_response_id=(
                value.get("previous_response_id")
                if isinstance(value.get("previous_response_id"), str)
                else None
            ),
            model=resolved_model,
            output_text=output_text,
            input_tokens=int(value.get("input_tokens", -1)),
            output_tokens=int(value.get("output_tokens", -1)),
            resources=(),
            unavailable_optional_attachments=tuple(
                item
                for item in value.get("unavailable_optional_attachments", [])
                if isinstance(item, str)
            ),
            requested_model=self.model_profile.model,
            reasoning_effort=self.model_profile.reasoning_effort,
            model_profile_sha256=self.model_profile.sha256,
            cached_input_tokens=int(value.get("cached_input_tokens", -1)),
            cache_write_tokens=int(value.get("cache_write_tokens", -1)),
            prompt_cache_policy=str(value.get("prompt_cache_policy", "")),
            latency_seconds=float(value.get("latency_seconds", 0.0)),
            request_evidence_path=(
                self.run_store.run_dir / "transport" / turn_id / "request.json"
            ),
            response_evidence_path=response_path,
        )

    def _finalize_turn(
        self,
        *,
        stage: ResearchProviderStage,
        turn_id: str,
        result: TransportTurnResult,
        recovered: bool,
    ) -> TransportTurnResult:
        if turn_id in self._finalized_turns:
            return self._finalized_turns[turn_id]
        actual = calculate_usage_cost(
            self.cost.pricing_policy,
            model_name=result.model,
            input_tokens=result.input_tokens,
            cached_input_tokens=result.cached_input_tokens,
            cache_write_tokens=result.cache_write_tokens,
            output_tokens=result.output_tokens,
        )
        self.cost.record_actual_cost(actual)
        self.run_store.write_evidence_once_json(
            f"cost/{turn_id}-actual.json",
            {
                "stage": stage.value,
                "actual": actual.to_dict(),
                "cumulative_calculated_cost_usd": decimal_text(
                    self.cost.spent_cost_usd
                ),
            },
        )
        self._append_event(
            "research_provider_response_recovered"
            if recovered
            else "research_provider_response",
            {
                "turn_id": turn_id,
                "stage": stage.value,
                "requested_model": result.requested_model,
                "resolved_model": result.model,
                "input_tokens": result.input_tokens,
                "output_tokens": result.output_tokens,
                "calculated_call_cost_usd": decimal_text(actual.cost_usd),
                "cumulative_calculated_cost_usd": decimal_text(
                    self.cost.spent_cost_usd
                ),
                "latency_seconds": result.latency_seconds,
                "provider_request_dispatched": not recovered,
                "durable_response_recovered": recovered,
            },
        )
        self._finalized_turns[turn_id] = result
        self._last_provider_response_monotonic = time.monotonic()
        return result

    def _record_incomplete_turn_usage(
        self,
        *,
        stage: ResearchProviderStage,
        turn_id: str,
    ) -> None:
        path = (
            self.run_store.run_dir
            / "transport"
            / turn_id
            / "incomplete-response.json"
        )
        if not path.is_file():
            return
        value = loads_strict_no_duplicates(path.read_text(encoding="utf-8"))
        if not isinstance(value, dict) or not isinstance(value.get("usage"), dict):
            raise ValueError(f"Incomplete provider usage evidence is malformed: {turn_id}")
        usage = value["usage"]
        required = (
            "input_tokens",
            "cached_input_tokens",
            "cache_write_tokens",
            "output_tokens",
        )
        if any(
            isinstance(usage.get(key), bool)
            or not isinstance(usage.get(key), int)
            or usage[key] < 0
            for key in required
        ):
            raise ValueError(f"Incomplete provider usage values are invalid: {turn_id}")
        resolved_model = value.get("resolved_model")
        if not isinstance(resolved_model, str) or not resolved_model:
            raise ValueError(f"Incomplete provider model identity is missing: {turn_id}")
        actual = calculate_usage_cost(
            self.cost.pricing_policy,
            model_name=resolved_model,
            input_tokens=usage["input_tokens"],
            cached_input_tokens=usage["cached_input_tokens"],
            cache_write_tokens=usage["cache_write_tokens"],
            output_tokens=usage["output_tokens"],
        )
        self.cost.record_actual_cost(actual)
        self.run_store.write_evidence_once_json(
            f"cost/{turn_id}-incomplete-actual.json",
            {
                "stage": stage.value,
                "provider_status": "incomplete",
                "actual": actual.to_dict(),
                "cumulative_calculated_cost_usd": decimal_text(
                    self.cost.spent_cost_usd
                ),
            },
        )
        self._append_event(
            "research_provider_incomplete_response",
            {
                "turn_id": turn_id,
                "stage": stage.value,
                "resolved_model": resolved_model,
                "input_tokens": usage["input_tokens"],
                "output_tokens": usage["output_tokens"],
                "calculated_call_cost_usd": decimal_text(actual.cost_usd),
                "cumulative_calculated_cost_usd": decimal_text(
                    self.cost.spent_cost_usd
                ),
                "provider_request_dispatched": True,
                "durable_response_recovered": False,
            },
        )

    def _record_budget(
        self,
        turn_id: str,
        decision: ResearchDispatchBudgetDecision,
    ) -> None:
        self.run_store.write_evidence_once_json(
            f"cost/{turn_id}-authorization.json",
            {
                "stage": decision.stage.value,
                "exact_input_tokens": decision.exact_input_tokens,
                "current_call": decision.current_call.to_dict(),
                "reserved_stages": [stage.value for stage in decision.reserved_stages],
                "reserved_cost_usd": decimal_text(decision.reserved_cost_usd),
                "spent_cost_usd": decimal_text(decision.spent_cost_usd),
                "hard_budget_usd": decimal_text(decision.hard_budget_usd),
                "required_available_cost_usd": decimal_text(
                    decision.required_available_cost_usd
                ),
                "authorized": decision.authorized,
                "rejection_reason": decision.rejection_reason,
            },
        )
        self._append_event(
            "research_dispatch_authorized"
            if decision.authorized
            else "research_dispatch_rejected",
            {
                "turn_id": turn_id,
                "stage": decision.stage.value,
                "exact_input_tokens": decision.exact_input_tokens,
                "current_call_cost_usd": decimal_text(decision.current_call.cost_usd),
                "reserved_cost_usd": decimal_text(decision.reserved_cost_usd),
                "authorized": decision.authorized,
                "rejection_reason": decision.rejection_reason,
            },
        )

    def _append_event(self, event_type: str, payload: dict[str, object]) -> None:
        active, _events = self.run_store.load_live_snapshot()
        projection = (
            dict(active.get("projection"))
            if isinstance(active, dict) and isinstance(active.get("projection"), dict)
            else {}
        )
        self.run_store.record_transition(event_type, payload, projection)

    def count_only(
        self,
        *,
        stage: ResearchProviderStage,
        turn_id: str,
        prompt: str,
        packet_dir: Path | None,
        additional_resources: tuple[TransportResource, ...] = (),
        planner_may_execute: bool = False,
        correction_available: bool = False,
        alternate_communication_required: bool = False,
        experiment_attempts_remaining: int = 0,
    ) -> ResearchCountGate:
        stage = ResearchProviderStage(stage)
        limit = self.cost.stage_limits[stage]
        counted = self.transport.count_turn_input(
            instructions=RESEARCH_PROVIDER_INSTRUCTIONS,
            prompt=prompt,
            packet_dir=packet_dir,
            run_store=self.run_store,
            turn_id=turn_id,
            cancelled=self.cancelled,
            model=self.model_profile.model,
            reasoning_effort=self.model_profile.reasoning_effort,
            model_profile_sha256=self.model_profile.sha256,
            max_output_tokens=limit.maximum_output_tokens,
            prompt_cache_policy=self.model_profile.prompt_cache_policy,
            additional_resources=additional_resources,
        )
        decision = self.cost.authorize_dispatch(
            stage,
            exact_input_tokens=counted.input_tokens,
            planner_may_execute=planner_may_execute,
            correction_available=correction_available,
            alternate_communication_required=alternate_communication_required,
        )
        self._record_budget(turn_id, decision)
        ceiling = self.cost.conservative_adaptive_ceiling(
            experiment_attempts_remaining=experiment_attempts_remaining,
            correction_available=correction_available,
            alternate_communication_required=alternate_communication_required,
        )
        return ResearchCountGate(counted, decision, decimal_text(ceiling))

    def dispatch(
        self,
        *,
        stage: ResearchProviderStage,
        turn_id: str,
        prompt: str,
        packet_dir: Path | None,
        additional_resources: tuple[TransportResource, ...] = (),
        planner_may_execute: bool = False,
        correction_available: bool = False,
        alternate_communication_required: bool = False,
    ) -> TransportTurnResult:
        stage = ResearchProviderStage(stage)
        limit = self.cost.stage_limits[stage]
        durable = self._load_durable_turn(turn_id)
        if durable is not None:
            return self._finalize_turn(
                stage=stage,
                turn_id=turn_id,
                result=durable,
                recovered=True,
            )

        def authorize(exact_input_tokens: int) -> None:
            decision = self.cost.authorize_dispatch(
                stage,
                exact_input_tokens=exact_input_tokens,
                planner_may_execute=planner_may_execute,
                correction_available=correction_available,
                alternate_communication_required=alternate_communication_required,
            )
            self._record_budget(turn_id, decision)
            if not decision.authorized:
                raise DispatchAuthorizationRejected(decision.rejection_reason or "Dollar gate rejected")
            self._pace_generation_dispatch(turn_id)

        try:
            result = self.transport.send_turn(
                instructions=RESEARCH_PROVIDER_INSTRUCTIONS,
                prompt=prompt,
                packet_dir=packet_dir,
                previous_response_id=None,
                run_store=self.run_store,
                turn_id=turn_id,
                cancelled=self.cancelled,
                model=self.model_profile.model,
                reasoning_effort=self.model_profile.reasoning_effort,
                model_profile_sha256=self.model_profile.sha256,
                max_output_tokens=limit.maximum_output_tokens,
                prompt_cache_policy=self.model_profile.prompt_cache_policy,
                authorize_dispatch=authorize,
                additional_resources=additional_resources,
            )
        except Exception:
            self._record_incomplete_turn_usage(stage=stage, turn_id=turn_id)
            raise
        return self._finalize_turn(
            stage=stage,
            turn_id=turn_id,
            result=result,
            recovered=False,
        )
