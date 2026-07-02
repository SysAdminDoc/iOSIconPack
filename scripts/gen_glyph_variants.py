#!/usr/bin/env python3
"""Generate transparent glyph-only catalog variants from monochrome vectors."""
from __future__ import annotations

import argparse
import html
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DRAWABLE_DIR = REPO_ROOT / "app" / "src" / "main" / "res" / "drawable"

ANDROID_URI = "http://schemas.android.com/apk/res/android"
ANDROID_NS = f"{{{ANDROID_URI}}}"

SOURCE_PREFIXES = (
    "ios26_lg_",
    "ios18_",
    "ios17_",
    "ios16_",
    "ios15_",
    "ios14_",
    "tp_",
)

BORDER_PATH = (
    "M96,8 C132,8 151,8 168,24 "
    "C184,41 184,60 184,96 "
    "C184,132 184,151 168,168 "
    "C151,184 132,184 96,184 "
    "C60,184 41,184 24,168 "
    "C8,151 8,132 8,96 "
    "C8,60 8,41 24,24 "
    "C41,8 60,8 96,8 Z"
)


def _android_attr(name: str) -> str:
    return f"{ANDROID_NS}{name}"


def _tag_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _source_mono_files() -> list[Path]:
    files: list[Path] = []
    for path in sorted(DRAWABLE_DIR.glob("*_mono.xml")):
        base = path.stem.removesuffix("_mono")
        if base.startswith(SOURCE_PREFIXES):
            files.append(path)
    return files


def _format_attr_name(name: str) -> str:
    if name.startswith(ANDROID_NS):
        return f"android:{name.removeprefix(ANDROID_NS)}"
    return name


def _format_attrs(attrs: dict[str, str]) -> str:
    return " ".join(
        f'{_format_attr_name(key)}="{html.escape(value, quote=True)}"'
        for key, value in attrs.items()
    )


def _normalized_path_attrs(path: ET.Element) -> dict[str, str]:
    attrs = dict(path.attrib)
    fill_attr = _android_attr("fillColor")
    stroke_attr = _android_attr("strokeColor")
    if attrs.get(fill_attr, "").upper() not in {"", "#00000000", "#00FFFFFF"}:
        attrs[fill_attr] = "#FFFFFFFF"
    if stroke_attr in attrs:
        attrs[stroke_attr] = "#FFFFFFFF"
    return attrs


def _source_paths(path: Path) -> list[dict[str, str]]:
    root = ET.parse(path).getroot()
    if _tag_name(root.tag) != "vector":
        return []
    paths: list[dict[str, str]] = []
    for element in root.iter():
        if _tag_name(element.tag) == "path":
            path_data = element.attrib.get(_android_attr("pathData"))
            if path_data:
                paths.append(_normalized_path_attrs(element))
    return paths


def _glyph_content(name: str, paths: list[dict[str, str]]) -> str:
    border_attrs = {
        _android_attr("fillColor"): "#00000000",
        _android_attr("strokeColor"): "#E6FFFFFF",
        _android_attr("strokeWidth"): "5",
        _android_attr("strokeLineCap"): "round",
        _android_attr("strokeLineJoin"): "round",
        _android_attr("pathData"): BORDER_PATH,
    }
    group_attrs = {
        _android_attr("pivotX"): "96",
        _android_attr("pivotY"): "96",
        _android_attr("scaleX"): "0.82",
        _android_attr("scaleY"): "0.82",
    }
    path_lines = "\n".join(
        f"        <path {_format_attrs(path)} />"
        for path in paths
    )
    return (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        f"<!-- Generated transparent glyph variant for {name}. -->\n"
        f'<vector xmlns:android="{ANDROID_URI}"\n'
        '    android:width="192dp"\n'
        '    android:height="192dp"\n'
        '    android:viewportWidth="192"\n'
        '    android:viewportHeight="192">\n'
        f"    <path {_format_attrs(border_attrs)} />\n"
        f"    <group {_format_attrs(group_attrs)}>\n"
        f"{path_lines}\n"
        "    </group>\n"
        "</vector>\n"
    )


def _write(path: Path, content: str, dry_run: bool, force: bool) -> bool:
    if path.exists() and not force:
        return False
    if dry_run:
        action = "overwrite" if path.exists() else "create"
        print(f"  [dry-run] would {action} {path.relative_to(REPO_ROOT)}")
        return True
    path.write_text(content, encoding="utf-8", newline="\n")
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview changes without writing files")
    parser.add_argument("--force", action="store_true",
                        help="Overwrite existing glyph variants")
    parser.add_argument("--prune", action="store_true",
                        help="Remove stale glyph variants whose mono source disappeared")
    args = parser.parse_args(argv)

    sources = _source_mono_files()
    if not sources:
        print("No vector monochrome sources found.", file=sys.stderr)
        return 1

    created = 0
    skipped_existing = 0
    skipped_non_vector = 0
    expected_names: set[str] = set()

    for source in sources:
        name = source.stem.removesuffix("_mono")
        expected_names.add(f"glyph_{name}")
        paths = _source_paths(source)
        if not paths:
            skipped_non_vector += 1
            continue
        target = DRAWABLE_DIR / f"glyph_{name}.xml"
        if _write(target, _glyph_content(name, paths), args.dry_run, args.force):
            created += 1
        else:
            skipped_existing += 1

    pruned = 0
    if args.prune:
        for target in sorted(DRAWABLE_DIR.glob("glyph_*.xml")):
            if target.stem in expected_names:
                continue
            pruned += 1
            if args.dry_run:
                print(f"  [dry-run] would delete {target.relative_to(REPO_ROOT)}")
            else:
                target.unlink()

    action = "would write" if args.dry_run else "wrote"
    print(
        f"gen_glyph_variants: {action} {created} glyph variant(s), "
        f"{skipped_existing} existing skipped, "
        f"{skipped_non_vector} non-vector source(s) skipped, {pruned} stale pruned."
    )
    return 0 if skipped_non_vector == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
