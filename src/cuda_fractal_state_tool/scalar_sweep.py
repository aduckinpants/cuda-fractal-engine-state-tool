from __future__ import annotations

import copy
import hashlib
import json
import math
import os
import tempfile
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Protocol

from .agent_bundle import load_existing_agent_bundle
from .async_jobs import JobCancelledError, JobContext
from .json_utils import loads_strict_no_duplicates
from .runtime_surface import (
    build_runtime_identity,
    runtime_identity_summary,
    runtime_identity_summary_sha256,
    sha256_file,
)
from .state_override import (
    ParsedStateOverride,
    StateOverrideMaterialization,
    enumerate_override_leaf_paths,
    materialize_state_override,
    parse_state_override,
)
from .state_override_proof import StateOverrideProofResult, execute_state_override_proof
from .sweep_presentation import (
    CapturedBaseReference,
    render_scalar_sweep_presentation,
    render_scalar_sweep_web_review,
    resolve_captured_base_reference,
)


SCALAR_SWEEP_VERSION = 1
SCALAR_SWEEP_RECEIPT_VERSION = 1
MEMBER_FAILURE_POLICIES = {"continue_independent", "stop_on_first_failure"}


class ScalarSweepPlanError(ValueError):
    pass


@dataclass(frozen=True)
class ScalarSweepPlan:
    exact_text: str
    exact_utf8: bytes
    sha256: str
    axis_path: str
    values: tuple[int | float, ...]
    member_failure_policy: str


@dataclass(frozen=True)
class PacketSweepBinding:
    packet_id: str
    finding_id: str
    manifest_sha256: str
    authority_identities: dict[str, Any]


@dataclass(frozen=True)
class ScalarSweepValidation:
    plan: ScalarSweepPlan
    fixed_override: ParsedStateOverride
    binding: PacketSweepBinding
    runtime_snapshot: dict[str, Any]
    concrete_overrides: tuple[bytes, ...]


@dataclass(frozen=True)
class ScalarSweepMemberResult:
    index: int
    value: int | float
    status: str
    override_sha256: str
    proof_id: str | None = None
    proof_receipt_sha256: str | None = None
    candidate_state_sha256: str | None = None
    candidate_frame_sha256: str | None = None
    candidate_display_path: Path | None = None
    candidate_display_sha256: str | None = None
    message: str | None = None
    # In-process authority for callers that need to promote the exact proven
    # member. Durable sweep evidence continues to use proof_id and receipt hash.
    proof_result: StateOverrideProofResult | None = None


@dataclass(frozen=True)
class ScalarSweepResult:
    sweep_id: str
    disposition: str
    sweep_dir: Path
    receipt_path: Path
    members: tuple[ScalarSweepMemberResult, ...]
    web_review_dir: Path | None = None


