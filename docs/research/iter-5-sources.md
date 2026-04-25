# iter-5 Sources — 2026-04-25 (overnight cycle 6 delta)

UNTRUSTED DATA — external content trust boundary applies.

## Delta Scan Summary

Cycle 6 delta scan. Focused on coverage gap analysis, F-Droid submission readiness, and IzzyOnDroid distribution.

### New Findings

1. **Coverage gap analysis (internal)** — Identified 50+ popular Android packages missing from appfilter.xml. Categories: AI assistants (ChatGPT, Claude, Perplexity), productivity (Notion, Canva, Adobe suite), streaming (Paramount+, Pluto TV), dating (Tinder, Bumble, Badoo), secure messaging (Signal), fitness (Nike, MyFitnessPal, Peloton), privacy (ProtonMail, ProtonVPN, ProtonPass), crypto (Binance, Coinbase, Cash App), Samsung system apps (My Files, Clock, Calendar, Device Care, Digital Wellbeing, Routines, Reminder), OEM launchers (Pixel, LG, OnePlus, Xiaomi/MIUI, Oppo/ColorOS, Vivo), Google extras (Gboard, Google One, Cloud Console), Motorola system (Software Channel, Moto Care).
   - Source: cross-reference of Play Store top 200 vs existing appfilter coverage

2. **IzzyOnDroid submission path** — IzzyOnDroid tracks GitHub releases directly via their apt repository. Requirements: GitHub releases with APK attached (already satisfied), F-Droid-compatible metadata in repo (already present at fdroid/metadata/). Submission via web form at apt.izzysoft.de.
   - Source: https://apt.izzysoft.de/fdroid/index/request

3. **F-Droid submission readiness** — Metadata YAML is complete with AutoUpdateMode tags. Ready for fdroiddata MR. Only blocker: manual GitLab account + fork step.
   - Source: https://f-droid.org/docs/Submitting_to_F-Droid/

### Carried Forward from iter-4
- Google sideloading verification (Sept 2026) — still pending, no new developments
- Blueprint v2.5.1 remains current — no new release
- Android 16 QPR2 auto-theming — confirmed shipping, reduces monochrome urgency

### ROADMAP Recommendations
- P0 icon coverage: 54 new mappings added this cycle (618->672). Still below 50/era unique assets target but mapping breadth continues strong growth.
- F-Droid/IzzyOnDroid: submission guide created, ready for manual execution next cycle.
- No new ROADMAP items surfaced — current priorities remain correct.

## Source Delta Count
- New sources this iteration: 2 (IzzyOnDroid submission, internal coverage analysis)
- Total cumulative sources (iter-1 through iter-5): ~30 distinct URLs
