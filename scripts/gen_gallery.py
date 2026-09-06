#!/usr/bin/env python3
"""Generate the docs/index.html icon browser for GitHub Pages.

Reads drawable.xml (era categories + icon list) and appfilter.xml (component
counts) to produce a single self-contained HTML file.  Icon images are loaded
from GitHub raw URLs so no assets need to be copied into docs/.

Usage
-----
  python3 scripts/gen_gallery.py           # writes docs/index.html
  python3 scripts/gen_gallery.py --dry-run # print output to stdout

The generated file is checked into the repo. GitHub Pages serves it from the
docs/ folder on the master branch. Run with `--check` locally before release to
fail when docs/index.html is stale.
"""
from __future__ import annotations

import argparse
import html as html_lib
import json
import re
import sys
import textwrap
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
DRAWABLE_XML = REPO_ROOT / "app/src/main/res/xml/drawable.xml"
APPFILTER_XML = REPO_ROOT / "app/src/main/res/xml/appfilter.xml"
PACK_DIR = REPO_ROOT / "app/src/main/res/drawable-xxxhdpi"
OUT_FILE = REPO_ROOT / "docs/index.html"
RELEASE_CHANNEL_STATUS = REPO_ROOT / "docs/release-channel.json"
GALLERY_EXCLUDED_CATEGORIES = {"Glyph"}

RAW_BASE = (
    "https://raw.githubusercontent.com/SysAdminDoc/iOSIconPack/master"
    "/app/src/main/res/drawable-xxxhdpi"
)
GITHUB_URL = "https://github.com/SysAdminDoc/iOSIconPack"

ERA_COLOURS: dict[str, str] = {
    "iOS 18":                 "#58A6FF",
    "iOS 17":                 "#A78BFA",
    "iOS 16":                 "#34D399",
    "iOS 15":                 "#FBBF24",
    "iOS 14":                 "#F87171",
    "iOS 26 Liquid Glass":    "#67E8F9",
    "Third Party":            "#9CA3AF",
}

ERA_SHORT: dict[str, str] = {
    "iOS 18":                "18",
    "iOS 17":                "17",
    "iOS 16":                "16",
    "iOS 15":                "15",
    "iOS 14":                "14",
    "iOS 26 Liquid Glass":   "26",
    "Third Party":           "TP",
}

# Prefix → category title mapping (for comparison grid)
PREFIX_TO_ERA: dict[str, str] = {
    "ios18_":    "iOS 18",
    "ios17_":    "iOS 17",
    "ios16_":    "iOS 16",
    "ios15_":    "iOS 15",
    "ios14_":    "iOS 14",
    "ios26_lg_": "iOS 26 Liquid Glass",
}
COMPARE_ERAS: list[tuple[str, str]] = [
    ("ios14_",    "iOS 14"),
    ("ios15_",    "iOS 15"),
    ("ios16_",    "iOS 16"),
    ("ios17_",    "iOS 17"),
    ("ios18_",    "iOS 18"),
    ("ios26_lg_", "iOS 26"),
]


# ---------------------------------------------------------------------------
# Parsers
# ---------------------------------------------------------------------------

def _parse_drawables() -> list[tuple[str, list[str]]]:
    """Return [(category_title, [drawable_name, ...]), ...] including tp_* icons."""
    text = DRAWABLE_XML.read_text(encoding="utf-8")
    categories: list[tuple[str, list[str]]] = []
    current_cat: str | None = None
    items: list[str] = []

    for line in text.splitlines():
        cat_m = re.search(r'<category\s+title="([^"]+)"', line)
        if cat_m:
            if current_cat is not None:
                categories.append((current_cat, items))
            current_cat = cat_m.group(1)
            items = []
            continue
        item_m = re.search(r'<item\s+drawable="([^"]+)"', line)
        if item_m and current_cat is not None:
            items.append(item_m.group(1))

    if current_cat is not None:
        categories.append((current_cat, items))
    categories = [
        (cat, icons)
        for cat, icons in categories
        if cat not in GALLERY_EXCLUDED_CATEGORIES
    ]

    # tp_* icons are not in drawable.xml; show every shipped PNG, even when a
    # default app mapping has moved to an era-aware variant.
    af_text = APPFILTER_XML.read_text(encoding="utf-8")
    tp_from_appfilter = {
        m.group(1)
        for m in re.finditer(r'drawable="(tp_[^"]+)"', af_text)
    }
    tp_from_disk = {p.stem for p in PACK_DIR.glob("tp_*.png")}
    tp_icons: list[str] = sorted(tp_from_appfilter | tp_from_disk)
    if tp_icons:
        categories.append(("Third Party", tp_icons))

    return categories


