from __future__ import annotations

import hashlib
import json
import os
import sys
import uuid
from dataclasses import dataclass
from pathlib import Path

from .async_jobs import JobContext
from .runtime_surface import sha256_file


PREVIEW_SCHEMA = "finding-preview-v2"


@dataclass(frozen=True)
class PreviewPolicy:
    max_width: int = 640
    max_height: int = 480
    max_decoded_pixels: int = 50_000_000
    max_dimension: int = 16_384
    timeout_seconds: float = 30.0


@dataclass(frozen=True)
class PreviewResult:
    source_path: Path
    source_sha256: str
    preview_path: Path
    preview_sha256: str
    source_width: int
    source_height: int
    preview_width: int
    preview_height: int
    cache_hit: bool


class PreviewService:
    def __init__(self, policy: PreviewPolicy = PreviewPolicy()) -> None:
        self.policy = policy

    def prepare(self, source_path: Path, cache_dir: Path, context: JobContext) -> PreviewResult:
        source_path = source_path.resolve()
        cache_dir = cache_dir.resolve()
        if not source_path.is_file():
            raise FileNotFoundError(f"Finding frame does not exist: {source_path}")
        if source_path.suffix.lower() not in {".png", ".bmp", ".jpg", ".jpeg"}:
            raise ValueError(f"Unsupported preview file extension: {source_path.suffix}")
        source_sha256 = sha256_file(source_path)
        key_payload = (
            f"{PREVIEW_SCHEMA}:{source_sha256}:{self.policy.max_width}x{self.policy.max_height}"
        ).encode("utf-8")
        cache_key = hashlib.sha256(key_payload).hexdigest()
        preview_path = cache_dir / f"{cache_key}.png"
        metadata_path = cache_dir / f"{cache_key}.json"
        if preview_path.exists() and metadata_path.exists():
            try:
                metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
                if not isinstance(metadata, dict):
                    raise ValueError("Preview cache metadata must be a JSON object")
                return self._result(source_path, source_sha256, preview_path, metadata, cache_hit=True)
            except (OSError, ValueError, TypeError, KeyError):
                preview_path.unlink(missing_ok=True)
                metadata_path.unlink(missing_ok=True)
        elif preview_path.exists() or metadata_path.exists():
            preview_path.unlink(missing_ok=True)
            metadata_path.unlink(missing_ok=True)

        cache_dir.mkdir(parents=True, exist_ok=True)
        temp_path = cache_dir / f"{cache_key}.tmp.{uuid.uuid4().hex}.png"
        command = [
            sys.executable,
            "-m",
            "cuda_fractal_state_tool.preview_worker",
            "--source",
            str(source_path),
            "--out",
            str(temp_path),
            "--max-width",
            str(self.policy.max_width),
            "--max-height",
            str(self.policy.max_height),
            "--max-pixels",
            str(self.policy.max_decoded_pixels),
            "--max-dimension",
            str(self.policy.max_dimension),
        ]
        metadata_temp = metadata_path.with_name(f"{metadata_path.name}.tmp.{uuid.uuid4().hex}")
        try:
            result = context.run_process(command, cwd=source_path.parent, timeout_seconds=self.policy.timeout_seconds)
            if result.timed_out:
                raise TimeoutError(f"Preview worker exceeded {self.policy.timeout_seconds:g} seconds")
            if result.exit_code not in (0, None):
                detail = result.stderr.strip() or result.stdout.strip()
                raise ValueError(f"Preview worker rejected the image: {detail}")
            context.raise_if_cancelled()
            if not temp_path.exists():
                raise RuntimeError("Preview worker succeeded without producing a derivative")
            payload = json.loads(result.stdout)
            if not isinstance(payload, dict) or payload.get("status") != "ok":
                raise RuntimeError("Preview worker returned an invalid result")
            metadata = {
                "preview_schema": PREVIEW_SCHEMA,
                "source_sha256": source_sha256,
                "preview_sha256": sha256_file(temp_path),
                "source_width": payload["source_width"],
                "source_height": payload["source_height"],
                "preview_width": payload["preview_width"],
                "preview_height": payload["preview_height"],
                "source_format": payload["source_format"],
                "upscaled": payload["upscaled"],
            }
            os.replace(str(temp_path), str(preview_path))
            metadata_temp.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            os.replace(str(metadata_temp), str(metadata_path))
        except Exception:
            temp_path.unlink(missing_ok=True)
            metadata_temp.unlink(missing_ok=True)
            raise
        return self._result(source_path, source_sha256, preview_path, metadata, cache_hit=False)

    @staticmethod
    def _result(
        source_path: Path,
        source_sha256: str,
        preview_path: Path,
        metadata: dict,
        cache_hit: bool,
    ) -> PreviewResult:
        if metadata.get("preview_schema") != PREVIEW_SCHEMA:
            raise ValueError("Preview cache schema is unsupported")
        if metadata.get("source_sha256") != source_sha256:
            raise ValueError("Preview cache metadata does not match the source image")
        if metadata.get("upscaled") is not False:
            raise ValueError("Preview cache violates the no-upscaling policy")
        preview_sha256 = sha256_file(preview_path)
        if metadata.get("preview_sha256") != preview_sha256:
            raise ValueError("Preview cache derivative hash does not match its metadata")
        return PreviewResult(
            source_path=source_path,
            source_sha256=source_sha256,
            preview_path=preview_path.resolve(),
            preview_sha256=preview_sha256,
            source_width=int(metadata["source_width"]),
            source_height=int(metadata["source_height"]),
            preview_width=int(metadata["preview_width"]),
            preview_height=int(metadata["preview_height"]),
            cache_hit=cache_hit,
        )
