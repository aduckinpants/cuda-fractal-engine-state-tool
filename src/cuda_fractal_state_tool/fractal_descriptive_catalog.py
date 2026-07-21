from __future__ import annotations

import hashlib
import os
import re
import subprocess
import tempfile
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from .async_jobs import JobContext
from .json_utils import loads_no_duplicates
from .runtime_surface import build_runtime_command


CATALOG_SCHEMA_VERSION = 1
CACHE_NAMESPACE = "fractal-descriptive-catalog-v1"

_ENTRY_FIELDS = {
    "selector_id",
    "display_name",
    "category",
    "family",
    "formula_growth_surface",
    "capability_flags",
    "runtime_flags",
    "description_status",
    "description",
}
_DESCRIPTION_FIELDS = {
    "math_summary",
    "recurrence_or_field_model",
    "state_order",
    "termination_or_classification",
    "interpretation_notes",
    "source_refs",
}
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class SelectedFractalDescription:
    catalog_sha256: str
    cache_path: Path
    entry: dict[str, Any]


def _require_nonempty_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Fractal descriptive catalog {label} must be a non-empty string")
    return value


def _validate_string_collection(value: Any, label: str) -> None:
    if not isinstance(value, list):
        raise ValueError(f"Fractal descriptive catalog {label} must be an array")
    seen: set[str] = set()
    for item in value:
        text = _require_nonempty_string(item, f"{label} item")
        if text in seen:
            raise ValueError(f"Fractal descriptive catalog {label} contains duplicate value: {text}")
        seen.add(text)


def _validate_description(selector: str, description: Any) -> None:
    if not isinstance(description, dict):
        raise ValueError(f"Reviewed fractal descriptive catalog entry {selector} has no description object")
    fields = set(description)
    if fields != _DESCRIPTION_FIELDS:
        missing = sorted(_DESCRIPTION_FIELDS - fields)
        unknown = sorted(fields - _DESCRIPTION_FIELDS)
        raise ValueError(
            f"Reviewed fractal descriptive catalog entry {selector} has invalid description fields; "
            f"missing={missing}, unknown={unknown}"
        )
    for field in (
        "math_summary",
        "recurrence_or_field_model",
        "state_order",
        "termination_or_classification",
        "interpretation_notes",
    ):
        _require_nonempty_string(description.get(field), f"{selector}.description.{field}")
    source_refs = description.get("source_refs")
    _validate_string_collection(source_refs, f"{selector}.description.source_refs")
    if not source_refs:
        raise ValueError(f"Reviewed fractal descriptive catalog entry {selector} has no source_refs")
    for source_ref in source_refs:
        source_path = source_ref.split("#", 1)[0]
        source_parts = source_path.split("/")
        if (
            source_ref.startswith(("/", "\\"))
            or "\\" in source_ref
            or re.match(r"^[A-Za-z]:", source_ref)
            or "://" in source_ref
            or any(part in {"", ".", ".."} for part in source_parts)
        ):
            raise ValueError(
                f"Reviewed fractal descriptive catalog entry {selector} has a non-repository-relative source_ref"
            )


