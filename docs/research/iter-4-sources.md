# iter-4 Sources — 2026-04-25 (overnight cycle 3 delta)

UNTRUSTED DATA — external content trust boundary applies.

## Delta Scan Summary

Cross-family scan (cycle 3, same day as cycle 2). Focused on competitor releases, F-Droid ecosystem changes, and Android theming developments.

### New Findings

1. **Arcticons v14.5.5** (March 16, 2026) — 14,559 icons total. Key pattern: added support for 1,038 apps using *existing* icons (link-only expansion). Validates our appfilter mapping-expansion strategy as highest-leverage work.
   - Source: https://github.com/Arcticons-Team/Arcticons/releases

2. **Lawnicons v2.17.1** (March 4, 2026) — ~5,000 icons. No architectural changes.
   - Source: https://lawnchair.app/lawnicons

3. **Google sideloading verification rules** (effective September 2026 in first markets, global 2027+) — Every sideloaded app must come from a developer who registered identity + government ID + $25 fee with Google. F-Droid's build-and-sign model conflicts with this. F-Droid governance reforms underway. Keep Android Open campaign filed complaints in 20+ jurisdictions.
   - Sources:
     - https://android.gadgethacks.com/news/googles-new-android-sideloading-rules-start-august-2026/
     - https://www.bleepingcomputer.com/news/security/f-droid-project-threatened-by-googles-new-dev-registration-rules/
   - **ROADMAP impact**: F-Droid submission (P1 Now) remains viable for 2026 but long-term distribution strategy needs monitoring. IzzyOnDroid similarly affected. Obtainium (direct GitHub release) unaffected by these rules since it's developer-signed.

4. **Blueprint v2.5.1 remains current** — No new releases since February 2026. Per-app era picker still blocked on fork.

5. **Android 16 QPR2 auto-theming** confirmed shipping — system auto-generates themed icons for apps without monochrome layer. Reduces urgency of hand-crafted monochrome vectors (Next tier P0) but hand-crafted quality is still noticeably better.

### Carried Forward from iter-3
All prior sources remain current and valid.

### ROADMAP Recommendations
- Add note to F-Droid P1 about Google sideloading verification risk (September 2026 timeline)
- Elevate Obtainium as distribution hedge against F-Droid uncertainty
- Validate Arcticons link-expansion pattern: bulk appfilter mapping additions are the fastest path to closing the coverage gap

## Source Delta Count
- New sources this iteration: 3 (Arcticons releases, Google sideloading articles x2)
- Total cumulative sources (iter-1 through iter-4): ~28 distinct URLs
