from __future__ import annotations

import hashlib
import json
import os
import shutil
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from .proposal import ProposalV1
from .workspace_layout import initialize_workspace_root


FINDING_KEY_SCHEMA = "finding-key-v1"
PROPOSAL_KEY_SCHEMA = "proposal-key-v1"
WORKSPACE_MANIFEST_SCHEMA_VERSION = 1
FINDINGS_INDEX_FILENAME = "findings_index.json"
WORKSPACE_LOCK_FILENAME = ".workspace-import.lock"

_PRIMARY_FRAME_EXTENSIONS = {".bmp", ".png", ".jpg", ".jpeg", ".webp"}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 64), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(f"{path.name}.tmp.{uuid.uuid4().hex}")
    with temp_path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(str(temp_path), str(path))


def _atomic_write_json(path: Path, payload: Any) -> None:
    _atomic_write_text(path, json.dumps(payload, indent=2, sort_keys=True) + "\n")


@contextmanager
def _workspace_lock(workspace_root: Path) -> Iterable[None]:
    lock_path = workspace_root / WORKSPACE_LOCK_FILENAME
    fd: int | None = None
    try:
        fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.write(fd, str(os.getpid()).encode("utf-8"))
        yield
    except FileExistsError as exc:
        raise RuntimeError(f"Workspace import lock already held: {lock_path}") from exc
    finally:
        if fd is not None:
            os.close(fd)
        if lock_path.exists():
            lock_path.unlink(missing_ok=True)


@dataclass(frozen=True)
class ResolvedCapture:
    input_path: Path
    resolution_mode: str
    bundle_root: Path
    state_path: Path
    finding_manifest_path: Path | None
    primary_frame_path: Path | None


@dataclass(frozen=True)
class ImportResult:
    finding_id: str
    finding_dir: Path
    workspace_manifest_path: Path
    findings_index_path: Path
    workspace_index_updated: bool
    authoring_base_state_sha256: str


