#!/usr/bin/env python3
"""Export PNG icon assets for Kustom/KWGT and Rainmeter widget workflows."""
from __future__ import annotations

import argparse
import csv
import json
import re
import shutil
import sys
import tempfile
import zipfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree as ET


REPO_ROOT = Path(__file__).resolve().parents[1]
DRAWABLE_XML = REPO_ROOT / "app/src/main/res/xml/drawable.xml"
APPFILTER_XML = REPO_ROOT / "app/src/main/res/xml/appfilter.xml"
PNG_DIR = REPO_ROOT / "app/src/main/res/drawable-xxxhdpi"
VERSION_FILE = REPO_ROOT / "buildSrc/src/main/java/MyApp.kt"
DEFAULT_OUTPUT = REPO_ROOT / "build/widget-catalog/iOSIconPack-widget-catalog.zip"

ERA_PREFIXES = {
    "ios18_": ("iOS 18", "iOS 18"),
    "ios17_": ("iOS 17", "iOS 17"),
    "ios16_": ("iOS 16", "iOS 16"),
    "ios15_": ("iOS 15", "iOS 15"),
    "ios14_": ("iOS 14", "iOS 14"),
    "ios26_lg_": ("iOS 26 Liquid Glass", "iOS 26"),
    "tp_": ("Third Party", "Third Party"),
    "ph_": ("Placeholder", "Placeholder"),
}

LABEL_OVERRIDES = {
    "appstore": "App Store",
    "facetime": "FaceTime",
    "github": "GitHub",
    "gmail": "Gmail",
    "google": "Google",
    "google_calendar": "Google Calendar",
    "google_classroom": "Google Classroom",
    "google_docs": "Google Docs",
    "google_drive": "Google Drive",
    "google_keep": "Google Keep",
    "google_maps": "Google Maps",
    "google_meet": "Google Meet",
    "google_one": "Google One",
    "google_photos": "Google Photos",
    "google_search": "Google Search",
    "google_sheets": "Google Sheets",
    "google_slides": "Google Slides",
    "google_translate": "Google Translate",
    "paypal": "PayPal",
    "youtube": "YouTube",
}


@dataclass(frozen=True)
class IconRecord:
    drawable: str
    label: str
    category: str
    era: str
    file: str
    components: list[str]
    packages: list[str]


def _read_version() -> str:
    match = re.search(r'const\s+val\s+versionName\s*=\s*"([^"]+)"', VERSION_FILE.read_text(encoding="utf-8"))
    return match.group(1) if match else "0.0.0"


def _prefix_info(drawable: str) -> tuple[str, str, str]:
    for prefix, (category, era) in ERA_PREFIXES.items():
        if drawable.startswith(prefix):
            return prefix, category, era
    return "", "Uncategorized", "Uncategorized"


def _label_from_drawable(drawable: str) -> str:
    prefix, _, _ = _prefix_info(drawable)
    slug = drawable.removeprefix(prefix) if prefix else drawable
    if slug in LABEL_OVERRIDES:
        return LABEL_OVERRIDES[slug]
    return " ".join(part.capitalize() for part in slug.split("_") if part)


def _drawable_categories() -> dict[str, str]:
    root = ET.parse(DRAWABLE_XML).getroot()
    categories: dict[str, str] = {}
    current = "Uncategorized"
    for child in root:
        if child.tag == "category":
            current = child.attrib.get("title", current)
        elif child.tag == "item" and "drawable" in child.attrib:
            categories[child.attrib["drawable"]] = current
    return categories


def _appfilter_components() -> dict[str, list[str]]:
    root = ET.parse(APPFILTER_XML).getroot()
    by_drawable: dict[str, list[str]] = {}
    for item in root.findall("item"):
        drawable = item.attrib.get("drawable")
        component = item.attrib.get("component")
        if drawable and component:
            by_drawable.setdefault(drawable, []).append(component)
    return {drawable: sorted(set(components)) for drawable, components in by_drawable.items()}


