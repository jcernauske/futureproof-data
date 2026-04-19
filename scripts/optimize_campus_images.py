#!/usr/bin/env python3
"""Optimize campus footer images into responsive WebP/AVIF/PNG variants."""

from __future__ import annotations

import argparse
import sys
import traceback
from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image

try:
    import pillow_avif  # noqa: F401  (registers AVIF codec with Pillow)
except ImportError:
    print(
        "ERROR: pillow-avif-plugin is not installed. Install with: "
        "uv pip install pillow-avif-plugin",
        file=sys.stderr,
    )
    sys.exit(1)


SOURCE_EXTENSIONS = {".png", ".jpg", ".jpeg"}

# (suffix, target_width, format, save_kwargs)
VARIANTS: list[tuple[str, int, str, dict]] = [
    ("-1400.webp", 1400, "WEBP", {"quality": 82, "method": 6}),
    ("-2048.webp", 2048, "WEBP", {"quality": 82, "method": 6}),
    ("-1400.avif", 1400, "AVIF", {"quality": 70}),
    ("-2048.avif", 2048, "AVIF", {"quality": 70}),
]


@dataclass
class Stats:
    sources_processed: int = 0
    sources_failed: int = 0
    outputs_generated: int = 0
    outputs_skipped_upscale: int = 0
    failures: list[tuple[Path, str]] = field(default_factory=list)


def resize_to_width(img: Image.Image, target_width: int) -> Image.Image:
    if img.width == target_width:
        return img
    ratio = target_width / img.width
    target_height = max(1, round(img.height * ratio))
    return img.resize((target_width, target_height), Image.Resampling.LANCZOS)


def stripped_copy(img: Image.Image) -> Image.Image:
    """Return a copy with no EXIF/ICC/metadata attached."""
    clean = Image.new(img.mode, img.size)
    clean.putdata(list(img.getdata()))
    return clean


def process_image(
    src: Path,
    out_dir: Path,
    dry_run: bool,
    stats: Stats,
) -> None:
    with Image.open(src) as raw:
        raw.load()
        # Normalize mode for downstream encoders.
        if raw.mode not in ("RGB", "RGBA"):
            base = raw.convert("RGBA" if "A" in raw.mode else "RGB")
        else:
            base = raw.copy()

    src_width = base.width
    basename = src.stem

    for suffix, target_width, fmt, save_kwargs in VARIANTS:
        out_path = out_dir / f"{basename}{suffix}"

        if target_width > src_width:
            stats.outputs_skipped_upscale += 1
            print(
                f"  skip {out_path.name} "
                f"(source is {src_width}px, target {target_width}px — no upscale)"
            )
            continue

        if dry_run:
            print(f"  would write {out_path.name} ({target_width}px, {fmt})")
            stats.outputs_generated += 1
            continue

        resized = resize_to_width(base, target_width)
        clean = stripped_copy(resized)

        # PNG/AVIF can keep alpha; WebP fine with either.
        if fmt == "PNG" and clean.mode == "RGBA":
            save_mode = clean
        elif fmt in ("WEBP", "AVIF"):
            save_mode = clean
        else:
            save_mode = clean.convert("RGB") if clean.mode == "RGBA" else clean

        save_mode.save(out_path, format=fmt, **save_kwargs)
        stats.outputs_generated += 1
        print(f"  wrote {out_path.name} ({target_width}px, {fmt})")


def dir_size_bytes(path: Path) -> int:
    return sum(p.stat().st_size for p in path.iterdir() if p.is_file())


def human_bytes(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate responsive WebP/AVIF/PNG variants for campus images."
    )
    parser.add_argument("input_dir", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be generated without writing files.",
    )
    args = parser.parse_args()

    if not args.input_dir.is_dir():
        print(f"ERROR: input dir does not exist: {args.input_dir}", file=sys.stderr)
        return 1

    if not args.dry_run:
        args.output_dir.mkdir(parents=True, exist_ok=True)

    sources = sorted(
        p
        for p in args.input_dir.iterdir()
        if p.is_file() and p.suffix.lower() in SOURCE_EXTENSIONS
    )

    if not sources:
        print(f"No source images found in {args.input_dir}")
        return 0

    print(f"Found {len(sources)} source image(s) in {args.input_dir}")
    print(f"Writing variants to {args.output_dir}{' (dry run)' if args.dry_run else ''}\n")

    stats = Stats()

    for src in sources:
        print(f"→ {src.name}")
        try:
            process_image(src, args.output_dir, args.dry_run, stats)
            stats.sources_processed += 1
        except Exception as exc:  # noqa: BLE001 — keep the batch going
            stats.sources_failed += 1
            stats.failures.append((src, str(exc)))
            print(f"  FAILED: {exc}", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Source files processed:  {stats.sources_processed}")
    if stats.sources_failed:
        print(f"Source files failed:     {stats.sources_failed}")
    print(f"Output files generated:  {stats.outputs_generated}")
    if stats.outputs_skipped_upscale:
        print(f"Variants skipped (upscale): {stats.outputs_skipped_upscale}")

    if not args.dry_run and args.output_dir.exists():
        in_bytes = dir_size_bytes(args.input_dir)
        out_bytes = dir_size_bytes(args.output_dir)
        saved_pct = (1 - out_bytes / in_bytes) * 100 if in_bytes else 0
        print(f"Input dir size:          {human_bytes(in_bytes)}")
        print(f"Output dir size:         {human_bytes(out_bytes)}")
        print(f"Saved:                   {saved_pct:.1f}%")

    if stats.failures:
        print("\nFailures:")
        for src, msg in stats.failures:
            print(f"  - {src.name}: {msg}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
