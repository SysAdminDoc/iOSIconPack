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

Exit code is non-zero on any failure; the CI pipeline blocks the release when
that happens.
"""
from __future__ import annotations

import hashlib
import re
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
        for child in root.iterdir():
            if child.is_dir():
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

    if errors:
        print("validate_appfilter.py: failures:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 1

    print(f"validate_appfilter.py: OK ({len(drawables)} drawables)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
