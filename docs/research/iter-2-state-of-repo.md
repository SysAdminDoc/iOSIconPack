# State of the Repo — iter-2 (2026-04-25)

## Identity
iOS-style icon pack for Android. 6 iOS eras (14–18 + 26 Liquid Glass) in one APK. Blueprint v2.5.1 dashboard. Free & open-source (MIT).

## Quantitative snapshot
- **Icons**: 135 PNGs in `drawable-xxxhdpi/` (192x192, fetched via iTunes Search API)
- **Appfilter entries**: 451 `<item>` mappings across Google/Samsung/Xiaomi/OnePlus/Huawei/etc
- **Monochrome stubs**: 90 XML files (45 mono + 45 themed) — bitmap placeholders, not hand-crafted vectors
- **Scripts**: 7 (`gen_gallery.py`, `gen_monochrome.py`, `icontool.py`, `set_era.py`, `validate_appfilter.py`, `validate_drawables.py`, `fetch_icons.py` at project root)
- **CI workflows**: 3 (`build.yml` — APK+AAB, `ci.yml` — validators, `issue-triage.yml` — auto-comment on icon requests)
- **Version**: v1.1.8 (versionCode=10)
- **Build**: Gradle 8.13, AGP 8.12.0, Kotlin 2.2.21, KSP 2.3.4
- **minSdk**: 26, **targetSdk**: 36

## What works
- Blueprint dashboard with AMOLED dark theme, icon browsing, per-era categories
- Adaptive launcher icon with monochrome themed layer
- `icontool.py` CLI: add/link/remove/rebuild/stats/check subcommands
- `fetch_icons.py`: iTunes API fetch, per-era color grading, SHA-256 hash cache
- GitHub Pages gallery with Browse + Compare Eras tabs
- CI: appfilter validation, drawable validation (size/format/squircle check), issue triage bot
- Signed release pipeline (APK + AAB via base64-encoded keystore secret)

## What's incomplete / stubbed
- Monochrome layers are bitmap stubs pointing at existing PNGs — need hand-crafted or runtime-tinted vectors
- Only 135 unique icon assets across 6 eras (~22 per era average) — target is 100+ per era
- No F-Droid / IzzyOnDroid distribution
- No per-app era picker (requires Blueprint fork)
- No shape-mask preview
- No glyph-only (backgroundless) variant

## Debt markers
- Zero `TODO`/`FIXME`/`HACK`/`XXX` in source
- CLAUDE.md version history says 247 appfilter entries but actual count is 451 — doc drift

## Philosophy / charter
- Era authenticity over icon count — each era should look distinctly like its iOS generation
- Free, open-source, no billing/license checks
- Dark-first UI (AMOLED, iOS blue accent)
- Blueprint upstream compatibility (don't fork unless necessary)
- Standalone works on any launcher (not Lawnchair-specific like Lawnicons)
