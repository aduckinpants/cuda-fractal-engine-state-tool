from __future__ import annotations

import hashlib
import json
import math
import os
import shutil
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from .agent_bundle import load_existing_agent_bundle
from .authority_container import parse_authority_container
from .fractal_viewport_facts import validate_viewport_facts_bytes
from .json_utils import loads_no_duplicates


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
        self.model_registry = model_registry or ProviderRegistry()

    def analyze(self, packet_dir: Path) -> FindingEnrichmentResult:
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
            "active_model_receipt_sha256": None,
            "model_provider": None,
            "semantic_options": {},
        }
        analysis_id = _sha256(_json_bytes(binding_seed))
        binding = {
            **binding_seed,
            "analysis_id": analysis_id,
        }
        provider_result = {
            "schema_version": ANALYSIS_SCHEMA_VERSION,
            "status": "unavailable",
            "reason": "active_model_receipt_not_supplied",
            "provider_id": None,
            "provider_version": None,
            "model_id": None,
            "epistemic_status": "exact_packet_fact",
        }
        artifacts = {
            "binding.json": _json_bytes(binding),
            "common-facts.json": _json_bytes(common_facts),
            "provider-result.json": _json_bytes(provider_result),
        }
        receipt = {
            "schema_version": ANALYSIS_SCHEMA_VERSION,
            "analysis_id": analysis_id,
            "status": "complete",
            "artifact_sha256": {name: _sha256(payload) for name, payload in artifacts.items()},
            "packet_directory": str(packet_dir),
        }
        artifacts["receipt.json"] = _json_bytes(receipt)

        analysis_dir = self.workspace_root / "findings" / bundle.finding_id / "analyses" / analysis_id
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
    def _validate_existing(analysis_dir: Path, artifacts: dict[str, bytes]) -> None:
        actual_files = {path.name for path in analysis_dir.iterdir() if path.is_file()}
        if actual_files != set(artifacts):
            raise ValueError("Existing analysis artifact set changed after publication")
        for name, expected in artifacts.items():
            path = analysis_dir / name
            if path.read_bytes() != expected:
                raise ValueError(f"Existing analysis artifact changed after publication: {name}")
