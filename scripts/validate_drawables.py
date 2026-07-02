#!/usr/bin/env python3
"""validate_drawables.py — local validator for PNG and vector drawable assets.

Checks:
  1. Every PNG in drawable-xxxhdpi/ is exactly 192x192 pixels.
  2. Every PNG is a valid PNG (correct magic bytes + parseable IHDR).
  3. Every PNG is under the size budget (200 KB).
  4. Every vector drawable in drawable/ parses as valid XML.
  5. Every item in drawable.xml has a corresponding file on disk.
  6. iOS 26 Liquid Glass PNGs use clipped squircle corners and opaque centers.
  7. Glyph-only variants exist for vector monochrome sources and stay vector.

Exit 0 on success, 1 on any failure.
"""
from __future__ import annotations

import json
import os
import struct
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

REPO_ROOT     = Path(__file__).resolve().parents[1]
RES_ROOT      = REPO_ROOT / "app/src/main/res"
ASSETS_DIR    = REPO_ROOT / "app/src/main/assets"
HDPI_DIR      = REPO_ROOT / "app/src/main/res/drawable-xxxhdpi"
VEC_DIR       = REPO_ROOT / "app/src/main/res/drawable"
DRAWABLE_XML  = REPO_ROOT / "app/src/main/res/xml/drawable.xml"
THEME_RESOURCES_XML = REPO_ROOT / "app/src/main/res/xml/theme_resources.xml"
ANDROID_MANIFEST = REPO_ROOT / "app/src/main/AndroidManifest.xml"
WALLPAPERS_XML = REPO_ROOT / "app/src/main/res/values/wallpapers.xml"
FRAMES_SETUP_XML = REPO_ROOT / "app/src/main/res/values/frames_setup.xml"
RAW_GITHUB_PREFIX = "https://raw.githubusercontent.com/SysAdminDoc/iOSIconPack/master/"

EXPECTED_SIZE = 192          # px
MAX_FILE_KB   = 200          # KB

# Corner region checked for squircle transparency (pixels from each corner)
SQUIRCLE_CORNER_REGION = 15   # px
SQUIRCLE_MAX_OPAQUE    = 5    # max opaque pixels allowed in each corner before warning
SQUIRCLE_CHECK_MAX_FILES = int(os.getenv("IOSICONS_SQUIRCLE_CHECK_MAX", "120"))

PNG_MAGIC     = b"\x89PNG\r\n\x1a\n"

# Launcher/system drawables in drawable/ that aren't icon-pack artwork
_VEC_SKIP_PREFIXES = ("ic_launcher", "ic_", "background", "foreground", "ic_muzei")
_ANDROID_NS = "{http://schemas.android.com/apk/res/android}"
_GLYPH_SOURCE_PREFIXES = (
    "ios14_",
    "ios15_",
    "ios16_",
    "ios17_",
    "ios18_",
    "ios26_lg_",
    "tp_",
)
_THEMED_BACKGROUND_BY_PREFIX = {
    "ios14_": "@color/ios14_themed_icon_background",
    "ios15_": "@color/ios15_themed_icon_background",
    "ios16_": "@color/ios16_themed_icon_background",
    "ios17_": "@color/ios17_themed_icon_background",
    "ios18_": "@color/ios18_themed_icon_background",
    "ios26_lg_": "@color/ios26_liquid_glass_themed_icon_background",
    "tp_": "@color/third_party_themed_icon_background",
}


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


def _collect_drawables() -> set[str]:
    drawables: set[str] = set()
    for path in VEC_DIR.glob("*.xml"):
        drawables.add(path.stem)
    for path in (REPO_ROOT / "app/src/main/res").glob("drawable-*/*"):
        if path.is_file() and path.suffix.lower() in {".png", ".webp", ".jpg", ".jpeg"}:
            drawables.add(path.stem)
    return drawables


