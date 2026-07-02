#!/usr/bin/env python3
"""Generate deterministic letter-tile placeholder icons for uncovered apps."""
from __future__ import annotations

import argparse
import colorsys
import hashlib
import re
import subprocess
import sys
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFilter, ImageFont
except ImportError:
    print(
        "gen_placeholders.py: Pillow is required. Install with:\n"
        "  python -m pip install -r requirements.txt",
        file=sys.stderr,
    )
    sys.exit(1)


REPO_ROOT = Path(__file__).resolve().parents[1]
PACK_DIR = REPO_ROOT / "app/src/main/res/drawable-xxxhdpi"
PLACEHOLDER_PREFIX = "ph_"
SIZE = 192


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    if not slug:
        raise ValueError("drawable name must contain at least one letter or digit")
    if not slug.startswith(PLACEHOLDER_PREFIX):
        slug = PLACEHOLDER_PREFIX + slug
    return slug


def _initials(label: str) -> str:
    words = re.findall(r"[A-Za-z0-9]+", label)
    if not words:
        return "?"
    if len(words) >= 2:
        return (words[0][0] + words[1][0]).upper()
    return words[0][:2].upper()


def _color_pair(key: str) -> tuple[tuple[int, int, int], tuple[int, int, int]]:
    digest = hashlib.sha256(key.encode("utf-8")).digest()
    hue = digest[0] / 255.0
    hue_2 = (hue + 0.08 + digest[1] / 2040.0) % 1.0
    top = colorsys.hls_to_rgb(hue, 0.42, 0.66)
    bottom = colorsys.hls_to_rgb(hue_2, 0.28, 0.72)
    return (
        tuple(int(channel * 255) for channel in top),
        tuple(int(channel * 255) for channel in bottom),
    )


def _parse_color(value: str | None) -> tuple[int, int, int] | None:
    if value is None:
        return None
    raw = value.strip().lstrip("#")
    if not re.fullmatch(r"[0-9a-fA-F]{6}", raw):
        raise ValueError("--color must be a 6-digit hex color")
    return tuple(int(raw[i : i + 2], 16) for i in (0, 2, 4))


def _load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        Path("C:/Windows/Fonts/seguisb.ttf"),
        Path("C:/Windows/Fonts/segoeuib.ttf"),
        Path("C:/Windows/Fonts/arialbd.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return ImageFont.truetype(str(candidate), size=size)
    return ImageFont.load_default()


def _fit_font(draw: ImageDraw.ImageDraw, text: str) -> ImageFont.ImageFont:
    for size in range(86, 42, -2):
        font = _load_font(size)
        left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
        if right - left <= 124 and bottom - top <= 94:
            return font
    return _load_font(44)


def _gradient(top: tuple[int, int, int], bottom: tuple[int, int, int]) -> Image.Image:
    image = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    pixels = image.load()
    for y in range(SIZE):
        ratio = y / (SIZE - 1)
        color = tuple(int(top[i] * (1 - ratio) + bottom[i] * ratio) for i in range(3))
        for x in range(SIZE):
            pixels[x, y] = (*color, 255)
    return image


def render_placeholder(label: str, color: tuple[int, int, int] | None = None) -> Image.Image:
    key = label.strip() or "placeholder"
    top, bottom = _color_pair(key)
    if color is not None:
        top = tuple(min(255, int(channel * 1.28)) for channel in color)
        bottom = tuple(max(0, int(channel * 0.62)) for channel in color)

    tile = _gradient(top, bottom)
    mask = Image.new("L", (SIZE, SIZE), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.rounded_rectangle((0, 0, SIZE - 1, SIZE - 1), radius=43, fill=255)

    shadow = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow)
    shadow_draw.rounded_rectangle((9, 13, SIZE - 9, SIZE - 5), radius=42, fill=(0, 0, 0, 90))
    shadow = shadow.filter(ImageFilter.GaussianBlur(10))

    image = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    image.alpha_composite(shadow)
    image.alpha_composite(Image.composite(tile, Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0)), mask))

    overlay = Image.new("RGBA", (SIZE, SIZE), (255, 255, 255, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    overlay_draw.rounded_rectangle((12, 12, SIZE - 13, SIZE - 13), radius=34, outline=(255, 255, 255, 54), width=2)
    overlay_draw.ellipse((-58, -70, SIZE + 30, 106), fill=(255, 255, 255, 38))
    image.alpha_composite(Image.composite(overlay, Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0)), mask))

    text = _initials(label)
    draw = ImageDraw.Draw(image)
    font = _fit_font(draw, text)
    left, top_box, right, bottom_box = draw.textbbox((0, 0), text, font=font)
    text_x = (SIZE - (right - left)) / 2 - left
    text_y = (SIZE - (bottom_box - top_box)) / 2 - top_box - 1
    draw.text((text_x + 2, text_y + 3), text, font=font, fill=(0, 0, 0, 92))
    draw.text((text_x, text_y), text, font=font, fill=(255, 255, 255, 244))
    return image


def _write_png(image: Image.Image, path: Path, force: bool) -> None:
    if path.exists() and not force:
        raise FileExistsError(f"{path} already exists; pass --force to overwrite")
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, format="PNG", optimize=True)


def _run_icontool_add(drawable: str, components: list[str]) -> int:
    if not components:
        return 0
    command = [sys.executable, str(REPO_ROOT / "scripts/icontool.py"), "add", drawable]
    for component in components:
        command.extend(["--component", component])
    return subprocess.run(command, cwd=REPO_ROOT).returncode


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--drawable", required=True, help="Drawable name; ph_ is added when omitted.")
    parser.add_argument("--label", required=True, help="App label used for initials and deterministic color.")
    parser.add_argument("--component", action="append", default=[], help="ComponentInfo to map via icontool add.")
    parser.add_argument("--color", default=None, help="Optional #RRGGBB background base color.")
    parser.add_argument("--output", default=None, help="Write a preview PNG to this path instead of the app catalog.")
    parser.add_argument("--force", action="store_true", help="Overwrite an existing placeholder PNG.")
    parser.add_argument("--dry-run", action="store_true", help="Print planned output without writing files.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        drawable = _slugify(args.drawable)
        color = _parse_color(args.color)
    except ValueError as exc:
        print(f"gen_placeholders.py: {exc}", file=sys.stderr)
        return 1

    if not args.output and not args.component:
        print("gen_placeholders.py: --component is required when writing into the app catalog", file=sys.stderr)
        return 1

    output = Path(args.output) if args.output else PACK_DIR / f"{drawable}.png"
    if not output.is_absolute():
        output = REPO_ROOT / output

    print(f"placeholder: {drawable} label={args.label!r} output={output}")
    if args.component:
        for component in args.component:
            print(f"  component: {component}")
    elif not args.output:
        print("  note: no --component supplied; generated asset will not be mapped")

    if args.dry_run:
        return 0

    try:
        image = render_placeholder(args.label, color=color)
        _write_png(image, output, args.force)
    except Exception as exc:
        print(f"gen_placeholders.py: {exc}", file=sys.stderr)
        return 1

    if args.output:
        print(f"  wrote preview {output}")
        return 0

    print(f"  wrote {output.relative_to(REPO_ROOT)}")
    return _run_icontool_add(drawable, args.component)


if __name__ == "__main__":
    sys.exit(main())
