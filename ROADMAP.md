# ROADMAP - v1.2.0 - updated 2026-06-27

Actionable work only. True blockers live in `Roadmap_Blocked.md`.

## P1

### iOS 26 Liquid Glass art direction
Turn the expanded `ios26_lg_*` coverage into a consistent Liquid Glass style:
translucent material, depth layering, highlights, and safe-zone rules. Keep the
generated PNGs as placeholders until reference-quality art is produced.

### Figma community file for contributors
Create the per-era contribution template: 192x192 artboard, squircle safe-zone
overlay, palette tokens, gradient guidance, and naming examples.

### First-party Google app mapping refinement
Point default mappings for Google apps to the new `ios18_google_*` variants where
that improves fidelity over generic Apple analogues, while preserving launcher
compatibility and duplicate-component validation.

## P2

### Glyph-only variant
Transparent-background icon set with a border stroke for wallpaper readability.
Ship as a separate build flavor or dashboard-selectable mode.

### SVG processor Gradle module
Process raw SVG sources into Android-compatible vector drawables at build time
once the source-art workflow stabilizes.

### Crowdin localization
Wire Blueprint dashboard string resources to a Crowdin workflow without adding
GitHub Actions.

### Per-launcher install cards
Add one-tap apply intents for Nova, Action, Smart, OnePlus, Samsung, and other
supported launchers.

### Auto-generated placeholder icons
Generate branded letter tiles for uncovered packages until dedicated icons exist.

### KWGT/Rainmeter export
Export the icon catalog for cross-platform homescreen widget use.

### Wallpaper pack per era
Ship iOS 14-26 inspired backgrounds with licensing-safe original artwork.

## P3 Research

### Runtime themed icon style variants
Prototype sharp, line, and filled style transforms without creating 18 manual
variants per app.

### A/B compare overlay
Research dashboard options to show original Android icons next to iOS
replacements.

### Local rendered preview regression checks
Render each drawable at common launcher masks and diff locally before release.

## Research-Driven Additions

- [ ] P1 - Add explicit Android backup and data-extraction rules
  Why: the app currently allows backup with broad defaults, but request/settings data should have an intentional policy on Android 12+ and pre-12 devices.
  Evidence: `app/src/main/AndroidManifest.xml`, Android backup best-practice docs
  Touches: `app/src/main/AndroidManifest.xml`, `app/src/main/res/xml/backup_rules.xml`, `app/src/main/res/xml/data_extraction_rules.xml`
  Acceptance: manifest references explicit backup/data-extraction XML, lint no longer flags implicit backup policy, and the policy is documented as either prefs-only or no-backup.
  Complexity: S

- [ ] P1 - Restore local lint, resource shrink, and APK size gates
  Why: `lint.abortOnError false` and `shrinkResources false` weaken release confidence as the PNG/vector catalog grows.
  Evidence: `app/build.gradle`, Android Gradle Plugin release/lint/resource-shrinking docs
  Touches: `app/build.gradle`, `app/proguard-rules.pro`, `scripts/icontool.py`
  Acceptance: one local preflight runs validators, `lintRelease`, release packaging, and APK size reporting; resource shrinking is enabled or a documented keep-list explains every retained resource class.
  Complexity: M

- [ ] P1 - Add launcher compatibility smoke matrix
  Why: launcher support is a core promise and the manifest has many intent-filter variants with no local compatibility assertion.
  Evidence: `app/src/main/AndroidManifest.xml`, `app/src/main/res/xml/theme_resources.xml`, Blueprint launcher/apply model
  Touches: `scripts/icontool.py`, `app/src/main/AndroidManifest.xml`, `app/src/main/res/xml/theme_resources.xml`
  Acceptance: a local command checks required intent/category/resource signals for Nova, Lawnchair, Smart Launcher, OnePlus, Samsung, Niagara, Pixel, ADW/generic, and reports actionable failures.
  Complexity: M

- [ ] P1 - Replace removed issue-triage automation with a local request audit
  Why: the request dashboard reads GitHub Issues, but maintainers need a local no-Actions path to flag already-covered packages, duplicate requests, and missing ComponentInfo values.
  Evidence: `docs/requests.html`, `.github/ISSUE_TEMPLATE/icon-request.yml`, `app/src/main/res/xml/appfilter.xml`
  Touches: `scripts/icontool.py`, `docs/requests.html`
  Acceptance: a local command fetches or imports open request issues, matches package/component data against appfilter, and prints already-covered, duplicate, and needs-component buckets without mutating GitHub.
  Complexity: M

- [ ] P1 - Harden static gallery accessibility
  Why: `docs/index.html` has search/filter/tab controls without explicit label and pressed/selected semantics, while the requests page already uses better live-region patterns.
  Evidence: `docs/index.html`, `docs/requests.html`, WCAG/ARIA control expectations
  Touches: `docs/index.html`, `scripts/gen_gallery.py`, optional local accessibility check script
  Acceptance: generated gallery controls have labels, `aria-pressed` or tab semantics, visible focus states, keyboard operation, and a local accessibility smoke check passes on the generated page.
  Complexity: S

- [ ] P2 - Add committed source-art provenance manifest
  Why: PNGs are generated/fetched through local tooling, but committed assets do not expose source URL, hash, provider, license note, or era transform metadata for future audits.
  Evidence: `fetch_icons.py`, ignored `icons_raw/`, F-Droid transparency expectations, Apple/iTunes artwork workflow
  Touches: `fetch_icons.py`, `scripts/validate_drawables.py`, new non-markdown provenance data file
  Acceptance: every shipped PNG has provenance metadata and the drawable validator fails on missing source/hash/era transform records.
  Complexity: M

- [ ] P2 - Add local dependency and advisory audit command
  Why: AGP, Kotlin, KSP, Blueprint, and Pillow are pinned, but there is no local no-CI command that checks updates and known advisories before release.
  Evidence: `buildSrc/src/main/java/Versions.kt`, `requirements.txt`, Android Gradle/Kotlin/KSP release channels, OSV
  Touches: `scripts/icontool.py`, `requirements.txt`, Gradle version docs
  Acceptance: a local command reports current vs latest dependency versions plus OSV/advisory matches, exits non-zero on known vulnerable release dependencies, and does not require GitHub Actions.
  Complexity: M