def check_drawable_files() -> list[str]:
    """Ensure every item in drawable.xml has a PNG or vector on disk."""
    errors: list[str] = []
    try:
        tree = ET.parse(DRAWABLE_XML)
    except ET.ParseError as exc:
        return [f"  MALFORMED drawable.xml: {exc}"]

    drawables = _collect_drawables()
    for item in tree.iter("item"):
        name = item.get("drawable", "")
        if not name:
            continue
        if name not in drawables:
            errors.append(f"  MISSING FILE  drawable.xml references '{name}' but no PNG/vector found")
    return errors


def _mono_root_counts() -> tuple[int, int, int]:
    vector_count = 0
    bitmap_count = 0
    other_count = 0
    for path in VEC_DIR.glob("*_mono.xml"):
        try:
            root = ET.parse(path).getroot()
        except ET.ParseError:
            other_count += 1
            continue
        if root.tag == "vector":
            vector_count += 1
        elif root.tag == "bitmap":
            bitmap_count += 1
        else:
            other_count += 1
    return vector_count, bitmap_count, other_count


def _expected_themed_background(name: str) -> str | None:
    for prefix, background in _THEMED_BACKGROUND_BY_PREFIX.items():
        if name.startswith(prefix):
            return background
    return None


def check_themed_backgrounds() -> tuple[list[str], int]:
    errors: list[str] = []
    themed_background_count = 0
    for path in sorted(VEC_DIR.glob("*_themed.xml")):
        name = path.stem.removesuffix("_themed")
        expected = _expected_themed_background(name)
        if expected is None:
            continue
        try:
            root = ET.parse(path).getroot()
        except ET.ParseError:
            continue
        background = root.find("background")
        actual = background.get(f"{_ANDROID_NS}drawable", "") if background is not None else ""
        if actual == expected:
            themed_background_count += 1
            continue
        errors.append(
            f"  WRONG THEMED BG  {path.name}: {actual or '<missing>'} (expected {expected})"
        )
    return errors, themed_background_count


def _tag_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def check_glyph_variants() -> tuple[list[str], int]:
    errors: list[str] = []
    expected: set[str] = set()

    for path in sorted(VEC_DIR.glob("*_mono.xml")):
        base = path.stem.removesuffix("_mono")
        if not base.startswith(_GLYPH_SOURCE_PREFIXES):
            continue
        try:
            root = ET.parse(path).getroot()
        except ET.ParseError:
            continue
        if _tag_name(root.tag) == "vector":
            expected.add(f"glyph_{base}")

    glyph_files = {path.stem: path for path in sorted(VEC_DIR.glob("glyph_*.xml"))}
    for name in sorted(expected - set(glyph_files)):
        errors.append(f"  MISSING GLYPH  {name}.xml")
    for name in sorted(set(glyph_files) - expected):
        errors.append(f"  STALE GLYPH  {name}.xml has no vector mono source")

    for name, path in glyph_files.items():
        try:
            root = ET.parse(path).getroot()
        except ET.ParseError as exc:
            errors.append(f"  MALFORMED GLYPH  {path.name}: {exc}")
            continue
        if _tag_name(root.tag) != "vector":
            errors.append(f"  BAD GLYPH ROOT  {path.name}: root must be <vector>")
            continue
        if any(_tag_name(element.tag) == "bitmap" for element in root.iter()):
            errors.append(f"  BITMAP GLYPH  {path.name}: glyph variants must stay vector-only")
        paths = [element for element in root.iter() if _tag_name(element.tag) == "path"]
        has_border = any(
            element.attrib.get(f"{_ANDROID_NS}strokeColor")
            and element.attrib.get(f"{_ANDROID_NS}fillColor", "").upper() in {
                "#00000000",
                "#00FFFFFF",
            }
            for element in paths
        )
        if not has_border:
            errors.append(f"  BORDERLESS GLYPH  {path.name}: missing transparent border stroke")

    return errors, len(glyph_files)


def _resource_name(value: str) -> str:
    return value.strip().removeprefix("@").split("/")[-1]


