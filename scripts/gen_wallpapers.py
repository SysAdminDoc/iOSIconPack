#!/usr/bin/env python3
"""Generate original, deterministic WebP wallpapers for the icon pack."""
from __future__ import annotations

import argparse
import json
import math
import random
import sys
from dataclasses import dataclass
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFilter
except ImportError:
    print(
        "gen_wallpapers.py: Pillow is required. Install with:\n"
        "  python -m pip install -r requirements.txt",
        file=sys.stderr,
    )
    sys.exit(1)


REPO_ROOT = Path(__file__).resolve().parents[1]
ASSET_DIR = REPO_ROOT / "app/src/main/assets/wallpapers"
THUMB_DIR = ASSET_DIR / "thumbs"
CATALOG = ASSET_DIR / "wallpapers.json"
REMOTE_BASE = "https://raw.githubusercontent.com/SysAdminDoc/iOSIconPack/master/app/src/main/assets/wallpapers"
FULL_SIZE = (720, 1600)
BASE_SIZE = (360, 800)
THUMB_SIZE = (180, 400)
COPYRIGHT = "MIT - original procedural artwork by SysAdminDoc"


@dataclass(frozen=True)
class WallpaperSpec:
    key: str
    name: str
    collection: str
    colors: tuple[str, str, str]
    accent: str
    seed: int
    motif: str


SPECS: tuple[WallpaperSpec, ...] = (
    WallpaperSpec("ios14_flow", "iOS 14 Flow", "iOS 14|Original|Gradient", ("#0a84ff", "#64d2ff", "#bf5af2"), "#ffd60a", 1401, "ribbons"),
    WallpaperSpec("ios15_bloom", "iOS 15 Bloom", "iOS 15|Original|Gradient", ("#ff375f", "#ff9f0a", "#64d2ff"), "#ffffff", 1501, "blooms"),
    WallpaperSpec("ios16_orbit", "iOS 16 Orbit", "iOS 16|Original|Abstract", ("#5e5ce6", "#30d158", "#0a84ff"), "#ff453a", 1601, "orbits"),
    WallpaperSpec("ios17_mist", "iOS 17 Mist", "iOS 17|Original|Soft", ("#f2f2f7", "#007aff", "#af52de"), "#34c759", 1701, "mist"),
    WallpaperSpec("ios18_tint", "iOS 18 Tint", "iOS 18|Original|Tinted", ("#1c1c1e", "#0a84ff", "#30d158"), "#ff9f0a", 1801, "mesh"),
    WallpaperSpec("ios26_glass", "iOS 26 Liquid Glass", "iOS 26|Original|Glass", ("#0b1020", "#5ac8fa", "#bf5af2"), "#ffffff", 2601, "glass"),
)


def _hex(value: str) -> tuple[int, int, int]:
    raw = value.lstrip("#")
    return tuple(int(raw[i : i + 2], 16) for i in (0, 2, 4))


def _blend(a: tuple[int, int, int], b: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    return tuple(int(a[i] * (1.0 - t) + b[i] * t) for i in range(3))


def _base_gradient(spec: WallpaperSpec) -> Image.Image:
    top, middle, bottom = (_hex(color) for color in spec.colors)
    image = Image.new("RGB", BASE_SIZE)
    pixels = image.load()
    for y in range(BASE_SIZE[1]):
        ratio = y / (BASE_SIZE[1] - 1)
        if ratio < 0.54:
            color = _blend(top, middle, ratio / 0.54)
        else:
            color = _blend(middle, bottom, (ratio - 0.54) / 0.46)
        for x in range(BASE_SIZE[0]):
            drift = int(16 * math.sin((x / BASE_SIZE[0]) * math.pi + ratio * 2.1))
            pixels[x, y] = tuple(max(0, min(255, channel + drift)) for channel in color)
    return image.convert("RGBA")


def _soft_layer(size: tuple[int, int], color: tuple[int, int, int], alpha: int) -> Image.Image:
    return Image.new("RGBA", size, (*color, alpha))


def _draw_ribbons(image: Image.Image, spec: WallpaperSpec, rng: random.Random) -> None:
    draw = ImageDraw.Draw(image, "RGBA")
    accent = _hex(spec.accent)
    width, height = image.size
    for idx in range(7):
        points: list[tuple[int, int]] = []
        offset = rng.randint(-90, 90)
        for step in range(9):
            x = int(step * width / 8)
            y = int(height * (0.20 + idx * 0.095) + math.sin(step * 1.2 + idx) * 54 + offset)
            points.append((x, y))
        draw.line(points, fill=(*accent, 34 + idx * 6), width=18 + idx * 2, joint="curve")


def _draw_blooms(image: Image.Image, spec: WallpaperSpec, rng: random.Random) -> None:
    width, height = image.size
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay, "RGBA")
    palette = [_hex(color) for color in spec.colors] + [_hex(spec.accent)]
    for idx in range(16):
        radius = rng.randint(44, 138)
        x = rng.randint(-40, width)
        y = rng.randint(-40, height)
        color = palette[idx % len(palette)]
        draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=(*color, rng.randint(26, 62)))
    image.alpha_composite(overlay.filter(ImageFilter.GaussianBlur(32)))


