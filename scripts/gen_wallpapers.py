#!/usr/bin/env python3
"""Generate original, deterministic WebP wallpapers for the icon pack."""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path

try:
    from PIL import Image, ImageOps
except ImportError:
    print(
        "gen_wallpapers.py: Pillow is required. Install with:\n"
        "  python -m pip install -r requirements.txt",
        file=sys.stderr,
    )
    sys.exit(1)


REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = REPO_ROOT / "assets/wallpapers/sources"
ASSET_DIR = REPO_ROOT / "app/src/main/assets/wallpapers"
THUMB_DIR = ASSET_DIR / "thumbs"
CATALOG = ASSET_DIR / "wallpapers.json"
REMOTE_BASE = "https://raw.githubusercontent.com/SysAdminDoc/iOSIconPack/master/app/src/main/assets/wallpapers"
FULL_SIZE = (720, 1600)
THUMB_SIZE = (180, 400)
COPYRIGHT = "MIT - original artwork by SysAdminDoc"


@dataclass(frozen=True)
class WallpaperSpec:
    key: str
    name: str
    collection: str


SPECS: tuple[WallpaperSpec, ...] = (
    WallpaperSpec("ios14_flow", "iOS 14 Flow", "iOS 14|Original|Gradient"),
    WallpaperSpec("ios15_bloom", "iOS 15 Bloom", "iOS 15|Original|Gradient"),
    WallpaperSpec("ios16_orbit", "iOS 16 Orbit", "iOS 16|Original|Abstract"),
    WallpaperSpec("ios17_mist", "iOS 17 Mist", "iOS 17|Original|Soft"),
    WallpaperSpec("ios18_tint", "iOS 18 Tint", "iOS 18|Original|Tinted"),
    WallpaperSpec("ios26_glass", "iOS 26 Liquid Glass", "iOS 26|Original|Glass"),
)


def render_wallpaper(spec: WallpaperSpec) -> Image.Image:
    source_path = SOURCE_DIR / f"{spec.key}.png"
    if not source_path.exists():
        raise FileNotFoundError(f"missing source artwork: {source_path.relative_to(REPO_ROOT)}")
    with Image.open(source_path) as source:
        return ImageOps.fit(
            source.convert("RGB"),
            FULL_SIZE,
            method=Image.Resampling.LANCZOS,
            centering=(0.5, 0.5),
        )


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
    with CATALOG.open("w", encoding="utf-8", newline="\n") as catalog_file:
        catalog_file.write(json.dumps(catalog, indent=2, sort_keys=True) + "\n")
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
    for spec in SPECS:
        source_path = SOURCE_DIR / f"{spec.key}.png"
        if not source_path.exists():
            errors.append(f"{spec.name}: missing source artwork {source_path.relative_to(REPO_ROOT)}")
            continue
        try:
            with Image.open(source_path) as source:
                if source.width < FULL_SIZE[0] or source.height < FULL_SIZE[1]:
                    errors.append(
                        f"{spec.name}: source artwork is {source.size}, expected at least {FULL_SIZE}"
                    )
        except (OSError, ValueError) as exc:
            errors.append(f"{spec.name}: cannot inspect source artwork ({exc})")

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
            except (OSError, ValueError) as exc:
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
    except (OSError, ValueError) as exc:
        print(f"gen_wallpapers.py: {exc}", file=sys.stderr)
        return 1
    print(f"gen_wallpapers.py: wrote {len(catalog)} wallpapers to {ASSET_DIR.relative_to(REPO_ROOT)}")
    return check()


if __name__ == "__main__":
    sys.exit(main())