def _resource_exists(name: str) -> bool:
    if not name:
        return False
    for family in ("drawable*", "mipmap*"):
        for path in RES_ROOT.glob(f"{family}/*"):
            if path.is_file() and path.stem == name:
                return True
    return False


def _wallpaper_item_count() -> int:
    if not WALLPAPERS_XML.exists():
        return 0
    try:
        root = ET.parse(WALLPAPERS_XML).getroot()
    except ET.ParseError:
        return 0
    count = 0
    for string in root.iter("string"):
        if string.get("name") == "json_url" and (string.text or "").strip():
            count += 1
    for array in root.iter("string-array"):
        if array.get("name") == "wallpapers_json_urls":
            count += sum(1 for item in array.iter("item") if (item.text or "").strip())
    return count


def _frames_wallpaper_json_url() -> str:
    if not WALLPAPERS_XML.exists():
        return ""
    try:
        root = ET.parse(WALLPAPERS_XML).getroot()
    except ET.ParseError:
        return ""
    for string in root.iter("string"):
        if string.get("name") == "json_url":
            return (string.text or "").strip()
    return ""


def _wallpaper_json_urls() -> list[str]:
    if not WALLPAPERS_XML.exists():
        return []
    try:
        root = ET.parse(WALLPAPERS_XML).getroot()
    except ET.ParseError:
        return []
    urls: list[str] = []
    frames_url = _frames_wallpaper_json_url()
    if frames_url:
        urls.append(frames_url)
    for array in root.iter("string-array"):
        if array.get("name") == "wallpapers_json_urls":
            urls.extend((item.text or "").strip() for item in array.iter("item") if (item.text or "").strip())
    return list(dict.fromkeys(urls))


def _wallpapers_section_enabled() -> bool:
    if not FRAMES_SETUP_XML.exists():
        return False
    try:
        root = ET.parse(FRAMES_SETUP_XML).getroot()
    except ET.ParseError:
        return False
    for item in root.iter("bool"):
        if item.get("name") == "show_wallpapers_section":
            return (item.text or "").strip().lower() == "true"
    return False


def _asset_path_from_url(url: str) -> Path | None:
    prefix = "file:///android_asset/"
    if url.startswith(prefix):
        return ASSETS_DIR / url.removeprefix(prefix)
    if url.startswith(RAW_GITHUB_PREFIX):
        return REPO_ROOT / url.removeprefix(RAW_GITHUB_PREFIX)
    return None


def check_wallpaper_assets() -> list[str]:
    errors: list[str] = []
    urls = _wallpaper_json_urls()
    if _wallpapers_section_enabled() and not _frames_wallpaper_json_url():
        errors.append("  EMPTY WALLPAPER SURFACE  wallpapers section is enabled but Frames json_url is empty")
        return errors
    if _wallpapers_section_enabled() and not urls:
        errors.append("  EMPTY WALLPAPER SURFACE  wallpapers section is enabled but no wallpaper JSON URL is configured")
        return errors

    for url in urls:
        path = _asset_path_from_url(url)
        if path is None:
            continue
        if not path.exists():
            errors.append(f"  MISSING WALLPAPER JSON  {url}")
            continue
        try:
            entries = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"  MALFORMED WALLPAPER JSON  {path.relative_to(REPO_ROOT)}: {exc}")
            continue
        if not isinstance(entries, list) or not entries:
            errors.append(f"  EMPTY WALLPAPER JSON  {path.relative_to(REPO_ROOT)}")
            continue
        for entry in entries:
            if not isinstance(entry, dict):
                errors.append(f"  MALFORMED WALLPAPER ENTRY  {path.relative_to(REPO_ROOT)} contains a non-object entry")
                continue
            name = str(entry.get("name") or "<unnamed>")
            for field in ("url", "thumbnail", "size", "dimensions", "copyright"):
                if field not in entry:
                    errors.append(f"  WALLPAPER METADATA  {name}: missing {field}")
            full_path = _asset_path_from_url(str(entry.get("url", "")))
            thumb_path = _asset_path_from_url(str(entry.get("thumbnail", "")))
            for label, asset in (("url", full_path), ("thumbnail", thumb_path)):
                if asset is None:
                    errors.append(f"  WALLPAPER ASSET  {name}: {label} is not a supported asset URL")
                    continue
                if not asset.exists():
                    errors.append(f"  WALLPAPER ASSET  {name}: missing {asset.relative_to(REPO_ROOT)}")
            if full_path and full_path.exists() and entry.get("size") != full_path.stat().st_size:
                errors.append(f"  WALLPAPER METADATA  {name}: size does not match file")
            if full_path and full_path.exists() and thumb_path and thumb_path.exists():
                try:
                    from PIL import Image  # type: ignore

                    with Image.open(full_path) as full_image:
                        expected = f"{full_image.size[0]} x {full_image.size[1]} px"
                        if entry.get("dimensions") != expected:
                            errors.append(f"  WALLPAPER METADATA  {name}: dimensions should be '{expected}'")
                    with Image.open(thumb_path) as thumb_image:
                        if thumb_image.size[0] > 480 or thumb_image.size[1] > 960:
                            errors.append(f"  WALLPAPER THUMBNAIL  {name}: thumbnail is too large at {thumb_image.size}")
                except Exception as exc:
                    errors.append(f"  WALLPAPER ASSET  {name}: cannot inspect image dimensions ({exc})")
    return errors


