#!/usr/bin/env python3
"""set_era — switch the active icon era in appfilter.xml.

Remaps every drawable reference in appfilter.xml from the current era to a
target era.  Useful for building per-era APKs and for testing how a new icon
looks across all six design generations.

Both res/xml/appfilter.xml and assets/appfilter.xml are updated atomically.

Usage
-----
  python3 scripts/set_era.py --list               # show available eras
  python3 scripts/set_era.py ios17                # switch to iOS 17
  python3 scripts/set_era.py ios26                # switch to iOS 26 Liquid Glass
  python3 scripts/set_era.py ios18                # reset to default (iOS 18)
  python3 scripts/set_era.py ios17 --dry-run      # preview changes, no write

Notes
-----
- Only drawables whose target PNG exists on disk are remapped; icons with no
  equivalent in the target era keep their current drawable.
- tp_* (third-party) entries are always left unchanged.
- After switching, run `python3 scripts/icontool.py check` to validate.
- The switch is reversible: run `set_era.py ios18` to restore the default.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from icontool import (  # noqa: E402
    APPFILTER_ASSET,
    APPFILTER_RES,
    DRAWABLE_HDPI,
    DRAWABLE_VEC,
    _read,
    _write_pair,
)

# ---------------------------------------------------------------------------
# Era registry
# ---------------------------------------------------------------------------

ERA_PREFIXES: dict[str, str] = {
    "ios14": "ios14_",
    "ios15": "ios15_",
    "ios16": "ios16_",
    "ios17": "ios17_",
    "ios18": "ios18_",
    "ios26": "ios26_lg_",
}

ERA_DISPLAY: dict[str, str] = {
    "ios14": "iOS 14",
    "ios15": "iOS 15",
    "ios16": "iOS 16",
    "ios17": "iOS 17",
    "ios18": "iOS 18 (default)",
    "ios26": "iOS 26 Liquid Glass",
}

DEFAULT_ERA = "ios18"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_ALL_ERA_PREFIXES = tuple(ERA_PREFIXES.values())


def _era_prefix_of(drawable: str) -> str | None:
    """Return the era prefix for *drawable*, or None if it is tp_* or unknown."""
    for prefix in _ALL_ERA_PREFIXES:
        if drawable.startswith(prefix):
            return prefix
    return None


def _strip_era(drawable: str, prefix: str) -> str:
    """Return the bare app-name portion after the era prefix."""
    return drawable[len(prefix):]


def _drawable_exists(drawable: str) -> bool:
    """Return True if *drawable* has a PNG or vector resource on disk."""
    png = DRAWABLE_HDPI / f"{drawable}.png"
    vd = DRAWABLE_VEC / f"{drawable}.xml"
    other = list((DRAWABLE_HDPI.parent).glob(f"drawable-*/{drawable}.png"))
    return png.exists() or vd.exists() or bool(other)


def _remap(
    content: str,
    target_prefix: str,
    *,
    dry_run: bool = False,
) -> tuple[str, int, int]:
    """Remap all era drawables in *content* to *target_prefix*.

    Returns (new_content, remapped_count, skipped_count).
    """
    item_pat = re.compile(
        r'(<item\s+component="[^"]+"\s+drawable=")([^"]+)("(?:\s*/)?>)'
    )

    remapped = 0
    skipped = 0
    result_parts: list[str] = []
    last_end = 0

    for m in item_pat.finditer(content):
        drawable = m.group(2)
        current_prefix = _era_prefix_of(drawable)

        if current_prefix is None:
            # tp_* or unknown — leave untouched
            continue

        if current_prefix == target_prefix:
            # Already in target era
            continue

        bare = _strip_era(drawable, current_prefix)
        candidate = f"{target_prefix}{bare}"

        if not _drawable_exists(candidate):
            skipped += 1
            continue

        # Perform the replacement
        result_parts.append(content[last_end : m.start(2)])
        result_parts.append(candidate)
        last_end = m.end(2)
        remapped += 1

    if result_parts:
        result_parts.append(content[last_end:])
        new_content = "".join(result_parts)
    else:
        new_content = content

    return new_content, remapped, skipped


def _detect_current_era(content: str) -> str:
    """Return the era key that the majority of mapped drawables belong to."""
    counts: dict[str, int] = {k: 0 for k in ERA_PREFIXES}
    item_pat = re.compile(r'drawable="([^"]+)"')
    for m in item_pat.finditer(content):
        d = m.group(1)
        for key, prefix in ERA_PREFIXES.items():
            if d.startswith(prefix):
                counts[key] += 1
    if not any(counts.values()):
        return DEFAULT_ERA
    return max(counts, key=lambda k: counts[k])


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_list(_args: argparse.Namespace) -> int:
    content = _read(APPFILTER_RES)
    current = _detect_current_era(content)
    print("Available eras:\n")
    for key, display in ERA_DISPLAY.items():
        marker = " ← active" if key == current else ""
        print(f"  {key:8}  {display}{marker}")
    print(
        "\nUsage: python3 scripts/set_era.py <era>   "
        "e.g. set_era.py ios17"
    )
    return 0


def cmd_set(args: argparse.Namespace) -> int:
    era: str = args.era
    dry_run: bool = args.dry_run

    if era not in ERA_PREFIXES:
        print(
            f"error: unknown era '{era}'. "
            f"Valid options: {', '.join(ERA_PREFIXES)}",
            file=sys.stderr,
        )
        return 1

    target_prefix = ERA_PREFIXES[era]
    content = _read(APPFILTER_RES)
    current_era = _detect_current_era(content)

    if current_era == era:
        print(f"Already on era '{era}' — nothing to do.")
        return 0

    new_content, remapped, skipped = _remap(
        content, target_prefix, dry_run=dry_run
    )

    current_display = ERA_DISPLAY.get(current_era, current_era)
    target_display = ERA_DISPLAY[era]
    print(
        f"Switching: {current_display}  →  {target_display}\n"
        f"  remapped : {remapped} icon(s)\n"
        f"  kept as-is: {skipped} (no {era} variant exists)\n"
    )

    if dry_run:
        print("Dry-run — no files written.")
        # Show a sample diff
        sample_lines = [
            ln for ln in new_content.splitlines()
            if f'drawable="{target_prefix}' in ln
        ][:8]
        if sample_lines:
            print("\nSample of remapped entries:")
            for ln in sample_lines:
                print(" ", ln.strip())
        return 0

    if remapped == 0:
        print("Nothing changed — no files written.")
        return 0

    _write_pair(APPFILTER_RES, APPFILTER_ASSET, new_content)
    print(f"\nDone. Run `python3 scripts/icontool.py check` to validate.")
    return 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="set_era",
        description=__doc__.splitlines()[1].strip(),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="\n".join(__doc__.splitlines()[3:]),
    )

    p.add_argument(
        "--list", "-l",
        action="store_true",
        help="List available eras and the currently active one.",
    )
    p.add_argument(
        "era",
        nargs="?",
        metavar="ERA",
        help=f"Target era: {', '.join(ERA_PREFIXES)}",
    )
    p.add_argument(
        "--dry-run", "-n",
        action="store_true",
        help="Preview changes without writing any files.",
    )

    return p


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.list or args.era is None:
        return cmd_list(args)
    return cmd_set(args)


if __name__ == "__main__":
    sys.exit(main())
