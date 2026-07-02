#!/usr/bin/env python3
"""icontool — contributor helper for iOSIconPack.

Manages appfilter.xml, drawable.xml, and appmap.xml atomically so contributors
don't have to edit four files by hand for every new icon.

Commands
--------
  add      Add a new icon and its component mapping(s)
  link     Alias an existing drawable to additional components
  remove   Remove component mappings (optionally prune drawable.xml)
  rebuild  Sync drawable.xml with files on disk (batch-add missing entries)
  sync     Sync assets/ copies to match res/xml/ (fixes drift)
  check    Run the full XML validator (validate_appfilter.py)
  placeholder  Generate a ph_* letter-tile placeholder and optional mapping
  widget-export  Export KWGT/Kustom and Rainmeter icon catalog assets
  wallpaper-generate  Generate or check bundled original wallpaper assets
  localization-check  Verify Crowdin config and localizable Android resources
  launcher-compat-check  Verify launcher intent/resource compatibility signals
  release-check  Verify release version metadata and git tag alignment
  release-channel-check  Verify GitHub Releases latest tag/assets
  preview-regression  Diff icon renders under common launcher masks
  developer-verification-check  Report Android developer verification readiness
  request-audit  Audit open icon requests against appfilter.xml
  coverage-gap  Score high-value missing package coverage from requests and public icon packs
  maven-provenance-check  Verify Maven repository/artifact provenance
  dependency-audit  Check core dependency versions and OSV advisories
  publish-check  Verify official publish APK signing inputs and fingerprint
  preflight  Run local release validators, Gradle checks, and APK size gate

Examples
--------
  # Add a new stock icon that already has a PNG in drawable-xxxhdpi:
  python3 scripts/icontool.py add ios18_safari \\
      -c "com.android.browser/com.android.browser.BrowserActivity"

  # Add a third-party icon with multiple component aliases:
  python3 scripts/icontool.py add tp_spotify \\
      -c "com.spotify.music/com.spotify.music.MainActivity" \\
      -c "com.spotify.music/com.spotify.music.SpotifyActivity"

  # Link an existing drawable to a new launcher variant:
  python3 scripts/icontool.py link ios18_phone \\
      -c "com.nothing.dialer/com.nothing.dialer.DialtactsActivity"

  # Remove a single component mapping:
  python3 scripts/icontool.py remove \\
      -c "com.android.browser/com.android.browser.BrowserActivity"

  # Remove all mappings for a drawable and also remove it from drawable.xml:
  python3 scripts/icontool.py remove --drawable ios18_safari --prune

  # Fix assets/ drift after a manual edit to res/xml/:
  python3 scripts/icontool.py sync

  # Validate everything:
  python3 scripts/icontool.py check
"""
from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import importlib.metadata
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[1]
RES_XML = REPO_ROOT / "app/src/main/res/xml"
ASSETS = REPO_ROOT / "app/src/main/assets"
DRAWABLE_HDPI = REPO_ROOT / "app/src/main/res/drawable-xxxhdpi"
DRAWABLE_VEC = REPO_ROOT / "app/src/main/res/drawable"

APPFILTER_RES = RES_XML / "appfilter.xml"
APPFILTER_ASSET = ASSETS / "appfilter.xml"
DRAWABLE_XML_RES = RES_XML / "drawable.xml"
DRAWABLE_XML_ASSET = ASSETS / "drawable.xml"
APPMAP_XML = RES_XML / "appmap.xml"
ICON_PACK_XML = REPO_ROOT / "app/src/main/res/values/icon_pack.xml"
MYAPP_KT = REPO_ROOT / "buildSrc/src/main/java/MyApp.kt"
VERSIONS_KT = REPO_ROOT / "buildSrc/src/main/java/Versions.kt"
REQUIREMENTS_TXT = REPO_ROOT / "requirements.txt"
README_MD = REPO_ROOT / "README.md"
FDROID_METADATA = REPO_ROOT / "fdroid/metadata/com.sysadmindoc.iosicons.yml"
CHANGELOG_XML = RES_XML / "changelog.xml"
HOME_SETUP_XML = REPO_ROOT / "app/src/main/res/values/home_setup.xml"
DEV_KEYSTORE = REPO_ROOT / "iosicons.jks"
PREVIEW_REGRESSION_BASELINE = REPO_ROOT / "scripts/preview_regression_baseline.json"
PREVIEW_ICON_SIZE = 192
PREVIEW_MASKS: tuple[str, ...] = ("full-square", "circle", "rounded-square", "squircle")
PREVIEW_SCHEMA_VERSION = 1
GITHUB_REPO = "SysAdminDoc/iOSIconPack"
GITHUB_API_ROOT = "https://api.github.com"
OSV_QUERYBATCH_URL = "https://api.osv.dev/v1/querybatch"
VERSION_TAG_RE = re.compile(r"^v([0-9]+(?:\.[0-9]+){2})$")
ANDROID_NS = "{http://schemas.android.com/apk/res/android}"
LAUNCHER_APPLY_SCHEME = "iosiconpack"
LAUNCHER_APPLY_HOST = "apply"
LAUNCHER_APPLY_SLUGS: tuple[str, ...] = (
    "nova",
    "action",
    "smart",
    "oneplus",
    "lawnchair",
    "niagara",
    "projectivy",
    "adw",
    "apex",
    "samsung",
)

ANDROID_VERIFICATION_GUIDE = "https://developer.android.com/developer-verification/guides"
ANDROID_VERIFICATION_FAQ = "https://developer.android.com/developer-verification/guides/faq"
VERIFICATION_INITIAL_DATE = "2026-09-30"
VERIFICATION_GLOBAL_ROLLOUT = "2027"
VERIFICATION_INITIAL_COUNTRIES = ("Brazil", "Indonesia", "Singapore", "Thailand")
VERIFICATION_INITIAL_STORES = (
    "Google Play",
    "HONOR App Market",
    "OPPO App Market",
    "Samsung Galaxy Store",
    "Palm Store",
    "V-Appstore",
    "Xiaomi GetApps",
)

PUBLISH_SIGNING_ENV: tuple[str, ...] = (
    "IOSICONS_KEYSTORE_PATH",
    "IOSICONS_STORE_PASSWORD",
    "IOSICONS_KEY_ALIAS",
    "IOSICONS_KEY_PASSWORD",
    "IOSICONS_RELEASE_CERT_SHA256",
)

MAVEN_REPOSITORIES: tuple[dict[str, str], ...] = (
    {
        "id": "google",
        "name": "Google Maven",
        "url": "https://dl.google.com/dl/android/maven2",
        "declaration": "google()",
        "reason": "Android Gradle Plugin, AndroidX, Material, Play services, and Google Android artifacts.",
    },
    {
        "id": "mavenCentral",
        "name": "Maven Central",
        "url": "https://repo.maven.apache.org/maven2",
        "declaration": "mavenCentral()",
        "reason": "Kotlin, Gradle plugin transitives, Blueprint direct artifact, and general OSS Java/Kotlin artifacts.",
    },
    {
        "id": "jitpack",
        "name": "JitPack",
        "url": "https://jitpack.io",
        "declaration": "https://jitpack.io",
        "reason": "Blueprint 2.5.1 transitives still resolve GitHub-hosted artifacts such as TouchImageView, sectioned-recyclerview, RecyclerView-FastScroll, and AdaptiveIconBitmap.",
    },
)
MAVEN_REPOSITORY_BY_ID = {repo["id"]: repo for repo in MAVEN_REPOSITORIES}
JITPACK_HINT_PREFIXES = (
    "com.github.",
    "com.jahirfiquitiva",
)

COVERAGE_GAP_PUBLIC_SOURCES: tuple[dict[str, str], ...] = (
    {
        "name": "Arcticons",
        "url": "https://raw.githubusercontent.com/Arcticons-Team/Arcticons/HEAD/newicons/appfilter.xml",
    },
    {
        "name": "Delta Icons",
        "url": "https://raw.githubusercontent.com/Delta-Icons/android/HEAD/app/src/main/res/xml/appfilter.xml",
    },
    {
        "name": "Lawnicons",
        "url": "https://raw.githubusercontent.com/LawnchairLauncher/lawnicons/HEAD/app/assets/appfilter.xml",
    },
)

# ---------------------------------------------------------------------------
# Era / category metadata
# ---------------------------------------------------------------------------

# Order matters: ios26_lg_ must be checked before ios26_ (longer prefix first).
ERA_PREFIXES: tuple[str, ...] = (
    "ios26_lg_",
    "ios18_",
    "ios17_",
    "ios16_",
    "ios15_",
    "ios14_",
    "tp_",
)

ERA_CATEGORY: dict[str, str] = {
    "ios18_": "iOS 18",
    "ios17_": "iOS 17",
    "ios16_": "iOS 16",
    "ios15_": "iOS 15",
    "ios14_": "iOS 14",
    "ios26_lg_": "iOS 26 - Liquid Glass",
    "tp_": "Third Party",
}

# Canonical order in drawable.xml — used when creating a missing category.
CATEGORY_ORDER: list[str] = [
    "iOS 18",
    "iOS 17",
    "iOS 16",
    "iOS 15",
    "iOS 14",
    "iOS 26 - Liquid Glass",
    "Third Party",
    "Glyph",
]

# tp_ and ph_ icons live only in appfilter.xml + on disk, never in drawable.xml.
TP_PREFIX = "tp_"
PLACEHOLDER_PREFIX = "ph_"
APPFILTER_ONLY_PREFIXES = (TP_PREFIX, PLACEHOLDER_PREFIX)
GLYPH_PREFIX = "glyph_"
GLYPH_CATEGORY = "Glyph"

ERA_ARRAY_NAMES: dict[str, str] = {
    "iOS 18": "ios18",
    "iOS 17": "ios17",
    "iOS 16": "ios16",
    "iOS 15": "ios15",
    "iOS 14": "ios14",
    "iOS 26 - Liquid Glass": "ios26_liquid_glass",
    "Glyph": "glyph",
}


def _era_prefix(drawable: str) -> str:
    for prefix in ERA_PREFIXES:
        if drawable.startswith(prefix):
            return prefix
    return ""


def _category_title(drawable: str) -> str:
    if drawable.startswith(GLYPH_PREFIX):
        return GLYPH_CATEGORY
    return ERA_CATEGORY.get(_era_prefix(drawable), "")


# ---------------------------------------------------------------------------
# Generic XML helpers
# ---------------------------------------------------------------------------

def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _write_atomic(path: Path, content: str) -> None:
    """Write *content* to *path* atomically using a temp file + os.replace."""
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".icontool.tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as fh:
            fh.write(content)
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def _write(path: Path, content: str) -> None:
    _write_atomic(path, content)


def _write_pair(res: Path, asset: Path, content: str) -> None:
    """Atomically write content to both the res/xml copy and the assets/ mirror.

    Writes res first (atomic rename), then copies to asset.  If either step
    fails an exception propagates; the caller should treat any failure as a
    partial-write and advise the user to run `icontool sync` after fixing the
    underlying issue.
    """
    _write_atomic(res, content)
    shutil.copy2(res, asset)
    print(f"  wrote {res.relative_to(REPO_ROOT)}")
    print(f"  wrote {asset.relative_to(REPO_ROOT)}")


def _insert_before_close(content: str, close_tag: str, new_line: str) -> str:
    """Insert new_line on its own line immediately before close_tag."""
    idx = content.rfind(close_tag)
    if idx == -1:
        return content.rstrip("\n") + "\n" + new_line + "\n"
    before = content[:idx].rstrip("\n")
    return before + "\n" + new_line + "\n" + content[idx:]


# ---------------------------------------------------------------------------
# Component helpers
# ---------------------------------------------------------------------------

_COMPONENT_INFO_RE = re.compile(r"ComponentInfo\{([^/]+)/([^}]+)\}")


def _parse_component(raw: str) -> tuple[str, str]:
    """Return (package, activity) from any supported input form."""
    m = _COMPONENT_INFO_RE.search(raw)
    if m:
        return m.group(1).strip(), m.group(2).strip()
    if "/" in raw:
        pkg, act = raw.split("/", 1)
        return pkg.strip(), act.strip()
    raise ValueError(
        f"Cannot parse component {raw!r}. "
        "Expected 'pkg/activity' or 'ComponentInfo{pkg/activity}'."
    )


def _norm_component(raw: str) -> str:
    pkg, act = _parse_component(raw)
    return f"ComponentInfo{{{pkg}/{act}}}"


# ---------------------------------------------------------------------------
# appfilter.xml operations
# ---------------------------------------------------------------------------

def _af_item(drawable: str, component: str) -> str:
    return f'    <item component="{_norm_component(component)}" drawable="{drawable}" />'


def _af_has_component(content: str, component: str) -> bool:
    return _norm_component(component) in content


def _af_insert(content: str, drawable: str, component: str) -> str:
    """Append a new item before </resources>.

    Third-party items are appended to the dedicated THIRD-PARTY block when it
    exists.  All other items are appended just before </resources>.
    """
    new_line = _af_item(drawable, component)
    is_tp = drawable.startswith("tp_")

    if is_tp:
        # Try to append inside the THIRD-PARTY section comment block.
        marker = "<!-- ==================== THIRD-PARTY"
        idx = content.rfind(marker)
        if idx != -1:
            close_idx = content.find("</resources>", idx)
            if close_idx != -1:
                before = content[:close_idx].rstrip("\n")
                return before + "\n" + new_line + "\n" + content[close_idx:]

    return _insert_before_close(content, "</resources>", new_line)


def _af_remove_component(content: str, component: str) -> tuple[str, bool]:
    """Remove the line containing *component*.  Returns (new_content, found)."""
    norm = _norm_component(component)
    lines = content.splitlines(keepends=True)
    new_lines = [ln for ln in lines if norm not in ln]
    found = len(new_lines) < len(lines)
    return "".join(new_lines), found


def _af_components_for_drawable(content: str, drawable: str) -> list[str]:
    """Return all ComponentInfo strings that map to *drawable*."""
    pat = re.compile(
        r'<item\s+component="([^"]+)"\s+drawable="' + re.escape(drawable) + r'"'
    )
    return pat.findall(content)


def _af_component_index(content: str) -> tuple[dict[str, str], dict[str, list[tuple[str, str]]]]:
    by_component: dict[str, str] = {}
    by_package: dict[str, list[tuple[str, str]]] = {}
    item_re = re.compile(r'<item\s+component="([^"]+)"\s+drawable="([^"]+)"')
    for component, drawable in item_re.findall(content):
        by_component[component] = drawable
        try:
            package, _ = _parse_component(component)
        except ValueError:
            continue
        by_package.setdefault(package, []).append((component, drawable))
    return by_component, by_package


# ---------------------------------------------------------------------------
# drawable.xml operations
# ---------------------------------------------------------------------------

def _dw_item(drawable: str) -> str:
    return f'    <item drawable="{drawable}" />'


def _dw_has(content: str, drawable: str) -> bool:
    return f'drawable="{drawable}"' in content


def _dw_insert(content: str, drawable: str) -> str:
    """Insert *drawable* under its era category section.

    If the category doesn't exist yet it is created at the correct position
    in canonical era order (CATEGORY_ORDER), just before the next existing
    category (or before </resources> if no later category exists).
    """
    category = _category_title(drawable)
    new_item = _dw_item(drawable)

    if not category:
        return _insert_before_close(content, "</resources>", new_item)

    # Locate the category header.
    cat_pat = re.compile(r'<category title="' + re.escape(category) + r'"[^/]*/>')
    m = cat_pat.search(content)
    if not m:
        # Category missing — insert it at the correct position in era order.
        cat_line = f'    <category title="{category}" />'
        block = f"\n{cat_line}\n{new_item}"
        # Find the next category that exists after this one in CATEGORY_ORDER.
        try:
            our_idx = CATEGORY_ORDER.index(category)
        except ValueError:
            our_idx = len(CATEGORY_ORDER)
        later_cats = CATEGORY_ORDER[our_idx + 1:]
        for later in later_cats:
            later_pat = re.compile(r'<category title="' + re.escape(later) + r'"[^/]*/>')
            lm = later_pat.search(content)
            if lm:
                # Insert before the next existing category (with preceding blank line).
                before = content[:lm.start()].rstrip("\n")
                return before + block + "\n\n" + content[lm.start():]
        # No later category found — append before </resources>.
        return _insert_before_close(content, "</resources>", block)

    # Walk forward from the category header to find where this section ends.
    lines = content.splitlines(keepends=True)
    cat_lineno = content[:m.start()].count("\n")  # 0-indexed line of category header

    last_item_lineno = cat_lineno
    for i in range(cat_lineno + 1, len(lines)):
        stripped = lines[i].strip()
        if stripped.startswith("<category") or stripped == "</resources>":
            break
        if stripped.startswith("<item "):
            last_item_lineno = i

    lines.insert(last_item_lineno + 1, new_item + "\n")
    return "".join(lines)


