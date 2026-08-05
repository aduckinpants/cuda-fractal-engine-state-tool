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

from .json_utils import loads_strict_no_duplicates


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


@dataclass(frozen=True)
class CapturedBaseReference:
    source_path: Path
    source_sha256: str
    axis_value: int | float
    packet_id: str
    finding_id: str


@dataclass(frozen=True)
class SweepWebReviewResult:
    web_review_dir: Path
    review_path: Path
    review_sha256: str
    evidence_path: Path
    evidence_sha256: str
    contact_sheet_path: Path
    contact_sheet_sha256: str


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


def _presentation_index(
    sweep_id: str,
    axis_path: str,
    captured_base: CapturedBaseReference,
    members: Sequence[Any],
) -> bytes:
    lines = [
        f"# Scalar Bracket Sweep {sweep_id}",
        "",
        f"Axis: `{axis_path}`",
        "",
        "This index is derived review evidence. It does not record human acceptance.",
        "",
        "## Captured base reference",
        "",
        f"- `{axis_path}` = `{captured_base.axis_value}`",
        "- Status: `CURRENT_CAPTURED_BASE`",
        "- This is not a sweep member and is not newly replay-proven.",
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


def resolve_captured_base_reference(
    packet_dir: Path,
    axis_path: str,
) -> CapturedBaseReference:
    packet_dir = packet_dir.resolve()
    manifest_path = packet_dir / "manifest.json"
    state_path = packet_dir / "state.json"
    if not manifest_path.is_file() or not state_path.is_file():
        raise ValueError("Scalar sweep packet is missing manifest.json or state.json")
    manifest = loads_strict_no_duplicates(manifest_path.read_text(encoding="utf-8"))
    state = loads_strict_no_duplicates(state_path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict) or not isinstance(state, dict):
        raise ValueError("Scalar sweep packet manifest or state is not an object")
    parts = axis_path.split(".")
    if len(parts) != 2 or parts[0] != "params":
        raise ValueError("Captured-base axis must be one direct params path")
    params = state.get("params")
    if not isinstance(params, dict) or parts[1] not in params:
        raise ValueError(f"Captured-base axis is absent from packet state: {axis_path}")
    axis_value = params[parts[1]]
    if isinstance(axis_value, bool) or not isinstance(axis_value, (int, float)):
        raise ValueError(f"Captured-base axis is not numeric: {axis_path}")

    derivative = manifest.get("web_frame_derivative")
    if not isinstance(derivative, dict):
        raise ValueError("Packet V8 has no captured source-frame provenance")
    relative = derivative.get("source_finding_relative_path")
    expected_sha = derivative.get("source_sha256")
    if not isinstance(relative, str) or not isinstance(expected_sha, str):
        raise ValueError("Packet V8 captured source-frame provenance is malformed")
    finding_dir = packet_dir.parent.parent.resolve()
    source_path = (finding_dir / relative).resolve()
    if not source_path.is_relative_to(finding_dir):
        raise ValueError("Packet V8 captured source-frame path escapes its finding")
    if not source_path.is_file():
        raise ValueError(f"Packet V8 captured source frame is missing: {source_path}")
    actual_sha = _sha256(source_path.read_bytes())
    if actual_sha != expected_sha:
        raise ValueError(f"Packet V8 captured source frame changed: {source_path}")
    packet_id = manifest.get("packet_id")
    finding_id = manifest.get("finding_id")
    if not isinstance(packet_id, str) or not isinstance(finding_id, str):
        raise ValueError("Packet V8 has no packet/finding identity")
    return CapturedBaseReference(source_path, expected_sha, axis_value, packet_id, finding_id)


def _image_tile(
    source_path: Path,
    expected_sha: str,
    *,
    changed_message: str,
) -> tuple[Image.Image, list[int], list[int]]:
    if not source_path.is_file():
        raise ValueError(f"Sweep presentation image is missing: {source_path}")
    payload = source_path.read_bytes()
    if _sha256(payload) != expected_sha:
        raise ValueError(f"{changed_message}: {source_path}")
    with Image.open(io.BytesIO(payload)) as opened:
        opened.load()
        source = opened.convert("RGB")
    source_size = [source.width, source.height]
    source.thumbnail((TILE_WIDTH, IMAGE_HEIGHT), Image.Resampling.LANCZOS)
    left = (TILE_WIDTH - source.width) // 2
    top = (IMAGE_HEIGHT - source.height) // 2
    canvas = Image.new("RGB", (TILE_WIDTH, IMAGE_HEIGHT), (24, 24, 27))
    canvas.paste(source, (left, top))
    return canvas, source_size, [left, top, source.width, source.height]


def _captured_base_tile(
    captured_base: CapturedBaseReference,
    axis_path: str,
) -> tuple[Image.Image, dict[str, Any]]:
    canvas, source_dimensions, thumbnail_box = _image_tile(
        captured_base.source_path,
        captured_base.source_sha256,
        changed_message="Captured base frame changed",
    )
    return canvas, {
        "kind": "captured_base",
        "index": None,
        "value": captured_base.axis_value,
        "axis_path": axis_path,
        "status": "CURRENT_CAPTURED_BASE",
        "proof_id": None,
        "source_path": str(captured_base.source_path),
        "source_sha256": captured_base.source_sha256,
        "source_dimensions": source_dimensions,
        "thumbnail_box": thumbnail_box,
        "packet_id": captured_base.packet_id,
        "finding_id": captured_base.finding_id,
        "is_sweep_member": False,
        "newly_replay_proven": False,
    }


def _source_tile(member: Any) -> tuple[Image.Image, dict[str, Any]]:
    source_path = member.candidate_display_path
    expected_sha = member.candidate_display_sha256
    record: dict[str, Any] = {
        "kind": "sweep_member",
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
        canvas, source_size, thumbnail_box = _image_tile(
            Path(source_path),
            expected_sha,
            changed_message="Replay-proven sweep member PNG changed",
        )
        record["source_dimensions"] = source_size
        record["thumbnail_box"] = thumbnail_box
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
    captured_base: CapturedBaseReference,
    members: Sequence[Any],
) -> SweepPresentationResult:
    if not members:
        raise ValueError("Scalar sweep presentation requires at least one member")
    sweep_dir = sweep_dir.resolve()
    tile_count = len(members) + 1
    columns = min(MAX_COLUMNS, tile_count)
    rows = math.ceil(tile_count / columns)
    width = columns * TILE_WIDTH
    height = rows * (IMAGE_HEIGHT + LABEL_HEIGHT)
    sheet = Image.new("RGB", (width, height), (15, 15, 17))
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default()
    records: list[dict[str, Any]] = []
    tiles: list[tuple[Image.Image, dict[str, Any], str]] = []
    base_tile, base_record = _captured_base_tile(captured_base, axis_path)
    tiles.append(
        (
            base_tile,
            base_record,
            f"CURRENT / CAPTURED BASE | {axis_path} = {captured_base.axis_value}\n"
            "not a sweep member | not newly replay-proven",
        )
    )
    for member in members:
        tile, record = _source_tile(member)
        tiles.append((tile, record, f"{axis_path} = {member.value}  |  {member.status}"))

    for position, (tile, record, label) in enumerate(tiles):
        column = position % columns
        row = position // columns
        left = column * TILE_WIDTH
        top = row * (IMAGE_HEIGHT + LABEL_HEIGHT)
        sheet.paste(tile, (left, top))
        draw.multiline_text(
            (left + 8, top + IMAGE_HEIGHT + 8),
            label,
            fill=(240, 240, 243),
            font=font,
            spacing=2,
        )
        record["sheet_tile"] = [left, top, TILE_WIDTH, IMAGE_HEIGHT + LABEL_HEIGHT]
        records.append(record)

    encoded = io.BytesIO()
    sheet.save(encoded, format="PNG", optimize=False, compress_level=6)
    png_bytes = encoded.getvalue()
    presentation_dir = sweep_dir / "presentation"
    contact_path = presentation_dir / "contact-sheet.png"
    index_path = presentation_dir / "index.md"
    receipt_path = presentation_dir / "contact-sheet-receipt.json"
    index_bytes = _presentation_index(sweep_id, axis_path, captured_base, members)
    _write_exact(contact_path, png_bytes)
    _write_exact(index_path, index_bytes)
    receipt = {
        "sweep_presentation_version": SWEEP_PRESENTATION_VERSION,
        "sweep_id": sweep_id,
        "axis_path": axis_path,
        "captured_base": {
            "value": captured_base.axis_value,
            "packet_id": captured_base.packet_id,
            "finding_id": captured_base.finding_id,
            "source_sha256": captured_base.source_sha256,
            "is_sweep_member": False,
            "newly_replay_proven": False,
        },
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


def _json_source_record(sweep_dir: Path, relative_path: str, role: str) -> dict[str, Any]:
    source_path = (sweep_dir / relative_path).resolve()
    if not source_path.is_relative_to(sweep_dir) or not source_path.is_file():
        raise ValueError(f"Sweep web-review source is missing: {relative_path}")
    payload = source_path.read_bytes()
    try:
        document = loads_strict_no_duplicates(payload.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError, ValueError) as exc:
        raise ValueError(f"Sweep web-review source is malformed: {relative_path}") from exc
    return {
        "path": relative_path.replace("\\", "/"),
        "role": role,
        "size_bytes": len(payload),
        "sha256": _sha256(payload),
        "document": document,
    }


def _sweep_review_markdown(
    *,
    sources: list[dict[str, Any]],
    contact_sheet_sha256: str,
    evidence_sha256: str,
) -> bytes:
    by_role = {source["role"]: source for source in sources if not source["role"].startswith("member_")}
    plan = by_role["sweep_plan"]["document"]
    binding = by_role["sweep_binding"]["document"]
    receipt = by_role["aggregate_receipt"]["document"]
    presentation = by_role["presentation_receipt"]["document"]
    base = presentation["captured_base"]
    lines = [
        f"# Scalar Bracket Sweep Review — {receipt['sweep_id']}",
        "",
        "This is a compact derived web handoff. The immutable source sweep artifacts remain authority.",
        "This review does not record or imply human acceptance.",
        "",
        "## Binding and fixed conditions",
        "",
        f"- Packet: `{binding['packet_id']}`",
        f"- Finding: `{binding['finding_id']}`",
        f"- Packet manifest SHA-256: `{binding['packet_manifest_sha256']}`",
        f"- Axis: `{receipt['axis_path']}`",
        f"- Ordered requested values: `{json.dumps(receipt['ordered_values'], ensure_ascii=False)}`",
        f"- Member failure policy: `{receipt['member_failure_policy']}`",
        f"- Fixed override SHA-256: `{receipt['fixed_override_sha256']}` (`{{}}` in the agent-authored V1 route)",
        "- Every member starts independently from the same exact packet base; values are not cumulative.",
        "",
        "## Current / captured base reference",
        "",
        f"- `{receipt['axis_path']}` = `{base['value']}`",
        f"- Captured source frame SHA-256: `{base['source_sha256']}`",
        "- Status: `CURRENT_CAPTURED_BASE`",
        "- The first contact-sheet tile is not a sweep member and is not newly replay-proven.",
        "",
        "## Ordered members",
        "",
        "| Index | Requested value | Status | Proof ID | Evidence reference |",
        "|---:|---:|---|---|---|",
    ]
    for member in receipt["members"]:
        logical_ref = next(
            (
                source["path"]
                for source in sources
                if source["role"] == f"member_proof_reference_{member['index']:03d}"
            ),
            f"receipt.json#/members/{member['index']}",
        )
        lines.append(
            f"| {member['index']} | `{member['value']}` | `{member['status']}` | "
            f"`{member.get('proof_id') or 'none'}` | `{logical_ref}` |"
        )
        if member.get("message") and member["status"] != "REPLAY_PROVEN":
            lines.append(f"\nFailure/note for member {member['index']}: {member['message']}\n")
    lines.extend(
        [
            "",
            "## Interpretation boundary",
            "",
            "- `REPLAY_PROVEN` means that member survived engine materialization and action-free replay.",
            "- `NO_EFFECT_ENGINE_EMITTED_BASE` means the requested distinct value engine-emitted the exact captured",
            "  base value; it is an unsuccessful member, not a CUDA or image-render failure.",
            "- Other failed or unstarted members are evidence, not missing values to interpolate away.",
            "- Visual trends across proven members are observations. They do not alone establish causality, monotonicity,",
            "  convergence, a mathematical phase transition, or behavior outside the sampled bracket.",
            "- The contact sheet is a derived comparison aid. Exact states, proof receipts, and hashes remain authoritative.",
            "",
            "## Transport identities",
            "",
            f"- `contact-sheet.png` SHA-256: `{contact_sheet_sha256}`",
            f"- `sweep-evidence.json` SHA-256: `{evidence_sha256}`",
            "- `human_acceptance`: `false`",
            "",
        ]
    )
    return ("\n".join(lines)).encode("utf-8")


def render_scalar_sweep_web_review(*, sweep_dir: Path) -> SweepWebReviewResult:
    """Create the deterministic three-file web projection of an immutable sweep."""

    sweep_dir = sweep_dir.resolve()
    member_dirs = sorted(
        path for path in (sweep_dir / "members").iterdir() if path.is_dir()
    )
    source_specs = [
        ("plan.json", "sweep_plan"),
        ("binding.json", "sweep_binding"),
        ("fixed-override.json", "fixed_override"),
        ("receipt.json", "aggregate_receipt"),
        ("presentation/contact-sheet-receipt.json", "presentation_receipt"),
    ]
    sources = [_json_source_record(sweep_dir, path, role) for path, role in source_specs]
    for member_dir in member_dirs:
        try:
            index = int(member_dir.name.split("-", 1)[0])
        except ValueError as exc:
            raise ValueError(f"Sweep member directory has no numeric index: {member_dir.name}") from exc
        relative = member_dir.relative_to(sweep_dir).as_posix()
        sources.append(
            _json_source_record(
                sweep_dir, f"{relative}/override.json", f"member_override_{index:03d}"
            )
        )
        sources.append(
            _json_source_record(
                sweep_dir,
                f"{relative}/proof-ref.json",
                f"member_proof_reference_{index:03d}",
            )
        )

    contact_source = sweep_dir / "presentation" / "contact-sheet.png"
    if not contact_source.is_file():
        raise ValueError("Sweep contact sheet is missing")
    contact_bytes = contact_source.read_bytes()
    contact_sha = _sha256(contact_bytes)
    presentation = next(
        source["document"] for source in sources if source["role"] == "presentation_receipt"
    )
    if presentation.get("contact_sheet", {}).get("sha256") != contact_sha:
        raise ValueError("Sweep contact sheet differs from its presentation receipt")

    evidence = {
        "sweep_web_evidence_version": 1,
        "authority": "derived_transport_projection_only",
        "source_sweep_id": next(
            source["document"]["sweep_id"]
            for source in sources
            if source["role"] == "aggregate_receipt"
        ),
        "sources": sources,
        "contact_sheet": {
            "path": "contact-sheet.png",
            "size_bytes": len(contact_bytes),
            "sha256": contact_sha,
        },
        "human_acceptance": False,
    }
    evidence_bytes = _json_bytes(evidence)
    evidence_sha = _sha256(evidence_bytes)
    review_bytes = _sweep_review_markdown(
        sources=sources,
        contact_sheet_sha256=contact_sha,
        evidence_sha256=evidence_sha,
    )

    web_dir = sweep_dir / "web-review"
    if web_dir.exists():
        extras = {path.name for path in web_dir.iterdir()} - {
            "sweep-review.md",
            "sweep-evidence.json",
            "contact-sheet.png",
        }
        if extras:
            raise ValueError(f"Sweep web-review directory contains unexpected files: {sorted(extras)}")
    review_path = web_dir / "sweep-review.md"
    evidence_path = web_dir / "sweep-evidence.json"
    contact_path = web_dir / "contact-sheet.png"
    _write_exact(contact_path, contact_bytes)
    _write_exact(evidence_path, evidence_bytes)
    _write_exact(review_path, review_bytes)
    return SweepWebReviewResult(
        web_review_dir=web_dir.resolve(),
        review_path=review_path.resolve(),
        review_sha256=_sha256(review_bytes),
        evidence_path=evidence_path.resolve(),
        evidence_sha256=evidence_sha,
        contact_sheet_path=contact_path.resolve(),
        contact_sheet_sha256=contact_sha,
    )