def check_launcher_resources() -> list[str]:
    errors: list[str] = []
    if THEME_RESOURCES_XML.exists():
        try:
            root = ET.parse(THEME_RESOURCES_XML).getroot()
        except ET.ParseError as exc:
            return [f"  MALFORMED theme_resources.xml: {exc}"]
        for node in root.iter():
            for attr in ("image", "image1", "image2", "selector"):
                raw = node.get(attr, "")
                if not raw:
                    continue
                name = _resource_name(raw)
                if not _resource_exists(name):
                    errors.append(
                        f"  MISSING LAUNCHER RESOURCE  theme_resources.xml <{node.tag}> {attr}='{raw}'"
                    )

    manifest = ANDROID_MANIFEST.read_text(encoding="utf-8") if ANDROID_MANIFEST.exists() else ""
    advertises_wallpapers = any(
        marker in manifest
        for marker in (
            "android.intent.action.SET_WALLPAPER",
            "android.intent.action.GET_CONTENT",
            "com.google.android.apps.muzei.api.MuzeiArtProvider",
        )
    )
    if advertises_wallpapers and _wallpaper_item_count() == 0:
        errors.append("  EMPTY WALLPAPER SURFACE  manifest advertises wallpapers but wallpapers_json_urls is empty")

    return errors