def _draw_orbits(image: Image.Image, spec: WallpaperSpec, rng: random.Random) -> None:
    draw = ImageDraw.Draw(image, "RGBA")
    width, height = image.size
    accent = _hex(spec.accent)
    for idx in range(11):
        cx = width * (0.15 + idx * 0.075)
        cy = height * (0.22 + 0.045 * math.sin(idx))
        rx = 100 + idx * 17
        ry = 42 + idx * 9
        box = (cx - rx, cy - ry + idx * 32, cx + rx, cy + ry + idx * 32)
        draw.ellipse(box, outline=(*accent, 34), width=2 + idx % 3)
    _draw_blooms(image, spec, rng)


def _draw_mist(image: Image.Image, spec: WallpaperSpec, rng: random.Random) -> None:
    width, height = image.size
    overlay = Image.new("RGBA", image.size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(overlay, "RGBA")
    for idx in range(9):
        y = int(height * (0.1 + idx * 0.1))
        draw.rounded_rectangle((-50, y, width + 50, y + rng.randint(42, 86)), radius=42, fill=(255, 255, 255, 28))
    image.alpha_composite(overlay.filter(ImageFilter.GaussianBlur(18)))


def _draw_mesh(image: Image.Image, spec: WallpaperSpec, rng: random.Random) -> None:
    draw = ImageDraw.Draw(image, "RGBA")
    width, height = image.size
    colors = [_hex(color) for color in spec.colors]
    for idx in range(18):
        x0 = rng.randint(-80, width)
        y0 = rng.randint(-80, height)
        x1 = rng.randint(-80, width)
        y1 = rng.randint(-80, height)
        color = colors[idx % len(colors)]
        draw.line((x0, y0, x1, y1), fill=(*color, 36), width=rng.randint(14, 36))
    _draw_blooms(image, spec, rng)


def _draw_glass(image: Image.Image, spec: WallpaperSpec, rng: random.Random) -> None:
    _draw_mesh(image, spec, rng)
    overlay = Image.new("RGBA", image.size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(overlay, "RGBA")
    width, height = image.size
    for idx in range(7):
        x = rng.randint(-20, width - 90)
        y = rng.randint(20, height - 160)
        w = rng.randint(95, 185)
        h = rng.randint(78, 210)
        draw.rounded_rectangle((x, y, x + w, y + h), radius=28, fill=(255, 255, 255, 24), outline=(255, 255, 255, 58), width=2)
    image.alpha_composite(overlay.filter(ImageFilter.GaussianBlur(1)))


def render_wallpaper(spec: WallpaperSpec) -> Image.Image:
    rng = random.Random(spec.seed)
    image = _base_gradient(spec)
    {
        "ribbons": _draw_ribbons,
        "blooms": _draw_blooms,
        "orbits": _draw_orbits,
        "mist": _draw_mist,
        "mesh": _draw_mesh,
        "glass": _draw_glass,
    }[spec.motif](image, spec, rng)
    image = image.filter(ImageFilter.GaussianBlur(0.25))
    return image.resize(FULL_SIZE, Image.Resampling.LANCZOS).convert("RGB")


def _asset_url(path: Path) -> str:
    return "file:///android_asset/" + path.relative_to(REPO_ROOT / "app/src/main/assets").as_posix()


def _remote_url(path: Path) -> str:
    return REMOTE_BASE + "/" + path.relative_to(ASSET_DIR).as_posix()


def _write_webp(image: Image.Image, path: Path, *, quality: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, format="WEBP", quality=quality, method=6)


def generate(force: bool = False) -> list[dict[str, object]]:
    catalog: list[dict[str, object]] = []
    for spec in SPECS:
        full_path = ASSET_DIR / f"{spec.key}.webp"
        thumb_path = THUMB_DIR / f"{spec.key}.webp"
        if not force and (full_path.exists() or thumb_path.exists()):
            raise FileExistsError(f"{spec.key} already exists; pass --force to overwrite")
        image = render_wallpaper(spec)
        thumb = image.resize(THUMB_SIZE, Image.Resampling.LANCZOS)
        _write_webp(image, full_path, quality=84)
        _write_webp(thumb, thumb_path, quality=78)
        catalog.append(
            {
                "name": spec.name,
                "author": "SysAdminDoc",
                "url": _asset_url(full_path),
                "thumbnail": _asset_url(thumb_path),
                "local_url": _asset_url(full_path),
                "local_thumbnail": _asset_url(thumb_path),
                "remote_url": _remote_url(full_path),
                "remote_thumbnail": _remote_url(thumb_path),
                "collections": spec.collection,
                "downloadable": True,
                "size": full_path.stat().st_size,
                "dimensions": f"{FULL_SIZE[0]} x {FULL_SIZE[1]} px",
                "copyright": COPYRIGHT,
            }
        )
    CATALOG.write_text(json.dumps(catalog, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return catalog


def _local_asset_path(url: str) -> Path | None:
    prefix = "file:///android_asset/"
    if not url.startswith(prefix):
        return None
    return REPO_ROOT / "app/src/main/assets" / url.removeprefix(prefix)


def check() -> int:
    if not CATALOG.exists():
        print(f"gen_wallpapers.py: missing {CATALOG.relative_to(REPO_ROOT)}", file=sys.stderr)
        return 1
    try:
        data = json.loads(CATALOG.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"gen_wallpapers.py: malformed catalog JSON: {exc}", file=sys.stderr)
        return 1
    if not isinstance(data, list) or len(data) != len(SPECS):
        print(f"gen_wallpapers.py: expected {len(SPECS)} wallpaper records", file=sys.stderr)
        return 1

    errors: list[str] = []
    for entry in data:
        if not isinstance(entry, dict):
            errors.append("wallpaper entry is not an object")
            continue
        for key in ("name", "url", "thumbnail", "size", "dimensions", "copyright"):
            if key not in entry:
                errors.append(f"{entry.get('name', '<unknown>')}: missing {key}")
        for key in ("url", "thumbnail"):
            path = _local_asset_path(str(entry.get(key, "")))
            if path is None:
                errors.append(f"{entry.get('name', '<unknown>')}: {key} is not a local asset URL")
                continue
            if not path.exists():
                errors.append(f"{entry.get('name', '<unknown>')}: missing asset {path.relative_to(REPO_ROOT)}")
                continue
            try:
                with Image.open(path) as image:
                    if key == "url" and image.size != FULL_SIZE:
                        errors.append(f"{entry.get('name', '<unknown>')}: full wallpaper is {image.size}, expected {FULL_SIZE}")
                    if key == "thumbnail" and image.size != THUMB_SIZE:
                        errors.append(f"{entry.get('name', '<unknown>')}: thumbnail is {image.size}, expected {THUMB_SIZE}")
            except Exception as exc:
                errors.append(f"{entry.get('name', '<unknown>')}: cannot inspect {path.name}: {exc}")
        full_path = _local_asset_path(str(entry.get("url", "")))
        if full_path and full_path.exists() and entry.get("size") != full_path.stat().st_size:
            errors.append(f"{entry.get('name', '<unknown>')}: size metadata does not match file")
        if entry.get("dimensions") != f"{FULL_SIZE[0]} x {FULL_SIZE[1]} px":
            errors.append(f"{entry.get('name', '<unknown>')}: dimensions metadata is wrong")

    if errors:
        print(f"gen_wallpapers.py: FAILED ({len(errors)} error(s))", file=sys.stderr)
        for error in errors:
            print(f"  {error}", file=sys.stderr)
        return 1
    print(f"gen_wallpapers.py: OK ({len(data)} local wallpaper records)")
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="Overwrite existing generated wallpaper assets.")
    parser.add_argument("--check", action="store_true", help="Validate generated wallpaper assets and JSON.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if args.check:
        return check()
    try:
        catalog = generate(force=args.force)
    except Exception as exc:
        print(f"gen_wallpapers.py: {exc}", file=sys.stderr)
        return 1
    print(f"gen_wallpapers.py: wrote {len(catalog)} wallpapers to {ASSET_DIR.relative_to(REPO_ROOT)}")
    return check()


if __name__ == "__main__":
    sys.exit(main())