class ProofExecutor(Protocol):
    def __call__(
        self,
        packet_dir: Path,
        override_text: str,
        runtime_cmd_path: Path,
        job: JobContext,
        **kwargs: Any,
    ) -> StateOverrideProofResult: ...


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _json_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n"
    ).encode("utf-8")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_once(path: Path, payload: bytes) -> None:
    if path.exists():
        raise FileExistsError(f"Immutable sweep artifact already exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp.{uuid.uuid4().hex}")
    try:
        with temporary.open("xb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(str(temporary), str(path))
    finally:
        if temporary.exists():
            temporary.unlink()


def _write_json_once(path: Path, value: Any) -> None:
    _write_once(path, _json_bytes(value))


def parse_scalar_sweep_plan(text: str) -> ScalarSweepPlan:
    try:
        exact_utf8 = text.encode("utf-8")
        value = loads_strict_no_duplicates(text)
    except (UnicodeError, json.JSONDecodeError, ValueError) as exc:
        detail = str(exc)
        if "Non-finite" in detail:
            raise ScalarSweepPlanError(f"Sweep values must be finite: {detail}") from exc
        raise ScalarSweepPlanError(f"Scalar sweep plan is not strict JSON: {detail}") from exc
    if not isinstance(value, dict):
        raise ScalarSweepPlanError("Scalar sweep plan must be one JSON object")
    if set(value) != {"sweep_version", "axis", "member_failure_policy"}:
        raise ScalarSweepPlanError("Scalar sweep plan fields must be exactly version, axis, and policy")
    if value.get("sweep_version") != SCALAR_SWEEP_VERSION:
        raise ScalarSweepPlanError("Unsupported scalar sweep version")
    axis = value.get("axis")
    if not isinstance(axis, dict) or set(axis) != {"path", "values"}:
        raise ScalarSweepPlanError("Scalar sweep axis must contain exactly path and values")
    path = axis.get("path")
    parts = path.split(".") if isinstance(path, str) else []
    if len(parts) != 2 or parts[0] != "params" or not parts[1] or any(
        token in parts[1] for token in "[]"
    ):
        raise ScalarSweepPlanError("Scalar sweep axis must be one direct scalar params leaf")
    values = axis.get("values")
    if not isinstance(values, list) or not 3 <= len(values) <= 9:
        raise ScalarSweepPlanError("Scalar sweep requires 3 through 9 explicit values")
    checked: list[int | float] = []
    for item in values:
        if isinstance(item, bool) or not isinstance(item, (int, float)) or not math.isfinite(item):
            raise ScalarSweepPlanError("Scalar sweep values must be finite JSON numbers")
        if any(item == prior for prior in checked):
            raise ScalarSweepPlanError("Scalar sweep values must not contain duplicates")
        checked.append(item)
    policy = value.get("member_failure_policy")
    if policy not in MEMBER_FAILURE_POLICIES:
        raise ScalarSweepPlanError("Scalar sweep member failure policy is unsupported")
    return ScalarSweepPlan(
        exact_text=text,
        exact_utf8=exact_utf8,
        sha256=_sha256(exact_utf8),
        axis_path=path,
        values=tuple(checked),
        member_failure_policy=policy,
    )


def _default_packet_binding(packet_dir: Path) -> PacketSweepBinding:
    bundle = load_existing_agent_bundle(packet_dir)
    if bundle.packet_version != 8:
        raise ScalarSweepPlanError("Scalar Bracket Sweep V1 requires Packet V8")
    manifest_bytes = bundle.manifest_path.read_bytes()
    try:
        manifest = loads_strict_no_duplicates(manifest_bytes.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError, ValueError) as exc:
        raise ScalarSweepPlanError("Packet V8 manifest is malformed") from exc
    identities = manifest.get("authority_identities") if isinstance(manifest, dict) else None
    if not isinstance(identities, dict):
        raise ScalarSweepPlanError("Packet V8 manifest has no authority identities")
    return PacketSweepBinding(
        packet_id=bundle.packet_id,
        finding_id=bundle.finding_id,
        manifest_sha256=bundle.manifest_sha256,
        authority_identities=copy.deepcopy(identities),
    )


def _default_runtime_snapshot(runtime_cmd_path: Path) -> dict[str, Any]:
    identity = build_runtime_identity(runtime_cmd_path, runtime_cmd_path.parent)
    summary = runtime_identity_summary(identity)
    return {
        "runtime_identity": summary,
        "runtime_identity_sha256": runtime_identity_summary_sha256(summary),
    }


def _concrete_override(fixed: ParsedStateOverride, axis_path: str, value: int | float) -> bytes:
    document = copy.deepcopy(fixed.document)
    params = document.setdefault("params", {})
    if not isinstance(params, dict):
        raise ScalarSweepPlanError("Fixed override params domain is not an object")
    params[axis_path.split(".", 1)[1]] = value
    return (
        json.dumps(document, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    ).encode("utf-8")


def _proof_emitted_exact_base(
    proof: StateOverrideProofResult,
    packet_dir: Path,
    axis_path: str,
) -> bool:
    """Classify an exact emitted-base collapse without changing proof tolerance."""

    engine_candidate_path = getattr(proof, "engine_candidate_path", None)
    merged_candidate_path = getattr(proof, "merged_candidate_path", None)
    if proof.status == "replay_proven" or engine_candidate_path is None or merged_candidate_path is None:
        return False
    paths = {
        "base": packet_dir / "state.json",
        "merged": Path(merged_candidate_path),
        "emitted": Path(engine_candidate_path),
        "receipt": proof.receipt_path,
    }
    if any(not path.is_file() for path in paths.values()):
        return False
    if sha256_file(paths["receipt"]) != proof.receipt_sha256:
        return False
    merged_sha = getattr(proof, "merged_candidate_sha256", None)
    if merged_sha and sha256_file(paths["merged"]) != merged_sha:
        return False
    engine_sha = getattr(proof, "engine_candidate_sha256", None)
    if engine_sha and sha256_file(paths["emitted"]) != engine_sha:
        return False
    try:
        receipt = loads_strict_no_duplicates(paths["receipt"].read_text(encoding="utf-8"))
        documents = {
            name: loads_strict_no_duplicates(path.read_text(encoding="utf-8"))
            for name, path in paths.items()
            if name != "receipt"
        }
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError):
        return False
    errors = receipt.get("errors") if isinstance(receipt, dict) else None
    if (
        receipt.get("status") != "rejected"
        or not isinstance(errors, list)
        or len(errors) != 1
        or not isinstance(errors[0], str)
        or not errors[0].startswith(f"Engine reverted requested value at {axis_path}:")
    ):
        return False
    axis_name = axis_path.split(".", 1)[1]
    try:
        base_value = documents["base"]["params"][axis_name]
        merged_value = documents["merged"]["params"][axis_name]
        emitted_value = documents["emitted"]["params"][axis_name]
    except (KeyError, TypeError):
        return False
    return merged_value != base_value and emitted_value == base_value


class ScalarBracketSweepService:
    def __init__(
        self,
        *,
        materialize: Callable[..., StateOverrideMaterialization] = materialize_state_override,
        proof: ProofExecutor = execute_state_override_proof,
        runtime_snapshot: Callable[[Path], dict[str, Any]] = _default_runtime_snapshot,
        packet_binding: Callable[[Path], PacketSweepBinding] = _default_packet_binding,
        captured_base_reference: Callable[[Path, str], CapturedBaseReference] = (
            resolve_captured_base_reference
        ),
    ) -> None:
        self.materialize = materialize
        self.proof = proof
        self.runtime_snapshot = runtime_snapshot
        self.packet_binding = packet_binding
        self.captured_base_reference = captured_base_reference

    def validate(
        self,
        *,
        packet_dir: Path,
        fixed_override_text: str,
        plan_text: str,
        runtime_cmd_path: Path,
    ) -> ScalarSweepValidation:
        packet_dir = packet_dir.resolve()
        runtime_cmd_path = runtime_cmd_path.resolve()
        plan = parse_scalar_sweep_plan(plan_text)
        try:
            fixed = parse_state_override(
                fixed_override_text if fixed_override_text.strip() else "{}"
            )
        except ValueError as exc:
            raise ScalarSweepPlanError(f"Fixed state override is invalid: {exc}") from exc
        if plan.axis_path in enumerate_override_leaf_paths(fixed):
            raise ScalarSweepPlanError(
                f"Fixed state override already contains sweep axis {plan.axis_path}"
            )
        binding = self.packet_binding(packet_dir)
        try:
            packet_state = loads_strict_no_duplicates(
                (packet_dir / "state.json").read_text(encoding="utf-8")
            )
        except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
            raise ScalarSweepPlanError("Packet base state is unavailable or malformed") from exc
        params = packet_state.get("params") if isinstance(packet_state, dict) else None
        axis_name = plan.axis_path.split(".", 1)[1]
        if not isinstance(params, dict) or axis_name not in params:
            raise ScalarSweepPlanError(f"Sweep axis is absent from packet base: {plan.axis_path}")
        base_value = params[axis_name]
        if any(value == base_value for value in plan.values):
            raise ScalarSweepPlanError(
                f"Scalar sweep value exactly repeats captured base {plan.axis_path}={base_value!r}"
            )
        runtime = self.runtime_snapshot(runtime_cmd_path)
        concrete = tuple(_concrete_override(fixed, plan.axis_path, value) for value in plan.values)
        try:
            with tempfile.TemporaryDirectory(prefix="scalar-sweep-preflight-") as temp_dir:
                root = Path(temp_dir)
                self.materialize(
                    packet_dir,
                    fixed.exact_text,
                    root / "fixed.json",
                    expected_manifest_sha256=binding.manifest_sha256,
                )
                for index, payload in enumerate(concrete):
                    self.materialize(
                        packet_dir,
                        payload.decode("utf-8"),
                        root / f"member-{index:03d}.json",
                        expected_manifest_sha256=binding.manifest_sha256,
                    )
        except Exception as exc:
            raise ScalarSweepPlanError(f"Scalar sweep plan preflight failed: {exc}") from exc
        if sha256_file(packet_dir / "manifest.json") != binding.manifest_sha256:
            raise ScalarSweepPlanError("Packet authority changed during scalar sweep preflight")
        return ScalarSweepValidation(plan, fixed, binding, runtime, concrete)

    def execute(
        self,
        *,
        packet_dir: Path,
        fixed_override_text: str,
        plan_text: str,
        runtime_cmd_path: Path,
        job: JobContext,
        sweeps_root: Path | None = None,
        runtime_compatibility_mode: str | None = None,
        on_progress: Callable[[dict[str, Any]], None] | None = None,
    ) -> ScalarSweepResult:
        packet_dir = packet_dir.resolve()
        runtime_cmd_path = runtime_cmd_path.resolve()
        validation = self.validate(
            packet_dir=packet_dir,
            fixed_override_text=fixed_override_text,
            plan_text=plan_text,
            runtime_cmd_path=runtime_cmd_path,
        )
        _progress(
            on_progress,
            {
                "event": "PLAN_VALIDATED",
                "axis_path": validation.plan.axis_path,
                "values": list(validation.plan.values),
            },
        )
        if sweeps_root is None:
            if packet_dir.parent.name != "packets":
                raise ScalarSweepPlanError("Packet directory is not beneath a finding packets directory")
            sweeps_root = packet_dir.parent.parent / "sweeps"
        sweep_id = str(uuid.uuid4())
        sweep_dir = sweeps_root.resolve() / sweep_id
        try:
            sweep_dir.mkdir(parents=True, exist_ok=False)
            _write_once(sweep_dir / "plan.json", validation.plan.exact_utf8)
            _write_once(
                sweep_dir / "fixed-override.json", validation.fixed_override.exact_utf8
            )
            _write_json_once(
                sweep_dir / "binding.json",
                {
                    "sweep_id": sweep_id,
                    "packet_id": validation.binding.packet_id,
                    "finding_id": validation.binding.finding_id,
                    "packet_manifest_sha256": validation.binding.manifest_sha256,
                    "authority_identities": validation.binding.authority_identities,
                    "runtime": validation.runtime_snapshot,
                    "fixed_override_sha256": validation.fixed_override.sha256,
                },
            )
        except Exception as exc:
            raise ScalarSweepPlanError(f"Could not allocate immutable scalar sweep evidence: {exc}") from exc

        members: list[ScalarSweepMemberResult] = []
        disposition = "COMPLETE"
        stop_status: str | None = None
        for index, (value, override_bytes) in enumerate(
            zip(validation.plan.values, validation.concrete_overrides, strict=True)
        ):
            if stop_status is not None:
                skipped = ScalarSweepMemberResult(
                        index=index,
                        value=value,
                        status=stop_status,
                        override_sha256=_sha256(override_bytes),
                )
                members.append(skipped)
                _progress(on_progress, _member_progress(skipped))
                continue
            if job.cancelled:
                disposition = "CANCELLED"
                stop_status = "NOT_STARTED_AFTER_CANCEL"
                skipped = ScalarSweepMemberResult(
                    index, value, stop_status, _sha256(override_bytes)
                )
                members.append(skipped)
                _progress(on_progress, _member_progress(skipped))
                continue
            if not self._authority_matches(packet_dir, runtime_cmd_path, validation):
                disposition = "AUTHORITY_DRIFT"
                stop_status = "NOT_STARTED_AFTER_AUTHORITY_DRIFT"
                skipped = ScalarSweepMemberResult(
                    index, value, stop_status, _sha256(override_bytes)
                )
                members.append(skipped)
                _progress(on_progress, _member_progress(skipped))
                continue

            member_dir = sweep_dir / "members" / f"{index:03d}-{_value_slug(value)}"
            _write_once(member_dir / "override.json", override_bytes)
            _progress(
                on_progress,
                {"event": "MEMBER_STARTED", "index": index, "value": value},
            )
            try:
                proof = self.proof(
                    packet_dir,
                    override_bytes.decode("utf-8"),
                    runtime_cmd_path,
                    job,
                    expected_manifest_sha256=validation.binding.manifest_sha256,
                    runtime_compatibility_mode=runtime_compatibility_mode,
                )
            except JobCancelledError:
                disposition = "CANCELLED"
                stop_status = "NOT_STARTED_AFTER_CANCEL"
                cancelled_member = ScalarSweepMemberResult(
                    index, value, "CANCELLED_DURING_PROOF", _sha256(override_bytes)
                )
                members.append(cancelled_member)
                _write_json_once(
                    member_dir / "proof-ref.json", _member_receipt(cancelled_member)
                )
                _progress(on_progress, _member_progress(cancelled_member))
                continue
            except Exception as exc:
                proof = None
                message = str(exc)
            else:
                message = proof.message

            if proof is not None:
                status = "REPLAY_PROVEN" if proof.status == "replay_proven" else "PROOF_FAILED"
                if status == "PROOF_FAILED" and _proof_emitted_exact_base(
                    proof,
                    packet_dir,
                    validation.plan.axis_path,
                ):
                    status = "NO_EFFECT_ENGINE_EMITTED_BASE"
                    message = (
                        f"Engine emitted the exact captured base value for {validation.plan.axis_path}; "
                        "this member produced no distinct state effect."
                    )
                member = ScalarSweepMemberResult(
                    index=index,
                    value=value,
                    status=status,
                    override_sha256=_sha256(override_bytes),
                    proof_id=proof.proof_id,
                    proof_receipt_sha256=proof.receipt_sha256,
                    candidate_state_sha256=proof.engine_candidate_sha256,
                    candidate_frame_sha256=proof.candidate_frame_sha256,
                    candidate_display_path=proof.candidate_display_path,
                    candidate_display_sha256=proof.candidate_display_sha256,
                    message=message,
                    proof_result=proof,
                )
                _write_json_once(member_dir / "proof-ref.json", _member_receipt(member))
            else:
                member = ScalarSweepMemberResult(
                    index, value, "PROOF_FAILED", _sha256(override_bytes), message=message
                )
                _write_json_once(member_dir / "proof-ref.json", _member_receipt(member))
            members.append(member)
            _progress(on_progress, _member_progress(member))

            if job.cancelled:
                disposition = "CANCELLED"
                stop_status = "NOT_STARTED_AFTER_CANCEL"
            elif not self._authority_matches(packet_dir, runtime_cmd_path, validation):
                disposition = "AUTHORITY_DRIFT"
                stop_status = "NOT_STARTED_AFTER_AUTHORITY_DRIFT"
            elif member.status in {"PROOF_FAILED", "NO_EFFECT_ENGINE_EMITTED_BASE"}:
                if validation.plan.member_failure_policy == "stop_on_first_failure":
                    disposition = "STOPPED_AFTER_MEMBER_FAILURE"
                    stop_status = "NOT_STARTED_AFTER_FAILURE"
                elif disposition == "COMPLETE":
                    disposition = "PARTIAL_MEMBER_FAILURES"

        presentation = None
        presentation_error = None
        try:
            presentation = render_scalar_sweep_presentation(
                sweep_dir=sweep_dir,
                sweep_id=sweep_id,
                axis_path=validation.plan.axis_path,
                captured_base=self.captured_base_reference(
                    packet_dir, validation.plan.axis_path
                ),
                members=members,
            )
        except Exception as exc:
            presentation_error = str(exc)
            disposition = "PRESENTATION_FAILED"
        receipt = {
            "scalar_sweep_receipt_version": SCALAR_SWEEP_RECEIPT_VERSION,
            "sweep_id": sweep_id,
            "created_at_utc": _utc_now(),
            "disposition": disposition,
            "binding_path": "binding.json",
            "binding_sha256": sha256_file(sweep_dir / "binding.json"),
            "plan_path": "plan.json",
            "plan_sha256": validation.plan.sha256,
            "axis_path": validation.plan.axis_path,
            "ordered_values": list(validation.plan.values),
            "member_failure_policy": validation.plan.member_failure_policy,
            "fixed_override_sha256": validation.fixed_override.sha256,
            "fixed_override_path": "fixed-override.json",
            "members": [_member_receipt(item) for item in members],
            "presentation": {
                "status": "complete" if presentation is not None else "failed",
                "error": presentation_error,
                "index_path": "presentation/index.md" if presentation else None,
                "index_sha256": presentation.index_sha256 if presentation else None,
                "contact_sheet_path": (
                    "presentation/contact-sheet.png" if presentation else None
                ),
                "contact_sheet_sha256": (
                    presentation.contact_sheet_sha256 if presentation else None
                ),
                "receipt_path": (
                    "presentation/contact-sheet-receipt.json" if presentation else None
                ),
                "receipt_sha256": presentation.receipt_sha256 if presentation else None,
                "human_acceptance": False,
            },
            "web_review": {
                "path": "web-review" if presentation else None,
                "generation": "deterministic_derived_after_aggregate_receipt",
                "human_acceptance": False,
            },
        }
        receipt_path = sweep_dir / "receipt.json"
        _write_json_once(receipt_path, receipt)
        web_review = None
        if presentation is not None:
            try:
                web_review = render_scalar_sweep_web_review(sweep_dir=sweep_dir)
            except Exception as exc:
                _progress(
                    on_progress,
                    {
                        "event": "WEB_REVIEW_FAILED",
                        "sweep_id": sweep_id,
                        "error": str(exc),
                    },
                )
                raise ScalarSweepPlanError(
                    f"Sweep proofs are preserved at {sweep_dir}, but web-review generation failed: {exc}"
                ) from exc
        _progress(
            on_progress,
            {
                "event": "SWEEP_COMPLETED",
                "disposition": disposition,
                "sweep_id": sweep_id,
                "sweep_dir": str(sweep_dir),
            },
        )
        return ScalarSweepResult(
            sweep_id=sweep_id,
            disposition=disposition,
            sweep_dir=sweep_dir,
            receipt_path=receipt_path,
            members=tuple(members),
            web_review_dir=web_review.web_review_dir if web_review else None,
        )

    def _authority_matches(
        self,
        packet_dir: Path,
        runtime_cmd_path: Path,
        validation: ScalarSweepValidation,
    ) -> bool:
        try:
            if sha256_file(packet_dir / "manifest.json") != validation.binding.manifest_sha256:
                return False
            return self.runtime_snapshot(runtime_cmd_path) == validation.runtime_snapshot
        except Exception:
            return False


def _member_receipt(member: ScalarSweepMemberResult) -> dict[str, Any]:
    return {
        "index": member.index,
        "value": member.value,
        "status": member.status,
        "override_sha256": member.override_sha256,
        "proof_id": member.proof_id,
        "proof_receipt_sha256": member.proof_receipt_sha256,
        "candidate_state_sha256": member.candidate_state_sha256,
        "candidate_frame_sha256": member.candidate_frame_sha256,
        "candidate_display_path": (
            str(member.candidate_display_path) if member.candidate_display_path else None
        ),
        "candidate_display_sha256": member.candidate_display_sha256,
        "message": member.message,
    }


def _member_progress(member: ScalarSweepMemberResult) -> dict[str, Any]:
    return {
        "event": "MEMBER_COMPLETED",
        "index": member.index,
        "value": member.value,
        "status": member.status,
        "proof_id": member.proof_id,
    }


def _progress(
    callback: Callable[[dict[str, Any]], None] | None,
    event: dict[str, Any],
) -> None:
    if callback is not None:
        callback(dict(event))


def _value_slug(value: int | float) -> str:
    text = json.dumps(value, ensure_ascii=True, allow_nan=False)
    return text.replace("-", "neg-").replace(".", "p")
