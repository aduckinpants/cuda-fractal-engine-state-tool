from __future__ import annotations

import hashlib
import io
import json
import math
import os
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

import PIL
from PIL import Image, ImageDraw, ImageFont


SWEEP_PRESENTATION_VERSION = 1
TILE_WIDTH = 512
IMAGE_HEIGHT = 320
LABEL_HEIGHT = 44
MAX_COLUMNS = 3


@dataclass(frozen=True)
class SweepPresentationResult:
    contact_sheet_path: Path
    contact_sheet_sha256: str
    width: int
    height: int
    index_path: Path
    index_sha256: str
    receipt_path: Path
    receipt_sha256: str
    source_records: tuple[dict[str, Any], ...]


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _json_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n"
    ).encode("utf-8")


def _write_exact(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() == payload:
            return
        raise FileExistsError(f"Immutable sweep presentation artifact differs: {path}")
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


def _presentation_index(sweep_id: str, axis_path: str, members: Sequence[Any]) -> bytes:
    lines = [
        f"# Scalar Bracket Sweep {sweep_id}",
        "",
        f"Axis: `{axis_path}`",
        "",
        "This index is derived review evidence. It does not record human acceptance.",
        "",
        "| Index | Value | Status | Proof | Candidate display |",
        "|---:|---:|---|---|---|",
    ]
    for item in members:
        display = str(item.candidate_display_path) if item.candidate_display_path else "—"
        lines.append(
            f"| {item.index} | `{item.value}` | {item.status} | "
            f"{item.proof_id or '—'} | {display} |"
        )
    return ("\n".join(lines) + "\n").encode("utf-8")


def _source_tile(member: Any) -> tuple[Image.Image, dict[str, Any]]:
    source_path = member.candidate_display_path
    expected_sha = member.candidate_display_sha256
    record: dict[str, Any] = {
        "index": member.index,
        "value": member.value,
        "status": member.status,
        "proof_id": member.proof_id,
        "source_path": str(source_path) if source_path else None,
        "source_sha256": expected_sha,
        "source_dimensions": None,
        "thumbnail_box": None,
    }
    canvas = Image.new("RGB", (TILE_WIDTH, IMAGE_HEIGHT), (24, 24, 27))
    if member.status == "REPLAY_PROVEN":
        if source_path is None or not isinstance(expected_sha, str):
            raise ValueError(f"Replay-proven sweep member {member.index} has no proof-owned PNG")
        path = Path(source_path)
        if not path.is_file():
            raise ValueError(f"Replay-proven sweep member PNG is missing: {path}")
        payload = path.read_bytes()
        if _sha256(payload) != expected_sha:
            raise ValueError(f"Replay-proven sweep member PNG changed: {path}")
        with Image.open(io.BytesIO(payload)) as opened:
            opened.load()
            source = opened.convert("RGB")
        source_size = source.size
        source.thumbnail((TILE_WIDTH, IMAGE_HEIGHT), Image.Resampling.LANCZOS)
        left = (TILE_WIDTH - source.width) // 2
        top = (IMAGE_HEIGHT - source.height) // 2
        canvas.paste(source, (left, top))
        record["source_dimensions"] = list(source_size)
        record["thumbnail_box"] = [left, top, source.width, source.height]
    else:
        draw = ImageDraw.Draw(canvas)
        font = ImageFont.load_default()
        message = f"{member.status}\nNo proven display"
        box = draw.multiline_textbbox((0, 0), message, font=font, align="center")
        width = box[2] - box[0]
        height = box[3] - box[1]
        draw.multiline_text(
            ((TILE_WIDTH - width) // 2, (IMAGE_HEIGHT - height) // 2),
            message,
            fill=(220, 220, 225),
            font=font,
            align="center",
        )
    return canvas, record


def render_scalar_sweep_presentation(
    *,
    sweep_dir: Path,
    sweep_id: str,
    axis_path: str,
    members: Sequence[Any],
) -> SweepPresentationResult:
    if not members:
        raise ValueError("Scalar sweep presentation requires at least one member")
    sweep_dir = sweep_dir.resolve()
    columns = min(MAX_COLUMNS, len(members))
    rows = math.ceil(len(members) / columns)
    width = columns * TILE_WIDTH
    height = rows * (IMAGE_HEIGHT + LABEL_HEIGHT)
    sheet = Image.new("RGB", (width, height), (15, 15, 17))
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default()
    records: list[dict[str, Any]] = []
    for position, member in enumerate(members):
        tile, record = _source_tile(member)
        column = position % columns
        row = position // columns
        left = column * TILE_WIDTH
        top = row * (IMAGE_HEIGHT + LABEL_HEIGHT)
        sheet.paste(tile, (left, top))
        label = f"{axis_path} = {member.value}  |  {member.status}"
        draw.text((left + 8, top + IMAGE_HEIGHT + 12), label, fill=(240, 240, 243), font=font)
        record["sheet_tile"] = [left, top, TILE_WIDTH, IMAGE_HEIGHT + LABEL_HEIGHT]
        records.append(record)

    encoded = io.BytesIO()
    sheet.save(encoded, format="PNG", optimize=False, compress_level=6)
    png_bytes = encoded.getvalue()
    presentation_dir = sweep_dir / "presentation"
    contact_path = presentation_dir / "contact-sheet.png"
    index_path = presentation_dir / "index.md"
    receipt_path = presentation_dir / "contact-sheet-receipt.json"
    index_bytes = _presentation_index(sweep_id, axis_path, members)
    _write_exact(contact_path, png_bytes)
    _write_exact(index_path, index_bytes)
    receipt = {
        "sweep_presentation_version": SWEEP_PRESENTATION_VERSION,
        "sweep_id": sweep_id,
        "axis_path": axis_path,
        "renderer": {
            "owner": "cuda_fractal_state_tool.sweep_presentation",
            "pillow_version": PIL.__version__,
            "tile_width": TILE_WIDTH,
            "image_height": IMAGE_HEIGHT,
            "label_height": LABEL_HEIGHT,
            "maximum_columns": MAX_COLUMNS,
            "resampling": "LANCZOS",
        },
        "sources": records,
        "contact_sheet": {
            "path": "contact-sheet.png",
            "sha256": _sha256(png_bytes),
            "width": width,
            "height": height,
        },
        "index": {"path": "index.md", "sha256": _sha256(index_bytes)},
        "human_acceptance": False,
    }
    receipt_bytes = _json_bytes(receipt)
    _write_exact(receipt_path, receipt_bytes)
    return SweepPresentationResult(
        contact_sheet_path=contact_path.resolve(),
        contact_sheet_sha256=_sha256(png_bytes),
        width=width,
        height=height,
        index_path=index_path.resolve(),
        index_sha256=_sha256(index_bytes),
        receipt_path=receipt_path.resolve(),
        receipt_sha256=_sha256(receipt_bytes),
        source_records=tuple(records),
    )