def check_liquid_glass_masks() -> list[str]:
    errors: list[str] = []
    for path in sorted(HDPI_DIR.glob("ios26_lg_*.png")):
        try:
            from PIL import Image  # type: ignore

            img = Image.open(path).convert("RGBA")
        except Exception as exc:
            errors.append(f"  LIQUID GLASS MASK  {path.name}: cannot inspect alpha ({exc})")
            continue

        w, h = img.size
        corners = (
            img.getpixel((0, 0))[3],
            img.getpixel((w - 1, 0))[3],
            img.getpixel((0, h - 1))[3],
            img.getpixel((w - 1, h - 1))[3],
        )
        if any(alpha > 12 for alpha in corners):
            errors.append(
                f"  LIQUID GLASS MASK  {path.name}: corners are not clipped transparent"
            )
        if img.getpixel((w // 2, h // 2))[3] < 220:
            errors.append(
                f"  LIQUID GLASS MASK  {path.name}: center is not opaque enough"
            )
    return errors


def check_squircle_corners() -> tuple[list[str], str | None]:
    """Warn if any PNG has too many opaque pixels in its four corner regions."""
    try:
        from PIL import Image  # type: ignore
    except ImportError:
        return [], None

    pngs = sorted(HDPI_DIR.glob("*.png"))
    if (
        len(pngs) > SQUIRCLE_CHECK_MAX_FILES
        and os.getenv("IOSICONS_FULL_SQUIRCLE_CHECK") != "1"
    ):
        return [], (
            f"squircle check skipped for {len(pngs)} PNGs "
            f"(set IOSICONS_FULL_SQUIRCLE_CHECK=1 for full warning scan)"
        )

    warnings: list[str] = []
    r = SQUIRCLE_CORNER_REGION
    for path in pngs:
        try:
            img = Image.open(path).convert("RGBA")
        except Exception:
            continue

        w, h = img.size
        corners = [
            img.crop((0, 0, r, r)),
            img.crop((w - r, 0, w, r)),
            img.crop((0, h - r, r, h)),
            img.crop((w - r, h - r, w, h)),
        ]
        labels = ["top-left", "top-right", "bottom-left", "bottom-right"]
        for region, label in zip(corners, labels):
            opaque = sum(1 for px in region.getdata() if px[3] > 10)
            if opaque > SQUIRCLE_MAX_OPAQUE:
                warnings.append(
                    f"  WARN squircle  {path.name}: {opaque} opaque px in {label} corner"
                )
    return warnings, None

def main() -> int:
    all_errors: list[str] = []

    png_errors = check_pngs()
    vec_errors = check_vectors()
    file_errors = check_drawable_files()
    themed_errors, themed_background_count = check_themed_backgrounds()
    glyph_errors, glyph_count = check_glyph_variants()
    wallpaper_errors = check_wallpaper_assets()
    launcher_errors = check_launcher_resources()
    liquid_glass_errors = check_liquid_glass_masks()
    squircle_warnings, squircle_note = check_squircle_corners()

    png_count = len(list(HDPI_DIR.glob("*.png")))
    vec_count = sum(
        1 for f in VEC_DIR.glob("*.xml")
        if not any(f.stem.startswith(p) for p in _VEC_SKIP_PREFIXES)
    )
    mono_count = sum(1 for _ in VEC_DIR.glob("*_mono.xml"))
    themed_count = sum(1 for _ in VEC_DIR.glob("*_themed.xml"))
    pure_vec_count = vec_count - mono_count - themed_count - glyph_count
    mono_vector_count, mono_bitmap_count, mono_other_count = _mono_root_counts()

    all_errors.extend(png_errors)
    all_errors.extend(vec_errors)
    all_errors.extend(file_errors)
    all_errors.extend(themed_errors)
    all_errors.extend(glyph_errors)
    all_errors.extend(wallpaper_errors)
    all_errors.extend(launcher_errors)
    all_errors.extend(liquid_glass_errors)

    if all_errors:
        print(f"validate_drawables.py: FAILED ({len(all_errors)} error(s))", file=sys.stderr)
        for err in all_errors:
            print(err, file=sys.stderr)
        return 1

    print(
        f"validate_drawables.py: OK "
        f"({png_count} PNGs at {EXPECTED_SIZE}x{EXPECTED_SIZE}px, "
        f"{pure_vec_count} catalog vector(s), "
        f"{mono_vector_count} monochrome vector(s), "
        f"{mono_bitmap_count} bitmap mono fallback(s), "
        f"{mono_other_count} other mono XML(s), "
        f"{glyph_count} transparent glyph variant(s), "
        f"{themed_count} themed wrapper(s), "
        f"{themed_background_count} era background(s))"
    )
    if squircle_warnings:
        affected = len({w.split()[2] for w in squircle_warnings})
        total_pngs = len(list(HDPI_DIR.glob("*.png")))
        print(
            f"  squircle check: {affected}/{total_pngs} icons have opaque corners "
            "(expected for Apple-sourced icons; launcher applies squircle mask at runtime)"
        )
    elif squircle_note:
        print(f"  {squircle_note}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
