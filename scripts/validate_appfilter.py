#!/usr/bin/env python3
"""Validate the icon pack's appfilter / drawable XML stack.

Checks enforced:
  1. `app/src/main/res/xml/appfilter.xml` and `app/src/main/assets/appfilter.xml`
     are byte-identical (Blueprint reads both; drift is a frequent regression).
  2. `app/src/main/res/xml/drawable.xml` and `app/src/main/assets/drawable.xml`
     are byte-identical.
  3. Every `<item drawable="..."/>` referenced from appfilter.xml resolves to an
     actual drawable on disk (checks both `res/drawable-*/` PNG + `res/drawable/`
     vector sets, matching `ios{ver}_{app}` and `tp_{app}` naming).
  4. No duplicate `<item component="..."/>` entries in appfilter.xml.
  5. First-party Google components with dedicated era art do not regress to
     generic Apple analogues or `tp_*` icons.

Exit code is non-zero on any failure; run this locally before release.
"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path
from xml.etree import ElementTree as ET

REPO_ROOT = Path(__file__).resolve().parents[1]
RES_XML = REPO_ROOT / "app/src/main/res/xml"
ASSETS = REPO_ROOT / "app/src/main/assets"
RES_DRAWABLE_ROOTS = [
    REPO_ROOT / "app/src/main/res/drawable",
    REPO_ROOT / "app/src/main/res/drawable-xxxhdpi",
    REPO_ROOT / "app/src/main/res/drawable-xxhdpi",
    REPO_ROOT / "app/src/main/res/drawable-xhdpi",
    REPO_ROOT / "app/src/main/res/drawable-hdpi",
    REPO_ROOT / "app/src/main/res/drawable-mdpi",
    REPO_ROOT / "app/src/main/res/drawable-nodpi",
]
ERA_PREFIXES = (
    "ios26_lg_",
    "ios18_",
    "ios17_",
    "ios16_",
    "ios15_",
    "ios14_",
)
GOOGLE_APPFILTER_DEFAULTS = {
    "ComponentInfo{com.android.chrome/com.google.android.apps.chrome.Main}": "chrome",
    "ComponentInfo{com.chrome.beta/com.google.android.apps.chrome.Main}": "chrome",
    "ComponentInfo{com.chrome.dev/com.google.android.apps.chrome.Main}": "chrome",
    "ComponentInfo{com.chrome.canary/com.google.android.apps.chrome.Main}": "chrome",
    "ComponentInfo{com.google.android.apps.photos/com.google.android.apps.photos.home.HomeActivity}": "google_photos",
    "ComponentInfo{com.google.android.apps.photosgo/com.google.android.apps.photos.home.HomeActivity}": "google_photos",
    "ComponentInfo{com.google.android.gm/com.google.android.gm.ConversationListActivityGmail}": "gmail",
    "ComponentInfo{com.google.android.gm/com.google.android.gm.GmailActivity}": "gmail",
    "ComponentInfo{com.google.android.apps.maps/com.google.android.maps.MapsActivity}": "google_maps",
    "ComponentInfo{com.google.android.apps.maps/com.google.android.apps.gmm.map.MapDisplayActivity}": "google_maps",
    "ComponentInfo{com.google.android.keep/com.google.android.keep.activities.BrowseActivity}": "google_keep",
    "ComponentInfo{com.google.android.calendar/com.android.calendar.AllInOneActivity}": "google_calendar",
    "ComponentInfo{com.google.android.apps.tachyon/com.google.android.apps.tachyon.MainActivity}": "google_meet",
    "ComponentInfo{com.google.android.apps.tachyon/com.google.android.apps.tachyon.ui.main.MainActivity}": "google_meet",
    "ComponentInfo{com.google.android.apps.meetings/com.google.android.apps.meetings.launch.MeetLaunchActivity}": "google_meet",
    "ComponentInfo{com.google.android.apps.meetings/com.google.android.apps.meetings.MainActivity}": "google_meet",
    "ComponentInfo{com.google.android.youtube/com.google.android.youtube.HomeActivity}": "youtube",
    "ComponentInfo{com.google.android.youtube/com.google.android.apps.youtube.app.WatchWhileActivity}": "youtube",
    "ComponentInfo{com.google.android.youtube/com.google.android.apps.youtube.app.honeycomb.Shell$HomeActivity}": "youtube",
    "ComponentInfo{com.google.android.apps.youtube.kids/com.google.android.apps.youtube.kids.browse.BrowseActivity}": "youtube",
    "ComponentInfo{com.google.android.youtube.tv/com.google.android.youtube.tv.MainActivity}": "youtube",
    "ComponentInfo{com.google.android.youtube.tvkids/com.google.android.youtube.tvkids.MainActivity}": "youtube",
    "ComponentInfo{com.google.android.apps.youtube.creator/com.google.android.apps.youtube.creator.MainActivity}": "youtube",
    "ComponentInfo{com.google.android.apps.youtube.unplugged/com.google.android.apps.youtube.unplugged.app.MainActivity}": "youtube",
    "ComponentInfo{com.google.android.apps.youtube.gaming/com.google.android.apps.youtube.gaming.MainActivity}": "youtube",
    "ComponentInfo{com.google.android.apps.docs/com.google.android.apps.docs.drive.startup.StartupActivity}": "google_drive",
    "ComponentInfo{com.google.android.apps.docs/com.google.android.apps.docs.app.NewMainProxyActivity}": "google_drive",
    "ComponentInfo{com.google.android.apps.docs.editors.docs/com.google.android.apps.docs.editors.kix.KixEditorActivity}": "google_docs",
    "ComponentInfo{com.google.android.apps.docs.editors.sheets/com.google.android.apps.docs.editors.sheets.SheetsEditorActivity}": "google_sheets",
    "ComponentInfo{com.google.android.apps.docs.editors.slides/com.google.android.apps.docs.editors.slides.SlidesEditorActivity}": "google_slides",
    "ComponentInfo{com.google.android.apps.translate/com.google.android.apps.translate.TranslateActivity}": "google_translate",
    "ComponentInfo{com.google.android.googlequicksearchbox/com.google.android.googlequicksearchbox.SearchActivity}": "google_search",
    "ComponentInfo{com.google.android.apps.googleassistant/com.google.android.apps.googleassistant.AssistantActivity}": "google_search",
    "ComponentInfo{com.google.android.apps.classroom/com.google.android.apps.classroom.ListCourseActivity}": "google_classroom",
    "ComponentInfo{com.google.android.apps.classroom/com.google.android.apps.classroom.ClassListActivity}": "google_classroom",
    "ComponentInfo{com.google.android.apps.subscriptions.red/com.google.android.apps.subscriptions.red.LaunchActivity}": "google_one",
}
GOOGLE_APPMAP_DEFAULTS = {
    "com.google.android.apps.chrome.Main": "chrome",
    "com.google.android.apps.photos.home.HomeActivity": "google_photos",
    "com.google.android.gm.ConversationListActivityGmail": "gmail",
    "com.google.android.gm.GmailActivity": "gmail",
    "com.google.android.maps.MapsActivity": "google_maps",
    "com.google.android.apps.gmm.map.MapDisplayActivity": "google_maps",
    "com.google.android.keep.activities.BrowseActivity": "google_keep",
    "com.android.calendar.AllInOneActivity": "google_calendar",
    "com.google.android.apps.tachyon.MainActivity": "google_meet",
    "com.google.android.apps.tachyon.ui.main.MainActivity": "google_meet",
    "com.google.android.apps.meetings.MainActivity": "google_meet",
    "com.google.android.apps.docs.app.NewMainProxyActivity": "google_drive",
    "com.google.android.apps.youtube.app.WatchWhileActivity": "youtube",
    "com.google.android.apps.youtube.app.honeycomb.Shell$HomeActivity": "youtube",
}


def _drawable_suffix(drawable: str) -> str:
    for prefix in ERA_PREFIXES:
        if drawable.startswith(prefix):
            return drawable[len(prefix):]
    if drawable.startswith("tp_"):
        return drawable[len("tp_"):]
    return drawable


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _check_pair(res: Path, asset: Path, errors: list[str]) -> None:
    if not res.exists():
        errors.append(f"missing: {res}")
        return
    if not asset.exists():
        errors.append(f"missing: {asset}")
        return
    if _digest(res) != _digest(asset):
        errors.append(
            f"drift: {res.relative_to(REPO_ROOT)} != {asset.relative_to(REPO_ROOT)}"
        )


def _collect_drawables() -> set[str]:
    drawables: set[str] = set()
    # Ignore ripple/selector/launcher helpers so valid pack content is still surfaced.
    skip_prefixes = ("ic_launcher", "ic_muzei", "abc_", "notification_", "tooltip_")
    for root in RES_DRAWABLE_ROOTS:
        if not root.exists():
            continue
        # Recurse so vector drawables organised into ios14/, ios15/, ... subfolders
        # are still counted when a future refactor reshapes res/drawable layout.
        for child in root.rglob("*"):
            if child.is_dir():
                continue
            if child.suffix.lower() not in {".png", ".xml", ".webp", ".jpg", ".jpeg"}:
                continue
            stem = child.stem
            if stem.startswith(skip_prefixes):
                continue
            drawables.add(stem)
    return drawables


def _validate_appfilter(path: Path, drawables: set[str], errors: list[str]) -> None:
    try:
        tree = ET.parse(path)
    except ET.ParseError as exc:
        errors.append(f"{path.relative_to(REPO_ROOT)}: xml parse error: {exc}")
        return
    components: dict[str, str] = {}
    for item in tree.getroot().findall("item"):
        drawable = item.get("drawable")
        component = item.get("component")
        if not drawable or not component:
            continue
        if drawable not in drawables:
            errors.append(
                f"{path.relative_to(REPO_ROOT)}: missing drawable '{drawable}' "
                f"for component {component}"
            )
        if component in components and components[component] != drawable:
            errors.append(
                f"{path.relative_to(REPO_ROOT)}: duplicate component {component} "
                f"maps to both '{components[component]}' and '{drawable}'"
            )
        components[component] = drawable
    for component, expected_suffix in GOOGLE_APPFILTER_DEFAULTS.items():
        drawable = components.get(component)
        if not drawable:
            errors.append(
                f"{path.relative_to(REPO_ROOT)}: missing Google default mapping "
                f"for {component}"
            )
            continue
        if _drawable_suffix(drawable) != expected_suffix:
            errors.append(
                f"{path.relative_to(REPO_ROOT)}: {component} maps to '{drawable}', "
                f"expected era-specific '*_{expected_suffix}'"
            )


def _validate_appmap(path: Path, errors: list[str]) -> None:
    try:
        tree = ET.parse(path)
    except ET.ParseError as exc:
        errors.append(f"{path.relative_to(REPO_ROOT)}: xml parse error: {exc}")
        return
    mappings: dict[str, str] = {}
    for item in tree.getroot().findall("item"):
        class_name = item.get("class")
        drawable = item.get("name")
        if not class_name or not drawable:
            continue
        mappings[class_name] = drawable
    for class_name, expected_suffix in GOOGLE_APPMAP_DEFAULTS.items():
        drawable = mappings.get(class_name)
        if not drawable:
            errors.append(
                f"{path.relative_to(REPO_ROOT)}: missing Google appmap mapping "
                f"for {class_name}"
            )
            continue
        if _drawable_suffix(drawable) != expected_suffix:
            errors.append(
                f"{path.relative_to(REPO_ROOT)}: {class_name} maps to '{drawable}', "
                f"expected era-specific '*_{expected_suffix}'"
            )


def _validate_drawable_xml(path: Path, drawables: set[str], errors: list[str]) -> None:
    try:
        tree = ET.parse(path)
    except ET.ParseError as exc:
        errors.append(f"{path.relative_to(REPO_ROOT)}: xml parse error: {exc}")
        return
    seen: set[str] = set()
    for item in tree.getroot().findall("item"):
        drawable = item.get("drawable")
        if not drawable:
            continue
        if drawable in seen:
            errors.append(
                f"{path.relative_to(REPO_ROOT)}: duplicate drawable entry '{drawable}'"
            )
        seen.add(drawable)
        if drawable not in drawables:
            errors.append(
                f"{path.relative_to(REPO_ROOT)}: missing drawable '{drawable}' "
                "(listed in dashboard but not shipped)"
            )


def main() -> int:
    errors: list[str] = []

    _check_pair(RES_XML / "appfilter.xml", ASSETS / "appfilter.xml", errors)
    _check_pair(RES_XML / "drawable.xml", ASSETS / "drawable.xml", errors)

    drawables = _collect_drawables()
    if not drawables:
        errors.append("no drawables discovered — repo layout changed?")

    for label in ("appfilter.xml",):
        xml_path = RES_XML / label
        if xml_path.exists():
            _validate_appfilter(xml_path, drawables, errors)
    for label in ("drawable.xml",):
        xml_path = RES_XML / label
        if xml_path.exists():
            _validate_drawable_xml(xml_path, drawables, errors)
    appmap = RES_XML / "appmap.xml"
    if appmap.exists():
        _validate_appmap(appmap, errors)

    if errors:
        print("validate_appfilter.py: failures:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 1

    print(f"validate_appfilter.py: OK ({len(drawables)} drawables)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
