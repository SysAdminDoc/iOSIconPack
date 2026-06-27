#!/usr/bin/env python3
"""Fetch real iOS app icons from Apple's iTunes Search API and store as PNGs.

Downloads 1024x1024 originals into `icons_raw/`, resizes to 192x192 for the
xxxhdpi bucket, applies a per-era color grade, and writes them under
`app/src/main/res/drawable-xxxhdpi/` using the canonical
`ios{ver}_{name}` / `tp_{name}` naming convention.

A SHA-256 hash cache (`icons_raw/.hash_cache.json`) skips redundant re-downloads
when the raw source file has not changed since the last run.

Usage:

    python3 fetch_icons.py                        # fetch everything
    python3 fetch_icons.py --only safari,photos   # fetch a subset
    python3 fetch_icons.py --dry-run              # show what would change
    python3 fetch_icons.py --validate             # list icons that exist on
                                                  # disk but have no appfilter
                                                  # mapping (dead weight)
    python3 fetch_icons.py --tp-only              # just third-party apps
    python3 fetch_icons.py --era ios18            # one era (repeatable)
    python3 fetch_icons.py --list                 # list all known icon names

Dependencies: Pillow. Install via `pip install -r requirements.txt` before
running — the script will NOT bootstrap pip on its own, per project policy.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen
from xml.etree import ElementTree as ET

try:
    from PIL import Image, ImageEnhance
except ImportError:
    sys.stderr.write(
        "fetch_icons.py: Pillow is required. Install with:\n"
        "    python3 -m pip install -r requirements.txt\n"
    )
    sys.exit(1)

# --- Paths --------------------------------------------------------------

SCRIPT_DIR = Path(__file__).resolve().parent
RAW_DIR = SCRIPT_DIR / "icons_raw"
PACK_DIR = SCRIPT_DIR / "app" / "src" / "main" / "res" / "drawable-xxxhdpi"
APPFILTER_XML = SCRIPT_DIR / "app" / "src" / "main" / "res" / "xml" / "appfilter.xml"
RAW_DIR.mkdir(parents=True, exist_ok=True)
PACK_DIR.mkdir(parents=True, exist_ok=True)

# --- App catalogue ------------------------------------------------------

APPLE_APP_IDS = {
    "safari": 1146562112,
    "messages": 1146560473,
    "photos": 1584215428,
    "music": 1108187390,
    "mail": 1108187098,
    "maps": 915056765,
    "weather": 1069513131,
    "notes": 1110145109,
    "calendar": 1108185179,
    "facetime": 1110145091,
    "health": 1242545199,
    "files": 1232058109,
    "wallet": 1160481993,
    "clock": 1584215688,
    "calculator": 1069511488,
    "compass": 1067456176,
    "appstore": 1108187803,
    "phone": 1146562108,
    "camera": 1584216193,
}
APPLE_SEARCH_ONLY = {
    # No public App Store app id is available for Settings, but the existing
    # pack ships a Settings icon and the search path keeps rebuilds complete.
    "settings": "Settings Apple iPhone",
}
SEARCH_TERMS = {k: f"{k.title()} Apple" for k in APPLE_APP_IDS}
SEARCH_TERMS["music"] = "Apple Music"
SEARCH_TERMS["maps"] = "Apple Maps"
SEARCH_TERMS["appstore"] = "App Store Apple"

THIRD_PARTY = {
    "instagram": "Instagram",
    "whatsapp": "WhatsApp Messenger",
    "telegram": "Telegram Messenger",
    "discord": "Discord",
    "spotify": "Spotify Music",
    "netflix": "Netflix",
    "youtube": "YouTube",
    "twitter": "X Twitter",
    "tiktok": "TikTok",
    "snapchat": "Snapchat",
    "facebook": "Facebook",
    "chrome": "Google Chrome",
    "gmail": "Gmail Google",
    "google_maps": "Google Maps",
    "uber": "Uber",
    "reddit": "Reddit",
    "slack": "Slack",
    "zoom": "Zoom Workplace",
    "pinterest": "Pinterest",
    "amazon": "Amazon Shopping",
    "paypal": "PayPal",
    "venmo": "Venmo",
    "robinhood": "Robinhood",
    "strava": "Strava",
    "shazam": "Shazam",
}

# Apps that should exist as per-era variants (`ios18_instagram`,
# `ios17_instagram`, `ios26_lg_instagram`, etc.) so the dashboard and per-era
# APK builds can show more than Apple stock icons.
ERA_APP_VARIANTS = {
    **THIRD_PARTY,
    "google_search": "Google Search",
    "google_drive": "Google Drive",
    "google_docs": "Google Docs",
    "google_sheets": "Google Sheets",
    "google_slides": "Google Slides",
    "google_photos": "Google Photos",
    "google_meet": "Google Meet",
    "google_calendar": "Google Calendar",
    "google_keep": "Google Keep",
    "google_translate": "Google Translate",
    "google_one": "Google One",
    "google_classroom": "Google Classroom",
}

ERAS = ("ios18", "ios17", "ios16", "ios15", "ios14")
LIQUID_GLASS_SUBSET = set(APPLE_APP_IDS) | set(APPLE_SEARCH_ONLY) | set(ERA_APP_VARIANTS)

# Per-era color grade parameters applied to every resized icon.
# Keys match ERAS + "ios26_lg" + "tp" (third-party, no grade).
# Tuple: (saturation_factor, contrast_factor, brightness_factor)
# 1.0 = identity for each channel.
ERA_GRADES: dict[str, tuple[float, float, float]] = {
    "ios18":    (1.05, 1.08, 1.00),   # slightly punchy, high contrast
    "ios17":    (0.92, 0.98, 1.02),   # desaturated, flat, airy
    "ios16":    (0.95, 1.00, 1.00),   # clean, slightly muted
    "ios15":    (1.08, 1.05, 0.98),   # warm, vibrant
    "ios14":    (1.12, 1.05, 0.97),   # richest saturation, warm shadows
    "ios26_lg": (0.88, 0.95, 1.05),   # frosted / cool, reduced saturation
    "tp":       (1.00, 1.00, 1.00),   # no grade — preserve brand colors
}

# --- Hash cache ---------------------------------------------------------

HASH_CACHE_PATH = RAW_DIR / ".hash_cache.json"


def _load_cache() -> dict[str, str]:
    if HASH_CACHE_PATH.exists():
        try:
            return json.loads(HASH_CACHE_PATH.read_text("utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def _save_cache(cache: dict[str, str]) -> None:
    try:
        HASH_CACHE_PATH.write_text(json.dumps(cache, indent=2, sort_keys=True), "utf-8")
    except OSError:
        pass


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


# --- HTTP helpers -------------------------------------------------------

def _fetch_json(url: str) -> dict | None:
    headers = {"User-Agent": "Mozilla/5.0 (iOSIconPack fetch_icons)"}
    for attempt in range(3):
        try:
            req = Request(url, headers=headers)
            with urlopen(req, timeout=15) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except (URLError, json.JSONDecodeError) as exc:
            if attempt < 2:
                time.sleep(1)
            else:
                print(f"    FAILED: {exc}", file=sys.stderr)
                return None
    return None


def _download(url: str, dst: Path, cache: dict[str, str] | None = None) -> bool:
    """Download *url* to *dst*. Skips if cached SHA-256 matches remote file."""
    headers = {"User-Agent": "Mozilla/5.0 (iOSIconPack fetch_icons)"}
    try:
        req = Request(url, headers=headers)
        # Stream into a temp file first so we can compare hashes before committing.
        with tempfile.NamedTemporaryFile(dir=dst.parent, delete=False, suffix=".tmp") as tmp:
            tmp_path = Path(tmp.name)
            with urlopen(req, timeout=30) as resp:
                shutil.copyfileobj(resp, tmp)
        new_hash = _sha256_file(tmp_path)
        if cache is not None and cache.get(str(dst)) == new_hash and dst.exists():
            tmp_path.unlink(missing_ok=True)
            print("    cached (unchanged)")
            return True
        tmp_path.replace(dst)
        if cache is not None:
            cache[str(dst)] = new_hash
        return True
    except URLError as exc:
        print(f"    download failed: {exc}", file=sys.stderr)
        if "tmp_path" in dir() and tmp_path.exists():
            tmp_path.unlink(missing_ok=True)
        return False


def _upgrade_artwork_url(url: str) -> str:
    return re.sub(r"\d+x\d+\w*\.", "1024x1024bb.", url)


def _icon_by_id(app_id: int) -> str | None:
    data = _fetch_json(f"https://itunes.apple.com/lookup?id={app_id}&country=us")
    if not data or data.get("resultCount", 0) == 0:
        return None
    art = data["results"][0].get("artworkUrl512") or data["results"][0].get("artworkUrl100")
    return _upgrade_artwork_url(art) if art else None


def _icon_by_search(term: str) -> str | None:
    encoded = term.replace(" ", "+")
    data = _fetch_json(
        f"https://itunes.apple.com/search?term={encoded}&entity=software&country=us&limit=5"
    )
    if not data or data.get("resultCount", 0) == 0:
        return None
    for result in data["results"]:
        seller = (result.get("sellerName") or "").lower()
        artist = (result.get("artistName") or "").lower()
        if "apple" in seller or "apple" in artist:
            art = result.get("artworkUrl512") or result.get("artworkUrl100")
            return _upgrade_artwork_url(art) if art else None
    art = data["results"][0].get("artworkUrl512") or data["results"][0].get("artworkUrl100")
    return _upgrade_artwork_url(art) if art else None


# --- Pipeline -----------------------------------------------------------

def _apply_era_grade(img: Image.Image, era: str) -> Image.Image:
    """Apply per-era Saturation / Contrast / Brightness adjustments."""
    sat, con, bri = ERA_GRADES.get(era, ERA_GRADES["tp"])
    if sat != 1.0:
        img = ImageEnhance.Color(img).enhance(sat)
    if con != 1.0:
        img = ImageEnhance.Contrast(img).enhance(con)
    if bri != 1.0:
        img = ImageEnhance.Brightness(img).enhance(bri)
    return img


def _resize(src: Path, dst: Path, size: int = 192, era: str = "tp") -> bool:
    try:
        img = Image.open(src).convert("RGBA")
        img = img.resize((size, size), Image.Resampling.LANCZOS)
        img = _apply_era_grade(img, era)
        img.save(dst, "PNG", optimize=True)
        return True
    except (OSError, ValueError) as exc:
        print(f"    resize failed: {exc}", file=sys.stderr)
        return False


def _process(name: str, icon_url: str, prefix: str, dry_run: bool,
             cache: dict[str, str] | None = None) -> bool:
    raw = RAW_DIR / f"{name}_1024.png"
    pack = PACK_DIR / f"{prefix}_{name}.png"
    if dry_run:
        print(f"    [dry-run] would write {pack.relative_to(SCRIPT_DIR)}")
        return True
    if not raw.exists() and not _download(icon_url, raw, cache):
        return False
    era_key = prefix if prefix in ERA_GRADES else "tp"
    return _resize(raw, pack, era=era_key)


def _process_era_variants(
    name: str,
    icon_url: str,
    eras: tuple[str, ...],
    include_lg: bool,
    dry_run: bool,
    cache: dict[str, str] | None,
) -> int:
    processed = 0
    for prefix in eras:
        if _process(name, icon_url, prefix, dry_run, cache):
            processed += 1
    if include_lg and name in LIQUID_GLASS_SUBSET:
        if _process(name, icon_url, "ios26_lg", dry_run, cache):
            processed += 1
    return processed


def _appfilter_components(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    try:
        tree = ET.parse(path)
    except ET.ParseError:
        return {}
    mapping: dict[str, str] = {}
    for item in tree.getroot().findall("item"):
        drawable = item.get("drawable")
        component = item.get("component")
        if drawable and component:
            mapping[drawable] = component
    return mapping


def _validate(only: set[str] | None = None) -> int:
    """Report icons that live on disk without a corresponding appfilter entry."""
    disk = {p.stem for p in PACK_DIR.glob("*.png")
            if p.stem.startswith(("ios", "tp_"))}
    if only:
        disk = {s for s in disk if any(s.endswith(n) for n in only)}
    mapped = set(_appfilter_components(APPFILTER_XML).keys())
    dead = sorted(disk - mapped)
    if not dead:
        print(f"validate: OK — {len(disk)} icons, all mapped in appfilter.xml")
        return 0
    print(f"validate: {len(dead)} icons without appfilter mapping:")
    for name in dead:
        print(f"  - {name}")
    return 1


# --- CLI ----------------------------------------------------------------

def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--only", help="Comma-separated icon names to process")
    parser.add_argument("--tp-only", action="store_true", help="Fetch only third-party apps")
    parser.add_argument(
        "--era", action="append", choices=list(ERAS) + ["ios26_lg"],
        help="Limit Apple-stock fetch to specific era(s); repeatable",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print the plan; don't write files")
    parser.add_argument("--validate", action="store_true",
                        help="Report icons without appfilter entries and exit")
    parser.add_argument("--list", action="store_true",
                        help="List all known icon names and exit")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    only_names: set[str] | None = (
        {n.strip() for n in args.only.split(",") if n.strip()}
        if args.only else None
    )

    if args.validate:
        return _validate(only_names)

    if args.list:
        print("Apple stock apps:")
        for name in sorted(set(APPLE_APP_IDS) | set(APPLE_SEARCH_ONLY)):
            print(f"  {name}")
        print("\nPer-era app variants:")
        for name in sorted(ERA_APP_VARIANTS):
            print(f"  {name}")
        print("\nThird-party apps:")
        for name in sorted(THIRD_PARTY):
            print(f"  tp_{name}")
        return 0

    eras = tuple(args.era) if args.era else ERAS
    include_lg = args.era is None or "ios26_lg" in args.era

    cache = _load_cache() if not args.dry_run else None
    success = 0
    failed: list[str] = []

    if not args.tp_only:
        print("--- Apple Stock Apps ---")
        for name, app_id in APPLE_APP_IDS.items():
            if only_names and name not in only_names:
                continue
            print(f"[{name}] lookup id={app_id}")
            icon_url = _icon_by_id(app_id)
            if not icon_url:
                icon_url = _icon_by_search(SEARCH_TERMS.get(name, name))
            if not icon_url:
                failed.append(name)
                print(f"    SKIPPED")
                continue
            success += _process_era_variants(
                name, icon_url, eras, include_lg, args.dry_run, cache
            )
            time.sleep(0.3)

        for name, term in APPLE_SEARCH_ONLY.items():
            if only_names and name not in only_names:
                continue
            print(f"[{name}] search='{term}'")
            icon_url = _icon_by_search(term)
            if not icon_url:
                failed.append(name)
                print("    SKIPPED")
                continue
            success += _process_era_variants(
                name, icon_url, eras, include_lg, args.dry_run, cache
            )
            time.sleep(0.3)

        print("\n--- Per-Era App Variants ---")
        for name, term in ERA_APP_VARIANTS.items():
            if only_names and name not in only_names:
                continue
            print(f"[{name}] search='{term}'")
            icon_url = _icon_by_search(term)
            if not icon_url:
                failed.append(name)
                print("    SKIPPED")
                continue
            success += _process_era_variants(
                name, icon_url, eras, include_lg, args.dry_run, cache
            )
            time.sleep(0.3)

    print("\n--- Third-Party Apps ---")
    for name, term in THIRD_PARTY.items():
        if only_names and name not in only_names:
            continue
        print(f"[{name}] search='{term}'")
        icon_url = _icon_by_search(term)
        if not icon_url:
            failed.append(f"tp_{name}")
            print(f"    SKIPPED")
            continue
        raw = RAW_DIR / f"tp_{name}_1024.png"
        pack = PACK_DIR / f"tp_{name}.png"
        if args.dry_run:
            print(f"    [dry-run] would write {pack.relative_to(SCRIPT_DIR)}")
            success += 1
        else:
            if not raw.exists():
                _download(icon_url, raw, cache)
            if raw.exists() and _resize(raw, pack, era="tp"):
                success += 1
            else:
                failed.append(f"tp_{name}")
        time.sleep(0.3)

    if cache is not None:
        _save_cache(cache)

    print("\n" + "=" * 60)
    print(f"{'DRY-RUN: ' if args.dry_run else ''}DONE: {success} icons processed")
    if failed:
        print(f"FAILED ({len(failed)}): {', '.join(failed)}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
