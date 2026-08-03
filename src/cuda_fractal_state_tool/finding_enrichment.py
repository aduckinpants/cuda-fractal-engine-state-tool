from __future__ import annotations

import hashlib
import json
import math
import os
import shutil
import tempfile
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from .agent_bundle import load_existing_agent_bundle
from .authority_container import parse_authority_container
from .fractal_viewport_facts import validate_viewport_facts_bytes
from .json_utils import loads_no_duplicates
from .polynomial_model_provider import (
    ANNOTATION_BUILDER_VERSION,
    ANNOTATION_RENDERER_VERSION,
    ActiveModelRuntimeClient,
    PolynomialOverPowerEscapeProvider,
    build_annotation_set,
    render_annotations,
)


ANALYSIS_SCHEMA_VERSION = 1
COMMON_PROVIDER_ID = "common_finding_facts.v1"
EPISTEMIC_STATUSES = frozenset(
    {
        "exact_packet_fact",
        "exact_symbolic_derivation",
        "numerical_solution_of_exact_derived_equation",
        "engine_authoritative_evaluation",
        "comparison_derived_result",
        "heuristic_detection",
        "interpretation_or_hypothesis",
    }
)


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _json_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _load_object(payload: bytes, label: str) -> dict[str, Any]:
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(f"{label} is not valid UTF-8") from exc
    try:
        value = loads_no_duplicates(text)
    except ValueError as exc:
        raise ValueError(f"{label} is invalid or contains duplicate keys: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a JSON object")
    _reject_nonfinite(value, label)
    return value


def _reject_nonfinite(value: Any, label: str) -> None:
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError(f"{label} contains non-finite numeric data")
    if isinstance(value, dict):
        for child in value.values():
            _reject_nonfinite(child, label)
    elif isinstance(value, list):
        for child in value:
            _reject_nonfinite(child, label)


