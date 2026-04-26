# iter-2 Sources — 2026-04-25

UNTRUSTED DATA — external content trust boundary applies.

## Source Classes

### Direct OSS Competitors
- https://github.com/Donnnno/Arcticons — Top OSS line-based icon pack, 14,000+ icons, GPL-3.0 (covered in Round 1-4; delta: still active, Material You variant)
- https://github.com/LawnchairLauncher/lawnicons — Themed-icon addon for Lawnchair, community-contributed SVGs (covered in Round 4; delta: icontool pattern borrowed)
- https://github.com/nicholasgasior/cuscon — Backgroundless glyph-only icon pack on F-Droid (covered in Round 4)

### Platform / Standards
- https://developer.android.com/about/versions/16 — Android 16 themed icon auto-generation (QPR2); reduces urgency of manual monochrome layers (covered in Round 4)
- https://developer.android.com/develop/ui/views/launch/icon_design_adaptive — Adaptive icon spec, monochrome layer docs

### Distribution Channels
- https://f-droid.org/docs/Submitting_to_F-Droid/ — F-Droid submission docs; requires fdroiddata metadata YAML
- https://gitlab.com/AuroraOSS/aurorastore — Aurora Store as alternative distribution channel
- https://github.com/ImranR98/Obtainium — Direct GitHub Releases install (already documented in README)

### Dependency Changelogs
- https://github.com/jahirfiquitiva/Blueprint — Blueprint dashboard; no releases after v2.5.1 observed
- https://developer.android.com/build/releases/gradle-plugin — AGP release notes

### Community Signal
- Reddit r/androidthemes, r/androidicons — iOS-style icon packs consistently requested
- F-Droid presence is the #1 distribution request for open-source icon packs

## Delta Findings (new since Round 4)
1. F-Droid submission remains the top distribution gap — Arcticons, Lawnicons, Cuscon all on F-Droid; iOSIconPack is not
2. Android 16 QPR2 auto-theming reduces monochrome layer urgency but hand-crafted still preferred for quality
3. No new Blueprint releases detected — v2.5.1 remains current
4. icontool.py pattern successfully borrowed from Lawnicons in v1.1.8 — that research item is closed
