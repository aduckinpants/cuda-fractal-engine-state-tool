from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Optional

from PIL import Image, ImageOps


ALLOWED_FORMATS = {"PNG", "BMP", "JPEG"}


def create_preview(
    source_path: Path,
    output_path: Path,
    max_width: int,
    max_height: int,
    max_pixels: int,
    max_dimension: int,
) -> dict[str, int | str | bool]:
    if max_width < 1 or max_height < 1 or max_pixels < 1 or max_dimension < 1:
        raise ValueError("Preview limits must be positive")
    previous_pillow_limit = Image.MAX_IMAGE_PIXELS
    Image.MAX_IMAGE_PIXELS = None
    try:
        with Image.open(source_path) as opened:
            image_format = opened.format
            if image_format not in ALLOWED_FORMATS:
                raise ValueError(f"Unsupported preview image format: {image_format}")
            source_width, source_height = opened.size
            if source_width < 1 or source_height < 1:
                raise ValueError("Preview source has invalid dimensions")
            if source_width > max_dimension or source_height > max_dimension:
                raise ValueError(
                    f"Preview source dimension exceeds policy: {source_width}x{source_height} > {max_dimension}"
                )
            if source_width * source_height > max_pixels:
                raise ValueError(
                    f"Preview source pixel count exceeds policy: {source_width * source_height} > {max_pixels}"
                )
            image = ImageOps.exif_transpose(opened).convert("RGBA")
            image.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            image.save(output_path, format="PNG", optimize=True)
            return {
                "source_format": image_format,
                "source_width": source_width,
                "source_height": source_height,
                "preview_width": image.width,
                "preview_height": image.height,
                "upscaled": image.width > source_width or image.height > source_height,
                "resampling": "pillow_lanczos_thumbnail",
                "pixel_mode": "RGBA",
                "orientation_handling": "pillow_exif_transpose",
            }
    finally:
        Image.MAX_IMAGE_PIXELS = previous_pillow_limit


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Isolated bounded finding-frame preview decoder")
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--max-width", type=int, required=True)
    parser.add_argument("--max-height", type=int, required=True)
    parser.add_argument("--max-pixels", type=int, required=True)
    parser.add_argument("--max-dimension", type=int, required=True)
    args = parser.parse_args(argv)
    try:
        payload = create_preview(
            args.source,
            args.out,
            args.max_width,
            args.max_height,
            args.max_pixels,
            args.max_dimension,
        )
    except Exception as exc:
        print(json.dumps({"status": "failed", "error": str(exc)}, sort_keys=True))
        return 2
    print(json.dumps({"status": "ok", **payload}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
