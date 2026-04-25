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
import os
import re
import shutil
import subprocess
import sys
import tempfile
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
]

# tp_ icons live only in appfilter.xml + on disk, never in drawable.xml.
TP_PREFIX = "tp_"


def _era_prefix(drawable: str) -> str:
    for prefix in ERA_PREFIXES:
        if drawable.startswith(prefix):
            return prefix
    return ""


def _category_title(drawable: str) -> str:
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

    # tp_ icons exist only in appfilter + on disk — never in drawable.xml.
    if not drawable.startswith(TP_PREFIX):
        if not _dw_has(dw, drawable):
            dw = _dw_insert(dw, drawable)
            cat = _category_title(drawable) or "unknown era"
            print(f"  + drawable.xml [{cat}]: {drawable}")
        else:
            print(f"  = drawable.xml: {drawable} already listed")

    _write_pair(APPFILTER_RES, APPFILTER_ASSET, af)
    _write_pair(DRAWABLE_XML_RES, DRAWABLE_XML_ASSET, dw)
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


def cmd_check(args: argparse.Namespace) -> int:  # noqa: ARG001
    rc = 0
    for script in ("validate_appfilter.py", "validate_drawables.py"):
        validator = REPO_ROOT / "scripts" / script
        if not validator.exists():
            print(f"warning: validator not found: {script}", file=sys.stderr)
            continue
        result = subprocess.run([sys.executable, str(validator)])
        if result.returncode != 0:
            rc = result.returncode
    return rc


def cmd_rebuild(args: argparse.Namespace) -> int:
    """Sync drawable.xml with files on disk.

    Scans drawable-xxxhdpi/ for PNG files and drawable/ for vector XMLs,
    then adds any that are missing from drawable.xml to the correct era
    category section.  tp_* icons are always excluded (they live only in
    appfilter.xml by design).

    With --prune, also removes drawable.xml entries whose file no longer
    exists on disk.
    """
    prune: bool = args.prune
    dry_run: bool = getattr(args, "dry_run", False)

    dw = _read(DRAWABLE_XML_RES)

    # Drawables currently listed in drawable.xml
    in_xml: set[str] = set(re.findall(r'<item\s+drawable="([^"]+)"', dw))

    # Drawables that exist on disk (PNGs + vector drawables, non-tp_, non-launcher)
    on_disk: set[str] = set()
    for f in DRAWABLE_HDPI.glob("*.png"):
        name = f.stem
        if not name.startswith(TP_PREFIX) and _era_prefix(name):
            on_disk.add(name)
    for f in DRAWABLE_VEC.glob("*.xml"):
        name = f.stem
        skip_prefixes = ("ic_launcher", "ic_", "tp_", "background", "foreground")
        if not any(name.startswith(p) for p in skip_prefixes) and _era_prefix(name):
            on_disk.add(name)

    missing: list[str] = sorted(on_disk - in_xml)
    stale: list[str] = sorted(in_xml - on_disk) if prune else []

    if not missing and not stale:
        print("drawable.xml is already in sync with disk — nothing to do.")
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
    print(f"\nDone — {len(missing)} added, {len(stale)} removed.")
    return 0


# ---------------------------------------------------------------------------
# CLI wiring
# ---------------------------------------------------------------------------

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
        help="Run the full validate_appfilter.py validator",
    )
    check_p.set_defaults(func=cmd_check)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