def _validate_catalog(catalog_bytes: bytes) -> dict[str, dict[str, Any]]:
    try:
        catalog_text = catalog_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("Fractal descriptive catalog is not valid UTF-8") from exc
    payload = loads_no_duplicates(catalog_text)
    if not isinstance(payload, dict) or set(payload) != {"schema_version", "entries"}:
        raise ValueError("Fractal descriptive catalog root must contain only schema_version and entries")
    if payload.get("schema_version") != CATALOG_SCHEMA_VERSION:
        raise ValueError(
            f"Unsupported fractal descriptive catalog schema_version: {payload.get('schema_version')}"
        )
    entries = payload.get("entries")
    if not isinstance(entries, list) or not entries:
        raise ValueError("Fractal descriptive catalog entries must be a non-empty array")

    by_selector: dict[str, dict[str, Any]] = {}
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise ValueError(f"Fractal descriptive catalog entry {index} must be an object")
        fields = set(entry)
        if fields != _ENTRY_FIELDS:
            missing = sorted(_ENTRY_FIELDS - fields)
            unknown = sorted(fields - _ENTRY_FIELDS)
            raise ValueError(
                f"Fractal descriptive catalog entry {index} has invalid fields; missing={missing}, unknown={unknown}"
            )
        selector = _require_nonempty_string(entry.get("selector_id"), f"entry {index}.selector_id")
        if selector in by_selector:
            raise ValueError(f"Fractal descriptive catalog contains duplicate selector_id: {selector}")
        for field in ("display_name", "category", "family", "formula_growth_surface"):
            _require_nonempty_string(entry.get(field), f"{selector}.{field}")
        _validate_string_collection(entry.get("capability_flags"), f"{selector}.capability_flags")
        _validate_string_collection(entry.get("runtime_flags"), f"{selector}.runtime_flags")
        status = entry.get("description_status")
        if status == "reviewed":
            _validate_description(selector, entry.get("description"))
        elif status == "unavailable":
            if entry.get("description") is not None:
                raise ValueError(
                    f"Unavailable fractal descriptive catalog entry {selector} must have a null description"
                )
        else:
            raise ValueError(
                f"Fractal descriptive catalog entry {selector} has unsupported description_status: {status}"
            )
        by_selector[selector] = entry
    return by_selector


def _atomic_cache_bytes(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != payload:
            raise ValueError(f"Fractal descriptive catalog cache collision at {path}")
        return
    temp_path = path.with_name(f"{path.name}.tmp.{uuid.uuid4().hex}")
    try:
        with temp_path.open("wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(str(temp_path), str(path))
    finally:
        if temp_path.exists():
            temp_path.unlink()


def load_selected_fractal_description(
    runtime_cmd_path: Path,
    workspace_root: Path,
    selector: str,
    runtime_identity_sha256: str,
    job: Optional[JobContext] = None,
    timeout_seconds: float = 30.0,
) -> SelectedFractalDescription:
    runtime_cmd_path = runtime_cmd_path.resolve()
    selector = _require_nonempty_string(selector, "selected selector")
    if not _SHA256_RE.fullmatch(runtime_identity_sha256):
        raise ValueError("Runtime identity SHA-256 must be a lowercase hexadecimal digest")

    with tempfile.TemporaryDirectory(prefix="fractal-descriptive-catalog-") as temp_dir:
        output_path = Path(temp_dir) / "catalog.json"
        command = build_runtime_command(
            runtime_cmd_path,
            "--describe-fractal-catalog-json",
            str(output_path.resolve()),
        )
        if job is not None:
            result = job.run_process(command, runtime_cmd_path.parent, timeout_seconds=timeout_seconds)
            exit_code = result.exit_code
            timed_out = result.timed_out
            detail = result.stderr.strip() or result.stdout.strip()
        else:
            try:
                completed = subprocess.run(
                    command,
                    cwd=str(runtime_cmd_path.parent),
                    text=True,
                    capture_output=True,
                    timeout=timeout_seconds,
                    check=False,
                )
            except subprocess.TimeoutExpired as exc:
                raise ValueError("Engine fractal descriptive catalog export timed out") from exc
            exit_code = completed.returncode
            timed_out = False
            detail = completed.stderr.strip() or completed.stdout.strip()
        if timed_out or exit_code != 0 or not output_path.is_file():
            suffix = f": {detail}" if detail else ""
            raise ValueError(f"Engine fractal descriptive catalog export failed{suffix}")
        catalog_bytes = output_path.read_bytes()

    by_selector = _validate_catalog(catalog_bytes)
    selected = by_selector.get(selector)
    if selected is None:
        raise ValueError(f"Fractal descriptive catalog does not contain selected selector: {selector}")
    catalog_sha256 = hashlib.sha256(catalog_bytes).hexdigest()
    cache_path = (
        workspace_root.resolve()
        / "cache"
        / CACHE_NAMESPACE
        / runtime_identity_sha256
        / catalog_sha256
        / "catalog.json"
    )
    _atomic_cache_bytes(cache_path, catalog_bytes)
    return SelectedFractalDescription(
        catalog_sha256=catalog_sha256,
        cache_path=cache_path.resolve(),
        entry=selected,
    )
