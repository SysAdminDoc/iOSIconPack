#!/usr/bin/env python3
"""gen_gallery.py — generate docs/index.html icon browser for GitHub Pages.

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
    "iOS 26 - Liquid Glass":  "#67E8F9",
    "Third Party":            "#9CA3AF",
}

ERA_SHORT: dict[str, str] = {
    "iOS 18":                "18",
    "iOS 17":                "17",
    "iOS 16":                "16",
    "iOS 15":                "15",
    "iOS 14":                "14",
    "iOS 26 - Liquid Glass": "26",
    "Third Party":           "TP",
}

# Prefix → category title mapping (for comparison grid)
PREFIX_TO_ERA: dict[str, str] = {
    "ios18_":    "iOS 18",
    "ios17_":    "iOS 17",
    "ios16_":    "iOS 16",
    "ios15_":    "iOS 15",
    "ios14_":    "iOS 14",
    "ios26_lg_": "iOS 26 - Liquid Glass",
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

    # tp_* icons are not in drawable.xml — collect from appfilter instead
    af_text = APPFILTER_XML.read_text(encoding="utf-8")
    in_drawable: set[str] = {d for _, lst in categories for d in lst}
    tp_icons: list[str] = sorted({
        m.group(1)
        for m in re.finditer(r'drawable="(tp_[^"]+)"', af_text)
    })
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


# ---------------------------------------------------------------------------
# HTML generation
# ---------------------------------------------------------------------------

def _css() -> str:
    return textwrap.dedent("""
        *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

        :root {
            --bg:       #0d1117;
            --surface:  #161b22;
            --border:   #30363d;
            --text:     #e6edf3;
            --muted:    #8b949e;
            --accent:   #58A6FF;
        }

        html { scroll-behavior: smooth; }

        body {
            background: var(--bg);
            color: var(--text);
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            min-height: 100vh;
        }

        /* Header */
        header {
            background: var(--surface);
            border-bottom: 1px solid var(--border);
            padding: 1.25rem 1.5rem;
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
        }

        .icon-count {
            font-size: 0.75rem;
            color: var(--muted);
            background: var(--bg);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 0.1rem 0.55rem;
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
        input:focus-visible {
            outline: 2px solid var(--accent);
            outline-offset: 2px;
        }

        /* Search */
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

        /* Era filter */
        .filter-bar {
            display: flex;
            gap: 0.4rem;
            flex-wrap: wrap;
        }

        .filter-btn {
            background: var(--bg);
            border: 1px solid var(--border);
            border-radius: 6px;
            color: var(--muted);
            cursor: pointer;
            font-size: 0.75rem;
            padding: 0.25rem 0.65rem;
            transition: all 0.15s;
        }
        .filter-btn:hover { border-color: var(--accent); color: var(--text); }
        .filter-btn.active,
        .filter-btn[aria-pressed="true"] {
            border-color: var(--accent);
            color: var(--accent);
            background: rgba(88,166,255,0.1);
        }

        /* Main */
        main {
            padding: 1.5rem;
            max-width: 1400px;
            margin: 0 auto;
        }

        /* Era section */
        .era-section { margin-bottom: 2.5rem; }
        .era-section[hidden] { display: none; }

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
            border-radius: 50%;
        }

        /* Icon grid */
        .icon-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(100px, 1fr));
            gap: 0.75rem;
        }

        /* Icon card */
        .icon-card {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 10px;
            cursor: default;
            display: flex;
            flex-direction: column;
            align-items: center;
            padding: 0.75rem 0.4rem 0.6rem;
            transition: border-color 0.15s, transform 0.15s;
            position: relative;
        }
        .icon-card:hover {
            border-color: var(--accent);
            transform: translateY(-2px);
        }
        .icon-card[hidden] { display: none !important; }

        .icon-img {
            width: 56px;
            height: 56px;
            object-fit: contain;
            border-radius: 12.5%;
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

        /* Empty state */
        #empty-msg {
            display: none;
            color: var(--muted);
            text-align: center;
            padding: 3rem 0;
            font-size: 0.9rem;
        }

        /* Footer */
        footer {
            border-top: 1px solid var(--border);
            color: var(--muted);
            font-size: 0.75rem;
            padding: 1rem 1.5rem;
            text-align: center;
        }
        footer a { color: var(--accent); text-decoration: none; }

        /* Tab nav */
        .tab-bar {
            display: flex;
            align-items: stretch;
            gap: 0.25rem;
            border-bottom: 1px solid var(--border);
            padding: 0 1.5rem;
            background: var(--surface);
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
            transition: color 0.15s, border-color 0.15s;
        }
        .tab-btn:hover { color: var(--text); }
        .tab-btn.active,
        .tab-btn[aria-selected="true"] {
            color: var(--accent);
            border-bottom-color: var(--accent);
        }

        /* Compare grid */
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
            color: var(--muted);
            white-space: nowrap;
            padding-right: 1rem;
        }
        .cmp-img {
            width: 44px;
            height: 44px;
            border-radius: 11px;
            border: 1px solid transparent;
            object-fit: contain;
            display: block;
            margin: 0 auto;
            transition: transform 0.15s;
        }
        .cmp-img:hover { transform: scale(1.15); }
        .cmp-missing { color: var(--border); font-size: 0.9rem; }
        #compare-view { padding-top: 0.5rem; }
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
                if (resultStatus) {
                    const noun = visible === 1 ? 'icon' : 'icons';
                    resultStatus.textContent = `Showing ${visible} ${noun}.`;
                }
            }

            search.addEventListener('input', update);

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

    comp_html = f'<span class="comp-badge">{comp_str}</span>' if comp_str else ""

    return (
        f'<div class="icon-card" data-name="{name.lower()}" data-era="{era_slug}">\n'
        f'  <span class="era-badge" style="{badge_style}">{badge_label}</span>\n'
        f'  <img class="icon-img" src="{img_url}" alt="{name}" loading="lazy">\n'
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
        f'<th style="color:{ERA_COLOURS.get(label, "#9CA3AF")}40;'
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
                cells += '<td><span class="cmp-missing">—</span></td>'
        rows.append(
            f'<tr><td class="cmp-label">{base}</td>{cells}</tr>'
        )

    rows_html = "\n".join(rows)
    return f"""\
<section id="compare-view" role="tabpanel" aria-labelledby="tab-compare" hidden>
  <p class="compare-note">Icons with era variants shown across all 6 design eras.</p>
  <div class="cmp-scroll">
    <table class="cmp-table">
      <thead>
        <tr><th class="cmp-label-th">App</th>{col_headers}</tr>
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
            f'  <div class="icon-grid">\n{cards}\n</div>\n</section>'
        )

    sections_joined = "\n\n".join(sections_html)
    filters_joined  = "\n        ".join(filter_buttons)

    return textwrap.dedent(f"""\
        <!DOCTYPE html>
        <html lang="en">
        <head>
          <meta charset="utf-8">
          <meta name="viewport" content="width=device-width, initial-scale=1">
          <meta name="description" content="iOS Icon Pack — {total_icons} icons across 6 iOS design generations for Android launchers">
          <meta name="theme-color" content="#0d1117">
          <title>iOS Icon Pack — Icon Browser</title>
          <style>
        {_css()}
          </style>
        </head>
        <body>

        <header>
          <div class="header-top">
            <h1>
              iOS Icon Pack — Icon Browser
              <span class="icon-count">{total_icons} icons</span>
            </h1>
            <a class="gh-link" href="{GITHUB_URL}" target="_blank" rel="noopener">
              ↗ GitHub
            </a>
          </div>
          <div class="search-wrap">
            <label class="sr-only" for="search">Search icons by drawable name</label>
            <input id="search" type="search" placeholder="Search icons…" autocomplete="off" spellcheck="false" aria-controls="browse-view" aria-describedby="gallery-result-status">
          </div>
          <p id="gallery-result-status" class="sr-only" aria-live="polite">{total_icons} icons available.</p>
          <div class="filter-bar" role="group" aria-label="Filter icons by era">
            {filters_joined}
          </div>
        </header>

        <nav class="tab-bar" aria-label="Gallery navigation">
          <div class="tab-list" role="tablist" aria-label="Gallery views">
            <button id="tab-browse" class="tab-btn active" type="button" role="tab" data-tab="browse" aria-selected="true" aria-controls="browse-view" tabindex="0">Browse</button>
            <button id="tab-compare" class="tab-btn" type="button" role="tab" data-tab="compare" aria-selected="false" aria-controls="compare-view" tabindex="-1">Compare Eras</button>
          </div>
          <a class="tab-btn" href="requests.html" style="text-decoration:none">Requests ↗</a>
        </nav>

        <main>
          <div id="browse-view" role="tabpanel" aria-labelledby="tab-browse">
            {sections_joined}
            <p id="empty-msg" role="status">No icons match your search.</p>
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
        ("result count status is a polite live region", 'id="gallery-result-status" class="sr-only" aria-live="polite"'),
        ("era filters are grouped", 'class="filter-bar" role="group" aria-label="Filter icons by era"'),
        ("active era filter exposes pressed state", 'class="filter-btn active" type="button" data-era="all" aria-pressed="true"'),
        ("inactive era filters expose pressed state", 'aria-pressed="false"'),
        ("gallery views expose a tablist", 'class="tab-list" role="tablist" aria-label="Gallery views"'),
        ("browse tab controls browse panel", 'id="tab-browse" class="tab-btn active" type="button" role="tab" data-tab="browse" aria-selected="true" aria-controls="browse-view"'),
        ("compare tab controls compare panel", 'id="tab-compare" class="tab-btn" type="button" role="tab" data-tab="compare" aria-selected="false" aria-controls="compare-view"'),
        ("browse panel references selected tab", 'id="browse-view" role="tabpanel" aria-labelledby="tab-browse"'),
        ("compare panel references selected tab", 'id="compare-view" role="tabpanel" aria-labelledby="tab-compare" hidden'),
        ("visible keyboard focus style is present", ':focus-visible'),
        ("filter script syncs aria-pressed", "setAttribute('aria-pressed'"),
        ("tab script syncs aria-selected", "setAttribute('aria-selected'"),
        ("keyboard roving focus handles arrow keys", "event.key === 'ArrowRight'"),
        ("keyboard tab activation handles Enter", "event.key === 'Enter'"),
    ]
    return [description for description, needle in checks if needle not in html]


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
            print("docs/index.html does not exist — run: python3 scripts/gen_gallery.py", file=sys.stderr)
            return 1
        on_disk = OUT_FILE.read_text(encoding="utf-8")
        if on_disk == generated:
            print("docs/index.html is up-to-date.")
            return 0
        print("docs/index.html is STALE — run: python3 scripts/gen_gallery.py", file=sys.stderr)
        return 1

    generate(dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    sys.exit(main())
