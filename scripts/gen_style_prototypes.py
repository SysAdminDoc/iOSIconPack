#!/usr/bin/env python3
"""Generate local sharp/line/filled themed-icon style prototypes.

The output is intentionally written under build/ by default so style experiments
do not become shipped drawables until a maintainer accepts a specific direction.
"""
from __future__ import annotations

import argparse
import html
import json
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DRAWABLE_DIR = REPO_ROOT / "app" / "src" / "main" / "res" / "drawable"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "build" / "style-prototypes"

ANDROID_URI = "http://schemas.android.com/apk/res/android"
ANDROID_NS = f"{{{ANDROID_URI}}}"
STYLES = ("sharp", "line", "filled")
SOURCE_PREFIXES = (
    "ios26_lg_",
    "ios18_",
    "ios17_",
    "ios16_",
    "ios15_",
    "ios14_",
    "tp_",
)


def _android_attr(name: str) -> str:
    return f"{ANDROID_NS}{name}"


def _tag_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _format_attr_name(name: str) -> str:
    if name.startswith(ANDROID_NS):
        return f"android:{name.removeprefix(ANDROID_NS)}"
    return name


def _format_attrs(attrs: dict[str, str]) -> str:
    return " ".join(
        f'{_format_attr_name(key)}="{html.escape(value, quote=True)}"'
        for key, value in attrs.items()
    )


def _normalise_drawable_name(raw: str) -> str:
    return raw.removesuffix(".xml").removesuffix("_mono")


def _source_mono_files(drawable_dir: Path, only: set[str] | None = None) -> list[Path]:
    files: list[Path] = []
    for path in sorted(drawable_dir.glob("*_mono.xml")):
        base = path.stem.removesuffix("_mono")
        if not base.startswith(SOURCE_PREFIXES):
            continue
        if only and base not in only and path.stem not in only:
            continue
        files.append(path)
    return files


def _is_closed_path(path_data: str) -> bool:
    return "Z" in path_data or "z" in path_data


def _source_paths(path: Path) -> tuple[dict[str, str], list[dict[str, str]]]:
    root = ET.parse(path).getroot()
    if _tag_name(root.tag) != "vector":
        raise ValueError(f"{path.name}: root is not <vector>")

    vector_attrs = {
        name: root.attrib.get(_android_attr(name), default)
        for name, default in (
            ("width", "192dp"),
            ("height", "192dp"),
            ("viewportWidth", "192"),
            ("viewportHeight", "192"),
        )
    }
    paths: list[dict[str, str]] = []
    for element in root.iter():
        if _tag_name(element.tag) != "path":
            continue
        path_data = element.attrib.get(_android_attr("pathData"))
        if not path_data:
            continue
        paths.append(dict(element.attrib))
    if not paths:
        raise ValueError(f"{path.name}: no pathData entries found")
    return vector_attrs, paths


def _style_path_attrs(path_attrs: dict[str, str], style: str) -> dict[str, str]:
    path_data = path_attrs[_android_attr("pathData")]
    fill_type = path_attrs.get(_android_attr("fillType"))
    source_stroke_width = path_attrs.get(_android_attr("strokeWidth"), "9")
    source_fill = path_attrs.get(_android_attr("fillColor"), "")
    source_stroke = path_attrs.get(_android_attr("strokeColor"), "")
    has_source_stroke = bool(source_stroke and source_stroke.upper() not in {"#00000000", "#00FFFFFF"})
    closed = _is_closed_path(path_data)

    attrs = {_android_attr("pathData"): path_data}
    if fill_type:
        attrs[_android_attr("fillType")] = fill_type

    if style == "line":
        attrs.update(
            {
                _android_attr("fillColor"): "#00000000",
                _android_attr("strokeColor"): "#FFFFFFFF",
                _android_attr("strokeWidth"): "8",
                _android_attr("strokeLineCap"): "round",
                _android_attr("strokeLineJoin"): "round",
            }
        )
    elif style == "filled":
        if closed or (source_fill and source_fill.upper() not in {"#00000000", "#00FFFFFF"}):
            attrs[_android_attr("fillColor")] = "#FFFFFFFF"
        else:
            attrs.update(
                {
                    _android_attr("fillColor"): "#00000000",
                    _android_attr("strokeColor"): "#FFFFFFFF",
                    _android_attr("strokeWidth"): source_stroke_width,
                    _android_attr("strokeLineCap"): path_attrs.get(_android_attr("strokeLineCap"), "round"),
                    _android_attr("strokeLineJoin"): path_attrs.get(_android_attr("strokeLineJoin"), "round"),
                }
            )
    elif style == "sharp":
        if has_source_stroke or not closed:
            attrs.update(
                {
                    _android_attr("fillColor"): "#00000000",
                    _android_attr("strokeColor"): "#FFFFFFFF",
                    _android_attr("strokeWidth"): source_stroke_width,
                    _android_attr("strokeLineCap"): "butt",
                    _android_attr("strokeLineJoin"): "miter",
                    _android_attr("strokeMiterLimit"): "4",
                }
            )
        else:
            attrs[_android_attr("fillColor")] = "#FFFFFFFF"
    else:
        raise ValueError(f"unknown style {style!r}")

    return attrs