def _atomic_write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        with temporary.open("xb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


class MathematicalModelProvider(Protocol):
    provider_id: str
    provider_version: int
    supported_model_ids: tuple[str, ...]


class ProviderRegistry:
    """Static one-owner registry for engine-declared mathematical model IDs."""

    def __init__(self, providers: tuple[MathematicalModelProvider, ...] = ()) -> None:
        self._by_provider_id: dict[str, MathematicalModelProvider] = {}
        self._by_model_id: dict[str, MathematicalModelProvider] = {}
        for provider in providers:
            self.register(provider)

    def register(self, provider: MathematicalModelProvider) -> None:
        provider_id = getattr(provider, "provider_id", None)
        provider_version = getattr(provider, "provider_version", None)
        model_ids = getattr(provider, "supported_model_ids", None)
        if not isinstance(provider_id, str) or not provider_id:
            raise ValueError("Mathematical model provider ID must be nonempty text")
        if isinstance(provider_version, bool) or not isinstance(provider_version, int) or provider_version < 1:
            raise ValueError(f"Mathematical model provider {provider_id} has an invalid version")
        if not isinstance(model_ids, tuple) or not model_ids or any(
            not isinstance(model_id, str) or not model_id for model_id in model_ids
        ):
            raise ValueError(f"Mathematical model provider {provider_id} has invalid model IDs")
        if len(model_ids) != len(set(model_ids)):
            raise ValueError(f"Mathematical model provider {provider_id} repeats a model ID")
        if provider_id in self._by_provider_id:
            raise ValueError(f"Duplicate mathematical model provider ID: {provider_id}")
        conflicts = sorted(model_id for model_id in model_ids if model_id in self._by_model_id)
        if conflicts:
            raise ValueError(f"Duplicate mathematical model ID ownership: {', '.join(conflicts)}")
        self._by_provider_id[provider_id] = provider
        for model_id in model_ids:
            self._by_model_id[model_id] = provider

    def resolve(self, model_id: str) -> MathematicalModelProvider | None:
        return self._by_model_id.get(model_id)


@dataclass(frozen=True)
class CommonFindingProvider:
    provider_id: str = COMMON_PROVIDER_ID
    provider_version: int = 2

    def derive(
        self,
        *,
        manifest: dict[str, Any],
        state: dict[str, Any],
        viewport: dict[str, Any],
        state_sha256: str,
        viewport_sha256: str,
    ) -> dict[str, Any]:
        render = state.get("render")
        view = state.get("view")
        params = state.get("params")
        if not isinstance(render, dict) or not isinstance(view, dict) or not isinstance(params, dict):
            raise ValueError("Packet state.json is missing object-valued render, view, or params authority")
        return {
            "schema_version": ANALYSIS_SCHEMA_VERSION,
            "provider_id": self.provider_id,
            "provider_version": self.provider_version,
            "epistemic_status": "exact_packet_fact",
            "finding_id": manifest["finding_id"],
            "packet_id": manifest["packet_id"],
            "selected_fractal_type": manifest["selected_fractal_type"],
            "selected_fractal_description_status": manifest.get(
                "selected_fractal_description_status", "unavailable"
            ),
            "state": {
                "sha256": state_sha256,
                "state_version": state.get("state_version"),
            },
            "render": {
                "width": render.get("width"),
                "height": render.get("height"),
                "device_id": render.get("device_id"),
            },
            "view": view,
            "iteration_limit": params.get("max_iter"),
            "viewport": {
                "sha256": viewport_sha256,
                "mapping_id": viewport["mapping_id"],
                "camera": viewport["camera"],
                "local_frame": viewport["local_frame"],
                "complex_pixel_basis": viewport["complex_pixel_basis"],
                "continuous_edge_corners": viewport["continuous_edge_corners"],
                "pixel_center_corners": viewport["pixel_center_corners"],
                "axis_aligned_complex_bounds": viewport["axis_aligned_complex_bounds"],
                "fit_model": viewport["fit_model"],
            },
        }


@dataclass(frozen=True)
class FindingEnrichmentResult:
    analysis_id: str
    analysis_dir: Path
    cache_hit: bool


class FindingEnrichmentService:
    """Build immutable enrichment artifacts from one exact Packet V8 authority."""

    def __init__(
        self,
        *,
        workspace_root: Path,
        common_provider: CommonFindingProvider | None = None,
        model_registry: ProviderRegistry | None = None,
    ) -> None:
        self.workspace_root = workspace_root.resolve()
        self.common_provider = common_provider or CommonFindingProvider()
        self.model_registry = model_registry or ProviderRegistry((PolynomialOverPowerEscapeProvider(),))

    def analyze(
        self,
        packet_dir: Path,
        *,
        runtime_executable: Path | None = None,
        runtime_compatibility_mode: str | None = None,
        runtime_timeout_seconds: float = 30.0,
    ) -> FindingEnrichmentResult:
        packet_dir = packet_dir.resolve()
        bundle = load_existing_agent_bundle(packet_dir)
        if bundle.packet_version != 8:
            raise ValueError("Finding enrichment requires an exact Packet V8 bundle")
        expected_packet_root = self.workspace_root / "findings" / bundle.finding_id / "packets"
        try:
            packet_dir.relative_to(expected_packet_root.resolve())
        except ValueError as exc:
            raise ValueError("Packet directory is outside the declared workspace finding authority") from exc

        manifest_bytes = bundle.manifest_path.read_bytes()
        manifest = _load_object(manifest_bytes, "Packet V8 manifest.json")
        state_bytes = (packet_dir / "state.json").read_bytes()
        state = _load_object(state_bytes, "Packet V8 state.json")
        if state.get("fractal_type") != bundle.selected_fractal_type:
            raise ValueError("Packet selected fractal disagrees with state.json")
        render = state.get("render")
        if not isinstance(render, dict):
            raise ValueError("Packet state.json has no render object")
        width = render.get("width")
        height = render.get("height")
        if isinstance(width, bool) or not isinstance(width, int) or width < 1:
            raise ValueError("Packet state.json render.width must be a positive integer")
        if isinstance(height, bool) or not isinstance(height, int) or height < 1:
            raise ValueError("Packet state.json render.height must be a positive integer")

        context = parse_authority_container((packet_dir / "finding-context.md").read_bytes())
        viewport_artifact = context.artifacts.get("fractal-viewport-facts.json")
        if viewport_artifact is None:
            raise ValueError("Packet V8 finding context has no engine-owned viewport facts")
        viewport = validate_viewport_facts_bytes(
            viewport_artifact.payload,
            expected_selector=bundle.selected_fractal_type,
            expected_width=width,
            expected_height=height,
        )
        state_sha256 = _sha256(state_bytes)
        if manifest.get("authority_identities", {}).get("state_sha256") != state_sha256:
            raise ValueError("Packet V8 state authority identity disagrees with state.json")

        common_facts = self.common_provider.derive(
            manifest=manifest,
            state=state,
            viewport=viewport,
            state_sha256=state_sha256,
            viewport_sha256=viewport_artifact.sha256,
        )
        web_frame = manifest.get("web_frame_derivative")
        source_frame_sha256 = web_frame.get("source_sha256") if isinstance(web_frame, dict) else None
        web_frame_sha256 = web_frame.get("derivative_sha256") if isinstance(web_frame, dict) else None
        common_facts["images"] = {
            "source_frame_sha256": source_frame_sha256,
            "web_frame_sha256": web_frame_sha256,
            "web_frame_status": web_frame.get("status") if isinstance(web_frame, dict) else "unavailable",
        }
        active_model_capture = None
        model_provider = None
        active_model_sha256 = None
        runtime_compatibility = None
        if runtime_executable is not None:
            packet_runtime_identity = manifest.get("runtime_identity")
            if not isinstance(packet_runtime_identity, dict):
                raise ValueError("Packet V8 manifest has no runtime identity")
            active_model_capture = ActiveModelRuntimeClient(
                runtime_executable,
                timeout_seconds=runtime_timeout_seconds,
            ).describe(
                state_path=packet_dir / "state.json",
                expected_selector=bundle.selected_fractal_type,
                packet_runtime_identity=packet_runtime_identity,
                compatibility_mode=runtime_compatibility_mode,
            )
            active_model_sha256 = _sha256(active_model_capture.receipt_bytes)
            runtime_compatibility = active_model_capture.runtime_compatibility
            provider_receipt = active_model_capture.receipt.get("provider")
            model_receipt = active_model_capture.receipt.get("model")
            if (
                isinstance(provider_receipt, dict)
                and provider_receipt.get("status") == "available"
                and isinstance(model_receipt, dict)
                and isinstance(model_receipt.get("model_id"), str)
            ):
                model_provider = self.model_registry.resolve(model_receipt["model_id"])

        binding_seed = {
            "analysis_schema_version": ANALYSIS_SCHEMA_VERSION,
            "finding_id": bundle.finding_id,
            "packet_id": bundle.packet_id,
            "manifest_sha256": bundle.manifest_sha256,
            "packet_sha256": bundle.packet_sha256,
            "state_sha256": state_sha256,
            "source_frame_sha256": source_frame_sha256,
            "web_frame_sha256": web_frame_sha256,
            "viewport_facts_sha256": viewport_artifact.sha256,
            "runtime_identity": manifest.get("runtime_identity"),
            "runtime_identity_sha256": manifest.get("runtime_identity_sha256"),
            "common_provider": {
                "provider_id": self.common_provider.provider_id,
                "provider_version": self.common_provider.provider_version,
            },
            "active_model_receipt_sha256": active_model_sha256,
            "active_model_runtime_executable_sha256": (
                active_model_capture.runtime_executable_sha256 if active_model_capture else None
            ),
            "runtime_compatibility": runtime_compatibility,
            "model_provider": (
                {
                    "provider_id": model_provider.provider_id,
                    "provider_version": model_provider.provider_version,
                }
                if model_provider is not None
                else None
            ),
            "semantic_options": (
                {
                    "annotation_builder_version": ANNOTATION_BUILDER_VERSION,
                    "annotation_renderer_version": ANNOTATION_RENDERER_VERSION,
                }
                if model_provider is not None
                else {}
            ),
        }
        analysis_id = _sha256(_json_bytes(binding_seed))
        binding = {
            **binding_seed,
            "analysis_id": analysis_id,
        }
        analysis_dir = self.workspace_root / "findings" / bundle.finding_id / "analyses" / analysis_id
        if active_model_capture is not None and analysis_dir.exists():
            self._validate_receipted_existing(
                analysis_dir,
                analysis_id=analysis_id,
                expected_binding=_json_bytes(binding),
                expected_active_model=active_model_capture.receipt_bytes,
            )
            return FindingEnrichmentResult(analysis_id, analysis_dir.resolve(), True)
        provider_result: dict[str, Any]
        model_artifacts: dict[str, bytes] = {}
        if active_model_capture is None:
            provider_result = self._unavailable_provider_result("active_model_receipt_not_supplied")
        else:
            model_artifacts["active-model-receipt.json"] = active_model_capture.receipt_bytes
            provider_receipt = active_model_capture.receipt["provider"]
            if provider_receipt["status"] == "unavailable":
                provider_result = self._unavailable_provider_result(
                    str(provider_receipt["unavailable_reason"]),
                    model_id=None,
                )
            elif model_provider is None:
                provider_result = self._unavailable_provider_result(
                    "no_registered_provider_for_engine_model",
                    model_id=active_model_capture.receipt["model"].get("model_id"),
                )
            else:
                provider_result, model_artifacts = self._build_model_artifacts(
                    packet_dir=packet_dir,
                    manifest=manifest,
                    viewport=viewport,
                    provider=model_provider,
                    active_model=active_model_capture,
                    analysis_id=analysis_id,
                    initial_artifacts=model_artifacts,
                    runtime_timeout_seconds=runtime_timeout_seconds,
                )
        artifacts = {
            "binding.json": _json_bytes(binding),
            "common-facts.json": _json_bytes(common_facts),
            "provider-result.json": _json_bytes(provider_result),
            **model_artifacts,
        }
        receipt = {
            "schema_version": ANALYSIS_SCHEMA_VERSION,
            "analysis_id": analysis_id,
            "status": "complete",
            "artifact_sha256": {name: _sha256(payload) for name, payload in artifacts.items()},
            "packet_directory": str(packet_dir),
        }
        artifacts["receipt.json"] = _json_bytes(receipt)

        if analysis_dir.exists():
            self._validate_existing(analysis_dir, artifacts)
            return FindingEnrichmentResult(analysis_id, analysis_dir.resolve(), True)
        analysis_dir.parent.mkdir(parents=True, exist_ok=True)
        stage = analysis_dir.parent / f".{analysis_id}.{uuid.uuid4().hex}.tmp"
        stage.mkdir()
        try:
            for name, payload in artifacts.items():
                _atomic_write(stage / name, payload)
            try:
                os.replace(stage, analysis_dir)
            except FileExistsError:
                self._validate_existing(analysis_dir, artifacts)
        finally:
            if stage.exists():
                shutil.rmtree(stage)
        return FindingEnrichmentResult(analysis_id, analysis_dir.resolve(), False)

    @staticmethod
    def _validate_receipted_existing(
        analysis_dir: Path,
        *,
        analysis_id: str,
        expected_binding: bytes,
        expected_active_model: bytes,
    ) -> None:
        receipt_path = analysis_dir / "receipt.json"
        if not receipt_path.is_file():
            raise ValueError("Existing model analysis has no immutable receipt")
        receipt = _load_object(receipt_path.read_bytes(), "Existing model analysis receipt")
        if receipt.get("analysis_id") != analysis_id or receipt.get("status") != "complete":
            raise ValueError("Existing model analysis receipt identity or status changed")
        recorded = receipt.get("artifact_sha256")
        if not isinstance(recorded, dict) or any(
            not isinstance(name, str) or not isinstance(digest, str)
            for name, digest in recorded.items()
        ):
            raise ValueError("Existing model analysis receipt has invalid artifact hashes")
        actual_files = {path.name for path in analysis_dir.iterdir() if path.is_file()}
        if actual_files != set(recorded) | {"receipt.json"}:
            raise ValueError("Existing model analysis artifact set changed after publication")
        for name, digest in recorded.items():
            if _sha256((analysis_dir / name).read_bytes()) != digest:
                raise ValueError(f"Existing model analysis artifact changed after publication: {name}")
        if (analysis_dir / "binding.json").read_bytes() != expected_binding:
            raise ValueError("Existing model analysis binding changed after publication")
        if (analysis_dir / "active-model-receipt.json").read_bytes() != expected_active_model:
            raise ValueError("Existing model analysis active-model receipt changed after publication")

    @staticmethod
    def _unavailable_provider_result(reason: str, *, model_id: str | None = None) -> dict[str, Any]:
        return {
            "schema_version": ANALYSIS_SCHEMA_VERSION,
            "status": "unavailable",
            "reason": reason,
            "provider_id": None,
            "provider_version": None,
            "model_id": model_id,
            "epistemic_status": "exact_packet_fact",
        }

    def _build_model_artifacts(
        self,
        *,
        packet_dir: Path,
        manifest: dict[str, Any],
        viewport: dict[str, Any],
        provider: Any,
        active_model: Any,
        analysis_id: str,
        initial_artifacts: dict[str, bytes],
        runtime_timeout_seconds: float,
    ) -> tuple[dict[str, Any], dict[str, bytes]]:
        provider_result = provider.derive(active_model.receipt)
        annotation_set = build_annotation_set(provider_result, viewport)
        annotations = annotation_set["annotations"]
        points = tuple(complex(item["point"]["real"], item["point"]["imag"]) for item in annotations)
        client = ActiveModelRuntimeClient(
            Path(active_model.command[0]),
            timeout_seconds=runtime_timeout_seconds,
        )
        sample_capture = client.sample(
            state_path=packet_dir / "state.json",
            points=points,
            request_id=f"finding-enrichment-{analysis_id[:24]}",
            active_model=active_model,
        )
        evaluations = []
        for annotation, sample in zip(annotations, sample_capture.response["samples"], strict=True):
            evaluations.append(
                {
                    "annotation_id": annotation["annotation_id"],
                    "point": annotation["point"],
                    "sample": sample,
                    "epistemic_status": "engine_authoritative_evaluation",
                }
            )
        engine_evaluation = {
            "schema_version": 1,
            "evaluation_surface": "fractal.sample",
            "active_model_receipt_sha256": _sha256(active_model.receipt_bytes),
            "runtime_executable_sha256": active_model.runtime_executable_sha256,
            "request_sha256": _sha256(sample_capture.request_bytes),
            "response_sha256": _sha256(sample_capture.response_bytes),
            "command": list(sample_capture.command),
            "request": sample_capture.request,
            "response": sample_capture.response,
            "feature_evaluations": evaluations,
        }
        artifacts = {
            **initial_artifacts,
            "engine-evaluation.json": _json_bytes(engine_evaluation),
            "annotation-set.json": _json_bytes(annotation_set),
        }
        web_frame_path = packet_dir / "web-agent-frame.png"
        if web_frame_path.is_file():
            render = viewport["render"]
            analyses_root = self.workspace_root / "findings" / manifest["finding_id"] / "analyses"
            analyses_root.mkdir(parents=True, exist_ok=True)
            with tempfile.TemporaryDirectory(prefix="annotation-render-", dir=analyses_root) as temp_dir:
                output_path = Path(temp_dir) / "annotated-web-frame.png"
                render_receipt = render_annotations(
                    web_frame_path,
                    output_path,
                    annotation_set,
                    source_viewport_width=render["width"],
                    source_viewport_height=render["height"],
                )
                artifacts["annotated-web-frame.png"] = output_path.read_bytes()
        else:
            render_receipt = {
                "schema_version": 1,
                "status": "unavailable",
                "reason": "packet_has_no_web_discussion_frame",
            }
        artifacts["annotation-render-receipt.json"] = _json_bytes(render_receipt)
        summary_lines = [
            "# Finding Enrichment Summary",
            "",
            f"- Provider: `{provider.provider_id}` version `{provider.provider_version}`",
            f"- Model: `{provider_result['model_id']}`",
            f"- Critical points: `{len(provider_result['features']['critical_points'])}`",
            f"- Fixed points: `{len(provider_result['features']['fixed_points'])}`",
            f"- Structural singular points: `{len(provider_result['features']['structural_singular_points'])}`",
            f"- Canonical engine evaluations: `{len(evaluations)}`",
            f"- Contained annotations: `{sum(item['viewport']['contained'] is True for item in annotations)}`",
            "",
            "Derived equations and numerical roots are analysis evidence. Canonical `fractal.sample`",
            "records are engine evaluation evidence. Neither establishes that an annotated feature caused",
            "the visible image structure.",
            "",
        ]
        artifacts["summary.md"] = "\n".join(summary_lines).encode("utf-8")
        return provider_result, artifacts

    @staticmethod
    def _validate_existing(analysis_dir: Path, artifacts: dict[str, bytes]) -> None:
        actual_files = {path.name for path in analysis_dir.iterdir() if path.is_file()}
        if actual_files != set(artifacts):
            raise ValueError("Existing analysis artifact set changed after publication")
        for name, expected in artifacts.items():
            path = analysis_dir / name
            if path.read_bytes() != expected:
                raise ValueError(f"Existing analysis artifact changed after publication: {name}")