def _component_package(component: str) -> str | None:
    match = re.match(r"ComponentInfo\{([^/]+)/", component)
    if match:
        return match.group(1)
    if "/" in component:
        return component.split("/", 1)[0]
    return None


def collect_icons(include_placeholders: bool = False) -> list[IconRecord]:
    categories = _drawable_categories()
    components = _appfilter_components()
    names = {path.stem for path in PNG_DIR.glob("*.png")}
    names.update(name for name in components if (PNG_DIR / f"{name}.png").exists())

    records: list[IconRecord] = []
    for drawable in sorted(names):
        if drawable.startswith("ph_") and not include_placeholders:
            continue
        source = PNG_DIR / f"{drawable}.png"
        if not source.exists():
            continue
        _, default_category, era = _prefix_info(drawable)
        icon_components = components.get(drawable, [])
        packages = sorted({pkg for pkg in (_component_package(c) for c in icon_components) if pkg})
        records.append(
            IconRecord(
                drawable=drawable,
                label=_label_from_drawable(drawable),
                category=categories.get(drawable, default_category),
                era=era,
                file=f"images/{drawable}.png",
                components=icon_components,
                packages=packages,
            )
        )
    return records


def _copy_images(icons: list[IconRecord], destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    for icon in icons:
        shutil.copy2(PNG_DIR / f"{icon.drawable}.png", destination / f"{icon.drawable}.png")


def _write_catalog_files(icons: list[IconRecord], destination: Path, version: str) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema": 1,
        "project": "iOS Icon Pack",
        "package": "com.sysadmindoc.iosicons",
        "version": version,
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "icon_count": len(icons),
        "icons": [asdict(icon) for icon in icons],
    }
    (destination / "catalog.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    with (destination / "catalog.csv").open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["drawable", "label", "category", "era", "file", "packages", "components"])
        for icon in icons:
            writer.writerow(
                [
                    icon.drawable,
                    icon.label,
                    icon.category,
                    icon.era,
                    icon.file,
                    ";".join(icon.packages),
                    ";".join(icon.components),
                ]
            )


def _write_kustom_export(root: Path, icons: list[IconRecord], version: str) -> None:
    kustom = root / "kustom" / "iOSIconPack"
    _copy_images(icons, kustom / "images")
    _write_catalog_files(icons, kustom, version)
    (kustom / "README.txt").write_text(
        "\n".join(
            [
                "iOS Icon Pack - Kustom/KWGT image assets",
                "",
                "Copy the images folder to /Kustom/images/iOSIconPack on the device.",
                "Use catalog.json or catalog.csv to map drawable names to labels and packages.",
                "In KWGT/KLWP, use an Image module bitmap formula that points at the copied PNG path.",
                "",
            ]
        ),
        encoding="utf-8",
    )


def _rainmeter_variable_name(drawable: str) -> str:
    return re.sub(r"[^A-Za-z0-9_]", "_", drawable)


def _write_rainmeter_export(root: Path, icons: list[IconRecord], version: str, preview_count: int) -> None:
    skin = root / "rainmeter" / "iOSIconPack"
    resources = skin / "@Resources"
    _copy_images(icons, resources / "Images")
    _write_catalog_files(icons, resources, version)

    lines = [
        "[Variables]",
        "IconRoot=#@#Images\\",
        f"IconCount={len(icons)}",
    ]
    for icon in icons:
        lines.append(f"{_rainmeter_variable_name(icon.drawable)}=#@#Images\\{icon.drawable}.png")
    (resources / "Variables.inc").write_text("\n".join(lines) + "\n", encoding="utf-8")

    preview_icons = icons[: max(1, min(preview_count, len(icons)))]
    skin_lines = [
        "[Rainmeter]",
        "Update=-1",
        "AccurateText=1",
        "",
        "[Metadata]",
        "Name=iOS Icon Pack Catalog",
        "Author=SysAdminDoc",
        "Information=Preview grid for exported iOS Icon Pack PNG assets.",
        f"Version={version}",
        "",
        "[Variables]",
        "@include=#@#Variables.inc",
        "IconSize=48",
        "Gap=10",
        "",
        "[MeterTitle]",
        "Meter=String",
        "Text=iOS Icon Pack",
        "FontFace=Segoe UI",
        "FontSize=14",
        "FontColor=255,255,255,255",
        "AntiAlias=1",
        "X=0",
        "Y=0",
        "",
    ]
    for index, icon in enumerate(preview_icons):
        column = index % 8
        row = index // 8
        x = column * 58
        y = 34 + row * 58
        skin_lines.extend(
            [
                f"[MeterIcon{index + 1}]",
                "Meter=Image",
                f"ImageName=#{_rainmeter_variable_name(icon.drawable)}#",
                "W=#IconSize#",
                "H=#IconSize#",
                f"X={x}",
                f"Y={y}",
                "",
            ]
        )
    (skin / "Catalog.ini").write_text("\n".join(skin_lines), encoding="utf-8")


def _write_zip(source_root: Path, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        output.unlink()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(p for p in source_root.rglob("*") if p.is_file()):
            archive.write(path, path.relative_to(source_root.parent).as_posix())


def _check_zip(path: Path, export_format: str = "all") -> int:
    required_suffixes = {
        "catalog.json",
        "catalog.csv",
    }
    if export_format in ("all", "kwgt"):
        required_suffixes.add("kustom/iOSIconPack/README.txt")
    if export_format in ("all", "rainmeter"):
        required_suffixes.add("rainmeter/iOSIconPack/Catalog.ini")
        required_suffixes.add("rainmeter/iOSIconPack/@Resources/Variables.inc")
    with zipfile.ZipFile(path) as archive:
        names = set(archive.namelist())
        missing = [suffix for suffix in sorted(required_suffixes) if not any(name.endswith(suffix) for name in names)]
        png_count = sum(1 for name in names if name.endswith(".png"))
    if missing:
        print("widget export check failed: missing " + ", ".join(missing), file=sys.stderr)
        return 1
    if png_count == 0:
        print("widget export check failed: no PNG images found", file=sys.stderr)
        return 1
    print(f"widget export check: OK ({png_count} PNG entries)")
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT),
        help=f"Output zip path (default: {DEFAULT_OUTPUT.relative_to(REPO_ROOT)})",
    )
    parser.add_argument(
        "--format",
        choices=("all", "kwgt", "rainmeter"),
        default="all",
        help="Export layout to include (default: all)",
    )
    parser.add_argument(
        "--include-placeholders",
        action="store_true",
        help="Include ph_* placeholder PNGs when present.",
    )
    parser.add_argument(
        "--rainmeter-preview-count",
        type=int,
        default=32,
        help="Number of icons in the Rainmeter sample grid (default: 32).",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Validate an existing export zip instead of generating one.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    output = Path(args.output)
    if not output.is_absolute():
        output = REPO_ROOT / output

    if args.check:
        return _check_zip(output, args.format)

    icons = collect_icons(include_placeholders=args.include_placeholders)
    if not icons:
        print("export_widget_catalog.py: no PNG icons found to export", file=sys.stderr)
        return 1

    version = _read_version()
    with tempfile.TemporaryDirectory(prefix="iosiconpack-widget-") as tmp:
        root = Path(tmp) / "iOSIconPack-widget-catalog"
        root.mkdir(parents=True)
        _write_catalog_files(icons, root, version)
        if args.format in ("all", "kwgt"):
            _write_kustom_export(root, icons, version)
        if args.format in ("all", "rainmeter"):
            _write_rainmeter_export(root, icons, version, args.rainmeter_preview_count)
        _write_zip(root, output)

    print(f"widget export: wrote {output}")
    print(f"widget export: {len(icons)} PNG icons, format={args.format}, version={version}")
    return _check_zip(output, args.format)


if __name__ == "__main__":
    sys.exit(main())
