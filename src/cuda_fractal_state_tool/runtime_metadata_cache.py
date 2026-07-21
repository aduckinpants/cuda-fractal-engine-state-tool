from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any, Mapping


_CACHE_IDENTITY_FIELDS = (
    "launcher_path",
    "launcher_sha256",
    "working_directory",
    "resolved_executable_path",
    "resolved_executable_sha256",
    "resolved_executable_file_version",
    "runtime_schema_path",
    "runtime_schema_sha256",
    "source_schema_path",
    "source_schema_sha256",
    "ui_salt_contract_path",
    "ui_salt_contract_sha256",
)


def _cache_identity_payload(identity: Mapping[str, Any]) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    for field in _CACHE_IDENTITY_FIELDS:
        value = identity.get(field)
        if value is not None:
            payload[field] = value
    return payload


def runtime_identity_cache_key(identity: Mapping[str, Any]) -> str:
    payload = json.dumps(_cache_identity_payload(identity), sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def runtime_cache_dir(cache_root: Path, identity: Mapping[str, Any]) -> Path:
    return cache_root / runtime_identity_cache_key(identity)


def cache_probe_output(cache_root: Path, cache_key: str, output_root: Path) -> Path:
    cache_dir = cache_root / cache_key
    cache_dir.parent.mkdir(parents=True, exist_ok=True)
    if cache_dir.exists():
        shutil.rmtree(cache_dir)
    shutil.copytree(output_root, cache_dir)
    return cache_dir


def restore_probe_output(cache_dir: Path, output_root: Path) -> None:
    output_root.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(cache_dir, output_root, dirs_exist_ok=True)