def _prototype_content(name: str, style: str, vector_attrs: dict[str, str], paths: list[dict[str, str]]) -> str:
    path_lines = "\n".join(
        f"    <path {_format_attrs(_style_path_attrs(path, style))} />"
        for path in paths
    )
    return (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        f"<!-- Generated {style} style prototype for {name}; not a shipped drawable. -->\n"
        f'<vector xmlns:android="{ANDROID_URI}"\n'
        f'    android:width="{vector_attrs["width"]}"\n'
        f'    android:height="{vector_attrs["height"]}"\n'
        f'    android:viewportWidth="{vector_attrs["viewportWidth"]}"\n'
        f'    android:viewportHeight="{vector_attrs["viewportHeight"]}">\n'
        f"{path_lines}\n"
        "</vector>\n"
    )


def _write_atomic(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".style.tmp")
    try:
        with open(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
        Path(tmp).replace(path)
    except Exception:
        Path(tmp).unlink(missing_ok=True)
        raise


def build_manifest(
    *,
    drawable_dir: Path = DRAWABLE_DIR,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    only: set[str] | None = None,
    limit: int = 0,
    write: bool = True,
) -> dict[str, object]:
    sources = _source_mono_files(drawable_dir, only)
    if limit > 0:
        sources = sources[:limit]
    if not sources:
        raise ValueError("no matching *_mono.xml sources found")

    files: list[dict[str, str]] = []
    for source in sources:
        name = source.stem.removesuffix("_mono")
        vector_attrs, paths = _source_paths(source)
        for style in STYLES:
            target = output_dir / style / f"{style}_{name}.xml"
            content = _prototype_content(name, style, vector_attrs, paths)
            if write:
                _write_atomic(target, content)
            files.append(
                {
                    "source": str(source.relative_to(REPO_ROOT)) if source.is_relative_to(REPO_ROOT) else str(source),
                    "style": style,
                    "output": str(target.relative_to(REPO_ROOT)) if target.is_relative_to(REPO_ROOT) else str(target),
                }
            )

    manifest: dict[str, object] = {
        "schema": 1,
        "styles": list(STYLES),
        "source_count": len(sources),
        "file_count": len(files),
        "files": files,
    }
    if write:
        _write_atomic(output_dir / "style_prototypes.json", json.dumps(manifest, indent=2) + "\n")
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT_DIR.relative_to(REPO_ROOT)),
        help="Output directory for generated prototypes (default: build/style-prototypes).",
    )
    parser.add_argument(
        "--drawable",
        action="append",
        default=[],
        help="Limit generation to a drawable base name such as ios18_safari; repeatable.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Generate only the first N matching sources for quick review (default: all).",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Validate prototype generation without writing output files.",
    )
    args = parser.parse_args(argv)

    output = Path(args.output)
    output_dir = output if output.is_absolute() else REPO_ROOT / output
    only = {_normalise_drawable_name(item) for item in args.drawable} or None

    try:
        manifest = build_manifest(
            output_dir=output_dir,
            only=only,
            limit=args.limit,
            write=not args.check,
        )
    except (OSError, ET.ParseError, ValueError) as exc:
        print(f"gen_style_prototypes: FAIL ({exc})", file=sys.stderr)
        return 1

    action = "validated" if args.check else "wrote"
    print(
        f"gen_style_prototypes: {action} {manifest['file_count']} "
        f"prototype file(s) from {manifest['source_count']} source(s)."
    )
    if not args.check:
        print(f"  output: {output_dir.relative_to(REPO_ROOT) if output_dir.is_relative_to(REPO_ROOT) else output_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