class SourceCaptureImporter:
    def __init__(self, workspace_root: Path) -> None:
        self.workspace_root = workspace_root.resolve()
        initialize_workspace_root(self.workspace_root)

    @property
    def findings_root(self) -> Path:
        return self.workspace_root / "findings"

    @property
    def findings_index_path(self) -> Path:
        return self.workspace_root / FINDINGS_INDEX_FILENAME

    def import_capture(self, source_path: Path) -> ImportResult:
        resolved = self.resolve_capture(source_path)
        state_sha256 = _sha256_file(resolved.state_path)
        finding_sha256 = _sha256_file(resolved.finding_manifest_path) if resolved.finding_manifest_path else None
        frame_sha256 = _sha256_file(resolved.primary_frame_path) if resolved.primary_frame_path else None
        finding_id = compute_finding_id(state_sha256, finding_sha256, frame_sha256)

        finding_dir = self.findings_root / finding_id
        source_dir = finding_dir / "source"
        workspace_manifest_path = finding_dir / "workspace.json"

        with _workspace_lock(self.workspace_root):
            source_dir.mkdir(parents=True, exist_ok=True)
            proposals_dir = finding_dir / "proposals"
            packets_dir = finding_dir / "packets"
            proposals_dir.mkdir(parents=True, exist_ok=True)
            packets_dir.mkdir(parents=True, exist_ok=True)

            self._copy_required_source_artifacts(resolved, source_dir)
            manifest_payload = self._build_workspace_manifest(
                finding_id,
                resolved,
                source_dir,
                state_sha256,
                finding_sha256,
                frame_sha256,
            )
            _atomic_write_json(workspace_manifest_path, manifest_payload)

            index_updated = True
            try:
                self._update_findings_index_from_scan()
            except Exception:
                index_updated = False

        return ImportResult(
            finding_id=finding_id,
            finding_dir=finding_dir,
            workspace_manifest_path=workspace_manifest_path,
            findings_index_path=self.findings_index_path,
            workspace_index_updated=index_updated,
            authoring_base_state_sha256=state_sha256,
        )

    def resolve_capture(self, source_path: Path) -> ResolvedCapture:
        input_path = source_path.resolve()
        if not input_path.exists():
            raise FileNotFoundError(f"Capture input does not exist: {input_path}")

        if input_path.is_dir():
            bundle_root = self._resolve_bundle_from_directory(input_path)
            resolution_mode = "directory"
            primary_frame_path = self._discover_primary_frame(bundle_root)
        else:
            name = input_path.name.lower()
            if name == "state.json":
                bundle_root = input_path.parent
                resolution_mode = "state_json"
                primary_frame_path = self._discover_primary_frame(bundle_root)
            elif name == "finding.json":
                bundle_root = input_path.parent
                resolution_mode = "finding_json"
                primary_frame_path = self._discover_primary_frame(bundle_root)
            else:
                bundle_root = self._resolve_bundle_from_primary_frame(input_path)
                resolution_mode = "primary_frame"
                primary_frame_path = input_path

        state_path = bundle_root / "state.json"
        if not state_path.exists():
            raise ValueError(f"Resolved capture bundle has no state.json: {bundle_root}")

        finding_manifest = bundle_root / "finding.json"
        finding_manifest_path = finding_manifest if finding_manifest.exists() else None
        return ResolvedCapture(
            input_path=input_path,
            resolution_mode=resolution_mode,
            bundle_root=bundle_root,
            state_path=state_path,
            finding_manifest_path=finding_manifest_path,
            primary_frame_path=primary_frame_path,
        )

    def rebuild_findings_index(self) -> Path:
        with _workspace_lock(self.workspace_root):
            self._update_findings_index_from_scan()
        return self.findings_index_path

    def _resolve_bundle_from_directory(self, directory: Path) -> Path:
        candidates = sorted(directory.rglob("state.json"))
        if not candidates:
            raise ValueError(f"No state.json found under directory: {directory}")
        if len(candidates) > 1:
            joined = ", ".join(str(path) for path in candidates[:5])
            raise ValueError(
                "Capture directory is ambiguous: multiple state.json candidates found. "
                f"Examples: {joined}"
            )
        return candidates[0].parent

    def _resolve_bundle_from_primary_frame(self, frame_path: Path) -> Path:
        if not frame_path.is_file():
            raise ValueError(f"Primary frame input must be a file: {frame_path}")
        candidates: list[Path] = []
        cursor = frame_path.parent
        seen: set[Path] = set()
        while True:
            marker = cursor / "state.json"
            if marker.exists() and cursor not in seen:
                seen.add(cursor)
                candidates.append(cursor)
            if cursor.parent == cursor:
                break
            cursor = cursor.parent
        if not candidates:
            raise ValueError(
                "Primary frame path could not be resolved to a capture bundle with state.json in an ancestor directory"
            )
        if len(candidates) > 1:
            joined = ", ".join(str(path) for path in candidates)
            raise ValueError(f"Primary frame path is ambiguous across multiple capture bundles: {joined}")
        return candidates[0]

    def _discover_primary_frame(self, bundle_root: Path) -> Path | None:
        candidates: list[Path] = []
        for candidate in sorted(bundle_root.iterdir()):
            if not candidate.is_file():
                continue
            if candidate.suffix.lower() not in _PRIMARY_FRAME_EXTENSIONS:
                continue
            if candidate.stem.lower().startswith("frame"):
                candidates.append(candidate)
        if len(candidates) > 1:
            joined = ", ".join(str(path) for path in candidates)
            raise ValueError(f"Capture bundle has ambiguous primary frame candidates: {joined}")
        return candidates[0] if candidates else None

    def _copy_required_source_artifacts(self, resolved: ResolvedCapture, source_dir: Path) -> None:
        self._copy_if_changed(resolved.state_path, source_dir / "state.json")
        if resolved.finding_manifest_path:
            self._copy_if_changed(resolved.finding_manifest_path, source_dir / "finding.json")
        if resolved.primary_frame_path:
            self._copy_if_changed(resolved.primary_frame_path, source_dir / resolved.primary_frame_path.name)

    def _copy_if_changed(self, source: Path, destination: Path) -> None:
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            if _sha256_file(source) == _sha256_file(destination):
                return
            raise ValueError(
                "Destination artifact differs from source for identical finding identity. "
                f"Refusing overwrite: {destination}"
            )
        shutil.copy2(source, destination)

    def _build_workspace_manifest(
        self,
        finding_id: str,
        resolved: ResolvedCapture,
        source_dir: Path,
        state_sha256: str,
        finding_sha256: str | None,
        frame_sha256: str | None,
    ) -> dict[str, Any]:
        manifest_path = source_dir.parent / "workspace.json"
        previous = {}
        if manifest_path.exists():
            loaded = json.loads(manifest_path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                previous = loaded

        source_aliases: list[str] = []
        existing_aliases = previous.get("source_aliases")
        if isinstance(existing_aliases, list):
            source_aliases.extend(str(item) for item in existing_aliases if isinstance(item, str))
        source_aliases.extend(
            [
                str(resolved.bundle_root),
                str(resolved.input_path),
            ]
        )

        deduped_aliases: list[str] = []
        seen: set[str] = set()
        for item in source_aliases:
            if item in seen:
                continue
            seen.add(item)
            deduped_aliases.append(item)

        imported_at = previous.get("imported_at_utc") if isinstance(previous.get("imported_at_utc"), str) else _utc_now()
        return {
            "workspace_manifest_schema_version": WORKSPACE_MANIFEST_SCHEMA_VERSION,
            "finding_key_schema": FINDING_KEY_SCHEMA,
            "finding_id": finding_id,
            "imported_at_utc": imported_at,
            "last_imported_at_utc": _utc_now(),
            "resolution": {
                "input_path": str(resolved.input_path),
                "resolution_mode": resolved.resolution_mode,
                "bundle_root": str(resolved.bundle_root),
                "state_path": str(resolved.state_path),
                "finding_manifest_path": str(resolved.finding_manifest_path) if resolved.finding_manifest_path else None,
                "primary_frame_path": str(resolved.primary_frame_path) if resolved.primary_frame_path else None,
            },
            "authoring_base": {
                "state_path": "source/state.json",
                "sha256": state_sha256,
            },
            "source_artifacts": {
                "state": {
                    "workspace_path": "source/state.json",
                    "sha256": state_sha256,
                },
                "finding_manifest": {
                    "workspace_path": "source/finding.json" if finding_sha256 else None,
                    "sha256": finding_sha256,
                },
                "primary_frame": {
                    "workspace_path": f"source/{resolved.primary_frame_path.name}" if frame_sha256 and resolved.primary_frame_path else None,
                    "sha256": frame_sha256,
                },
            },
            "paths": {
                "source_dir": "source",
                "packets_dir": "packets",
                "proposals_dir": "proposals",
            },
            "source_aliases": deduped_aliases,
        }

    def _update_findings_index_from_scan(self) -> None:
        entries: list[dict[str, Any]] = []
        findings_root = self.findings_root
        if findings_root.exists():
            for finding_dir in sorted(path for path in findings_root.iterdir() if path.is_dir()):
                manifest_path = finding_dir / "workspace.json"
                if not manifest_path.exists():
                    continue
                payload = json.loads(manifest_path.read_text(encoding="utf-8"))
                if not isinstance(payload, dict):
                    continue
                entries.append(
                    {
                        "finding_id": payload.get("finding_id"),
                        "workspace_manifest_path": str(manifest_path.resolve()),
                        "last_imported_at_utc": payload.get("last_imported_at_utc"),
                        "authoring_base_sha256": (payload.get("authoring_base") or {}).get("sha256"),
                    }
                )
        index_payload = {
            "index_schema_version": 1,
            "generated_at_utc": _utc_now(),
            "entries": entries,
        }
        _atomic_write_json(self.findings_index_path, index_payload)


def compute_finding_id(
    state_sha256: str,
    finding_manifest_sha256: str | None,
    primary_frame_sha256: str | None,
) -> str:
    payload = {
        "key_schema": FINDING_KEY_SCHEMA,
        "state_sha256": state_sha256,
        "finding_manifest_sha256": finding_manifest_sha256,
        "primary_frame_sha256": primary_frame_sha256,
    }
    return _sha256_bytes(_canonical_json_bytes(payload))


def canonical_validated_override_map(overrides: dict[str, Any]) -> dict[str, Any]:
    # Normalize through JSON to ensure deterministic typing and recursive key ordering.
    return json.loads(_canonical_json_bytes(overrides).decode("utf-8"))


def compute_proposal_id(
    proposal: ProposalV1,
    finding_id: str,
    authoring_base_state_sha256: str,
) -> str:
    payload = {
        "key_schema": PROPOSAL_KEY_SCHEMA,
        "finding_id": finding_id,
        "authoring_base_state_sha256": authoring_base_state_sha256,
        "proposal_version": proposal.proposal_version,
        "overrides": canonical_validated_override_map(dict(proposal.overrides)),
    }
    return _sha256_bytes(_canonical_json_bytes(payload))


def build_validation_run_id() -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
    return f"{stamp}_{uuid.uuid4().hex[:8]}"