def _dw_remove(content: str, drawable: str) -> tuple[str, bool]:
    pat = re.compile(r'[ \t]*<item drawable="' + re.escape(drawable) + r'"\s*/>\n?')
    new = pat.sub("", content)
    return new, new != content


# ---------------------------------------------------------------------------
# icon_pack.xml operations
# ---------------------------------------------------------------------------

def _drawable_categories(content: str) -> list[tuple[str, list[str]]]:
    categories: list[tuple[str, list[str]]] = []
    current: str | None = None
    items: list[str] = []
    for line in content.splitlines():
        cat = re.search(r'<category\s+title="([^"]+)"', line)
        if cat:
            if current is not None:
                categories.append((current, items))
            current = cat.group(1)
            items = []
            continue
        item = re.search(r'<item\s+drawable="([^"]+)"', line)
        if item and current is not None:
            items.append(item.group(1))
    if current is not None:
        categories.append((current, items))
    return categories


def _array_xml(name: str, values: list[str], indent: str = "    ") -> str:
    lines = [f'{indent}<string-array name="{name}">']
    lines.extend(f"{indent}    <item>{value}</item>" for value in values)
    lines.append(f"{indent}</string-array>")
    return "\n".join(lines)


def _ios18_filter(items: list[str], names: set[str]) -> list[str]:
    return [name for name in items if name.startswith("ios18_") and name.removeprefix("ios18_") in names]


def _sync_icon_pack_xml(drawable_content: str) -> None:
    categories = _drawable_categories(drawable_content)
    by_title = {title: items for title, items in categories}
    all_items = [item for _, items in categories for item in items]
    ios18 = by_title.get("iOS 18", [])

    preview_preferred = [
        "ios18_safari", "ios18_messages", "ios18_photos", "ios18_camera",
        "ios18_settings", "ios18_music", "ios18_mail", "ios18_maps",
        "ios18_clock", "ios18_weather", "ios18_notes", "ios18_phone",
    ]
    preview = [item for item in preview_preferred if item in ios18]
    if len(preview) < 12:
        preview.extend(item for item in ios18 if item not in preview)
    preview = preview[:12]

    google_names = {
        "chrome", "gmail", "google_calendar", "google_classroom", "google_docs",
        "google_drive", "google_keep", "google_maps", "google_meet", "google_one",
        "google_photos", "google_search", "google_sheets", "google_slides",
        "google_translate", "youtube",
    }
    social_names = {
        "discord", "facebook", "instagram", "pinterest", "reddit", "slack",
        "snapchat", "telegram", "tiktok", "twitter", "whatsapp",
    }
    media_names = {
        "camera", "facetime", "google_meet", "google_photos", "music", "netflix",
        "photos", "shazam", "spotify", "youtube",
    }
    productivity_names = {
        "calendar", "chrome", "files", "gmail", "google_calendar",
        "google_classroom", "google_docs", "google_drive", "google_keep",
        "google_sheets", "google_slides", "google_translate", "mail", "notes",
        "safari", "slack", "zoom",
    }

    arrays: list[tuple[str, list[str]]] = [
        ("icons_preview", preview),
        ("icon_filters", [
            "all", "ios18", "ios17", "ios16", "ios15", "ios14",
            "ios26_liquid_glass", "glyph", "system", "google", "social",
            "media", "productivity", "games",
        ]),
        ("all", all_items),
    ]
    for title in CATEGORY_ORDER:
        array_name = ERA_ARRAY_NAMES.get(title)
        if array_name:
            arrays.append((array_name, by_title.get(title, [])))
    arrays.extend([
        ("system", _ios18_filter(ios18, {
            "appstore", "calculator", "calendar", "clock", "compass", "files",
            "health", "mail", "phone", "settings", "wallet", "weather",
        })),
        ("google", _ios18_filter(ios18, google_names)),
        ("social", _ios18_filter(ios18, social_names)),
        ("media", _ios18_filter(ios18, media_names)),
        ("productivity", _ios18_filter(ios18, productivity_names)),
        ("games", []),
    ])

    body = "\n\n".join(_array_xml(name, values) for name, values in arrays)
    content = (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<resources xmlns:tools="http://schemas.android.com/tools" '
        'tools:ignore="ExtraTranslation">\n\n'
        f"{body}\n\n"
        "</resources>\n"
    )
    _write(ICON_PACK_XML, content)
    print(f"  wrote {ICON_PACK_XML.relative_to(REPO_ROOT)}")


# ---------------------------------------------------------------------------
# appmap.xml operations
# ---------------------------------------------------------------------------

def _am_item(activity: str, drawable: str) -> str:
    return f'    <item class="{activity}" name="{drawable}" />'


def _am_has(content: str, activity: str) -> bool:
    return f'class="{activity}"' in content


def _am_insert(content: str, activity: str, drawable: str) -> str:
    return _insert_before_close(content, "</appmap>", _am_item(activity, drawable))


def _am_remove(content: str, activity: str) -> tuple[str, bool]:
    lines = content.splitlines(keepends=True)
    new = [ln for ln in lines if f'class="{activity}"' not in ln]
    return "".join(new), len(new) < len(lines)


def _am_load() -> str:
    if APPMAP_XML.exists():
        return _read(APPMAP_XML)
    return '<?xml version="1.0" encoding="UTF-8"?>\n<appmap>\n</appmap>\n'


# ---------------------------------------------------------------------------
# Drawable-file existence check
# ---------------------------------------------------------------------------

def _drawable_exists(drawable: str) -> bool:
    png = DRAWABLE_HDPI / f"{drawable}.png"
    vd = DRAWABLE_VEC / f"{drawable}.xml"
    # Also check other density buckets.
    other_pngs = list((REPO_ROOT / "app/src/main/res").glob(
        f"drawable-*/{drawable}.png"
    ))
    return png.exists() or vd.exists() or bool(other_pngs)


# ---------------------------------------------------------------------------
# Release metadata check
# ---------------------------------------------------------------------------

def _required_match(label: str, path: Path, pattern: str, errors: list[str]) -> str:
    if not path.exists():
        errors.append(f"{label}: missing {path.relative_to(REPO_ROOT)}")
        return ""
    content = _read(path)
    match = re.search(pattern, content, re.MULTILINE | re.DOTALL)
    if not match:
        errors.append(f"{label}: pattern not found in {path.relative_to(REPO_ROOT)}")
        return ""
    return match.group(1).strip()


