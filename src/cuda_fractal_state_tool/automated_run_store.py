from __future__ import annotations

import json
import os
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .workspace_layout import initialize_workspace_root


AUTOMATED_RUN_MANIFEST_VERSION = 1
AUTOMATED_EVENT_VERSION = 1
ACTIVE_TURN_VERSION = 1
ATOMIC_REPLACE_ATTEMPTS = 12
ATOMIC_REPLACE_DELAY_SECONDS = 0.025


class AtomicWriteError(RuntimeError):
    def __init__(self, path: Path, attempts: int, cause: OSError) -> None:
        super().__init__(
            f"Atomic replacement failed after {attempts} attempts: {path}: {cause}"
        )
        self.path = path
        self.attempts = attempts
        self.cause = cause


class RunStoreWriteError(RuntimeError):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        event_appended: bool,
        event_sequence: int | None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.event_appended = event_appended
        self.event_sequence = event_sequence


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode(
        "utf-8"
    )


def _compact_json_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _is_retryable_replace_error(exc: OSError) -> bool:
    if os.name != "nt":
        return False
    return isinstance(exc, PermissionError) or getattr(exc, "winerror", None) in {5, 32}


def _atomic_write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        with temporary.open("xb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        for attempt in range(1, ATOMIC_REPLACE_ATTEMPTS + 1):
            try:
                os.replace(temporary, path)
                break
            except OSError as exc:
                if not _is_retryable_replace_error(exc) or attempt == ATOMIC_REPLACE_ATTEMPTS:
                    raise AtomicWriteError(path, attempt, exc) from exc
                time.sleep(ATOMIC_REPLACE_DELAY_SECONDS * attempt)
    finally:
        temporary.unlink(missing_ok=True)


def _load_object(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"{label} is unavailable or malformed: {path}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{label} is not a JSON object: {path}")
    return value


@dataclass(frozen=True)
class AutomatedRunStore:
    run_dir: Path
    _projection_lock: threading.RLock = field(
        default_factory=threading.RLock,
        init=False,
        repr=False,
        compare=False,
    )

    @classmethod
    def create(
        cls,
        workspace_root: Path,
        *,
        run_id: str,
        protocol_snapshot: dict[str, Any],
        initial_packet: dict[str, Any],
    ) -> "AutomatedRunStore":
        workspace_root = workspace_root.resolve()
        initialize_workspace_root(workspace_root)
        if not run_id or Path(run_id).name != run_id:
            raise ValueError("Automated run ID must be a safe directory name")
        run_dir = workspace_root / "automated-runs" / run_id
        try:
            run_dir.mkdir(parents=True, exist_ok=False)
        except FileExistsError as exc:
            raise FileExistsError(f"Automated run already exists: {run_dir}") from exc
        manifest = {
            "automated_run_manifest_version": AUTOMATED_RUN_MANIFEST_VERSION,
            "run_id": run_id,
            "created_at_utc": _utc_now(),
            "protocol_snapshot": protocol_snapshot,
            "initial_packet": initial_packet,
        }
        _atomic_write(run_dir / "manifest.json", _json_bytes(manifest))
        (run_dir / "rounds").mkdir()
        return cls(run_dir=run_dir.resolve())

    @classmethod
    def open(cls, run_dir: Path) -> "AutomatedRunStore":
        store = cls(run_dir=run_dir.resolve())
        manifest = _load_object(store.manifest_path, "Automated run manifest")
        if manifest.get("automated_run_manifest_version") != AUTOMATED_RUN_MANIFEST_VERSION:
            raise ValueError("Unsupported automated run manifest version")
        if manifest.get("run_id") != store.run_dir.name:
            raise ValueError("Automated run identity disagrees with its directory")
        return store

    @property
    def manifest_path(self) -> Path:
        return self.run_dir / "manifest.json"

    @property
    def events_path(self) -> Path:
        return self.run_dir / "events.ndjson"

    @property
    def active_turn_path(self) -> Path:
        return self.run_dir / "active-turn.json"

    def write_evidence_json(self, relative_path: str, value: Any) -> Path:
        """Atomically retain sanitized orchestration evidence below this run."""
        path = self._evidence_path(relative_path)
        try:
            _atomic_write(path, _json_bytes(value))
        except AtomicWriteError as exc:
            raise RunStoreWriteError(
                "EVIDENCE_JSON_WRITE_FAILED",
                str(exc),
                event_appended=False,
                event_sequence=None,
            ) from exc
        return path

    def write_evidence_bytes(self, relative_path: str, payload: bytes) -> Path:
        path = self._evidence_path(relative_path)
        try:
            _atomic_write(path, payload)
        except AtomicWriteError as exc:
            raise RunStoreWriteError(
                "EVIDENCE_BYTES_WRITE_FAILED",
                str(exc),
                event_appended=False,
                event_sequence=None,
            ) from exc
        return path

    def _evidence_path(self, relative_path: str) -> Path:
        candidate = Path(relative_path)
        if (
            not relative_path
            or candidate.is_absolute()
            or ".." in candidate.parts
            or candidate.name in {"", ".", ".."}
        ):
            raise ValueError("Automated evidence path must be a safe relative path")
        resolved = (self.run_dir / candidate).resolve()
        if self.run_dir not in resolved.parents:
            raise ValueError("Automated evidence path escapes its run directory")
        return resolved

    def read_events(self) -> list[dict[str, Any]]:
        with self._projection_lock:
            if not self.events_path.exists():
                return []
            events: list[dict[str, Any]] = []
            for line_number, line in enumerate(
                self.events_path.read_text(encoding="utf-8").splitlines(), start=1
            ):
                try:
                    event = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise ValueError(f"Automated event line {line_number} is malformed") from exc
                if not isinstance(event, dict):
                    raise ValueError(f"Automated event line {line_number} is not an object")
                if event.get("event_version") != AUTOMATED_EVENT_VERSION:
                    raise ValueError(
                        f"Automated event line {line_number} has an unsupported version"
                    )
                if event.get("sequence") != line_number:
                    raise ValueError("Automated event history has a sequence gap or duplicate")
                if not isinstance(event.get("projection"), dict):
                    raise ValueError("Automated event has no current-state projection")
                events.append(event)
            return events

    def record_transition(
        self,
        event_type: str,
        payload: dict[str, Any],
        projection: dict[str, Any],
    ) -> dict[str, Any]:
        if not event_type.strip():
            raise ValueError("Automated event type is required")
        with self._projection_lock:
            events = self.read_events()
            event = {
                "event_version": AUTOMATED_EVENT_VERSION,
                "sequence": len(events) + 1,
                "recorded_at_utc": _utc_now(),
                "event_type": event_type,
                "payload": payload,
                "projection": projection,
            }
            self.events_path.parent.mkdir(parents=True, exist_ok=True)
            with self.events_path.open("ab") as handle:
                handle.write(_compact_json_bytes(event))
                handle.flush()
                os.fsync(handle.fileno())
            try:
                self._write_active_turn(event["sequence"], projection)
            except RunStoreWriteError as exc:
                raise RunStoreWriteError(
                    "ACTIVE_TURN_PROJECTION_WRITE_FAILED_AFTER_EVENT_APPEND",
                    str(exc),
                    event_appended=True,
                    event_sequence=event["sequence"],
                ) from exc
            return event

    def _write_active_turn(self, sequence: int, projection: dict[str, Any]) -> None:
        active = {
            "active_turn_version": ACTIVE_TURN_VERSION,
            "last_event_sequence": sequence,
            "projection": projection,
        }
        try:
            _atomic_write(self.active_turn_path, _json_bytes(active))
        except AtomicWriteError as exc:
            raise RunStoreWriteError(
                "ACTIVE_TURN_PROJECTION_WRITE_FAILED",
                str(exc),
                event_appended=False,
                event_sequence=sequence,
            ) from exc

    def load_active_turn(self) -> dict[str, Any]:
        with self._projection_lock:
            active = _load_object(self.active_turn_path, "Automated active-turn projection")
            if active.get("active_turn_version") != ACTIVE_TURN_VERSION:
                raise ValueError("Unsupported automated active-turn version")
            return active

    def load_live_snapshot(self) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
        """Read the derived projection and append-only events under one in-process lock."""
        with self._projection_lock:
            active = self.load_active_turn() if self.active_turn_path.is_file() else None
            return active, self.read_events()

    def recover_active_turn(self) -> dict[str, Any]:
        with self._projection_lock:
            events = self.read_events()
            if not events:
                raise ValueError("Automated run has no event history to recover")
            latest = events[-1]
            expected_sequence = latest["sequence"]
            expected_projection = latest["projection"]
            if not self.active_turn_path.exists():
                self._write_active_turn(expected_sequence, expected_projection)
                return expected_projection
            active = self.load_active_turn()
            active_sequence = active.get("last_event_sequence")
            if not isinstance(active_sequence, int):
                raise ValueError("Automated active-turn projection has no valid event sequence")
            if active_sequence > expected_sequence:
                raise ValueError("Automated active-turn projection is ahead of event history")
            if active_sequence < expected_sequence:
                self._write_active_turn(expected_sequence, expected_projection)
                return expected_projection
            if active.get("projection") != expected_projection:
                raise ValueError("Automated active-turn projection disagrees with event history")
            return expected_projection
