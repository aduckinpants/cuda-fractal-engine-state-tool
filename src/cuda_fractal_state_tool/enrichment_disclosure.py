from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from .agent_bundle import load_existing_agent_bundle
from .finding_enrichment import FindingEnrichmentService
from .json_utils import loads_strict_no_duplicates


DISCLOSURE_MANIFEST_VERSION = 1
_ASSISTED_ARTIFACTS = (
    ("common-facts.json", "enrichment_common_facts", "file"),
    ("provider-result.json", "enrichment_model_result", "file"),
    ("engine-evaluation.json", "enrichment_engine_evaluation", "file"),
    ("annotation-set.json", "enrichment_annotation_set", "file"),
    ("summary.md", "enrichment_summary", "file"),
    ("annotated-web-frame.png", "enrichment_annotated_frame", "vision"),
)


class DisclosureProfile(str, Enum):
    BLIND = "blind"
    ASSISTED = "assisted"
    BREAK_BLIND = "break_blind"


@dataclass(frozen=True)
class DisclosureResource:
    transport_filename: str
    analysis_filename: str
    role: str
    media_role: str
    sha256: str
    size_bytes: int
    local_path: Path
    payload: bytes


@dataclass(frozen=True)
class EnrichmentDisclosure:
    disclosure_id: str
    profile: DisclosureProfile
    packet_id: str
    packet_manifest_sha256: str
    finding_id: str
    analysis_id: str | None
    manifest: dict[str, Any]
    manifest_bytes: bytes
    resources: tuple[DisclosureResource, ...]


def _json_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n"
    ).encode("utf-8")


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _load_object(path: Path, label: str) -> dict[str, Any]:
    try:
        value = loads_strict_no_duplicates(path.read_bytes().decode("utf-8"))
    except (OSError, UnicodeError, ValueError) as exc:
        raise ValueError(f"{label} is unavailable or malformed: {path}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a JSON object")
    return value


def build_blind_disclosure(bundle: Any) -> EnrichmentDisclosure:
    seed = {
        "disclosure_manifest_version": DISCLOSURE_MANIFEST_VERSION,
        "profile": DisclosureProfile.BLIND.value,
        "packet_id": bundle.packet_id,
        "packet_manifest_sha256": bundle.manifest_sha256,
        "finding_id": bundle.finding_id,
        "analysis_id": None,
        "resources": [],
    }
    disclosure_id = _sha256(_json_bytes(seed))
    manifest = {**seed, "disclosure_id": disclosure_id}
    return EnrichmentDisclosure(
        disclosure_id=disclosure_id,
        profile=DisclosureProfile.BLIND,
        packet_id=bundle.packet_id,
        packet_manifest_sha256=bundle.manifest_sha256,
        finding_id=bundle.finding_id,
        analysis_id=None,
        manifest=manifest,
        manifest_bytes=_json_bytes(manifest),
        resources=(),
    )


class FindingDisclosureService:
    """Select exact immutable enrichment outputs without changing analysis identity."""

    def __init__(
        self,
        *,
        workspace_root: Path,
        runtime_executable: Path,
        runtime_compatibility_mode: str | None = None,
        enrichment: FindingEnrichmentService | None = None,
    ) -> None:
        self.workspace_root = workspace_root.resolve()
        self.runtime_executable = runtime_executable.resolve()
        self.runtime_compatibility_mode = runtime_compatibility_mode
        self.enrichment = enrichment or FindingEnrichmentService(workspace_root=self.workspace_root)

    def prepare(
        self,
        packet_dir: Path,
        profile: DisclosureProfile,
    ) -> EnrichmentDisclosure:
        packet_dir = packet_dir.resolve()
        bundle = load_existing_agent_bundle(packet_dir)
        if bundle.packet_version != 8:
            raise ValueError("Enrichment disclosure requires Packet V8")
        analysis_dir: Path | None = None
        analysis_id: str | None = None
        selected: list[DisclosureResource] = []
        if profile is DisclosureProfile.BLIND:
            return build_blind_disclosure(bundle)
        else:
            result = self.enrichment.analyze(
                packet_dir,
                runtime_executable=self.runtime_executable,
                runtime_compatibility_mode=self.runtime_compatibility_mode,
            )
            analysis_dir = result.analysis_dir
            analysis_id = result.analysis_id
            selected = self._select_assisted_resources(analysis_dir, analysis_id)
        records = [
            {
                "analysis_filename": item.analysis_filename,
                "transport_filename": item.transport_filename,
                "role": item.role,
                "media_role": item.media_role,
                "sha256": item.sha256,
                "size_bytes": item.size_bytes,
            }
            for item in selected
        ]
        seed = {
            "disclosure_manifest_version": DISCLOSURE_MANIFEST_VERSION,
            "profile": profile.value,
            "packet_id": bundle.packet_id,
            "packet_manifest_sha256": bundle.manifest_sha256,
            "finding_id": bundle.finding_id,
            "analysis_id": analysis_id,
            "resources": records,
        }
        disclosure_id = _sha256(_json_bytes(seed))
        manifest = {**seed, "disclosure_id": disclosure_id}
        return EnrichmentDisclosure(
            disclosure_id=disclosure_id,
            profile=profile,
            packet_id=bundle.packet_id,
            packet_manifest_sha256=bundle.manifest_sha256,
            finding_id=bundle.finding_id,
            analysis_id=analysis_id,
            manifest=manifest,
            manifest_bytes=_json_bytes(manifest),
            resources=tuple(selected),
        )

    @staticmethod
    def _select_assisted_resources(
        analysis_dir: Path,
        analysis_id: str,
    ) -> list[DisclosureResource]:
        receipt = _load_object(analysis_dir / "receipt.json", "Analysis receipt")
        if receipt.get("analysis_id") != analysis_id or receipt.get("status") != "complete":
            raise ValueError("Analysis receipt does not authorize disclosure")
        recorded = receipt.get("artifact_sha256")
        if not isinstance(recorded, dict):
            raise ValueError("Analysis receipt has no artifact hash ledger")
        selected: list[DisclosureResource] = []
        prefix = f"enrichment-{analysis_id[:12]}-"
        for filename, role, media_role in _ASSISTED_ARTIFACTS:
            expected = recorded.get(filename)
            path = analysis_dir / filename
            if expected is None:
                continue
            if not isinstance(expected, str) or not path.is_file():
                raise ValueError(f"Receipted enrichment artifact is unavailable: {filename}")
            payload = path.read_bytes()
            if _sha256(payload) != expected:
                raise ValueError(f"Receipted enrichment artifact changed: {filename}")
            selected.append(
                DisclosureResource(
                    transport_filename=prefix + filename,
                    analysis_filename=filename,
                    role=role,
                    media_role=media_role,
                    sha256=expected,
                    size_bytes=len(payload),
                    local_path=path.resolve(),
                    payload=payload,
                )
            )
        required = {"common-facts.json", "provider-result.json"}
        if required.difference(item.analysis_filename for item in selected):
            raise ValueError("Analysis is missing the required assisted disclosure facts")
        return selected