def _git_tag_exists(tag: str) -> bool:
    result = subprocess.run(
        ["git", "rev-parse", "--verify", "--quiet", f"refs/tags/{tag}"],
        cwd=REPO_ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return result.returncode == 0


def _git_text(args: list[str]) -> tuple[int, str, str]:
    result = subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    return result.returncode, result.stdout, result.stderr


def _parse_myapp_version(content: str) -> tuple[str, str]:
    version_name = re.search(r'const\s+val\s+versionName\s*=\s*"([^"]+)"', content)
    version_code = re.search(r"const\s+val\s+version\s*=\s*(\d+)", content)
    return (
        version_name.group(1).strip() if version_name else "",
        version_code.group(1).strip() if version_code else "",
    )


def _version_tuple(value: str) -> tuple[int, int, int]:
    parts = value.split(".")
    if len(parts) != 3 or not all(part.isdigit() for part in parts):
        return (9999, 9999, 9999)
    return (int(parts[0]), int(parts[1]), int(parts[2]))


def _git_version_tag_errors(expected_version: str, expected_code: str) -> list[str]:
    errors: list[str] = []
    rc, stdout, stderr = _git_text(["tag", "--list", "v[0-9]*"])
    if rc != 0:
        errors.append(f"git tag list failed: {stderr.strip()}")
        return errors

    myapp_path = MYAPP_KT.relative_to(REPO_ROOT).as_posix()
    for tag in sorted(stdout.splitlines(), key=lambda item: _version_tuple(item.strip().removeprefix("v"))):
        tag = tag.strip()
        if not tag:
            continue
        match = VERSION_TAG_RE.fullmatch(tag)
        if not match:
            errors.append(f"git tag is not a three-part app SemVer tag: {tag}")
            continue

        rc, tag_text, stderr = _git_text(["show", f"{tag}:{myapp_path}"])
        if rc != 0:
            errors.append(f"git tag {tag}: cannot read {myapp_path}: {stderr.strip()}")
            continue

        tag_version, tag_code = _parse_myapp_version(tag_text)
        if tag_version != match.group(1):
            errors.append(f"git tag {tag}: tagged app versionName is {tag_version or 'missing'}")
        if not tag_code:
            errors.append(f"git tag {tag}: tagged app versionCode is missing")
        if tag_version == expected_version and expected_code and tag_code != expected_code:
            errors.append(f"git tag {tag}: tagged app versionCode {tag_code or 'missing'} != {expected_code}")

    return errors


def _normalize_sha256(value: str | None) -> str:
    return (value or "").replace(":", "").replace(" ", "").strip().upper()


def _default_release_apk(version_name: str) -> Path:
    return (
        REPO_ROOT
        / "app/build/outputs/apk/release"
        / f"com.sysadmindoc.iosicons-{version_name}-release.apk"
    )


def _repo_relative_path(raw: str) -> Path:
    path = Path(raw)
    return path if path.is_absolute() else REPO_ROOT / path


def _display_path(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def _preview_png_paths(drawable_dir: Path = DRAWABLE_HDPI) -> list[Path]:
    return sorted(path for path in drawable_dir.glob("*.png") if path.is_file())


def _preview_pillow_modules():
    try:
        from PIL import Image, ImageChops, ImageDraw  # type: ignore
    except ImportError as exc:
        raise RuntimeError(
            "preview-regression: Pillow is required. Install dependencies with "
            "`python -m pip install -r requirements.txt`."
        ) from exc
    return Image, ImageChops, ImageDraw


def _superellipse_points(size: int, exponent: float = 4.6) -> list[tuple[float, float]]:
    center = (size - 1) / 2
    radius = center
    points: list[tuple[float, float]] = []
    for degree in range(360):
        theta = math.radians(degree)
        cos_theta = math.cos(theta)
        sin_theta = math.sin(theta)
        x = center + radius * math.copysign(abs(cos_theta) ** (2 / exponent), cos_theta)
        y = center + radius * math.copysign(abs(sin_theta) ** (2 / exponent), sin_theta)
        points.append((x, y))
    return points


def _preview_mask(mask_name: str, size: int = PREVIEW_ICON_SIZE):
    Image, _, ImageDraw = _preview_pillow_modules()
    scale = 4
    large = size * scale
    mask = Image.new("L", (large, large), 0)
    draw = ImageDraw.Draw(mask)

    if mask_name == "full-square":
        draw.rectangle((0, 0, large, large), fill=255)
    elif mask_name == "circle":
        draw.ellipse((0, 0, large - 1, large - 1), fill=255)
    elif mask_name == "rounded-square":
        draw.rounded_rectangle((0, 0, large - 1, large - 1), radius=int(large * 0.224), fill=255)
    elif mask_name == "squircle":
        draw.polygon(_superellipse_points(large), fill=255)
    else:
        raise ValueError(f"unknown preview mask: {mask_name}")

    return mask.resize((size, size), Image.Resampling.LANCZOS)


def _preview_render(image, mask_name: str):
    Image, ImageChops, _ = _preview_pillow_modules()
    icon = image.convert("RGBA")
    if icon.size != (PREVIEW_ICON_SIZE, PREVIEW_ICON_SIZE):
        icon = icon.resize((PREVIEW_ICON_SIZE, PREVIEW_ICON_SIZE), Image.Resampling.LANCZOS)
    mask = _preview_mask(mask_name, PREVIEW_ICON_SIZE)
    rendered = icon.copy()
    rendered.putalpha(ImageChops.multiply(icon.getchannel("A"), mask))
    return rendered


def _preview_pixel_hash(image) -> str:
    return hashlib.sha256(image.tobytes()).hexdigest()


def _preview_regression_manifest(drawable_dir: Path = DRAWABLE_HDPI) -> dict[str, object]:
    Image, _, _ = _preview_pillow_modules()
    entries: dict[str, dict[str, object]] = {}

    for path in _preview_png_paths(drawable_dir):
        with Image.open(path) as raw:
            icon = raw.convert("RGBA")

        if icon.size != (PREVIEW_ICON_SIZE, PREVIEW_ICON_SIZE):
            raise RuntimeError(
                f"preview-regression: {path.name} is {icon.size[0]}x{icon.size[1]}px; "
                f"expected {PREVIEW_ICON_SIZE}x{PREVIEW_ICON_SIZE}px"
            )

        alpha_bounds = icon.getchannel("A").getbbox()
        renders = {
            mask_name: _preview_pixel_hash(_preview_render(icon, mask_name))
            for mask_name in PREVIEW_MASKS
        }
        entries[path.stem] = {
            "source_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "alpha_bounds": list(alpha_bounds or ()),
            "renders": renders,
        }

    return {
        "schema": PREVIEW_SCHEMA_VERSION,
        "source": "app/src/main/res/drawable-xxxhdpi",
        "icon_size": PREVIEW_ICON_SIZE,
        "masks": list(PREVIEW_MASKS),
        "entry_count": len(entries),
        "entries": entries,
    }


def _preview_manifest_diff(
    expected: dict[str, object],
    actual: dict[str, object],
) -> dict[str, object]:
    expected_entries = expected.get("entries")
    actual_entries = actual.get("entries")
    if not isinstance(expected_entries, dict) or not isinstance(actual_entries, dict):
        return {
            "metadata": ["baseline/current manifest is missing an entries object"],
            "missing": [],
            "added": [],
            "changed": [],
        }

    metadata: list[str] = []
    for field in ("schema", "icon_size", "masks"):
        if expected.get(field) != actual.get(field):
            metadata.append(f"{field}: baseline={expected.get(field)!r} current={actual.get(field)!r}")

    expected_names = set(expected_entries)
    actual_names = set(actual_entries)
    missing = sorted(expected_names - actual_names)
    added = sorted(actual_names - expected_names)
    changed: list[dict[str, object]] = []

    for name in sorted(expected_names & actual_names):
        expected_entry = expected_entries[name]
        actual_entry = actual_entries[name]
        if not isinstance(expected_entry, dict) or not isinstance(actual_entry, dict):
            changed.append({"drawable": name, "fields": ["entry"]})
            continue

        fields: list[str] = []
        for field in ("source_sha256", "alpha_bounds"):
            if expected_entry.get(field) != actual_entry.get(field):
                fields.append(field)

        expected_renders = expected_entry.get("renders")
        actual_renders = actual_entry.get("renders")
        if not isinstance(expected_renders, dict) or not isinstance(actual_renders, dict):
            fields.append("renders")
        else:
            for mask_name in PREVIEW_MASKS:
                if expected_renders.get(mask_name) != actual_renders.get(mask_name):
                    fields.append(f"render:{mask_name}")

        if fields:
            changed.append({"drawable": name, "fields": fields})

    return {
        "metadata": metadata,
        "missing": missing,
        "added": added,
        "changed": changed,
    }


def _preview_has_diff(diff: dict[str, object]) -> bool:
    return any(diff.get(key) for key in ("metadata", "missing", "added", "changed"))


def _print_preview_diff(diff: dict[str, object], limit: int) -> None:
    metadata = diff.get("metadata") or []
    missing = diff.get("missing") or []
    added = diff.get("added") or []
    changed = diff.get("changed") or []

    if metadata:
        print("  metadata drift:")
        for item in list(metadata)[:limit]:
            print(f"    - {item}")
    if missing:
        print(f"  missing drawables ({len(missing)}):")
        for item in list(missing)[:limit]:
            print(f"    - {item}")
    if added:
        print(f"  added drawables ({len(added)}):")
        for item in list(added)[:limit]:
            print(f"    - {item}")
    if changed:
        print(f"  changed drawables ({len(changed)}):")
        for item in list(changed)[:limit]:
            if isinstance(item, dict):
                fields = ", ".join(str(field) for field in item.get("fields", []))
                print(f"    - {item.get('drawable')}: {fields}")


def _find_apksigner() -> Path | None:
    candidates: list[Path] = []
    for env_name in ("ANDROID_HOME", "ANDROID_SDK_ROOT"):
        value = os.environ.get(env_name)
        if value:
            candidates.append(Path(value))
    local_appdata = os.environ.get("LOCALAPPDATA")
    if local_appdata:
        candidates.append(Path(local_appdata) / "Android" / "Sdk")

    exe_name = "apksigner.bat" if os.name == "nt" else "apksigner"
    for sdk in candidates:
        build_tools = sdk / "build-tools"
        if not build_tools.exists():
            continue
        tools = sorted(
            (candidate / exe_name for candidate in build_tools.iterdir()),
            key=lambda item: item.parent.name,
        )
        existing = [tool for tool in tools if tool.exists()]
        if existing:
            return existing[-1]
    return None


def _apk_signer_sha256(apk: Path, errors: list[str]) -> str:
    apksigner = _find_apksigner()
    if apksigner is None:
        errors.append("Android SDK apksigner not found under ANDROID_HOME, ANDROID_SDK_ROOT, or LOCALAPPDATA")
        return ""

    result = subprocess.run(
        [str(apksigner), "verify", "--print-certs", str(apk)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        errors.append(f"apksigner failed for {_display_path(apk)}: {result.stderr.strip()}")
        return ""

    match = re.search(
        r"(?:Signer #1|V\d+ Signer):?\s+certificate SHA-256 digest:\s*([A-Fa-f0-9:]+)",
        result.stdout,
    )
    if not match:
        errors.append("apksigner output did not include a signer SHA-256 digest")
        return ""
    return _normalize_sha256(match.group(1))


def _release_metadata_errors() -> tuple[list[str], str, str]:
    errors: list[str] = []

    version_name = _required_match(
        "build versionName",
        MYAPP_KT,
        r'const\s+val\s+versionName\s*=\s*"([^"]+)"',
        errors,
    )
    version_code = _required_match(
        "build versionCode",
        MYAPP_KT,
        r"const\s+val\s+version\s*=\s*(\d+)",
        errors,
    )
    readme_version = _required_match(
        "README badge",
        README_MD,
        r"badge/version-v?([0-9]+(?:\.[0-9]+){2})-",
        errors,
    )
    fdroid_version = _required_match(
        "F-Droid CurrentVersion",
        FDROID_METADATA,
        r"^CurrentVersion:\s*'?([^'\r\n]+)'?",
        errors,
    )
    fdroid_code = _required_match(
        "F-Droid CurrentversionCode",
        FDROID_METADATA,
        r"^CurrentversionCode:\s*(\d+)",
        errors,
    )
    changelog_version = _required_match(
        "dashboard changelog",
        CHANGELOG_XML,
        r'<version\s+title="([^"]+)"',
        errors,
    )

    expected = version_name
    if expected:
        for label, actual in (
            ("README badge", readme_version),
            ("F-Droid CurrentVersion", fdroid_version),
            ("dashboard changelog", changelog_version),
        ):
            if actual and actual != expected:
                errors.append(f"{label}: {actual} != {expected}")

        if version_code and fdroid_code and version_code != fdroid_code:
            errors.append(f"F-Droid CurrentversionCode: {fdroid_code} != {version_code}")

        expected_tag = f"v{expected}"
        fdroid_text = _read(FDROID_METADATA) if FDROID_METADATA.exists() else ""
        build_re = re.compile(
            r"-\s+versionName:\s*'([^']+)'\s*"
            r"\n\s+versionCode:\s*(\d+)\s*"
            r"\n\s+commit:\s*([^\s]+)"
        )
        build_entries = build_re.findall(fdroid_text)
        matching_builds = [entry for entry in build_entries if entry[0] == expected]
        if not matching_builds:
            errors.append(f"F-Droid Builds: missing versionName {expected}")
        else:
            _, build_code, build_commit = matching_builds[-1]
            if version_code and build_code != version_code:
                errors.append(f"F-Droid build versionCode: {build_code} != {version_code}")
            if build_commit != expected_tag:
                errors.append(f"F-Droid build commit: {build_commit} != {expected_tag}")

        if not _git_tag_exists(expected_tag):
            errors.append(f"git tag missing: {expected_tag}")
        if version_code:
            errors.extend(_git_version_tag_errors(expected, version_code))
        return errors, expected, expected_tag

    return errors, "", ""


def _publish_signing_errors(apk: Path) -> list[str]:
    errors: list[str] = []

    missing = [name for name in PUBLISH_SIGNING_ENV if not os.environ.get(name, "").strip()]
    if missing:
        errors.append("missing publish signing env vars: " + ", ".join(missing))

    keystore_raw = os.environ.get("IOSICONS_KEYSTORE_PATH", "").strip()
    if keystore_raw:
        keystore = _repo_relative_path(keystore_raw)
        if not keystore.exists():
            errors.append(f"IOSICONS_KEYSTORE_PATH does not exist: {keystore}")
        elif keystore.resolve() == DEV_KEYSTORE.resolve():
            errors.append("IOSICONS_KEYSTORE_PATH cannot point at the committed dev keystore")

    expected = _normalize_sha256(os.environ.get("IOSICONS_RELEASE_CERT_SHA256"))
    if expected and not re.fullmatch(r"[A-F0-9]{64}", expected):
        errors.append("IOSICONS_RELEASE_CERT_SHA256 must be a 64-character SHA-256 hex digest")

    if not apk.exists():
        errors.append(f"release APK not found: {_display_path(apk)}")
        return errors

    if expected:
        actual = _apk_signer_sha256(apk, errors)
        if actual and actual != expected:
            errors.append(f"release APK signer SHA-256 mismatch: {actual} != {expected}")

    return errors


def _github_json(repo: str, endpoint: str, errors: list[str]) -> object | None:
    url = f"{GITHUB_API_ROOT}/repos/{repo}/{endpoint.lstrip('/')}"
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "iOSIconPack-icontool",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    request = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace").strip()
        errors.append(f"GitHub API {endpoint}: HTTP {exc.code} {exc.reason} {detail}")
    except urllib.error.URLError as exc:
        errors.append(f"GitHub API {endpoint}: {exc.reason}")
    except json.JSONDecodeError as exc:
        errors.append(f"GitHub API {endpoint}: invalid JSON: {exc}")
    return None


def _release_channel_errors(repo: str) -> tuple[list[str], str, str]:
    metadata_errors, version_name, expected_tag = _release_metadata_errors()
    errors = list(metadata_errors)
    if not version_name:
        return errors, "", ""

    latest = _github_json(repo, "releases/latest", errors)
    releases = _github_json(repo, "releases?per_page=100", errors)

    if isinstance(latest, dict):
        latest_tag = str(latest.get("tag_name") or "")
        if latest_tag != expected_tag:
            errors.append(f"GitHub latest release tag: {latest_tag or 'missing'} != {expected_tag}")

    expected_release: dict[str, object] | None = None
    current_version = _version_tuple(version_name)
    if isinstance(releases, list):
        for item in releases:
            if not isinstance(item, dict):
                continue
            tag = str(item.get("tag_name") or "")
            if tag == expected_tag:
                expected_release = item

            match = VERSION_TAG_RE.fullmatch(tag)
            if match and _version_tuple(match.group(1)) > current_version:
                errors.append(f"GitHub release {tag}: newer than checked-out app version {version_name}")

        if expected_release is None:
            errors.append(f"GitHub release missing: {expected_tag}")

    if expected_release is not None:
        assets = expected_release.get("assets")
        asset_list = assets if isinstance(assets, list) else []
        expected_asset = f"iOSIconPack-{expected_tag}-release.apk"
        matching_asset: dict[str, object] | None = None
        for item in asset_list:
            if isinstance(item, dict) and item.get("name") == expected_asset:
                matching_asset = item
                break

        if matching_asset is None:
            actual = ", ".join(
                str(item.get("name"))
                for item in asset_list
                if isinstance(item, dict) and item.get("name")
            ) or "none"
            errors.append(f"GitHub release {expected_tag}: missing asset {expected_asset} (assets: {actual})")
        else:
            size = int(matching_asset.get("size") or 0)
            if size <= 0:
                errors.append(f"GitHub release {expected_tag}: asset {expected_asset} is empty")
            digest = str(matching_asset.get("digest") or "")
            if not re.fullmatch(r"sha256:[A-Fa-f0-9]{64}", digest):
                errors.append(f"GitHub release {expected_tag}: asset {expected_asset} missing sha256 digest")

    return errors, version_name, expected_tag


def _current_app_metadata(errors: list[str]) -> dict[str, str]:
    return {
        "app_id": _required_match(
            "build appId",
            MYAPP_KT,
            r'const\s+val\s+appId\s*=\s*"([^"]+)"',
            errors,
        ),
        "version_name": _required_match(
            "build versionName",
            MYAPP_KT,
            r'const\s+val\s+versionName\s*=\s*"([^"]+)"',
            errors,
        ),
        "version_code": _required_match(
            "build versionCode",
            MYAPP_KT,
            r"const\s+val\s+version\s*=\s*(\d+)",
            errors,
        ),
        "min_sdk": _required_match(
            "minSdk",
            VERSIONS_KT,
            r"const\s+val\s+minSdk\s*=\s*(\d+)",
            errors,
        ),
        "target_sdk": _required_match(
            "targetSdk",
            VERSIONS_KT,
            r"const\s+val\s+targetSdk\s*=\s*(\d+)",
            errors,
        ),
    }


def _published_channel_summary(app_id: str) -> list[str]:
    channels: list[str] = []
    readme = _read(README_MD) if README_MD.exists() else ""
    fdroid = _read(FDROID_METADATA) if FDROID_METADATA.exists() else ""
    if "obtainium://" in readme.lower():
        channels.append("GitHub Releases via Obtainium link in README")
    if "releases/latest" in readme:
        channels.append("Manual APK install from GitHub Releases latest link")
    if FDROID_METADATA.exists() and (not app_id or app_id in FDROID_METADATA.name):
        channels.append("F-Droid metadata present under fdroid/metadata/")
    if "play.google.com" in readme.lower() or "Play Store" in fdroid:
        channels.append("Google Play listing referenced")
    if not channels:
        channels.append("No install channel detected in README or F-Droid metadata")

    return channels


def _issue_field(body: str, label: str) -> str:
    lines = (body or "").splitlines()
    start: int | None = None
    label_lower = label.lower()
    for index, line in enumerate(lines):
        if line.strip().lower() == f"### {label_lower}":
            start = index + 1
            break
    if start is None:
        return ""

    values: list[str] = []
    for line in lines[start:]:
        if line.startswith("### "):
            break
        values.append(line)
    value = re.sub(r"\n{3,}", "\n\n", "\n".join(values)).strip()
    if value.lower() in {"_no response_", "no response", "none", "n/a"}:
        return ""
    return value


def _package_from_play_url(value: str) -> str:
    match = re.search(r"[?&]id=([A-Za-z0-9._]+)", value or "")
    return match.group(1) if match else ""


def _issue_labels(issue: dict[str, object]) -> set[str]:
    labels = issue.get("labels") or []
    names: set[str] = set()
    if isinstance(labels, list):
        for label in labels:
            if isinstance(label, dict):
                name = str(label.get("name") or "")
            else:
                name = str(label)
            if name:
                names.add(name)
    return names


def _normalize_issue(issue: dict[str, object]) -> dict[str, object]:
    body = str(issue.get("body") or "")
    package_name = _issue_field(body, "Package name")
    if not package_name:
        package_name = _package_from_play_url(_issue_field(body, "Play Store URL"))

    component_raw = _issue_field(body, "ComponentInfo (optional)")
    component = ""
    if component_raw:
        try:
            component = _norm_component(component_raw)
        except ValueError:
            component = ""

    return {
        "number": int(issue.get("number") or 0),
        "title": str(issue.get("title") or ""),
        "url": str(issue.get("html_url") or ""),
        "app_name": _issue_field(body, "App name"),
        "package": package_name.strip(),
        "component": component,
        "labels": _issue_labels(issue),
    }


def _load_issues_from_file(path: Path) -> list[dict[str, object]]:
    raw = json.loads(path.read_text(encoding="utf-8-sig"))
    if isinstance(raw, dict) and isinstance(raw.get("issues"), list):
        raw = raw["issues"]
    if not isinstance(raw, list):
        raise ValueError("issue input must be a JSON list or an object with an issues list")
    return [item for item in raw if isinstance(item, dict)]


def _fetch_icon_request_issues(repo: str, errors: list[str]) -> list[dict[str, object]]:
    issues: list[dict[str, object]] = []
    page = 1
    while True:
        endpoint = f"issues?state=open&labels=icon-request&per_page=100&page={page}"
        data = _github_json(repo, endpoint, errors)
        if not isinstance(data, list):
            break
        page_issues = [
            item for item in data
            if isinstance(item, dict) and "pull_request" not in item
        ]
        issues.extend(page_issues)
        if len(data) < 100:
            break
        page += 1
    return issues


def _coverage_drawable_base(drawable: str) -> str:
    name = drawable.strip().removesuffix(".xml").removesuffix(".png").removesuffix(".webp")
    if name.startswith(GLYPH_PREFIX):
        name = name.removeprefix(GLYPH_PREFIX)
    for prefix in ERA_PREFIXES:
        if name.startswith(prefix):
            return name.removeprefix(prefix)
    if name.startswith(PLACEHOLDER_PREFIX):
        return name.removeprefix(PLACEHOLDER_PREFIX)
    return name


def _coverage_humanize(value: str) -> str:
    cleaned = re.sub(r"[_\-.]+", " ", _coverage_drawable_base(value)).strip()
    return " ".join(part.capitalize() for part in cleaned.split())


def _coverage_drawable_priority(drawable: str) -> tuple[int, str]:
    if drawable.startswith("ios18_"):
        return (0, drawable)
    if drawable.startswith(TP_PREFIX):
        return (1, drawable)
    if drawable.startswith("ios26_lg_"):
        return (2, drawable)
    if drawable.startswith("ios17_"):
        return (3, drawable)
    if drawable.startswith("ios16_"):
        return (4, drawable)
    if drawable.startswith("ios15_"):
        return (5, drawable)
    if drawable.startswith("ios14_"):
        return (6, drawable)
    if drawable.startswith(PLACEHOLDER_PREFIX):
        return (7, drawable)
    return (8, drawable)


def _coverage_existing_drawables_by_base() -> dict[str, str]:
    drawables: set[str] = set()
    for path in DRAWABLE_HDPI.glob("*.png"):
        drawables.add(path.stem)
    for path in DRAWABLE_VEC.glob("*.xml"):
        drawables.add(path.stem)

    by_base: dict[str, str] = {}
    for drawable in sorted(drawables):
        if drawable.startswith(GLYPH_PREFIX) or drawable.endswith(("_mono", "_themed")):
            continue
        base = _coverage_drawable_base(drawable)
        if not base:
            continue
        current = by_base.get(base)
        if current is None or _coverage_drawable_priority(drawable) < _coverage_drawable_priority(current):
            by_base[base] = drawable
    return by_base


def _coverage_slug(value: str) -> str:
    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", "_", value).strip("_")
    return re.sub(r"_+", "_", value)


def _coverage_candidate_keys(candidate: dict[str, object]) -> list[str]:
    keys: list[str] = []
    for drawable in sorted(candidate["drawables"]):  # type: ignore[index]
        keys.append(_coverage_drawable_base(str(drawable)))
    for title in sorted(candidate["titles"]):  # type: ignore[index]
        keys.append(_coverage_slug(str(title)))
    package_name = str(candidate["package"])
    package_parts = [part for part in package_name.split(".") if part]
    keys.extend(_coverage_slug(part) for part in reversed(package_parts[-3:]))
    return [key for key in dict.fromkeys(keys) if key]


def _coverage_parse_source_spec(spec: str) -> tuple[str, str]:
    if "=" in spec:
        name, locator = spec.split("=", 1)
        return name.strip() or locator.strip(), locator.strip()
    path = _repo_relative_path(spec)
    return path.stem or spec, spec


def _coverage_read_source(locator: str, timeout: float) -> str:
    if re.match(r"https?://", locator, re.IGNORECASE):
        request = urllib.request.Request(
            locator,
            headers={
                "Accept": "application/xml,text/xml,*/*",
                "User-Agent": "iOSIconPack-coverage-gap",
            },
        )
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.read().decode("utf-8-sig")
    return _repo_relative_path(locator).read_text(encoding="utf-8-sig")


def _coverage_parse_appfilter_source(name: str, locator: str, content: str) -> list[dict[str, object]]:
    try:
        root = ET.fromstring(content)
    except ET.ParseError as exc:
        raise ValueError(f"{name}: XML parse error: {exc}") from exc

    signals: list[dict[str, object]] = []
    for element in root.iter():
        component = (element.get("component") or "").strip()
        if not component:
            continue
        try:
            normalized = _norm_component(component)
            package_name, _ = _parse_component(normalized)
        except ValueError:
            continue

        drawable = (
            element.get("drawable")
            or element.get("name")
            or element.get("prefix")
            or ""
        ).strip()
        title = (element.get("name") or _coverage_humanize(drawable)).strip()
        if not title:
            title = package_name.split(".")[-1]
        signals.append(
            {
                "source": name,
                "kind": "public",
                "package": package_name,
                "component": normalized,
                "drawable": _coverage_drawable_base(drawable),
                "title": title,
            }
        )
    return signals


def _coverage_issue_signals(raw_issues: list[dict[str, object]], include_all: bool) -> list[dict[str, object]]:
    signals: list[dict[str, object]] = []
    for issue in raw_issues:
        if not include_all and "icon-request" not in _issue_labels(issue):
            continue
        normalized = _normalize_issue(issue)
        package_name = str(normalized.get("package") or "")
        component = str(normalized.get("component") or "")
        if component:
            try:
                package_name, _ = _parse_component(component)
            except ValueError:
                pass
        if not package_name:
            continue
        app_name = str(normalized.get("app_name") or normalized.get("title") or package_name)
        signals.append(
            {
                "source": "request",
                "kind": "request",
                "package": package_name,
                "component": component,
                "drawable": "",
                "title": app_name,
                "number": int(normalized.get("number") or 0),
                "url": str(normalized.get("url") or ""),
            }
        )
    return signals


def _coverage_local_evidence(
    package_name: str,
    components: set[str],
    by_component: dict[str, str],
    by_package: dict[str, list[tuple[str, str]]],
) -> str:
    for component in sorted(components):
        drawable = by_component.get(component)
        if drawable:
            return f"{component} -> {drawable}"
    mappings = by_package.get(package_name) or []
    if mappings:
        component, drawable = mappings[0]
        return f"{component} -> {drawable}"
    return ""


def _coverage_score(candidate: dict[str, object]) -> int:
    requests = candidate["requests"]  # type: ignore[index]
    source_counts = candidate["source_counts"]  # type: ignore[index]
    components = candidate["components"]  # type: ignore[index]
    request_count = len(requests)
    public_source_count = len(source_counts)
    public_component_count = sum(int(count) for count in source_counts.values())  # type: ignore[union-attr]
    score = request_count * 50
    score += public_source_count * 18
    score += min(public_component_count, 20) * 2
    if request_count and public_source_count:
        score += 15
    if candidate.get("existing_drawable"):
        score += 6
    if len(components) > 1:
        score += min(len(components) - 1, 10)
    return score


def _coverage_component_guess(candidate: dict[str, object]) -> str:
    components = sorted(candidate["components"])  # type: ignore[index]
    if components:
        suffix = f" (+{len(components) - 1} more)" if len(components) > 1 else ""
        return components[0] + suffix
    return "needs ComponentInfo"


def _coverage_signal_summary(candidate: dict[str, object]) -> str:
    parts: list[str] = []
    requests = sorted(int(number) for number in candidate["requests"])  # type: ignore[index]
    if requests:
        parts.append("requests " + ",".join(f"#{number}" for number in requests))
    source_counts = candidate["source_counts"]  # type: ignore[index]
    for source, count in sorted(source_counts.items()):  # type: ignore[union-attr]
        parts.append(f"{source} x{count}")
    return "; ".join(parts) or "none"


def _coverage_build_candidates(
    signals: list[dict[str, object]],
    by_component: dict[str, str],
    by_package: dict[str, list[tuple[str, str]]],
) -> tuple[list[dict[str, object]], int]:
    existing_by_base = _coverage_existing_drawables_by_base()
    candidates: dict[str, dict[str, object]] = {}

    for signal in signals:
        package_name = str(signal.get("package") or "")
        if not package_name:
            continue
        candidate = candidates.setdefault(
            package_name,
            {
                "package": package_name,
                "titles": set(),
                "components": set(),
                "drawables": set(),
                "requests": set(),
                "request_urls": [],
                "source_counts": {},
                "covered_by": "",
                "existing_drawable": "",
                "score": 0,
            },
        )
        title = str(signal.get("title") or "")
        component = str(signal.get("component") or "")
        drawable = str(signal.get("drawable") or "")
        if title:
            candidate["titles"].add(title)  # type: ignore[union-attr]
        if component:
            candidate["components"].add(component)  # type: ignore[union-attr]
        if drawable:
            candidate["drawables"].add(drawable)  # type: ignore[union-attr]

        if signal.get("kind") == "request":
            number = int(signal.get("number") or 0)
            if number:
                candidate["requests"].add(number)  # type: ignore[union-attr]
            url = str(signal.get("url") or "")
            if url:
                candidate["request_urls"].append(url)  # type: ignore[union-attr]
        else:
            source = str(signal.get("source") or "public")
            source_counts = candidate["source_counts"]  # type: ignore[index]
            source_counts[source] = int(source_counts.get(source, 0)) + 1  # type: ignore[union-attr]

    covered_count = 0
    for candidate in candidates.values():
        package_name = str(candidate["package"])
        components = candidate["components"]  # type: ignore[index]
        covered_by = _coverage_local_evidence(package_name, components, by_component, by_package)  # type: ignore[arg-type]
        candidate["covered_by"] = covered_by
        if covered_by:
            covered_count += 1

        for key in _coverage_candidate_keys(candidate):
            existing = existing_by_base.get(key)
            if existing:
                candidate["existing_drawable"] = existing
                break
        candidate["score"] = _coverage_score(candidate)

    ordered = sorted(
        candidates.values(),
        key=lambda item: (-int(item["score"]), str(item["package"])),
    )
    return ordered, covered_count


def _print_bullets(items: list[str] | tuple[str, ...], indent: str = "  - ") -> None:
    for item in items:
        print(f"{indent}{item}")


def _gradle_wrapper() -> Path:
    return REPO_ROOT / ("gradlew.bat" if os.name == "nt" else "gradlew")


def _format_bytes(size: int) -> str:
    mib = size / (1024 * 1024)
    return f"{mib:.2f} MiB ({size:,} bytes)"


def _gradle_env() -> dict[str, str]:
    env = os.environ.copy()
    if not env.get("JAVA_HOME"):
        android_studio_jbr = Path("C:/Program Files/Android/Android Studio/jbr")
        if android_studio_jbr.exists():
            env["JAVA_HOME"] = str(android_studio_jbr)
    if not env.get("ANDROID_HOME"):
        local_appdata = env.get("LOCALAPPDATA")
        if local_appdata:
            android_sdk = Path(local_appdata) / "Android" / "Sdk"
            if android_sdk.exists():
                env["ANDROID_HOME"] = str(android_sdk)
    return env


def _declared_maven_repositories() -> tuple[list[dict[str, str]], list[str]]:
    build_gradle = REPO_ROOT / "build.gradle"
    text = _read(build_gradle)
    declared: list[dict[str, str]] = []
    errors: list[str] = []

    for repo in MAVEN_REPOSITORIES:
        if repo["declaration"] in text:
            declared.append(repo)

    known_urls = {repo["url"] for repo in MAVEN_REPOSITORIES}
    known_urls.add("https://jitpack.io")
    for match in re.finditer(r"maven\s*\{\s*url\s+['\"]([^'\"]+)['\"]", text, re.DOTALL):
        url = match.group(1).rstrip("/")
        if url not in known_urls:
            errors.append(f"undocumented Maven repository in build.gradle: {url}")

    return declared, errors


def _gradle_dependency_report() -> tuple[int, str, str]:
    gradle = _gradle_wrapper()
    if not gradle.exists():
        return 1, "", f"Gradle wrapper not found: {gradle}"

    command = [
        str(gradle),
        "--console",
        "plain",
        ":app:dependencies",
        "--configuration",
        "releaseRuntimeClasspath",
        "buildEnvironment",
        "--no-daemon",
    ]
    result = subprocess.run(
        command,
        cwd=REPO_ROOT,
        env=_gradle_env(),
        capture_output=True,
        text=True,
    )
    return result.returncode, result.stdout, result.stderr


def _parse_gradle_artifacts(report: str) -> dict[tuple[str, str, str], set[str]]:
    artifacts: dict[tuple[str, str, str], set[str]] = {}
    current_scope = ""
    coord_re = re.compile(r"^([A-Za-z0-9_.\-$]+):([A-Za-z0-9_.\-$]+):([^\s()]+)")

    for raw_line in report.splitlines():
        line = raw_line.strip()
        if line.startswith("releaseRuntimeClasspath "):
            current_scope = "releaseRuntimeClasspath"
            continue
        if line == "classpath":
            current_scope = "buildscriptClasspath"
            continue
        if not current_scope or "(c)" in line:
            continue

        marker = re.search(r"(?:\+---|\\---)\s+(.+)", line)
        if not marker:
            continue
        dep_text = marker.group(1)
        dep_text = dep_text.split(" (*)", 1)[0].split(" (n)", 1)[0].strip()
        original, _, resolved = dep_text.partition(" -> ")
        original = original.strip()
        if not original:
            continue
        if resolved:
            resolved_parts = resolved.strip().split()
            if not resolved_parts:
                continue
            target = resolved_parts[0]
        else:
            original_parts = original.split()
            if not original_parts:
                continue
            target = original_parts[0]
        if target.count(":") < 2:
            target_match = coord_re.match(original)
            if not target_match:
                continue
            group, name, _ = target_match.groups()
            target = f"{group}:{name}:{target}"

        match = coord_re.match(target)
        if not match:
            continue
        version = match.group(3)
        if "{" in version or "}" in version:
            continue
        artifact = (match.group(1), match.group(2), version)
        artifacts.setdefault(artifact, set()).add(current_scope)

    return artifacts


def _maven_pom_url(repo: dict[str, str], group: str, artifact: str, version: str) -> str:
    path = "/".join(group.split("."))
    return f"{repo['url'].rstrip('/')}/{path}/{artifact}/{version}/{artifact}-{version}.pom"


def _fetch_text(url: str, timeout: float) -> tuple[str | None, str | None]:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "iOSIconPack-icontool"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            if response.status != 200:
                return None, f"HTTP {response.status}"
            return response.read().decode("utf-8", errors="replace"), None
    except urllib.error.HTTPError as exc:
        return None, f"HTTP {exc.code}"
    except urllib.error.URLError as exc:
        return None, str(exc.reason)
    except TimeoutError:
        return None, "timed out"


def _repo_probe_order(
    group: str,
    declared_repos: list[dict[str, str]],
) -> list[dict[str, str]]:
    allow_jitpack = group.startswith(JITPACK_HINT_PREFIXES)
    if group.startswith("androidx.") or group.startswith("com.android.") or group.startswith("com.google.android."):
        preferred = ("google", "mavenCentral")
    elif allow_jitpack:
        preferred = ("mavenCentral", "jitpack", "google")
    else:
        preferred = ("mavenCentral", "google")

    declared_by_id = {repo["id"]: repo for repo in declared_repos}
    ordered: list[dict[str, str]] = []
    for repo_id in preferred:
        repo = declared_by_id.get(repo_id)
        if repo is not None:
            ordered.append(repo)
    for repo in declared_repos:
        if repo["id"] == "jitpack" and not allow_jitpack:
            continue
        if repo not in ordered:
            ordered.append(repo)
    return ordered


def _pom_metadata(pom_xml: str) -> tuple[str, str]:
    try:
        root = ET.fromstring(pom_xml)
    except ET.ParseError:
        return "missing", "missing"

    def text_at(path: str) -> str:
        node = root.find(path)
        return (node.text or "").strip() if node is not None else ""

    licenses = [
        (node.text or "").strip()
        for node in root.findall(".//{*}licenses/{*}license/{*}name")
        if (node.text or "").strip()
    ]
    license_text = ", ".join(dict.fromkeys(licenses)) if licenses else "missing"
    source_url = (
        text_at(".//{*}scm/{*}url")
        or text_at(".//{*}scm/{*}connection")
        or text_at(".//{*}url")
        or "missing"
    )
    return license_text, source_url


def _resolve_maven_artifact(
    artifact: tuple[str, str, str],
    declared_repos: list[dict[str, str]],
    timeout: float,
) -> dict[str, str]:
    group, name, version = artifact
    misses: list[str] = []
    for repo in _repo_probe_order(group, declared_repos):
        url = _maven_pom_url(repo, group, name, version)
        pom, error = _fetch_text(url, timeout)
        if pom is None:
            misses.append(f"{repo['id']}:{error}")
            continue
        license_text, source_url = _pom_metadata(pom)
        return {
            "coordinate": f"{group}:{name}:{version}",
            "repository": repo["id"],
            "repository_name": repo["name"],
            "pom_url": url,
            "license": license_text,
            "source": source_url,
            "status": "OK",
        }

    return {
        "coordinate": f"{group}:{name}:{version}",
        "repository": "unresolved",
        "repository_name": "unresolved",
        "pom_url": "missing",
        "license": "missing",
        "source": "missing",
        "status": "; ".join(misses) if misses else "no declared repositories",
    }


_PRERELEASE_VERSION_RE = re.compile(
    r"(?:^|[.\-+_])(?:alpha|beta|rc|dev|preview|eap|snapshot|m\d|canary)",
    re.IGNORECASE,
)


def _is_stable_version(version: str) -> bool:
    return bool(version) and _PRERELEASE_VERSION_RE.search(version) is None


def _version_sort_key(version: str) -> tuple[int, int, int, int, str]:
    numbers = [int(value) for value in re.findall(r"\d+", version)]
    padded = (numbers + [0, 0, 0, 0])[:4]
    return (*padded, version.lower())


def _latest_stable_version(versions: list[str]) -> str:
    stable = [version for version in versions if _is_stable_version(version)]
    if not stable:
        return ""
    return sorted(stable, key=_version_sort_key)[-1]


def _maven_metadata_url(repo: dict[str, str], group: str, artifact: str) -> str:
    path = "/".join(group.split("."))
    return f"{repo['url'].rstrip('/')}/{path}/{artifact}/maven-metadata.xml"


def _maven_metadata_versions(
    group: str,
    artifact: str,
    repositories: list[str],
    timeout: float,
) -> tuple[str, str, str]:
    misses: list[str] = []
    for repo_id in repositories:
        repo = MAVEN_REPOSITORY_BY_ID.get(repo_id)
        if repo is None:
            misses.append(f"{repo_id}: unknown repository")
            continue
        url = _maven_metadata_url(repo, group, artifact)
        content, error = _fetch_text(url, timeout)
        if content is None:
            misses.append(f"{repo_id}: {error}")
            continue
        try:
            root = ET.fromstring(content)
        except ET.ParseError as exc:
            misses.append(f"{repo_id}: malformed metadata ({exc})")
            continue
        versions = [
            (node.text or "").strip()
            for node in root.findall(".//{*}version")
            if (node.text or "").strip()
        ]
        latest = _latest_stable_version(versions)
        if latest:
            return latest, f"{repo['name']} ({url})", ""
        misses.append(f"{repo_id}: no stable versions in metadata")
    return "", "", "; ".join(misses)


def _pypi_versions(package: str, timeout: float) -> tuple[str, str]:
    url = f"https://pypi.org/pypi/{package}/json"
    content, error = _fetch_text(url, timeout)
    if content is None:
        return "", error or "unavailable"
    try:
        data = json.loads(content)
    except json.JSONDecodeError as exc:
        return "", f"invalid PyPI JSON: {exc}"
    releases = data.get("releases")
    if isinstance(releases, dict):
        latest = _latest_stable_version([str(version) for version in releases])
        if latest:
            return latest, url
    info = data.get("info")
    version = str(info.get("version") or "") if isinstance(info, dict) else ""
    return (version, url) if version else ("", "PyPI JSON did not include versions")


def _requirement_spec(package: str) -> tuple[str, str]:
    if not REQUIREMENTS_TXT.exists():
        return "", ""
    pattern = re.compile(
        r"^\s*" + re.escape(package) + r"\s*([<>=!~]=?)\s*([A-Za-z0-9_.!+\-]+)",
        re.IGNORECASE,
    )
    for line in REQUIREMENTS_TXT.read_text(encoding="utf-8").splitlines():
        stripped = line.split("#", 1)[0].strip()
        if not stripped:
            continue
        match = pattern.match(stripped)
        if match:
            return stripped, match.group(2)
    return "", ""


def _installed_python_distribution(package: str) -> str:
    try:
        return importlib.metadata.version(package)
    except importlib.metadata.PackageNotFoundError:
        return ""


def _dependency_specs() -> tuple[list[dict[str, str]], list[str]]:
    errors: list[str] = []

    def version_constant(name: str) -> str:
        return _required_match(
            f"Versions.{name}",
            VERSIONS_KT,
            rf'const\s+val\s+{re.escape(name)}\s*=\s*"([^"]+)"',
            errors,
        )

    agp = version_constant("gradle")
    kotlin = version_constant("kotlin")
    ksp = version_constant("ksp")
    blueprint = version_constant("blueprint")
    pillow_requirement, pillow_minimum = _requirement_spec("Pillow")
    pillow_installed = _installed_python_distribution("Pillow")
    if not pillow_requirement:
        errors.append("requirements.txt: missing Pillow requirement")

    deps = [
        {
            "id": "agp",
            "name": "Android Gradle Plugin",
            "ecosystem": "Maven",
            "package": "com.android.tools.build:gradle",
            "current": agp,
            "advisory_version": agp,
            "scope": "buildscript",
            "repositories": "google,mavenCentral",
        },
        {
            "id": "kotlin",
            "name": "Kotlin Gradle Plugin",
            "ecosystem": "Maven",
            "package": "org.jetbrains.kotlin:kotlin-gradle-plugin",
            "current": kotlin,
            "advisory_version": kotlin,
            "scope": "buildscript",
            "repositories": "mavenCentral,google",
        },
        {
            "id": "ksp",
            "name": "KSP Gradle Plugin",
            "ecosystem": "Maven",
            "package": "com.google.devtools.ksp:com.google.devtools.ksp.gradle.plugin",
            "current": ksp,
            "advisory_version": ksp,
            "scope": "buildscript",
            "repositories": "mavenCentral,google",
        },
        {
            "id": "blueprint",
            "name": "Blueprint dashboard",
            "ecosystem": "Maven",
            "package": "dev.jahir:Blueprint",
            "current": blueprint,
            "advisory_version": blueprint,
            "scope": "releaseRuntimeClasspath",
            "repositories": "mavenCentral,jitpack",
        },
        {
            "id": "pillow",
            "name": "Pillow",
            "ecosystem": "PyPI",
            "package": "Pillow",
            "current": pillow_installed or pillow_minimum,
            "advisory_version": pillow_installed or pillow_minimum,
            "scope": "local tooling",
            "repositories": "pypi",
            "requirement": pillow_requirement,
            "installed": pillow_installed,
        },
    ]
    return deps, errors


def _dependency_latest(dep: dict[str, str], timeout: float) -> tuple[str, str, str]:
    if dep["ecosystem"] == "PyPI":
        latest, source = _pypi_versions(dep["package"], timeout)
        return latest, source, "" if latest else source
    group, artifact = dep["package"].split(":", 1)
    latest, source, error = _maven_metadata_versions(
        group,
        artifact,
        [repo.strip() for repo in dep["repositories"].split(",") if repo.strip()],
        timeout,
    )
    return latest, source, error


def _osv_vuln_ids(result: object) -> list[str]:
    if not isinstance(result, dict):
        return []
    vulns = result.get("vulns")
    if not isinstance(vulns, list):
        return []
    ids: list[str] = []
    for vuln in vulns:
        if isinstance(vuln, dict):
            vuln_id = str(vuln.get("id") or "")
            if vuln_id:
                ids.append(vuln_id)
    return ids


def _osv_query(deps: list[dict[str, str]], timeout: float) -> tuple[dict[str, list[str]], str]:
    query_deps = [dep for dep in deps if dep.get("advisory_version")]
    if not query_deps:
        return {}, "no dependency versions available for OSV query"
    payload = {
        "queries": [
            {
                "package": {
                    "ecosystem": dep["ecosystem"],
                    "name": dep["package"],
                },
                "version": dep["advisory_version"],
            }
            for dep in query_deps
        ]
    }
    request = urllib.request.Request(
        OSV_QUERYBATCH_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "User-Agent": "iOSIconPack-dependency-audit",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace").strip()
        return {}, f"OSV HTTP {exc.code}: {detail}"
    except urllib.error.URLError as exc:
        return {}, f"OSV unavailable: {exc.reason}"
    except (TimeoutError, json.JSONDecodeError) as exc:
        return {}, f"OSV query failed: {exc}"

    results = data.get("results") if isinstance(data, dict) else None
    if not isinstance(results, list):
        return {}, "OSV response did not include results"
    advisories: dict[str, list[str]] = {}
    for dep, result in zip(query_deps, results):
        advisories[dep["id"]] = _osv_vuln_ids(result)
    return advisories, ""


def _manifest_filters(errors: list[str]) -> list[tuple[set[str], set[str]]]:
    manifest = REPO_ROOT / "app/src/main/AndroidManifest.xml"
    try:
        root = ET.parse(manifest).getroot()
    except ET.ParseError as exc:
        errors.append(f"AndroidManifest.xml is malformed: {exc}")
        return []

    filters: list[tuple[set[str], set[str]]] = []
    for intent_filter in root.iter("intent-filter"):
        actions = {
            child.get(f"{ANDROID_NS}name", "")
            for child in intent_filter.findall("action")
            if child.get(f"{ANDROID_NS}name")
        }
        categories = {
            child.get(f"{ANDROID_NS}name", "")
            for child in intent_filter.findall("category")
            if child.get(f"{ANDROID_NS}name")
        }
        filters.append((actions, categories))
    return filters


def _has_intent_filter(
    filters: list[tuple[set[str], set[str]]],
    actions: set[str] | None = None,
    categories: set[str] | None = None,
) -> bool:
    required_actions = actions or set()
    required_categories = categories or set()
    return any(
        required_actions.issubset(filter_actions)
        and required_categories.issubset(filter_categories)
        for filter_actions, filter_categories in filters
    )


def _theme_resources_has_label() -> bool:
    theme_resources = RES_XML / "theme_resources.xml"
    if not theme_resources.exists():
        return False
    try:
        root = ET.parse(theme_resources).getroot()
    except ET.ParseError:
        return False
    return any((node.get("value") or "").strip() for node in root.iter("Label"))


def _launcher_core_resources_present() -> list[str]:
    missing: list[str] = []
    for path in (APPFILTER_RES, DRAWABLE_XML_RES, APPMAP_XML, ICON_PACK_XML, RES_XML / "theme_resources.xml"):
        if not path.exists():
            missing.append(_display_path(path))
    if not _theme_resources_has_label():
        missing.append("app/src/main/res/xml/theme_resources.xml Label")
    return missing


def _values_string_array(root: ET.Element, name: str) -> list[str]:
    for node in root.findall("string-array"):
        if node.get("name") == name:
            return [(item.text or "").strip() for item in node.findall("item")]
    return []


def _home_apply_card_errors() -> list[str]:
    errors: list[str] = []
    if not HOME_SETUP_XML.exists():
        return [f"missing {_display_path(HOME_SETUP_XML)}"]
    try:
        root = ET.parse(HOME_SETUP_XML).getroot()
    except ET.ParseError as exc:
        return [f"{_display_path(HOME_SETUP_XML)} is malformed: {exc}"]

    arrays = {
        name: _values_string_array(root, name)
        for name in (
            "home_list_titles",
            "home_list_descriptions",
            "home_list_icons",
            "home_list_links",
        )
    }
    lengths = {name: len(values) for name, values in arrays.items()}
    if len(set(lengths.values())) != 1:
        errors.append(f"home list arrays must have equal lengths: {lengths}")

    links = set(arrays["home_list_links"])
    for slug in LAUNCHER_APPLY_SLUGS:
        link = f"{LAUNCHER_APPLY_SCHEME}://{LAUNCHER_APPLY_HOST}/{slug}"
        if link not in links:
            errors.append(f"missing launcher apply home card link: {link}")
    return errors


def _launcher_apply_deep_link_errors() -> list[str]:
    manifest = REPO_ROOT / "app/src/main/AndroidManifest.xml"
    try:
        root = ET.parse(manifest).getroot()
    except ET.ParseError as exc:
        return [f"AndroidManifest.xml is malformed: {exc}"]

    for activity in root.iter("activity"):
        name = activity.get(f"{ANDROID_NS}name", "")
        if name not in {".LauncherApplyActivity", "com.sysadmindoc.iosicons.LauncherApplyActivity"}:
            continue
        if activity.get(f"{ANDROID_NS}exported") != "true":
            return ["LauncherApplyActivity must be exported for browsable apply links"]
        for intent_filter in activity.findall("intent-filter"):
            actions = {
                child.get(f"{ANDROID_NS}name", "")
                for child in intent_filter.findall("action")
            }
            categories = {
                child.get(f"{ANDROID_NS}name", "")
                for child in intent_filter.findall("category")
            }
            data = [
                (
                    child.get(f"{ANDROID_NS}scheme", ""),
                    child.get(f"{ANDROID_NS}host", ""),
                )
                for child in intent_filter.findall("data")
            ]
            if (
                "android.intent.action.VIEW" in actions
                and "android.intent.category.DEFAULT" in categories
                and "android.intent.category.BROWSABLE" in categories
                and (LAUNCHER_APPLY_SCHEME, LAUNCHER_APPLY_HOST) in data
            ):
                return []
        return ["LauncherApplyActivity is missing iosiconpack://apply VIEW deep-link filter"]
    return ["LauncherApplyActivity is missing from AndroidManifest.xml"]


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_add(args: argparse.Namespace) -> int:
    drawable: str = args.drawable.removesuffix(".png")
    components: list[str] = args.component

    if not _drawable_exists(drawable):
        print(
            f"error: no drawable file found for '{drawable}'.\n"
            f"  Place the PNG at:\n"
            f"    {DRAWABLE_HDPI / (drawable + '.png')}\n"
            f"  or a vector drawable at:\n"
            f"    {DRAWABLE_VEC / (drawable + '.xml')}",
            file=sys.stderr,
        )
        return 1

    af = _read(APPFILTER_RES)
    dw = _read(DRAWABLE_XML_RES)
    am = _am_load()

    added = 0
    for comp in components:
        norm = _norm_component(comp)
        if _af_has_component(af, comp):
            print(f"  skip (already in appfilter): {norm}")
            continue
        af = _af_insert(af, drawable, comp)
        _, act = _parse_component(comp)
        if not _am_has(am, act):
            am = _am_insert(am, act, drawable)
        added += 1
        print(f"  + appfilter/appmap: {norm} -> {drawable}")

    # Appfilter-only icons exist on disk and in mappings, never in drawable.xml.
    if not drawable.startswith(APPFILTER_ONLY_PREFIXES):
        if not _dw_has(dw, drawable):
            dw = _dw_insert(dw, drawable)
            cat = _category_title(drawable) or "unknown era"
            print(f"  + drawable.xml [{cat}]: {drawable}")
        else:
            print(f"  = drawable.xml: {drawable} already listed")
    else:
        print(f"  = drawable.xml: skipped appfilter-only drawable {drawable}")

    _write_pair(APPFILTER_RES, APPFILTER_ASSET, af)
    _write_pair(DRAWABLE_XML_RES, DRAWABLE_XML_ASSET, dw)
    _sync_icon_pack_xml(dw)
    _write(APPMAP_XML, am)
    print(f"  wrote {APPMAP_XML.relative_to(REPO_ROOT)}")
    print(f"\nDone — {added} component(s) added for '{drawable}'.")
    return 0


def cmd_link(args: argparse.Namespace) -> int:
    drawable: str = args.drawable.removesuffix(".png")
    components: list[str] = args.component

    af = _read(APPFILTER_RES)
    am = _am_load()

    added = 0
    for comp in components:
        norm = _norm_component(comp)
        if _af_has_component(af, comp):
            print(f"  skip (already in appfilter): {norm}")
            continue
        af = _af_insert(af, drawable, comp)
        _, act = _parse_component(comp)
        if not _am_has(am, act):
            am = _am_insert(am, act, drawable)
        added += 1
        print(f"  + {norm} -> {drawable}")

    _write_pair(APPFILTER_RES, APPFILTER_ASSET, af)
    _write(APPMAP_XML, am)
    print(f"  wrote {APPMAP_XML.relative_to(REPO_ROOT)}")
    print(f"\nDone — {added} component(s) linked to '{drawable}'.")
    return 0


def cmd_remove(args: argparse.Namespace) -> int:
    components: list[str] = args.component or []
    drawable: str | None = getattr(args, "drawable", None)
    prune: bool = args.prune

    if not components and not drawable:
        print("error: supply at least one --component or --drawable.", file=sys.stderr)
        return 1

    af = _read(APPFILTER_RES)
    dw = _read(DRAWABLE_XML_RES)
    am = _am_load()
    removed = 0

    # Collect activities being removed so we can check if they're still
    # referenced by other appfilter entries after all removals are done.
    removed_activities: set[str] = set()

    # Remove explicit components.
    for comp in components:
        norm = _norm_component(comp)
        af, found = _af_remove_component(af, comp)
        if found:
            _, act = _parse_component(comp)
            removed_activities.add(act)
            removed += 1
            print(f"  - {norm}")
        else:
            print(f"  skip (not found): {norm}")

    # Remove all components for a specific drawable.
    if drawable:
        for comp in _af_components_for_drawable(af, drawable):
            af, found = _af_remove_component(af, comp)
            if found:
                _, act = _parse_component(comp)
                removed_activities.add(act)
                removed += 1
                print(f"  - {comp}")

    # Only remove appmap entries for activities no longer referenced in appfilter.
    for act in removed_activities:
        if f'class="{act}"' not in af:
            am, _ = _am_remove(am, act)

    if drawable and prune:
        # Only remove from drawable.xml if no more appfilter entries reference it.
        remaining = _af_components_for_drawable(af, drawable)
        if remaining:
            print(
                f"  skip prune: {drawable} still has {len(remaining)} "
                "component(s) in appfilter"
            )
        else:
            dw, pruned = _dw_remove(dw, drawable)
            if pruned:
                print(f"  - drawable.xml: {drawable}")
            else:
                print(f"  skip prune: {drawable} not found in drawable.xml")

    _write_pair(APPFILTER_RES, APPFILTER_ASSET, af)
    _write_pair(DRAWABLE_XML_RES, DRAWABLE_XML_ASSET, dw)
    _write(APPMAP_XML, am)
    print(f"  wrote {APPMAP_XML.relative_to(REPO_ROOT)}")
    print(f"\nDone — {removed} component(s) removed.")
    return 0


def cmd_sync(args: argparse.Namespace) -> int:  # noqa: ARG001
    pairs = [
        (APPFILTER_RES, APPFILTER_ASSET),
        (DRAWABLE_XML_RES, DRAWABLE_XML_ASSET),
    ]
    for res, asset in pairs:
        if not res.exists():
            print(f"  missing: {res.relative_to(REPO_ROOT)}", file=sys.stderr)
            continue
        shutil.copy2(res, asset)
        print(f"  synced: {asset.relative_to(REPO_ROOT)}")
    print("\nSync complete.")
    return 0


def cmd_launcher_compat_check(args: argparse.Namespace) -> int:  # noqa: ARG001
    errors: list[str] = []
    filters = _manifest_filters(errors)
    core_missing = _launcher_core_resources_present()
    if core_missing:
        errors.extend(f"launcher core resource missing: {item}" for item in core_missing)
    errors.extend(_home_apply_card_errors())
    errors.extend(_launcher_apply_deep_link_errors())

    checks: list[tuple[str, bool, str]] = [
        (
            "ADW/generic theme",
            _has_intent_filter(
                filters,
                {"org.adw.launcher.THEMES"},
                {"android.intent.category.DEFAULT"},
            ),
            "org.adw.launcher.THEMES + DEFAULT",
        ),
        (
            "ADW icon picker",
            _has_intent_filter(
                filters,
                {"org.adw.launcher.icons.ACTION_PICK_ICON"},
                {"android.intent.category.DEFAULT"},
            ),
            "org.adw.launcher.icons.ACTION_PICK_ICON + DEFAULT",
        ),
        (
            "Nova Launcher",
            _has_intent_filter(filters, {"android.intent.action.MAIN"}, {"com.teslacoilsw.launcher.THEME"})
            and _has_intent_filter(
                filters,
                {"com.novalauncher.THEME"},
                {"com.novalauncher.category.CUSTOM_ICON_PICKER"},
            ),
            "MAIN + com.teslacoilsw.launcher.THEME and Nova custom picker",
        ),
        (
            "Lawnchair",
            _has_intent_filter(
                filters,
                {"ch.deletescape.lawnchair.ICONPACK"},
                {"ch.deletescape.lawnchair.PICK_ICON"},
            ),
            "ch.deletescape.lawnchair.ICONPACK + PICK_ICON",
        ),
        (
            "Smart Launcher",
            _has_intent_filter(
                filters,
                {
                    "ginlemon.smartlauncher.THEMES",
                    "ginlemon.smartlauncher.BUBBLESTYLE",
                    "ginlemon.smartlauncher.BUBBLEICONS",
                },
                {"android.intent.category.DEFAULT"},
            ),
            "Smart Launcher theme/bubble actions + DEFAULT",
        ),
        (
            "OnePlus Launcher",
            _has_intent_filter(
                filters,
                {"net.oneplus.launcher.icons.ACTION_PICK_ICON"},
                {"android.intent.category.DEFAULT"},
            ),
            "net.oneplus.launcher.icons.ACTION_PICK_ICON + DEFAULT",
        ),
        (
            "Samsung One UI",
            not core_missing
            and _has_intent_filter(
                filters,
                {"org.adw.launcher.THEMES"},
                {"android.intent.category.DEFAULT"},
            ),
            "generic icon-pack resources + ADW theme compatibility channel",
        ),
        (
            "Niagara Launcher",
            not core_missing
            and _has_intent_filter(
                filters,
                {"org.adw.launcher.THEMES"},
                {"android.intent.category.DEFAULT"},
            ),
            "generic ADW theme compatibility channel",
        ),
        (
            "Pixel Launcher",
            _has_intent_filter(
                filters,
                {"com.google.android.apps.nexuslauncher.ACTION_ICON_PACK"},
                {"android.intent.category.DEFAULT"},
            ),
            "com.google.android.apps.nexuslauncher.ACTION_ICON_PACK + DEFAULT",
        ),
        (
            "Holo/LauncherPro generic",
            _has_intent_filter(
                filters,
                {"android.intent.action.MAIN"},
                {"com.fede.launcher.THEME_ICONPACK"},
            ),
            "MAIN + com.fede.launcher.THEME_ICONPACK",
        ),
    ]

    print("launcher compatibility smoke matrix")
    for name, ok, evidence in checks:
        print(f"  {'OK' if ok else 'FAIL'}  {name}: {evidence}")
        if not ok:
            errors.append(f"{name}: missing {evidence}")

    if errors:
        print("launcher compatibility check: FAIL", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1

    print("launcher compatibility check: OK")
    return 0


def cmd_preview_regression(args: argparse.Namespace) -> int:
    baseline = _repo_relative_path(
        getattr(args, "baseline", None) or str(PREVIEW_REGRESSION_BASELINE)
    )
    current_output = getattr(args, "current_output", None)
    diff_limit = int(getattr(args, "diff_limit", 20) or 20)

    try:
        manifest = _preview_regression_manifest()
    except (RuntimeError, OSError, ValueError) as exc:
        print(f"preview regression check: FAIL ({exc})", file=sys.stderr)
        return 1

    if current_output:
        output_path = _repo_relative_path(current_output)
        _write(output_path, json.dumps(manifest, indent=2, sort_keys=True) + "\n")
        print(f"preview regression check: wrote current manifest {_display_path(output_path)}")

    if getattr(args, "update_baseline", False):
        _write(baseline, json.dumps(manifest, indent=2, sort_keys=True) + "\n")
        print(
            "preview regression check: updated "
            f"{_display_path(baseline)} ({manifest['entry_count']} drawables x {len(PREVIEW_MASKS)} masks)"
        )
        return 0

    if not baseline.exists():
        print(f"preview regression check: FAIL missing baseline {_display_path(baseline)}", file=sys.stderr)
        print("  run `python scripts/icontool.py preview-regression --update-baseline`", file=sys.stderr)
        return 1

    try:
        expected = json.loads(_read(baseline))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"preview regression check: FAIL cannot read baseline ({exc})", file=sys.stderr)
        return 1

    diff = _preview_manifest_diff(expected, manifest)
    if _preview_has_diff(diff):
        print("preview regression check: FAIL")
        _print_preview_diff(diff, diff_limit)
        if not current_output:
            print("  add --current-output build/preview-regression-current.json for a full current manifest")
        print("  update the baseline only after visually accepting the icon/mask changes")
        return 1

    print(f"preview regression check: OK ({manifest['entry_count']} drawables x {len(PREVIEW_MASKS)} masks)")
    return 0


def cmd_check(args: argparse.Namespace) -> int:  # noqa: ARG001
    rc = 0
    for script in ("validate_appfilter.py", "validate_drawables.py", "validate_localization.py"):
        validator = REPO_ROOT / "scripts" / script
        if not validator.exists():
            print(f"warning: validator not found: {script}", file=sys.stderr)
            continue
        result = subprocess.run([sys.executable, str(validator)])
        if result.returncode != 0:
            rc = result.returncode
    gallery = REPO_ROOT / "scripts" / "gen_gallery.py"
    if gallery.exists():
        for flag in ("--check", "--a11y-check"):
            result = subprocess.run([sys.executable, str(gallery), flag])
            if result.returncode != 0:
                rc = result.returncode
    wallpapers = REPO_ROOT / "scripts" / "gen_wallpapers.py"
    if wallpapers.exists():
        result = subprocess.run([sys.executable, str(wallpapers), "--check"])
        if result.returncode != 0:
            rc = result.returncode
    preview_rc = cmd_preview_regression(
        argparse.Namespace(
            baseline=str(PREVIEW_REGRESSION_BASELINE),
            current_output=None,
            diff_limit=20,
            update_baseline=False,
        )
    )
    if preview_rc != 0:
        rc = preview_rc
    release_rc = cmd_release_check(args)
    if release_rc != 0:
        rc = release_rc
    launcher_rc = cmd_launcher_compat_check(args)
    if launcher_rc != 0:
        rc = launcher_rc
    return rc


def cmd_localization_check(args: argparse.Namespace) -> int:  # noqa: ARG001
    validator = REPO_ROOT / "scripts" / "validate_localization.py"
    if not validator.exists():
        print("localization check: validator not found", file=sys.stderr)
        return 1
    return subprocess.run([sys.executable, str(validator)]).returncode


def cmd_release_check(args: argparse.Namespace) -> int:  # noqa: ARG001
    errors, version_name, expected_tag = _release_metadata_errors()
    if errors:
        print("release metadata check: FAIL", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1

    print(f"release metadata check: OK ({version_name}, {expected_tag})")
    return 0


def cmd_release_channel_check(args: argparse.Namespace) -> int:
    errors, version_name, expected_tag = _release_channel_errors(args.repo)
    if errors:
        print("release channel check: FAIL", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1

    print(f"release channel check: OK ({args.repo}, {version_name}, {expected_tag})")
    return 0


def cmd_developer_verification_check(args: argparse.Namespace) -> int:
    errors: list[str] = []
    metadata = _current_app_metadata(errors)
    app_id = metadata["app_id"]
    version_name = metadata["version_name"]
    version_code = metadata["version_code"]
    apk = _repo_relative_path(args.apk) if args.apk else _default_release_apk(version_name)

    signer_errors: list[str] = []
    signer_sha = _apk_signer_sha256(apk, signer_errors) if apk.exists() else ""
    if not apk.exists():
        errors.append(f"release APK not found: {_display_path(apk)}")

    expected_sha = _normalize_sha256(os.environ.get("IOSICONS_RELEASE_CERT_SHA256"))
    if expected_sha and signer_sha and signer_sha != expected_sha:
        errors.append(f"release APK signer SHA-256 mismatch: {signer_sha} != {expected_sha}")

    missing_publish_env = [name for name in PUBLISH_SIGNING_ENV if not os.environ.get(name, "").strip()]
    operator_actions: list[str] = []
    if missing_publish_env:
        operator_actions.append(
            "Official signing/verification identity is not fully local: missing "
            + ", ".join(missing_publish_env)
        )
    if not expected_sha:
        operator_actions.append("Record the production signing certificate SHA-256 in IOSICONS_RELEASE_CERT_SHA256.")

    print("Android developer verification readiness")
    print(f"  package: {app_id or 'unknown'}")
    print(f"  version: {version_name or 'unknown'} ({version_code or 'unknown'})")
    print(f"  sdk: min {metadata['min_sdk'] or 'unknown'}, target {metadata['target_sdk'] or 'unknown'}")
    print(f"  APK: {_display_path(apk)}")
    print(f"  APK signer SHA-256: {signer_sha or 'unavailable'}")
    if expected_sha:
        print("  release certificate env: present")
    else:
        print("  release certificate env: missing")

    print("\nDetected install channels")
    _print_bullets(_published_channel_summary(app_id))

    print("\nAndroid verification timeline")
    print(
        "  - Initial enforcement: "
        f"{VERIFICATION_INITIAL_DATE} in {', '.join(VERIFICATION_INITIAL_COUNTRIES)}"
    )
    print(f"  - Global rollout target: {VERIFICATION_GLOBAL_ROLLOUT} and beyond")
    print("  - ADB installs remain available for development and test devices")

    print("\nStores in the initial Android verification rollout")
    _print_bullets(VERIFICATION_INITIAL_STORES)

    print("\nNext actions")
    _print_bullets(
        [
            "Create or use an Android Developer Console account for non-Play distribution.",
            f"Register package name {app_id or '<package>'} with the APK signed by the production key.",
            "For Google Play distribution, confirm Play Console verification and app registration status.",
            "For Samsung, Xiaomi, OPPO, vivo, Honor, or Transsion distribution, complete store account verification before the regional enforcement date.",
            "For GitHub Releases, Obtainium, and F-Droid users, prepare registration before the 2027 global rollout even though GitHub/Obtainium are not in the initial listed stores.",
        ]
    )

    print("\nSources")
    _print_bullets([ANDROID_VERIFICATION_GUIDE, ANDROID_VERIFICATION_FAQ])

    if operator_actions:
        print("\nOperator actions required")
        _print_bullets(operator_actions)

    if signer_errors:
        errors.extend(signer_errors)

    if errors:
        print("\ndeveloper verification check: FAIL", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1

    if args.strict and operator_actions:
        print("\ndeveloper verification check: ACTION REQUIRED", file=sys.stderr)
        for action in operator_actions:
            print(f"  - {action}", file=sys.stderr)
        return 1

    status = "ACTION REQUIRED" if operator_actions else "OK"
    print(f"\ndeveloper verification check: {status}")
    return 0


def cmd_request_audit(args: argparse.Namespace) -> int:
    errors: list[str] = []
    if args.input:
        try:
            raw_issues = _load_issues_from_file(_repo_relative_path(args.input))
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            print(f"request audit: cannot read input: {exc}", file=sys.stderr)
            return 1
        source = args.input
    else:
        raw_issues = _fetch_icon_request_issues(args.repo, errors)
        source = f"GitHub {args.repo} open icon-request issues"

    if errors:
        print("request audit: FAIL", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1

    appfilter = _read(APPFILTER_RES)
    by_component, by_package = _af_component_index(appfilter)
    requests = [
        _normalize_issue(issue)
        for issue in raw_issues
        if "icon-request" in _issue_labels(issue) or args.input
    ]

    groups: dict[str, list[dict[str, object]]] = {}
    for request in requests:
        key = str(request.get("component") or request.get("package") or request.get("title") or request.get("number"))
        groups.setdefault(key, []).append(request)

    already_covered: list[tuple[dict[str, object], str]] = []
    needs_component: list[dict[str, object]] = []
    ready: list[dict[str, object]] = []
    malformed: list[dict[str, object]] = []

    for request in requests:
        package_name = str(request.get("package") or "")
        component = str(request.get("component") or "")
        if component and component in by_component:
            already_covered.append((request, f"{component} -> {by_component[component]}"))
        elif package_name and package_name in by_package:
            component_hit, drawable = by_package[package_name][0]
            already_covered.append((request, f"{component_hit} -> {drawable}"))
        elif component:
            ready.append(request)
        elif package_name:
            needs_component.append(request)
        else:
            malformed.append(request)

    duplicates = {
        key: values
        for key, values in groups.items()
        if key and len(values) > 1
    }

    def issue_label(issue: dict[str, object]) -> str:
        number = int(issue.get("number") or 0)
        app_name = str(issue.get("app_name") or issue.get("title") or "Unknown app")
        package_name = str(issue.get("package") or "no package")
        return f"#{number} {app_name} ({package_name})"

    print("icon request audit")
    print(f"  source: {source}")
    print(f"  requests: {len(requests)}")
    print(f"  already-covered: {len(already_covered)}")
    print(f"  duplicate groups: {len(duplicates)}")
    print(f"  needs ComponentInfo: {len(needs_component)}")
    print(f"  ready to map: {len(ready)}")
    print(f"  malformed: {len(malformed)}")

    if already_covered:
        print("\nAlready covered")
        for request, evidence in already_covered:
            print(f"  - {issue_label(request)}: {evidence}")

    if duplicates:
        print("\nDuplicate request groups")
        for key, values in sorted(duplicates.items()):
            joined = ", ".join(f"#{int(item.get('number') or 0)}" for item in values)
            print(f"  - {key}: {joined}")

    if needs_component:
        print("\nNeeds ComponentInfo")
        for request in needs_component:
            print(f"  - {issue_label(request)}")

    if ready:
        print("\nReady to map")
        for request in ready:
            print(f"  - {issue_label(request)}: {request['component']}")

    if malformed:
        print("\nMalformed request forms")
        for request in malformed:
            print(f"  - {issue_label(request)}")

    return 0


def cmd_coverage_gap(args: argparse.Namespace) -> int:
    errors: list[str] = []
    warnings: list[str] = []
    signals: list[dict[str, object]] = []

    if args.input:
        try:
            raw_issues = _load_issues_from_file(_repo_relative_path(args.input))
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            print(f"coverage gap: cannot read issue input: {exc}", file=sys.stderr)
            return 1
        issue_source = args.input
    elif args.no_requests:
        raw_issues = []
        issue_source = "disabled"
    else:
        raw_issues = _fetch_icon_request_issues(args.repo, errors)
        issue_source = f"GitHub {args.repo} open icon-request issues"

    if errors:
        print("coverage gap: FAIL", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1

    signals.extend(_coverage_issue_signals(raw_issues, include_all=bool(args.input)))

    source_specs: list[tuple[str, str]] = []
    if not args.no_public_sources:
        source_specs.extend((item["name"], item["url"]) for item in COVERAGE_GAP_PUBLIC_SOURCES)
    for spec in args.source:
        source_specs.append(_coverage_parse_source_spec(spec))

    loaded_sources: list[str] = []
    for name, locator in source_specs:
        try:
            content = _coverage_read_source(locator, args.timeout)
            parsed = _coverage_parse_appfilter_source(name, locator, content)
        except (OSError, urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ValueError) as exc:
            message = f"{name}: {exc}"
            if args.strict_sources:
                print(f"coverage gap: source failed: {message}", file=sys.stderr)
                return 1
            warnings.append(message)
            continue
        signals.extend(parsed)
        loaded_sources.append(f"{name} ({len(parsed)} signal{'s' if len(parsed) != 1 else ''})")

    appfilter = _read(APPFILTER_RES)
    by_component, by_package = _af_component_index(appfilter)
    candidates, covered_count = _coverage_build_candidates(signals, by_component, by_package)
    missing = [candidate for candidate in candidates if not candidate.get("covered_by")]
    rows = candidates if args.include_covered else missing
    rows = rows[: max(1, args.top)]

    if args.json:
        payload = {
            "issue_source": issue_source,
            "loaded_sources": loaded_sources,
            "warnings": warnings,
            "local_covered_packages": len(by_package),
            "signals": len(signals),
            "candidate_count": len(candidates),
            "covered_candidate_count": covered_count,
            "missing_candidate_count": len(missing),
            "candidates": [
                {
                    "rank": index,
                    "score": int(candidate["score"]),
                    "package": candidate["package"],
                    "app_names": sorted(candidate["titles"]),  # type: ignore[arg-type]
                    "component_guess": _coverage_component_guess(candidate),
                    "existing_drawable": candidate.get("existing_drawable") or None,
                    "covered_by": candidate.get("covered_by") or None,
                    "signals": _coverage_signal_summary(candidate),
                    "request_urls": candidate["request_urls"],
                }
                for index, candidate in enumerate(rows, start=1)
            ],
        }
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0

    print("coverage gap score")
    print(f"  issue source: {issue_source}")
    print(f"  public sources loaded: {len(loaded_sources)} of {len(source_specs)}")
    for source in loaded_sources:
        print(f"    - {source}")
    print(f"  local packages covered: {len(by_package)}")
    print(f"  raw signals: {len(signals)}")
    print(f"  candidates: {len(candidates)} total, {len(missing)} missing, {covered_count} already covered")
    if warnings:
        print("  source warnings:")
        for warning in warnings:
            print(f"    - {warning}")

    if not rows:
        print("\nNo coverage gaps found from the selected sources.")
        return 0

    heading = "Top packages" if args.include_covered else "Top missing packages"
    print(f"\n{heading}")
    for index, candidate in enumerate(rows, start=1):
        titles = sorted(candidate["titles"])  # type: ignore[arg-type]
        title = titles[0] if titles else str(candidate["package"]).split(".")[-1]
        existing = str(candidate.get("existing_drawable") or "none")
        covered = str(candidate.get("covered_by") or "")
        print(f"  {index:>2}. score {int(candidate['score']):>3}  {candidate['package']}")
        print(f"      app: {title}")
        print(f"      component: {_coverage_component_guess(candidate)}")
        print(f"      existing drawable: {existing}")
        if covered:
            print(f"      covered by: {covered}")
        print(f"      signals: {_coverage_signal_summary(candidate)}")

    return 0


def cmd_maven_provenance_check(args: argparse.Namespace) -> int:
    declared_repos, errors = _declared_maven_repositories()
    if not declared_repos:
        errors.append("no documented Maven repositories found in build.gradle")

    print("maven provenance check")
    print("  declared repositories:")
    for repo in declared_repos:
        print(f"    - {repo['name']} ({repo['url']})")
        print(f"      reason: {repo['reason']}")

    if errors:
        print("\nmaven provenance check: FAIL", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1

    rc, stdout, stderr = _gradle_dependency_report()
    if rc != 0:
        print("\nmaven provenance check: Gradle dependency report failed", file=sys.stderr)
        if stderr.strip():
            print(stderr.strip(), file=sys.stderr)
        if stdout.strip():
            print(stdout.strip(), file=sys.stderr)
        return rc

    artifacts = _parse_gradle_artifacts(stdout)
    if not artifacts:
        print("\nmaven provenance check: FAIL", file=sys.stderr)
        print("  - no artifacts parsed from Gradle dependency report", file=sys.stderr)
        return 1

    resolved: list[dict[str, str]] = []
    sorted_artifacts = sorted(artifacts)
    workers = max(1, args.jobs)
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(_resolve_maven_artifact, artifact, declared_repos, args.timeout): artifact
            for artifact in sorted_artifacts
        }
        for future in concurrent.futures.as_completed(futures):
            metadata = future.result()
            scopes = sorted(artifacts[futures[future]])
            metadata["scopes"] = ",".join(scopes)
            resolved.append(metadata)

    resolved.sort(key=lambda item: item["coordinate"])

    repo_counts: dict[str, int] = {}
    for item in resolved:
        repo_counts[item["repository"]] = repo_counts.get(item["repository"], 0) + 1

    print(f"  resolved artifacts: {len(resolved)}")
    print("  repository usage:")
    for repo_id, count in sorted(repo_counts.items()):
        print(f"    - {repo_id}: {count}")

    jitpack_used = any(item["repository"] == "jitpack" for item in resolved)
    jitpack_declared = any(repo["id"] == "jitpack" for repo in declared_repos)
    if jitpack_used:
        print("  JitPack rationale: Blueprint 2.5.1 transitives require JitPack-hosted artifacts.")

    print("\nArtifacts")
    for item in resolved:
        print(
            f"  - {item['coordinate']} [{item['scopes']}] "
            f"repo={item['repository']} license={item['license']} source={item['source']}"
        )

    missing_metadata = [
        item["coordinate"]
        for item in resolved
        if item["repository"] != "unresolved"
        and (item["license"] == "missing" or item["source"] == "missing")
    ]
    unresolved = [
        f"{item['coordinate']} ({item['status']})"
        for item in resolved
        if item["repository"] == "unresolved"
    ]

    errors = []
    if unresolved:
        errors.append(f"{len(unresolved)} artifact POM(s) could not be resolved from declared repositories")
    if jitpack_declared and not jitpack_used:
        errors.append("JitPack is declared but no resolved artifact required it; remove the repository or update the documented rationale")

    if missing_metadata:
        print("\nMetadata warnings")
        for coordinate in missing_metadata[: args.warning_limit]:
            print(f"  - {coordinate}: missing license or source URL in POM")
        if len(missing_metadata) > args.warning_limit:
            print(f"  - ... {len(missing_metadata) - args.warning_limit} more")

    if unresolved:
        print("\nUnresolved artifacts")
        for item in unresolved[: args.warning_limit]:
            print(f"  - {item}")
        if len(unresolved) > args.warning_limit:
            print(f"  - ... {len(unresolved) - args.warning_limit} more")

    if errors:
        print("\nmaven provenance check: FAIL", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1

    print("\nmaven provenance check: OK")
    return 0


def cmd_dependency_audit(args: argparse.Namespace) -> int:
    deps, errors = _dependency_specs()
    metadata_errors: list[str] = []
    records: list[dict[str, object]] = []

    for dep in deps:
        latest, source, error = _dependency_latest(dep, args.timeout)
        if error:
            metadata_errors.append(f"{dep['name']}: {error}")
        current = dep.get("current", "")
        status = "unknown"
        if latest and current:
            status = "current" if latest == current else "update available"
        records.append(
            {
                **dep,
                "latest": latest,
                "latest_source": source,
                "status": status,
                "advisories": [],
            }
        )

    advisory_error = ""
    if args.skip_osv:
        advisory_error = "OSV advisory query skipped by --skip-osv"
    else:
        advisories, advisory_error = _osv_query(deps, args.timeout)
        for record in records:
            record["advisories"] = advisories.get(str(record["id"]), [])

    vulnerable = [
        record for record in records
        if record.get("advisories")
    ]

    if args.json:
        payload = {
            "dependencies": records,
            "metadata_errors": errors + metadata_errors,
            "advisory_error": advisory_error,
            "vulnerable": [
                {
                    "id": record["id"],
                    "package": record["package"],
                    "version": record["advisory_version"],
                    "advisories": record["advisories"],
                }
                for record in vulnerable
            ],
        }
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print("dependency advisory audit")
        print(f"  metadata timeout: {args.timeout:.1f}s")
        print(f"  OSV: {'skipped' if args.skip_osv else OSV_QUERYBATCH_URL}")
        print("\nDependencies")
        for record in records:
            current = str(record.get("current") or "missing")
            latest = str(record.get("latest") or "unavailable")
            status = str(record.get("status") or "unknown")
            requirement = str(record.get("requirement") or "")
            installed = str(record.get("installed") or "")
            details = []
            if requirement:
                details.append(f"requirement {requirement}")
            if installed:
                details.append(f"installed {installed}")
            detail_text = f" ({'; '.join(details)})" if details else ""
            print(
                f"  - {record['name']}: current {current}, latest stable {latest}, "
                f"{status}{detail_text}"
            )
            print(f"    package: {record['ecosystem']} {record['package']} [{record['scope']}]")
            if record.get("latest_source"):
                print(f"    latest source: {record['latest_source']}")
            advisory_ids = record.get("advisories") or []
            if advisory_ids:
                print(f"    advisories: {', '.join(str(item) for item in advisory_ids)}")
            elif not args.skip_osv:
                print("    advisories: none")

        if errors or metadata_errors:
            print("\nMetadata errors")
            for error in errors + metadata_errors:
                print(f"  - {error}")
        if advisory_error:
            print("\nAdvisory check")
            print(f"  - {advisory_error}")
        if vulnerable:
            print("\nKnown vulnerable dependencies")
            for record in vulnerable:
                print(
                    f"  - {record['package']} {record['advisory_version']}: "
                    + ", ".join(str(item) for item in record["advisories"])
                )

    if errors or metadata_errors:
        return 1
    if advisory_error and not args.skip_osv:
        return 1
    if vulnerable:
        return 1
    if not args.json:
        print("\ndependency advisory audit: OK")
    return 0


def cmd_publish_check(args: argparse.Namespace) -> int:
    metadata_errors, version_name, expected_tag = _release_metadata_errors()
    apk = _repo_relative_path(args.apk) if args.apk else _default_release_apk(version_name)
    errors = metadata_errors + _publish_signing_errors(apk)

    if errors:
        print("publish release check: FAIL", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1

    print(f"publish release check: OK ({version_name}, {expected_tag}, {_display_path(apk)})")
    return 0


def cmd_preflight(args: argparse.Namespace) -> int:
    print("preflight: repository validators")
    check_rc = cmd_check(args)
    if check_rc != 0:
        return check_rc

    gradle = _gradle_wrapper()
    if not gradle.exists():
        print(f"preflight: Gradle wrapper missing: {_display_path(gradle)}", file=sys.stderr)
        return 1

    tasks = args.gradle_task or ["test", "lintRelease", "assembleRelease"]
    command = [str(gradle), *tasks, "--no-daemon"]
    print("\npreflight: " + " ".join([gradle.name, *tasks, "--no-daemon"]))
    result = subprocess.run(command, cwd=REPO_ROOT, env=_gradle_env())
    if result.returncode != 0:
        return result.returncode

    metadata_errors, version_name, _ = _release_metadata_errors()
    if metadata_errors:
        print("preflight: release metadata changed during build", file=sys.stderr)
        for error in metadata_errors:
            print(f"  - {error}", file=sys.stderr)
        return 1

    apk = _repo_relative_path(args.apk) if args.apk else _default_release_apk(version_name)
    if not apk.exists():
        print(f"preflight: release APK not found: {_display_path(apk)}", file=sys.stderr)
        return 1

    size = apk.stat().st_size
    limit = int(args.max_apk_mb * 1024 * 1024)
    print(f"\npreflight: release APK size {_format_bytes(size)}")
    print(f"preflight: size budget {args.max_apk_mb:.2f} MiB")
    if size > limit:
        print(f"preflight: FAIL size budget exceeded by {_format_bytes(size - limit)}", file=sys.stderr)
        return 1

    print("preflight: OK")
    return 0


def cmd_rebuild(args: argparse.Namespace) -> int:
    """Sync drawable.xml with files on disk.

    Scans drawable-xxxhdpi/ for PNG files and drawable/ for vector XMLs,
    then adds any that are missing from drawable.xml to the correct era
    category section.  tp_* and ph_* icons are always excluded (they live only in
    appfilter.xml by design).

    With --prune, also removes drawable.xml entries whose file no longer
    exists on disk.
    """
    prune: bool = args.prune
    dry_run: bool = getattr(args, "dry_run", False)

    dw = _read(DRAWABLE_XML_RES)

    # Drawables currently listed in drawable.xml
    in_xml: set[str] = set(re.findall(r'<item\s+drawable="([^"]+)"', dw))

    # Drawables that exist on disk (PNGs + vector drawables, non-appfilter-only, non-launcher)
    on_disk: set[str] = set()
    for f in DRAWABLE_HDPI.glob("*.png"):
        name = f.stem
        if not name.startswith(APPFILTER_ONLY_PREFIXES) and _era_prefix(name):
            on_disk.add(name)
    for f in DRAWABLE_VEC.glob("*.xml"):
        name = f.stem
        skip_prefixes = ("ic_launcher", "ic_", TP_PREFIX, PLACEHOLDER_PREFIX, "background", "foreground")
        skip_suffixes = ("_mono", "_themed")
        if (
            not any(name.startswith(p) for p in skip_prefixes)
            and not name.endswith(skip_suffixes)
            and (_era_prefix(name) or name.startswith(GLYPH_PREFIX))
        ):
            on_disk.add(name)

    missing: list[str] = sorted(on_disk - in_xml)
    stale: list[str] = sorted(in_xml - on_disk) if prune else []

    if not missing and not stale:
        print("drawable.xml is already in sync with disk — nothing to do.")
        if not dry_run:
            _sync_icon_pack_xml(dw)
        return 0

    if missing:
        print(f"Adding {len(missing)} missing drawable(s):")
    for drawable in missing:
        cat = _category_title(drawable) or "unknown era"
        if dry_run:
            print(f"  + [{cat}] {drawable}")
        else:
            if not _dw_has(dw, drawable):
                dw = _dw_insert(dw, drawable)
                print(f"  + [{cat}] {drawable}")

    if stale:
        print(f"\nRemoving {len(stale)} stale entry(ies):")
    for drawable in stale:
        if dry_run:
            print(f"  - [stale] {drawable}")
        else:
            dw, _ = _dw_remove(dw, drawable)
            print(f"  - [removed] {drawable}")

    if dry_run:
        counts = f"{len(missing)} to add"
        if prune:
            counts += f", {len(stale)} to remove"
        print(f"\nDry-run complete: {counts}. No files written.")
        return 0

    _write_pair(DRAWABLE_XML_RES, DRAWABLE_XML_ASSET, dw)
    _sync_icon_pack_xml(dw)
    print(f"\nDone — {len(missing)} added, {len(stale)} removed.")
    return 0


def cmd_placeholder(args: argparse.Namespace) -> int:
    """Generate a deterministic ph_* placeholder and optional component mapping."""
    command = [
        sys.executable,
        str(REPO_ROOT / "scripts" / "gen_placeholders.py"),
        "--drawable",
        args.drawable,
        "--label",
        args.label,
    ]
    for component in args.component:
        command.extend(["--component", component])
    if args.color:
        command.extend(["--color", args.color])
    if args.output:
        command.extend(["--output", args.output])
    if args.force:
        command.append("--force")
    if args.dry_run:
        command.append("--dry-run")
    return subprocess.run(command, cwd=REPO_ROOT).returncode


def cmd_widget_export(args: argparse.Namespace) -> int:
    """Export widget-ready catalog assets for Kustom/KWGT and Rainmeter."""
    command = [
        sys.executable,
        str(REPO_ROOT / "scripts" / "export_widget_catalog.py"),
        "--output",
        args.output,
        "--format",
        args.format,
        "--rainmeter-preview-count",
        str(args.rainmeter_preview_count),
    ]
    if args.include_placeholders:
        command.append("--include-placeholders")
    if args.check:
        command.append("--check")
    return subprocess.run(command, cwd=REPO_ROOT).returncode


def cmd_wallpaper_generate(args: argparse.Namespace) -> int:
    """Generate or validate bundled wallpaper assets."""
    command = [sys.executable, str(REPO_ROOT / "scripts" / "gen_wallpapers.py")]
    if args.force:
        command.append("--force")
    if args.check:
        command.append("--check")
    return subprocess.run(command, cwd=REPO_ROOT).returncode


def cmd_stats(args: argparse.Namespace) -> int:  # noqa: ARG001
    """Print icon pack statistics: counts by era, top apps by mapping count."""
    # ── per-era PNG counts from disk ──────────────────────────────────────────
    era_counts: dict[str, int] = {}
    for f in sorted(DRAWABLE_HDPI.glob("*.png")):
        prefix = _era_prefix(f.stem)
        if prefix:
            era_counts[prefix] = era_counts.get(prefix, 0) + 1

    # ── component counts per drawable (from appfilter.xml) ───────────────────
    af = _read(APPFILTER_RES)
    mapping_counts: dict[str, int] = {}
    for m in re.finditer(r'drawable="([^"]+)"', af):
        name = m.group(1)
        mapping_counts[name] = mapping_counts.get(name, 0) + 1

    total_pngs     = sum(era_counts.values())
    total_mappings = sum(mapping_counts.values())

    # ── era name lookup ───────────────────────────────────────────────────────
    prefix_to_name: dict[str, str] = {
        "ios14_":    "iOS 14",
        "ios15_":    "iOS 15",
        "ios16_":    "iOS 16",
        "ios17_":    "iOS 17",
        "ios18_":    "iOS 18",
        "ios26_lg_": "iOS 26 Liquid Glass",
        "tp_":       "Third Party",
    }

    print("=" * 42)
    print("iOS Icon Pack — Stats")
    print("=" * 42)
    print(f"{'Era':<24} {'Icons':>6}  {'Mappings':>8}")
    print("-" * 42)

    for prefix in ERA_PREFIXES:
        name        = prefix_to_name.get(prefix, prefix.rstrip("_"))
        icon_count  = era_counts.get(prefix, 0)
        map_count   = sum(v for k, v in mapping_counts.items() if k.startswith(prefix))
        print(f"  {name:<22} {icon_count:>6}  {map_count:>8}")

    print("-" * 42)
    print(f"  {'TOTAL':<22} {total_pngs:>6}  {total_mappings:>8}")
    print()

    # ── top N drawables by mapping count ─────────────────────────────────────
    top_n: int = getattr(args, "top", 10)
    top = sorted(mapping_counts.items(), key=lambda x: x[1], reverse=True)[:top_n]
    print(f"Top {top_n} drawables by appfilter mapping count:")
    for i, (name, count) in enumerate(top, 1):
        print(f"  {i:>2}. {name:<32} {count:>3} mapping{'s' if count != 1 else ''}")

    return 0

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="icontool",
        description=__doc__.splitlines()[1].strip(),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="\n".join(__doc__.splitlines()[3:]),
    )
    sub = p.add_subparsers(dest="command", metavar="COMMAND", required=True)

    # --- add ---
    add_p = sub.add_parser(
        "add",
        help="Add a new icon (asset must already exist in drawable-xxxhdpi or drawable/)",
    )
    add_p.add_argument(
        "drawable",
        help="Drawable name without extension, e.g. ios18_safari or tp_spotify",
    )
    add_p.add_argument(
        "--component", "-c",
        action="append",
        required=True,
        metavar="PKG/ACTIVITY",
        help="ComponentInfo to map (repeatable). Accept 'pkg/act' or full ComponentInfo{} form.",
    )
    add_p.set_defaults(func=cmd_add)

    # --- link ---
    link_p = sub.add_parser(
        "link",
        help="Alias an existing drawable to additional component(s) without touching drawable.xml",
    )
    link_p.add_argument("drawable", help="Existing drawable name")
    link_p.add_argument(
        "--component", "-c",
        action="append",
        required=True,
        metavar="PKG/ACTIVITY",
        help="Additional ComponentInfo(s) to map (repeatable).",
    )
    link_p.set_defaults(func=cmd_link)

    # --- remove ---
    rm_p = sub.add_parser(
        "remove",
        help="Remove component mappings from appfilter.xml (and optionally drawable.xml)",
    )
    rm_p.add_argument(
        "--component", "-c",
        action="append",
        metavar="PKG/ACTIVITY",
        help="ComponentInfo to remove (repeatable).",
    )
    rm_p.add_argument(
        "--drawable", "-d",
        default=None,
        help="Remove ALL appfilter entries for this drawable name.",
    )
    rm_p.add_argument(
        "--prune",
        action="store_true",
        help="Also remove the drawable from drawable.xml (requires --drawable; "
             "skipped if other components still reference it).",
    )
    rm_p.set_defaults(func=cmd_remove)

    # --- rebuild ---
    rb_p = sub.add_parser(
        "rebuild",
        help="Sync drawable.xml with files on disk (add missing entries, optionally prune stale ones)",
    )
    rb_p.add_argument(
        "--prune",
        action="store_true",
        help="Also remove drawable.xml entries whose PNG/vector no longer exists on disk.",
    )
    rb_p.add_argument(
        "--dry-run", "-n",
        action="store_true",
        help="Preview changes without writing any files.",
    )
    rb_p.set_defaults(func=cmd_rebuild)

    # --- sync ---
    sync_p = sub.add_parser(
        "sync",
        help="Copy res/xml/ appfilter.xml and drawable.xml to assets/ (fixes drift)",
    )
    sync_p.set_defaults(func=cmd_sync)

    # --- check ---
    check_p = sub.add_parser(
        "check",
        help="Run drawable, appfilter, and release metadata validators",
    )
    check_p.set_defaults(func=cmd_check)

    # --- placeholder ---
    placeholder_p = sub.add_parser(
        "placeholder",
        help="Generate a deterministic ph_* letter-tile placeholder and optional mapping",
    )
    placeholder_p.add_argument(
        "--drawable",
        required=True,
        help="Drawable name; ph_ is added when omitted.",
    )
    placeholder_p.add_argument(
        "--label",
        required=True,
        help="App label used for placeholder initials and color.",
    )
    placeholder_p.add_argument(
        "--component", "-c",
        action="append",
        default=[],
        metavar="PKG/ACTIVITY",
        help="ComponentInfo to map through icontool add (repeatable).",
    )
    placeholder_p.add_argument(
        "--color",
        default=None,
        help="Optional #RRGGBB background base color.",
    )
    placeholder_p.add_argument(
        "--output",
        default=None,
        help="Write a preview PNG to this path instead of the app catalog.",
    )
    placeholder_p.add_argument(
        "--force",
        action="store_true",
        help="Overwrite an existing placeholder PNG.",
    )
    placeholder_p.add_argument(
        "--dry-run", "-n",
        action="store_true",
        help="Print planned output without writing files.",
    )
    placeholder_p.set_defaults(func=cmd_placeholder)

    # --- widget-export ---
    widget_export_p = sub.add_parser(
        "widget-export",
        help="Export KWGT/Kustom and Rainmeter-ready icon catalog assets",
    )
    widget_export_p.add_argument(
        "--output",
        default="build/widget-catalog/iOSIconPack-widget-catalog.zip",
        help="Output zip path (default: build/widget-catalog/iOSIconPack-widget-catalog.zip).",
    )
    widget_export_p.add_argument(
        "--format",
        choices=("all", "kwgt", "rainmeter"),
        default="all",
        help="Export layout to include (default: all).",
    )
    widget_export_p.add_argument(
        "--include-placeholders",
        action="store_true",
        help="Include ph_* placeholder PNGs when present.",
    )
    widget_export_p.add_argument(
        "--rainmeter-preview-count",
        type=int,
        default=32,
        help="Number of icons in the Rainmeter sample grid (default: 32).",
    )
    widget_export_p.add_argument(
        "--check",
        action="store_true",
        help="Validate an existing export zip instead of generating one.",
    )
    widget_export_p.set_defaults(func=cmd_widget_export)

    # --- wallpaper-generate ---
    wallpaper_p = sub.add_parser(
        "wallpaper-generate",
        help="Generate or check bundled original wallpaper assets",
    )
    wallpaper_p.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing generated wallpaper assets.",
    )
    wallpaper_p.add_argument(
        "--check",
        action="store_true",
        help="Validate generated wallpaper assets and JSON.",
    )
    wallpaper_p.set_defaults(func=cmd_wallpaper_generate)

    # --- localization-check ---
    localization_p = sub.add_parser(
        "localization-check",
        help="Verify Crowdin config and localizable Android resources",
    )
    localization_p.set_defaults(func=cmd_localization_check)

    # --- launcher-compat-check ---
    launcher_p = sub.add_parser(
        "launcher-compat-check",
        help="Verify launcher intent filters and core icon-pack XML resources",
    )
    launcher_p.set_defaults(func=cmd_launcher_compat_check)

    # --- release-check ---
    release_p = sub.add_parser(
        "release-check",
        help="Verify versionName, README, F-Droid metadata, changelog, and git tag alignment",
    )
    release_p.set_defaults(func=cmd_release_check)

    # --- release-channel-check ---
    release_channel_p = sub.add_parser(
        "release-channel-check",
        help="Verify GitHub Releases latest tag, expected APK asset, and release tag drift",
    )
    release_channel_p.add_argument(
        "--repo",
        default=GITHUB_REPO,
        help=f"GitHub owner/repo to inspect (default: {GITHUB_REPO})",
    )
    release_channel_p.set_defaults(func=cmd_release_channel_check)

    # --- preview-regression ---
    preview_p = sub.add_parser(
        "preview-regression",
        help="Diff rendered icon previews under common launcher masks against a local baseline",
    )
    preview_p.add_argument(
        "--baseline",
        default=str(PREVIEW_REGRESSION_BASELINE.relative_to(REPO_ROOT)),
        help="Baseline JSON path (default: scripts/preview_regression_baseline.json)",
    )
    preview_p.add_argument(
        "--current-output",
        default=None,
        help="Optional path to write the current rendered-hash manifest.",
    )
    preview_p.add_argument(
        "--diff-limit",
        type=int,
        default=20,
        help="Maximum rows to print per diff section (default: 20).",
    )
    preview_p.add_argument(
        "--update-baseline",
        action="store_true",
        help="Overwrite the baseline with the current accepted renders.",
    )
    preview_p.set_defaults(func=cmd_preview_regression)

    # --- developer-verification-check ---
    developer_verification_p = sub.add_parser(
        "developer-verification-check",
        help="Report Android developer verification readiness for sideload/store distribution",
    )
    developer_verification_p.add_argument(
        "--apk",
        default=None,
        help="Release APK to inspect (default: app/build/outputs/apk/release/<applicationId>-<version>-release.apk)",
    )
    developer_verification_p.add_argument(
        "--strict",
        action="store_true",
        help="Exit non-zero when operator verification/signing actions are still required",
    )
    developer_verification_p.set_defaults(func=cmd_developer_verification_check)

    # --- request-audit ---
    request_audit_p = sub.add_parser(
        "request-audit",
        help="Audit icon-request issues against appfilter coverage without mutating GitHub",
    )
    request_audit_p.add_argument(
        "--repo",
        default=GITHUB_REPO,
        help=f"GitHub owner/repo to fetch when --input is omitted (default: {GITHUB_REPO})",
    )
    request_audit_p.add_argument(
        "--input",
        default=None,
        help="Read saved GitHub issue JSON from this file instead of fetching live issues",
    )
    request_audit_p.set_defaults(func=cmd_request_audit)

    # --- coverage-gap ---
    coverage_gap_p = sub.add_parser(
        "coverage-gap",
        help="Score high-value missing package coverage from requests and public icon packs",
    )
    coverage_gap_p.add_argument(
        "--repo",
        default=GITHUB_REPO,
        help=f"GitHub owner/repo to fetch requests from when --input is omitted (default: {GITHUB_REPO})",
    )
    coverage_gap_p.add_argument(
        "--input",
        default=None,
        help="Read saved GitHub issue JSON from this file instead of fetching live request issues",
    )
    coverage_gap_p.add_argument(
        "--source",
        action="append",
        default=[],
        metavar="NAME=URL_OR_PATH",
        help="Add a public package source to score; accepts icon-pack appfilter XML (repeatable).",
    )
    coverage_gap_p.add_argument(
        "--no-public-sources",
        action="store_true",
        help="Skip the built-in Arcticons, Delta Icons, and Lawnicons appfilter sources.",
    )
    coverage_gap_p.add_argument(
        "--no-requests",
        action="store_true",
        help="Skip live GitHub request issues when --input is omitted.",
    )
    coverage_gap_p.add_argument(
        "--include-covered",
        action="store_true",
        help="Include packages that are already covered locally.",
    )
    coverage_gap_p.add_argument(
        "--strict-sources",
        action="store_true",
        help="Fail instead of warning when a public package source cannot be read.",
    )
    coverage_gap_p.add_argument(
        "--timeout",
        type=float,
        default=15.0,
        help="Seconds to wait for each remote package source (default: 15).",
    )
    coverage_gap_p.add_argument(
        "--top",
        type=int,
        default=25,
        help="Number of ranked packages to print (default: 25).",
    )
    coverage_gap_p.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON instead of text.",
    )
    coverage_gap_p.set_defaults(func=cmd_coverage_gap)

    # --- maven-provenance-check ---
    maven_provenance_p = sub.add_parser(
        "maven-provenance-check",
        help="List resolved Gradle artifacts with Maven repository, license, and source provenance",
    )
    maven_provenance_p.add_argument(
        "--timeout",
        type=float,
        default=4.0,
        help="Seconds to wait for each POM request (default: 4)",
    )
    maven_provenance_p.add_argument(
        "--jobs",
        type=int,
        default=16,
        help="Parallel POM fetch workers (default: 16)",
    )
    maven_provenance_p.add_argument(
        "--warning-limit",
        type=int,
        default=25,
        help="Maximum missing-metadata/unresolved rows to print per section (default: 25)",
    )
    maven_provenance_p.set_defaults(func=cmd_maven_provenance_check)

    # --- dependency-audit ---
    dependency_audit_p = sub.add_parser(
        "dependency-audit",
        help="Check core dependency versions and OSV advisories before release",
    )
    dependency_audit_p.add_argument(
        "--timeout",
        type=float,
        default=15.0,
        help="Seconds to wait for Maven, PyPI, and OSV requests (default: 15)",
    )
    dependency_audit_p.add_argument(
        "--skip-osv",
        action="store_true",
        help="Skip OSV advisory lookup; useful for offline version-only diagnostics.",
    )
    dependency_audit_p.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON instead of text.",
    )
    dependency_audit_p.set_defaults(func=cmd_dependency_audit)

    # --- publish-check ---
    publish_p = sub.add_parser(
        "publish-check",
        help="Verify official signing env vars and APK signer fingerprint for a publish release",
    )
    publish_p.add_argument(
        "--apk",
        default=None,
        help="Release APK to verify (default: app/build/outputs/apk/release/<applicationId>-<version>-release.apk)",
    )
    publish_p.set_defaults(func=cmd_publish_check)

    # --- preflight ---
    preflight_p = sub.add_parser(
        "preflight",
        help="Run local validators, Gradle test/lint/release packaging, and APK size gate",
    )
    preflight_p.add_argument(
        "--apk",
        default=None,
        help="Release APK to inspect after Gradle tasks complete (default: app/build/outputs/apk/release/<applicationId>-<version>-release.apk)",
    )
    preflight_p.add_argument(
        "--max-apk-mb",
        type=float,
        default=13.0,
        help="Maximum release APK size in MiB (default: 13.0)",
    )
    preflight_p.add_argument(
        "--gradle-task",
        action="append",
        default=None,
        help="Gradle task to run before size check (repeatable; default: test, lintRelease, assembleRelease)",
    )
    preflight_p.set_defaults(func=cmd_preflight)

    # --- stats ---
    stats_p = sub.add_parser(
        "stats",
        help="Print icon and mapping counts by era, and top drawables by mapping count",
    )
    stats_p.add_argument(
        "--top", "-t",
        type=int,
        default=10,
        metavar="N",
        help="Number of top drawables to show (default: 10)",
    )
    stats_p.set_defaults(func=cmd_stats)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