def _parse_component_counts() -> dict[str, int]:
    """Return {drawable_name: component_count}."""
    text = APPFILTER_XML.read_text(encoding="utf-8")
    counts: dict[str, int] = defaultdict(int)
    for m in re.finditer(r'drawable="([^"]+)"', text):
        counts[m.group(1)] += 1
    return dict(counts)


def _release_channel_notice() -> str:
    """Return a visible install-channel warning when the generated status is stale."""
    if not RELEASE_CHANNEL_STATUS.exists():
        return ""
    try:
        status = json.loads(RELEASE_CHANNEL_STATUS.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return textwrap.dedent(f"""\
          <aside class="release-warning" role="status" aria-live="polite">
            <strong>Install channel status unavailable</strong>
            <span>Regenerate <code>{html_lib.escape(RELEASE_CHANNEL_STATUS.name)}</code> before changing install copy.</span>
          </aside>""")

    if status.get("ok") is True:
        return ""

    expected_tag = html_lib.escape(str(status.get("expected_tag") or "the current tag"))
    latest_tag = html_lib.escape(str(status.get("latest_release_tag") or "missing"))
    expected_asset = html_lib.escape(str(status.get("expected_asset") or "the release APK"))
    return textwrap.dedent(f"""\
      <aside class="release-warning" role="status" aria-live="polite">
        <strong>Install channel is stale</strong>
        <span>GitHub Releases latest is {latest_tag}, but this source tree expects {expected_tag} and {expected_asset}. Obtainium and manual installs may fetch an older APK until the signed release asset is published.</span>
        <span><a href="release-channel.json">View generated channel status</a>.</span>
      </aside>""")


# ---------------------------------------------------------------------------
# HTML generation
# ---------------------------------------------------------------------------

def _css() -> str:
    return textwrap.dedent("""
        *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

        :root {
            --bg: #0d1117;
            --surface: #161b22;
            --surface-elevated: #1c2431;
            --border: #30363d;
            --text: #e6edf3;
            --muted: #8b949e;
            --accent: #58A6FF;
            --accent-soft: rgba(88, 166, 255, 0.14);
            --shadow: 0 14px 34px rgba(0, 0, 0, 0.22);
        }

        @media (prefers-color-scheme: light) {
            :root {
                --bg: #f6f8fa;
                --surface: #ffffff;
                --surface-elevated: #f2f5f9;
                --border: #d0d7de;
                --text: #1f2328;
                --muted: #57606a;
                --accent: #0969da;
                --accent-soft: rgba(9, 105, 218, 0.12);
                --shadow: 0 12px 30px rgba(31, 35, 40, 0.10);
            }
        }

        html { scroll-behavior: smooth; }

        body {
            background: var(--bg);
            color: var(--text);
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            min-height: 100vh;
        }

        [hidden] { display: none !important; }

        .skip-link {
            position: absolute;
            left: 1rem;
            top: 0.75rem;
            z-index: 20;
            background: var(--accent);
            color: var(--bg);
            border-radius: 8px;
            font-weight: 700;
            padding: 0.55rem 0.75rem;
            transform: translateY(-160%);
            transition: transform 0.15s ease;
        }
        .skip-link:focus-visible { transform: translateY(0); }

        header {
            background: var(--surface);
            border-bottom: 1px solid var(--border);
            padding: 1.15rem 1.5rem 1.25rem;
            position: sticky;
            top: 0;
            z-index: 10;
            display: flex;
            flex-direction: column;
            gap: 0.75rem;
        }

        .header-top {
            display: flex;
            align-items: center;
            justify-content: space-between;
            flex-wrap: wrap;
            gap: 0.5rem;
        }

        h1 {
            font-size: 1.15rem;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 0.5rem;
            line-height: 1.25;
        }

        .icon-count {
            font-size: 0.75rem;
            color: var(--muted);
            background: var(--bg);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 0.1rem 0.55rem;
            white-space: nowrap;
        }

        a.gh-link {
            color: var(--muted);
            text-decoration: none;
            font-size: 0.8rem;
            display: flex;
            align-items: center;
            gap: 0.3rem;
        }
        a.gh-link:hover { color: var(--accent); }

        .header-copy {
            color: var(--muted);
            font-size: 0.82rem;
            line-height: 1.45;
            max-width: 62rem;
        }

        .release-warning {
            background: #3b2300;
            border: 1px solid #9a6700;
            border-radius: 8px;
            color: #ffd8a8;
            display: flex;
            flex-direction: column;
            gap: 0.25rem;
            font-size: 0.82rem;
            line-height: 1.45;
            max-width: 64rem;
            padding: 0.65rem 0.75rem;
        }
        .release-warning strong { color: #ffdfb3; }
        .release-warning a {
            color: #ffd8a8;
            font-weight: 700;
        }

        .sr-only {
            position: absolute;
            width: 1px;
            height: 1px;
            padding: 0;
            margin: -1px;
            overflow: hidden;
            clip: rect(0, 0, 0, 0);
            white-space: nowrap;
            border: 0;
        }

        a:focus-visible,
        button:focus-visible,
        input:focus-visible,
        table:focus-visible {
            outline: 2px solid var(--accent);
            outline-offset: 3px;
        }

        .search-wrap {
            display: flex;
            gap: 0.5rem;
            align-items: center;
        }

        #search {
            flex: 1;
            max-width: 360px;
            background: var(--bg);
            border: 1px solid var(--border);
            border-radius: 6px;
            color: var(--text);
            font-size: 0.85rem;
            padding: 0.4rem 0.75rem;
            outline: none;
        }
        #search:focus-visible { border-color: var(--accent); }
        #search::placeholder { color: var(--muted); }

        .clear-btn {
            background: var(--surface-elevated);
            border: 1px solid var(--border);
            border-radius: 8px;
            color: var(--muted);
            cursor: pointer;
            font-size: 0.78rem;
            min-height: 34px;
            padding: 0.35rem 0.7rem;
            transition: background 0.15s ease, border-color 0.15s ease, color 0.15s ease;
        }
        .clear-btn:hover {
            border-color: var(--accent);
            color: var(--text);
        }

        .gallery-status {
            color: var(--muted);
            font-size: 0.78rem;
            line-height: 1.35;
            min-height: 1.1rem;
        }

        .filter-bar {
            display: flex;
            gap: 0.45rem;
            flex-wrap: wrap;
        }

        .filter-btn {
            background: var(--bg);
            border: 1px solid var(--border);
            border-radius: 8px;
            color: var(--muted);
            cursor: pointer;
            display: inline-flex;
            align-items: center;
            gap: 0.45rem;
            font-size: 0.75rem;
            min-height: 34px;
            padding: 0.32rem 0.7rem;
            transition: background 0.15s ease, border-color 0.15s ease, color 0.15s ease, transform 0.15s ease;
        }
        .filter-btn::before {
            content: "";
            width: 8px;
            height: 8px;
            border-radius: 4px;
            background: var(--dot, var(--accent));
            opacity: 0.78;
        }
        .filter-btn:hover {
            border-color: var(--accent);
            color: var(--text);
            transform: translateY(-1px);
        }
        .filter-btn.active,
        .filter-btn[aria-pressed="true"] {
            border-color: var(--accent);
            color: var(--accent);
            background: var(--accent-soft);
        }

        main {
            padding: 1.5rem;
            max-width: 1400px;
            margin: 0 auto;
        }

        .era-section { margin-bottom: 2.5rem; }

        .era-heading {
            display: flex;
            align-items: center;
            gap: 0.6rem;
            margin-bottom: 1rem;
            font-size: 0.9rem;
            font-weight: 600;
            color: var(--muted);
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }

        .era-dot {
            width: 8px;
            height: 8px;
            border-radius: 4px;
        }

        .icon-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(100px, 1fr));
            gap: 0.75rem;
        }

        .icon-card {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 10px;
            cursor: default;
            display: flex;
            flex-direction: column;
            align-items: center;
            padding: 0.75rem 0.4rem 0.6rem;
            min-height: 118px;
            transition: border-color 0.15s ease, box-shadow 0.15s ease, transform 0.15s ease;
            position: relative;
        }
        .icon-card:hover {
            border-color: var(--accent);
            box-shadow: var(--shadow);
            transform: translateY(-2px);
        }

        .icon-img {
            width: 56px;
            height: 56px;
            object-fit: contain;
            border-radius: 12px;
            background: var(--bg);
            margin-bottom: 0.5rem;
        }

        .icon-name {
            font-size: 0.65rem;
            color: var(--muted);
            text-align: center;
            word-break: break-all;
            line-height: 1.3;
        }

        .era-badge {
            position: absolute;
            top: 0.35rem;
            right: 0.35rem;
            font-size: 0.55rem;
            font-weight: 700;
            border-radius: 4px;
            padding: 0.1rem 0.3rem;
            opacity: 0.85;
        }

        .comp-badge {
            position: absolute;
            bottom: 0.35rem;
            right: 0.35rem;
            font-size: 0.55rem;
            color: var(--muted);
            background: var(--bg);
            border: 1px solid var(--border);
            border-radius: 4px;
            padding: 0.1rem 0.3rem;
        }

        .empty-state {
            display: none;
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 10px;
            color: var(--muted);
            text-align: center;
            padding: 2.5rem 1rem;
            font-size: 0.9rem;
            line-height: 1.6;
        }
        .empty-state strong {
            color: var(--text);
            display: block;
            font-size: 1rem;
            margin-bottom: 0.25rem;
        }
        .empty-state a {
            color: var(--accent);
            font-weight: 600;
            text-decoration: none;
        }
        .empty-state a:hover { text-decoration: underline; }

        #empty-msg {
            display: none;
        }

        footer {
            border-top: 1px solid var(--border);
            color: var(--muted);
            font-size: 0.75rem;
            padding: 1rem 1.5rem;
            text-align: center;
        }
        footer a { color: var(--accent); text-decoration: none; }

        .tab-bar {
            display: flex;
            align-items: stretch;
            justify-content: space-between;
            gap: 0.25rem;
            border-bottom: 1px solid var(--border);
            padding: 0 1.5rem;
            background: var(--surface);
            overflow-x: auto;
        }
        .tab-list {
            display: flex;
            gap: 0.25rem;
        }
        .tab-btn {
            background: transparent;
            border: none;
            border-bottom: 2px solid transparent;
            color: var(--muted);
            cursor: pointer;
            font-size: 0.82rem;
            padding: 0.6rem 0.9rem;
            margin-bottom: -1px;
            transition: color 0.15s ease, border-color 0.15s ease, background 0.15s ease;
            white-space: nowrap;
        }
        .tab-btn:hover { color: var(--text); }
        .tab-btn.active,
        .tab-btn[aria-selected="true"] {
            color: var(--accent);
            border-bottom-color: var(--accent);
        }
        .tab-link {
            color: var(--muted);
            text-decoration: none;
        }

        .compare-note {
            color: var(--muted);
            font-size: 0.8rem;
            margin-bottom: 1.25rem;
        }
        .cmp-scroll { overflow-x: auto; }
        .cmp-table {
            border-collapse: collapse;
            min-width: 520px;
            width: 100%;
        }
        .cmp-table th, .cmp-table td {
            padding: 0.4rem 0.5rem;
            text-align: center;
            vertical-align: middle;
        }
        .cmp-table thead th {
            font-size: 0.7rem;
            font-weight: 700;
            letter-spacing: 0.06em;
            text-transform: uppercase;
            position: sticky;
            top: 0;
        }
        .cmp-label-th {
            text-align: left !important;
            color: var(--muted) !important;
            background: var(--bg) !important;
            border-bottom: none !important;
            font-size: 0.7rem !important;
            min-width: 80px;
        }
        .cmp-table tbody tr:hover { background: var(--surface); }
        .cmp-table tbody tr:hover .cmp-label { color: var(--text); }
        .cmp-label {
            text-align: left;
            font-size: 0.72rem;
            font-weight: 500;
            color: var(--muted);
            white-space: nowrap;
            padding-right: 1rem;
        }
        .cmp-img {
            width: 44px;
            height: 44px;
            border-radius: 10px;
            border: 1px solid transparent;
            object-fit: contain;
            display: block;
            margin: 0 auto;
            transition: transform 0.15s ease;
        }
        .cmp-img:hover { transform: scale(1.15); }
        .cmp-missing { color: var(--border); font-size: 0.9rem; }
        #compare-view { padding-top: 0.5rem; }

        @media (max-width: 640px) {
            header { padding: 1rem; }
            main { padding: 1rem; }
            .search-wrap { align-items: stretch; }
            #search { max-width: none; }
            .clear-btn { flex-shrink: 0; }
            .tab-bar { padding: 0 1rem; }
            .icon-grid { grid-template-columns: repeat(auto-fill, minmax(88px, 1fr)); }
        }

        @media (prefers-reduced-motion: reduce) {
            html { scroll-behavior: auto; }
            *, *::before, *::after {
                animation-duration: 0.01ms !important;
                animation-iteration-count: 1 !important;
                transition-duration: 0.01ms !important;
            }
        }
    """).strip()


def _js() -> str:
    return textwrap.dedent("""
        (function () {
            const search = document.getElementById('search');
            const filterBtns = document.querySelectorAll('.filter-btn');
            const cards = document.querySelectorAll('.icon-card');
            const sections = document.querySelectorAll('.era-section');
            const emptyMsg = document.getElementById('empty-msg');
            const resultStatus = document.getElementById('gallery-result-status');
            const browseView = document.getElementById('browse-view');
            const compareView = document.getElementById('compare-view');
            const clearSearch = document.getElementById('clear-search');
            const tabBtns = document.querySelectorAll('.tab-btn[data-tab]');

            let activeEra = 'all';

            function update() {
                const q = search.value.toLowerCase().trim();
                let visible = 0;

                cards.forEach(card => {
                    const nameMatch = card.dataset.name.includes(q);
                    const eraMatch  = activeEra === 'all' || card.dataset.era === activeEra;
                    const show = nameMatch && eraMatch;
                    card.hidden = !show;
                    if (show) visible++;
                });

                // Hide empty sections
                sections.forEach(sec => {
                    const anyVisible = [...sec.querySelectorAll('.icon-card')]
                        .some(c => !c.hidden);
                    sec.hidden = !anyVisible;
                });

                emptyMsg.style.display = visible === 0 ? 'block' : 'none';
                if (clearSearch) {
                    clearSearch.hidden = q.length === 0;
                }
                if (resultStatus) {
                    const noun = visible === 1 ? 'icon' : 'icons';
                    const filter = activeEra === 'all'
                        ? ''
                        : ` in ${document.querySelector('.filter-btn.active')?.textContent ?? 'this era'}`;
                    resultStatus.textContent = `Showing ${visible} ${noun}${filter}.`;
                }
            }

            search.addEventListener('input', update);
            if (clearSearch) {
                clearSearch.addEventListener('click', () => {
                    search.value = '';
                    search.focus();
                    update();
                });
            }

            function moveFocus(items, current, delta) {
                const list = Array.from(items);
                const index = list.indexOf(current);
                if (index === -1) return;
                const next = (index + delta + list.length) % list.length;
                list[next].focus();
            }

            function setActiveFilter(selected) {
                filterBtns.forEach(btn => {
                    const isActive = btn === selected;
                    btn.classList.toggle('active', isActive);
                    btn.setAttribute('aria-pressed', String(isActive));
                });
                activeEra = selected.dataset.era;
                update();
            }

            filterBtns.forEach(btn => {
                btn.addEventListener('click', () => {
                    setActiveFilter(btn);
                });
                btn.addEventListener('keydown', event => {
                    if (event.key === 'ArrowRight' || event.key === 'ArrowDown') {
                        event.preventDefault();
                        moveFocus(filterBtns, btn, 1);
                    } else if (event.key === 'ArrowLeft' || event.key === 'ArrowUp') {
                        event.preventDefault();
                        moveFocus(filterBtns, btn, -1);
                    } else if (event.key === 'Home') {
                        event.preventDefault();
                        filterBtns[0].focus();
                    } else if (event.key === 'End') {
                        event.preventDefault();
                        filterBtns[filterBtns.length - 1].focus();
                    }
                });
            });

            function setActiveTab(selected) {
                tabBtns.forEach(btn => {
                    const isActive = btn === selected;
                    btn.classList.toggle('active', isActive);
                    btn.setAttribute('aria-selected', String(isActive));
                    btn.tabIndex = isActive ? 0 : -1;
                });
                const tab = selected.dataset.tab;
                browseView.hidden = tab !== 'browse';
                compareView.hidden = tab !== 'compare';

                const searchWrap = document.querySelector('.search-wrap');
                const filterBar = document.querySelector('.filter-bar');
                const hide = tab === 'compare';
                if (searchWrap) searchWrap.hidden = hide;
                if (filterBar) filterBar.hidden = hide;
            }

            tabBtns.forEach(btn => {
                btn.addEventListener('click', () => {
                    setActiveTab(btn);
                });
                btn.addEventListener('keydown', event => {
                    if (event.key === 'ArrowRight') {
                        event.preventDefault();
                        moveFocus(tabBtns, btn, 1);
                    } else if (event.key === 'ArrowLeft') {
                        event.preventDefault();
                        moveFocus(tabBtns, btn, -1);
                    } else if (event.key === 'Home') {
                        event.preventDefault();
                        tabBtns[0].focus();
                    } else if (event.key === 'End') {
                        event.preventDefault();
                        tabBtns[tabBtns.length - 1].focus();
                    } else if (event.key === 'Enter' || event.key === ' ') {
                        event.preventDefault();
                        setActiveTab(btn);
                    }
                });
            });

            update();
        })();
    """).strip()


def _card_html(
    name: str,
    era: str,
    comp_count: int,
) -> str:
    colour = ERA_COLOURS.get(era, "#9CA3AF")
    short  = ERA_SHORT.get(era, "TP")
    img_url = f"{RAW_BASE}/{name}.png"
    label  = (name
              .replace("ios14_", "").replace("ios15_", "").replace("ios16_", "")
              .replace("ios17_", "").replace("ios18_", "").replace("ios26_lg_", "")
              .replace("tp_", ""))
    era_slug = era.replace(" ", "-").replace(".", "").replace("/", "").replace("--", "-").lower()
    comp_str = f"×{comp_count}" if comp_count else ""
    badge_label = short if era != "Third Party" else "TP"
    badge_style = f"background:{colour}22;color:{colour}"

    comp_html = (
        f'<span class="comp-badge" aria-label="{comp_count} launcher mappings">{comp_str}</span>'
        if comp_str else ""
    )

    return (
        f'<div class="icon-card" role="listitem" aria-label="{label} icon, {era}" '
        f'data-name="{name.lower()}" data-era="{era_slug}">\n'
        f'  <span class="era-badge" style="{badge_style}" aria-label="{era}">{badge_label}</span>\n'
        f'  <img class="icon-img" src="{img_url}" alt="" aria-hidden="true" loading="lazy">\n'
        f'  <span class="icon-name">{label}</span>\n'
        f'  {comp_html}\n'
        f'</div>'
    )


def _base_app_names() -> list[str]:
    """Return sorted base names (e.g. 'mail') that have an ios18_* drawable on disk."""
    names: list[str] = []
    for p in sorted(PACK_DIR.glob("ios18_*.png")):
        names.append(p.stem.removeprefix("ios18_"))
    return names


def _comparison_html() -> str:
    """Return HTML for the era-comparison grid section."""
    bases = _base_app_names()

    col_headers = "".join(
        f'<th scope="col" style="color:{ERA_COLOURS.get(label, "#9CA3AF")}40;'
        f'background:{ERA_COLOURS.get(label, "#9CA3AF")}15;'
        f'border-bottom:2px solid {ERA_COLOURS.get(label, "#9CA3AF")};">'
        f'{short}</th>'
        for _, label in COMPARE_ERAS
        for short in [ERA_SHORT.get(label, label)]
    )

    rows: list[str] = []
    for base in bases:
        cells = ""
        for prefix, label in COMPARE_ERAS:
            drawable = f"{prefix}{base}"
            exists = (PACK_DIR / f"{drawable}.png").exists()
            colour = ERA_COLOURS.get(label, "#9CA3AF")
            if exists:
                img_url = f"{RAW_BASE}/{drawable}.png"
                cells += (
                    f'<td><img class="cmp-img" src="{img_url}" '
                    f'alt="{drawable}" loading="lazy" '
                    f'title="{drawable}" '
                    f'style="border-color:{colour}33"></td>'
                )
            else:
                cells += '<td><span class="cmp-missing">N/A</span></td>'
        rows.append(
            f'<tr><th class="cmp-label" scope="row">{base}</th>{cells}</tr>'
        )

    rows_html = "\n".join(rows)
    return f"""\
<section id="compare-view" role="tabpanel" aria-labelledby="tab-compare" hidden>
  <p class="compare-note">Icons with era variants shown across all 6 design eras.</p>
  <div class="cmp-scroll">
    <table class="cmp-table">
      <caption class="sr-only">Icon artwork comparison by iOS era</caption>
      <thead>
        <tr><th class="cmp-label-th" scope="col">App</th>{col_headers}</tr>
      </thead>
      <tbody>
{rows_html}
      </tbody>
    </table>
  </div>
</section>"""


def _generate_html() -> str:
    """Return the gallery HTML string without writing or printing."""
    categories = _parse_drawables()
    counts     = _parse_component_counts()
    total_icons = sum(len(icons) for _, icons in categories)
    release_notice = _release_channel_notice()

    filter_buttons = [
        '<button class="filter-btn active" type="button" data-era="all" '
        'aria-pressed="true">All eras</button>',
    ]
    for cat, _ in categories:
        colour   = ERA_COLOURS.get(cat, "#9CA3AF")
        era_slug = cat.replace(" ", "-").replace(".", "").replace("/", "").replace("--", "-").lower()
        filter_buttons.append(
            f'<button class="filter-btn" type="button" data-era="{era_slug}" '
            f'aria-pressed="false" '
            f'style="--dot:{colour}">{cat}</button>'
        )

    sections_html: list[str] = []
    for cat, icons in categories:
        colour   = ERA_COLOURS.get(cat, "#9CA3AF")
        era_slug = cat.replace(" ", "-").replace(".", "").replace("/", "").replace("--", "-").lower()
        cards    = "\n".join(_card_html(icon, cat, counts.get(icon, 0)) for icon in icons)
        sections_html.append(
            f'<section class="era-section" data-era="{era_slug}">\n'
            f'  <h2 class="era-heading">'
            f'<span class="era-dot" style="background:{colour}"></span>{cat}'
            f'<span class="icon-count">{len(icons)}</span></h2>\n'
            f'  <div class="icon-grid" role="list">\n{cards}\n</div>\n</section>'
        )

    sections_joined = "\n\n".join(sections_html)
    filters_joined  = "\n        ".join(filter_buttons)

    return textwrap.dedent(f"""\
        <!DOCTYPE html>
        <html lang="en">
        <head>
          <meta charset="utf-8">
          <meta name="viewport" content="width=device-width, initial-scale=1">
          <meta name="description" content="Browse {total_icons} iOS-inspired icons across six design generations for Android launchers.">
          <meta name="theme-color" content="#0d1117">
          <title>iOS Icon Pack: Icon Browser</title>
          <style>
        {_css()}
          </style>
        </head>
        <body>
        <a class="skip-link" href="#browse-view">Skip to icon gallery</a>

        <header>
          <div class="header-top">
            <h1>
              iOS Icon Pack: Icon Browser
              <span class="icon-count">{total_icons} icons</span>
            </h1>
            <a class="gh-link" href="{GITHUB_URL}" target="_blank" rel="noopener">
              ↗ GitHub
            </a>
          </div>
          <p class="header-copy">Browse every icon by era. Compare generations, then request anything that's missing.</p>
          {release_notice}
          <div class="search-wrap">
            <label class="sr-only" for="search">Search icons by drawable name</label>
            <input id="search" type="search" placeholder="Search icons…" autocomplete="off" spellcheck="false" aria-controls="browse-view" aria-describedby="gallery-result-status">
            <button id="clear-search" class="clear-btn" type="button" hidden>Clear</button>
          </div>
          <p id="gallery-result-status" class="gallery-status" aria-live="polite">{total_icons} icons available.</p>
          <div class="filter-bar" role="group" aria-label="Filter icons by era">
            {filters_joined}
          </div>
        </header>

        <nav class="tab-bar" aria-label="Gallery navigation">
          <div class="tab-list" role="tablist" aria-label="Gallery views">
            <button id="tab-browse" class="tab-btn active" type="button" role="tab" data-tab="browse" aria-selected="true" aria-controls="browse-view" tabindex="0">Browse</button>
            <button id="tab-compare" class="tab-btn" type="button" role="tab" data-tab="compare" aria-selected="false" aria-controls="compare-view" tabindex="-1">Compare Eras</button>
          </div>
          <a class="tab-btn tab-link" href="requests.html">Requests ↗</a>
        </nav>

        <main>
          <div id="browse-view" role="tabpanel" aria-labelledby="tab-browse">
            {sections_joined}
            <div id="empty-msg" class="empty-state" role="status">
              <strong>No matching icons</strong>
              Try another app name or <a href="requests.html">open the request queue</a>.
            </div>
          </div>
          {_comparison_html()}
        </main>

        <footer>
          Generated from <a href="{GITHUB_URL}/blob/master/app/src/main/res/xml/drawable.xml">drawable.xml</a>
          &amp; <a href="{GITHUB_URL}/blob/master/app/src/main/res/xml/appfilter.xml">appfilter.xml</a> ·
          <a href="{GITHUB_URL}/releases/latest">Download APK</a>
        </footer>

        <script>
        {_js()}
        </script>

        </body>
        </html>
    """)


def _accessibility_errors(html: str) -> list[str]:
    """Return deterministic smoke-test failures for generated gallery semantics."""
    checks: list[tuple[str, str]] = [
        ("search input has an explicit label", '<label class="sr-only" for="search">'),
        ("search input references browse results", 'aria-controls="browse-view"'),
        ("search input references live result status", 'aria-describedby="gallery-result-status"'),
        ("result count status is visible and polite", 'id="gallery-result-status" class="gallery-status" aria-live="polite"'),
        ("clear search action is available", 'id="clear-search" class="clear-btn" type="button" hidden'),
        ("skip link is available", 'class="skip-link" href="#browse-view"'),
        ("era filters are grouped", 'class="filter-bar" role="group" aria-label="Filter icons by era"'),
        ("active era filter exposes pressed state", 'class="filter-btn active" type="button" data-era="all" aria-pressed="true"'),
        ("inactive era filters expose pressed state", 'aria-pressed="false"'),
        ("gallery views expose a tablist", 'class="tab-list" role="tablist" aria-label="Gallery views"'),
        ("browse tab controls browse panel", 'id="tab-browse" class="tab-btn active" type="button" role="tab" data-tab="browse" aria-selected="true" aria-controls="browse-view"'),
        ("compare tab controls compare panel", 'id="tab-compare" class="tab-btn" type="button" role="tab" data-tab="compare" aria-selected="false" aria-controls="compare-view"'),
        ("browse panel references selected tab", 'id="browse-view" role="tabpanel" aria-labelledby="tab-browse"'),
        ("compare panel references selected tab", 'id="compare-view" role="tabpanel" aria-labelledby="tab-compare" hidden'),
        ("icon grid exposes list semantics", 'class="icon-grid" role="list"'),
        ("empty state has recovery path", 'Try another app name or <a href="requests.html">open the request queue</a>.'),
        ("comparison table has a screen-reader caption", '<caption class="sr-only">Icon artwork comparison by iOS era</caption>'),
        ("reduced motion preference is respected", '@media (prefers-reduced-motion: reduce)'),
        ("visible keyboard focus style is present", ':focus-visible'),
        ("clear search script updates the query", "clearSearch.addEventListener('click'"),
        ("filter script syncs aria-pressed", "setAttribute('aria-pressed'"),
        ("tab script syncs aria-selected", "setAttribute('aria-selected'"),
        ("keyboard roving focus handles arrow keys", "event.key === 'ArrowRight'"),
        ("keyboard tab activation handles Enter", "event.key === 'Enter'"),
    ]
    errors = [description for description, needle in checks if needle not in html]
    if 'class="release-warning"' in html:
        warning_checks = [
            ("release warning has status semantics", 'class="release-warning" role="status" aria-live="polite"'),
            ("release warning links to release channel docs", "release-channel.json"),
        ]
        errors.extend(description for description, needle in warning_checks if needle not in html)
    return errors


def generate(dry_run: bool = False) -> str:
    html = _generate_html()
    total = sum(len(icons) for _, icons in _parse_drawables())
    if dry_run:
        print(html)
    else:
        OUT_FILE.parent.mkdir(exist_ok=True)
        OUT_FILE.write_text(html, encoding="utf-8", newline="\n")
        print(f"Wrote {OUT_FILE} ({len(html):,} bytes, {total} icons)")
    return html


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--dry-run", "-n", action="store_true",
                   help="Print HTML to stdout instead of writing docs/index.html")
    p.add_argument("--check", action="store_true",
                   help="Exit 1 if docs/index.html is stale")
    p.add_argument("--a11y-check", action="store_true",
                   help="Exit 1 if generated gallery accessibility semantics regress")
    args = p.parse_args(argv)

    if args.a11y_check:
        errors = _accessibility_errors(_generate_html())
        if errors:
            print("docs/index.html accessibility smoke check failed:", file=sys.stderr)
            for error in errors:
                print(f"  - {error}", file=sys.stderr)
            return 1
        print("docs/index.html accessibility smoke check passed.")
        return 0

    if args.check:
        generated = _generate_html()
        if not OUT_FILE.exists():
            print("docs/index.html does not exist. Run: python3 scripts/gen_gallery.py", file=sys.stderr)
            return 1
        on_disk = OUT_FILE.read_text(encoding="utf-8")
        if on_disk == generated:
            print("docs/index.html is up-to-date.")
            return 0
        print("docs/index.html is stale. Run: python3 scripts/gen_gallery.py", file=sys.stderr)
        return 1

    generate(dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    sys.exit(main())
