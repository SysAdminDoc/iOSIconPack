#!/usr/bin/env python3
"""validate_drawables.py — CI validator for PNG and vector drawable assets.

Checks:
  1. Every PNG in drawable-xxxhdpi/ is exactly 192x192 pixels.
  2. Every PNG is a valid PNG (correct magic bytes + parseable IHDR).
  3. Every PNG is under the size budget (200 KB).
  4. Every vector drawable in drawable/ parses as valid XML.
  5. Every item in drawable.xml has a corresponding file on disk.

Exit 0 on success, 1 on any failure.
"""
from __future__ import annotations

import struct
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

REPO_ROOT     = Path(__file__).resolve().parents[1]
HDPI_DIR      = REPO_ROOT / "app/src/main/res/drawable-xxxhdpi"
VEC_DIR       = REPO_ROOT / "app/src/main/res/drawable"
DRAWABLE_XML  = REPO_ROOT / "app/src/main/res/xml/drawable.xml"

EXPECTED_SIZE = 192          # px
MAX_FILE_KB   = 200          # KB

# Corner region checked for squircle transparency (pixels from each corner)
SQUIRCLE_CORNER_REGION = 15   # px
SQUIRCLE_MAX_OPAQUE    = 5    # max opaque pixels allowed in each corner before warning

PNG_MAGIC     = b"\x89PNG\r\n\x1a\n"

# Launcher/system drawables in drawable/ that aren't icon-pack artwork
_VEC_SKIP_PREFIXES = ("ic_launcher", "ic_", "background", "foreground", "ic_muzei")


def _png_dimensions(data: bytes) -> tuple[int, int]:
    """Return (width, height) from a PNG's IHDR chunk."""
    if data[:8] != PNG_MAGIC:
        raise ValueError("Not a PNG (bad magic bytes)")
    if len(data) < 24:
        raise ValueError("File too short to contain IHDR")
    w = struct.unpack(">I", data[16:20])[0]
    h = struct.unpack(">I", data[20:24])[0]
    return w, h


def check_pngs() -> list[str]:
    errors: list[str] = []
    for path in sorted(HDPI_DIR.glob("*.png")):
        size_kb = path.stat().st_size / 1024
        try:
            data = path.read_bytes()
            w, h = _png_dimensions(data)
        except (ValueError, OSError) as exc:
            errors.append(f"  INVALID PNG  {path.name}: {exc}")
            continue

        if w != EXPECTED_SIZE or h != EXPECTED_SIZE:
            errors.append(
                f"  WRONG SIZE   {path.name}: {w}x{h} (expected {EXPECTED_SIZE}x{EXPECTED_SIZE})"
            )
        if size_kb > MAX_FILE_KB:
            errors.append(
                f"  TOO LARGE    {path.name}: {size_kb:.1f} KB (budget {MAX_FILE_KB} KB)"
            )
    return errors


def check_vectors() -> list[str]:
    errors: list[str] = []
    for path in sorted(VEC_DIR.glob("*.xml")):
        if any(path.stem.startswith(p) for p in _VEC_SKIP_PREFIXES):
            continue
        try:
            ET.parse(path)
        except ET.ParseError as exc:
            errors.append(f"  MALFORMED XML  {path.name}: {exc}")
    return errors


def check_drawable_files() -> list[str]:
    """Ensure every item in drawable.xml has a PNG or vector on disk."""
    errors: list[str] = []
    try:
        tree = ET.parse(DRAWABLE_XML)
    except ET.ParseError as exc:
        return [f"  MALFORMED drawable.xml: {exc}"]

    for item in tree.iter("item"):
        name = item.get("drawable", "")
        if not name:
            continue
        has_png = (HDPI_DIR / f"{name}.png").exists()
        has_vec = (VEC_DIR / f"{name}.xml").exists()
        # Also check other density buckets
        other = list((REPO_ROOT / "app/src/main/res").glob(f"drawable-*/{name}.png"))
        if not has_png and not has_vec and not other:
            errors.append(f"  MISSING FILE  drawable.xml references '{name}' but no PNG/vector found")
    return errors


def check_squircle_corners() -> list[str]:
    """Warn if any PNG has too many opaque pixels in its four corner regions.

    A proper squircle icon should be fully transparent in the 4 corners.
    This check is a WARN-only heuristic — it exits 0 regardless.
    Requires Pillow; skips gracefully if not installed.
    """
    try:
        from PIL import Image  # type: ignore
    except ImportError:
        return []

    warnings: list[str] = []
    r = SQUIRCLE_CORNER_REGION
    for path in sorted(HDPI_DIR.glob("*.png")):
        try:
            img = Image.open(path).convert("RGBA")
        except Exception:
            continue

        w, h = img.size
        corners = [
            img.crop((0, 0, r, r)),            # top-left
            img.crop((w - r, 0, w, r)),        # top-right
            img.crop((0, h - r, r, h)),        # bottom-left
            img.crop((w - r, h - r, w, h)),    # bottom-right
        ]
        labels = ["top-left", "top-right", "bottom-left", "bottom-right"]
        for region, label in zip(corners, labels):
            pixels = list(region.getdata())
            opaque = sum(1 for px in pixels if px[3] > 10)
            if opaque > SQUIRCLE_MAX_OPAQUE:
                warnings.append(
                    f"  WARN squircle  {path.name}: {opaque} opaque px in {label} corner"
                )
    return warnings


def main() -> int:
    all_errors: list[str] = []

    png_errors = check_pngs()
    vec_errors = check_vectors()
    file_errors = check_drawable_files()
    squircle_warnings = check_squircle_corners()

    png_count = len(list(HDPI_DIR.glob("*.png")))
    vec_count = sum(
        1 for f in VEC_DIR.glob("*.xml")
        if not any(f.stem.startswith(p) for p in _VEC_SKIP_PREFIXES)
    )
    mono_count = sum(1 for _ in VEC_DIR.glob("*_mono.xml"))
    themed_count = sum(1 for _ in VEC_DIR.glob("*_themed.xml"))
    pure_vec_count = vec_count - mono_count - themed_count

    all_errors.extend(png_errors)
    all_errors.extend(vec_errors)
    all_errors.extend(file_errors)

    if all_errors:
        print(f"validate_drawables.py: FAILED ({len(all_errors)} error(s))", file=sys.stderr)
        for err in all_errors:
            print(err, file=sys.stderr)
        return 1

    print(
        f"validate_drawables.py: OK "
        f"({png_count} PNGs at {EXPECTED_SIZE}x{EXPECTED_SIZE}px, "
        f"{pure_vec_count} vector(s), "
        f"{mono_count} mono stub(s), "
        f"{themed_count} themed wrapper(s))"
    )
    if squircle_warnings:
        affected = len({w.split()[2] for w in squircle_warnings})
        total_pngs = len(list(HDPI_DIR.glob("*.png")))
        print(
            f"  squircle check: {affected}/{total_pngs} icons have opaque corners "
            f"(expected for Apple-sourced icons — launcher applies squircle mask at runtime)"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
