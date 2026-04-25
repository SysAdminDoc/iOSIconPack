#!/usr/bin/env python3
"""Scaffold Android 13+ monochrome bitmap stubs for every ios18_* and tp_* icon.

Android 13 introduced the `<monochrome>` layer inside `<adaptive-icon>` XML.
Launchers that support themed icons (Pixel Launcher, Lawnchair 14+) tint this
layer using the user's wallpaper-derived Material You color.

This script generates placeholder `drawable/<name>_mono.xml` files — each is a
`<bitmap>` pointing at the existing raster PNG.  The bitmaps are usable as-is
(Android thresholds them at runtime), but can be replaced with hand-crafted
vector paths for better results.

Also generates `drawable/<name>_themed.xml` adaptive-icon wrappers that
reference the monochrome stub, making the icons compatible with launchers that
apply themed-icon support via adaptive-icon XML (e.g. Pixel Launcher).

Usage:
    python3 scripts/gen_monochrome.py            # generate all stubs
    python3 scripts/gen_monochrome.py --dry-run  # preview without writing
    python3 scripts/gen_monochrome.py --force    # overwrite existing stubs
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DRAWABLE_DIR = REPO_ROOT / "app" / "src" / "main" / "res" / "drawable"
PACK_DIR = REPO_ROOT / "app" / "src" / "main" / "res" / "drawable-xxxhdpi"

MONO_TEMPLATE = """\
<?xml version="1.0" encoding="utf-8"?>
<!--
    Monochrome stub for {name}.
    Replace with a hand-crafted vector <path> for better themed-icon results.
    See: https://developer.android.com/develop/ui/views/launch/icon_design_adaptive#monochrome
-->
<bitmap xmlns:android="http://schemas.android.com/apk/res/android"
    android:src="@drawable/{name}" />
"""

THEMED_TEMPLATE = """\
<?xml version="1.0" encoding="utf-8"?>
<!--
    Adaptive-icon wrapper that exposes a monochrome layer for Android 13+
    themed-icon support. Launchers read this when the user enables "Themed icons".
-->
<adaptive-icon xmlns:android="http://schemas.android.com/apk/res/android">
    <background android:drawable="@color/ic_launcher_background" />
    <foreground android:drawable="@drawable/{name}" />
    <monochrome android:drawable="@drawable/{name}_mono" />
</adaptive-icon>
"""


def _target_icons() -> list[str]:
    """Return sorted list of drawable names to generate mono stubs for."""
    names: list[str] = []
    for p in sorted(PACK_DIR.glob("*.png")):
        stem = p.stem
        if stem.startswith("ios18_") or stem.startswith("tp_"):
            names.append(stem)
    return names


def _write(path: Path, content: str, dry_run: bool, force: bool) -> bool:
    if path.exists() and not force:
        return False
    if dry_run:
        action = "overwrite" if path.exists() else "create"
        print(f"  [dry-run] would {action} {path.relative_to(REPO_ROOT)}")
        return True
    path.write_text(content, encoding="utf-8")
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview changes without writing files")
    parser.add_argument("--force", action="store_true",
                        help="Overwrite existing stub files")
    args = parser.parse_args(argv)

    DRAWABLE_DIR.mkdir(parents=True, exist_ok=True)

    icons = _target_icons()
    if not icons:
        print("No ios18_* or tp_* icons found in drawable-xxxhdpi/.", file=sys.stderr)
        return 1

    created_mono = 0
    created_themed = 0
    skipped = 0

    for name in icons:
        mono_path = DRAWABLE_DIR / f"{name}_mono.xml"
        themed_path = DRAWABLE_DIR / f"{name}_themed.xml"

        w_mono = _write(mono_path, MONO_TEMPLATE.format(name=name), args.dry_run, args.force)
        w_themed = _write(themed_path, THEMED_TEMPLATE.format(name=name), args.dry_run, args.force)

        if w_mono:
            created_mono += 1
        else:
            skipped += 1
        if w_themed:
            created_themed += 1

    if not args.dry_run:
        print(f"gen_monochrome: {created_mono} mono stubs + {created_themed} themed wrappers written"
              f"{f', {skipped} skipped (already exist; use --force to overwrite)' if skipped else ''}.")
        print()
        print("Next steps:")
        print("  1. Replace <bitmap> stubs with hand-crafted <vector> paths for better quality.")
        print("     Reference: https://developer.android.com/develop/ui/views/launch/icon_design_adaptive#monochrome")
        print("  2. Test on a Pixel device with 'Themed icons' enabled in Wallpaper & Style settings.")
        print("  3. Run `python scripts/icontool.py check` to confirm assets are valid.")
    else:
        print(f"[dry-run] would write {created_mono} mono stubs + {created_themed} themed wrappers.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
