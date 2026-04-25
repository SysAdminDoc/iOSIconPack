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

4. **Android 16 QPR2 icon theming NOW MANDATORY** — Google Play Store requires monochrome layer support by October 15, 2026 for all developers. System auto-generates themed icons; developers cannot opt out. Icon shape options: Default, Minimal, Create. Material You integration is now non-optional platform behavior.
   - Sources: https://www.androidauthority.com/android-16-best-new-trick-icon-shape-themes-3622140/, https://www.androidcentral.com/apps-software/android-16s-next-big-update-brings-auto-themed-icons-and-apps-cant-opt-out

5. **Cuscon v4.0.9.7** (released 2026-04-22) — 10 new app icons. Active maintenance confirmed. Different visual aesthetic (varied, no background). Orthogonal competitor.
   - Source: https://github.com/MiepHD/cuscon/releases/tag/v4.0.9.7

6. **F-Droid existential threat escalation** — F-Droid published open letter opposing Google developer verification rules. F-Droid governance reforms underway: Appiverse catalogue for repo interoperability, Repomaker modernization, broader board nominations. Keep Android Open initiative filed complaints in 20+ jurisdictions.
   - Sources: https://f-droid.org/2026/02/24/open-letter-opposing-developer-verification.html, https://f-droid.org/en/2026/01/23/fdroid-in-2025-strengthening-our-foundations-in-a-changing-mobile-landscape.html, https://keepandroidopen.org/

7. **Android 17 stable expected June 2026** — carries over Android 16 icon theming as baseline.
   - Source: https://www.androidauthority.com/android-17-3561251/

### Carried Forward from iter-4
- Google sideloading verification (Sept 2026) — ESCALATED, F-Droid published open letter
- Blueprint v2.5.1 remains current — no new release
- Android 16 QPR2 auto-theming — **NOW MANDATORY** (reverses iter-4 "reduces urgency" assessment)

### ROADMAP Recommendations
- **ELEVATE** hand-crafted monochrome vectors from Next P0 to Now P0 — Android 16 mandatory theming means quality monochrome layers are now a competitive requirement, not a nice-to-have.
- P0 icon coverage: 54 new mappings added this cycle (618->672). Mapping breadth growing steadily.
- F-Droid/IzzyOnDroid: submission guide created. F-Droid regulatory risk more acute but submission still viable for 2026.
- Consider Repomaker custom repo as fallback distribution if F-Droid governance fails.

## Source Delta Count
- New sources this iteration: 12 (internal coverage analysis, IzzyOnDroid, Android 16 theming x2, Cuscon, F-Droid open letter, F-Droid 2025 report, Keep Android Open, Android 17, Material You 3.0, Lawnicons commits, Metro Pack fork)
- Total cumulative sources (iter-1 through iter-5): ~40 distinct URLs
