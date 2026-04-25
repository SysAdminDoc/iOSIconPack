# ROADMAP — v1.1.9 — updated 2026-04-25 (cycle 7)

Forward-looking scope for the Android iOS-style icon pack (Blueprint dashboard, 6 eras, Kotlin/AMOLED).

## Recently Shipped

Items completed since v1.0.0 (moved here from prior ROADMAP versions):
- icontool.py CLI (v1.1.3) — single-command contributor workflow
- F-Droid metadata YAML + fastlane store listing (v1.1.3)
- GitHub Pages gallery with Browse + Compare Eras + Requests tabs (v1.1.4–v1.1.8)
- Era-switching CLI set_era.py (v1.1.4)
- Per-era APK builds in CI (v1.1.5)
- validate_drawables.py CI check (v1.1.6)
- Issue triage action with auto-comment (v1.1.7)
- Monochrome bitmap stubs for 45 icons (v1.1.7)
- fetch_icons per-era color grading + SHA-256 hash cache (v1.1.7)
- Squircle corner compliance check (v1.1.8)
- icontool stats subcommand (v1.1.8)
- Obtainium install documentation (v1.1.4)
- Niagara Launcher intent filter (v1.1.0)
- 451 appfilter component mappings (up from 214 at v1.0.0)

## Now

Items actively in progress or ready to start this cycle.

### P0: Expand icon coverage to 50+ per era (authenticity-first)
Biggest gap vs competitors (Arcticons: 14,559; Lawnicons: 7,581; Cuscon: 5,000+; Simply Adaptive: 25,000+). Currently ~22 icons per era average. Target: 50+ unique assets per era for the top Play Store apps. Each new icon must be sourced from the correct iOS generation — no cross-era reuse. This preserves the charter's "era authenticity over icon count" by growing breadth without diluting per-era fidelity. `fetch_icons.py --only` supports incremental additions; batch by era.
- **Impact**: 5 | **Effort**: 4 | **Risk**: Low — authenticity gate is the per-era color grading in fetch_icons.py
- Sources: [Arcticons](https://github.com/Donnnno/Arcticons), [materialos appfilter](https://github.com/materialos/android-icon-pack)

### P1: Submit to F-Droid fdroiddata repo
Metadata YAML and fastlane listing are ready. Need to open a merge request against [fdroiddata](https://gitlab.com/fdroiddata/fdroiddata). Arcticons, Lawnicons, and Cuscon are all on F-Droid with high download counts. Reproducible build, no Play Store dependencies. **Risk update (April 2026):** Google's sideloading verification rules (September 2026 in Brazil/Indonesia/Singapore/Thailand, global 2027+) threaten F-Droid's build-and-sign model. F-Droid published an [open letter](https://f-droid.org/2026/02/24/open-letter-opposing-developer-verification.html) opposing verification; Keep Android Open coalition (56 signatories, EFF/FSF/Tor) filed complaints in 20+ jurisdictions. Submit now while the window is open. Obtainium (direct GitHub Releases) is unaffected and serves as distribution hedge.
- **Impact**: 5 | **Effort**: 1 | **Risk**: Low → Medium (regulatory)
- Sources: [F-Droid submission docs](https://f-droid.org/docs/Submitting_to_F-Droid/), [Google sideloading rules](https://android.gadgethacks.com/news/googles-new-android-sideloading-rules-start-august-2026/)

### P1: IzzyOnDroid listing
Similar to F-Droid metadata. Active community that tracks GitHub-native releases. Minimal additional effort once F-Droid metadata exists.
- **Impact**: 3 | **Effort**: 1 | **Risk**: Low
- Sources: [IzzyOnDroid](https://apt.izzysoft.de/fdroid/)

### P0: Hand-crafted monochrome vectors for top 25 icons
Replace bitmap monochrome stubs with proper single-color vector paths. **Android 16 QPR2 mandatory themed icon support (Oct 15, 2026 deadline)** means quality monochrome layers are now a competitive requirement. System auto-generates themed icons (3 modes: Predetermined, Minimum, Create) but hand-crafted quality is noticeably better. Google DDA Section 5.3 now requires developers to grant users icon color modification permission. Priority: 25 third-party icons first (most visibility), then 19 stock Apple icons.
- **Impact**: 5 | **Effort**: 3 | **Risk**: Low — deadline is Oct 2026
- Sources: [Android 16 themed icons](https://developer.android.com/about/versions/16), [adaptive icon spec](https://developer.android.com/develop/ui/views/launch/icon_design_adaptive), [no opt-out](https://9to5google.com/2025/09/16/android-16-auto-themed-icons-apps-cant-opt-out/), [DDA theming agreement](https://www.androidauthority.com/google-play-icon-theming-agreement-3597899/)

### P1: iOS 26 Liquid Glass era icon art direction
iOS 26 introduces Liquid Glass — the biggest visual overhaul since iOS 7. Icons use layered compositions with blur, translucency, shadows, and specular highlights across 6 appearance modes (Default, Dark, Clear Light, Clear Dark, Tinted Light, Tinted Dark). Apple's new Icon Composer tool (Xcode 26) supports multi-layer icon authoring. The project's `ios26_lg_*` naming convention is already established; this task defines the art direction: translucent glass material, depth layering, and safe-zone compliance for the Liquid Glass era. Deliverable: style guide doc + 10 reference icons.
- **Impact**: 5 | **Effort**: 3 | **Risk**: Low — WWDC 2025 shipped, public spec available
- Sources: [Liquid Glass guide](https://getskyscraper.com/blog/liquid-glass-app-icon-design-ios-26-guide), [Apple Liquid Glass](https://www.mobileaction.co/blog/apple-liquid-glass-design/), [iOS 26 overview](https://www.macrumors.com/guide/ios-26-liquid-glass/)

## Next

Scheduled for near-term releases.

### P1: Material You dynamic-color per era
Render era-appropriate tints from the system wallpaper palette. Arcticons ships this as a Material You adaptive variant. Implementation: runtime tint transform on the foreground layer, not separate drawable sets.
- **Impact**: 4 | **Effort**: 3 | **Risk**: Low
- Sources: [Arcticons Material You](https://github.com/Donnnno/Arcticons)

### P1: Figma community file for contributors
Per-era style guide: squircle path spec, corner-radius formula, color palette, gradient angle, safe-zone overlay, contribution template (192x192 artboard). Lawnicons credits their Figma file with dramatically faster contributor onboarding.
- **Impact**: 3 | **Effort**: 2 | **Risk**: Low
- Sources: [Lawnicons Figma](https://www.figma.com/community/file/1544976260626797886)

### P1: First-party Google apps parity across all 6 eras
One of the bigger coverage gaps. Google Suite (Gmail, Maps, Calendar, Drive, Docs, Sheets, Photos, Meet, etc.) should have era-specific icons for all 6 eras, not just iOS 18.
- **Impact**: 4 | **Effort**: 3 | **Risk**: Low

## Later

Acknowledged, deferred. Depends on Now/Next items or higher effort.

### P0: Per-app era picker (blocked)
Blueprint UI for choosing which iOS era to apply per individual app. Currently assumes one era globally. Requires Blueprint fork or upstream PR. `set_era.py` is a CLI workaround but not user-facing.
- Blocked on: Blueprint fork
- Sources: [Blueprint](https://github.com/jahirfiquitiva/Blueprint)

### P1: Shape-mask preview in dashboard
Preview icons rendered in different launcher mask shapes (square, rounded, squircle, teardrop, circle, cylinder) before applying. Reference: Launcher3 IconShape.java.
- Blocked on: Blueprint fork
- Sources: [Launcher3](https://github.com/amirzaidi/Launcher3)

### P2: Glyph-only (backgroundless) variant
Transparent-background icon set with 4dp border stroke for wallpaper readability. Ship as separate build flavor (`glyph` vs `squircle`) or dashboard toggle. Cuscon's F-Droid popularity (~5000 icons) confirms the audience.
- Sources: [Cuscon](https://github.com/nicholasgasior/cuscon)

### P2: SVG processor Gradle module
Kotlin module that processes raw SVGs into Android-compatible vector drawables at build time. Worth adapting from Lawnicons once icon count exceeds ~500.
- Sources: [Lawnicons svg-processor](https://github.com/LawnchairLauncher/lawnicons/tree/develop/svg-processor)

### P2: Crowdin localization
Wire Crowdin to Blueprint dashboard string resources for automatic translation PRs. Low effort, high international visibility.
- Sources: [Lawnicons Crowdin](https://github.com/LawnchairLauncher/lawnicons)

### P2: Per-launcher install cards
One-tap apply intents for Nova/Action/Smart/OnePlus/Samsung instead of generic docs. Pattern from Ultimate_Theme_UI_Template.
- Sources: [Ultimate Theme UI Template](https://github.com/designrifts/Ultimate_Theme_UI_Template)

### P2: Auto-generated placeholder icons
Colored letter tile matching the app's brand color for uncovered packages. Fills gaps until real icons are added.

### P2: KWGT/Rainmeter export
Cross-platform homescreen widget icon sets. Niche but requested.

### P2: Wallpaper pack per era
Stock iOS 14-26 inspired backgrounds (AI-generated alternatives for licensing safety).

## Under Consideration

Not committed, not rejected. Needs more research or validation.

### Themed icon style variants (sharp/line/filled)
6 eras x 3 styles = 18 variants per app = untenable manually. Only viable as a runtime transform (tint + opacity). Needs: proof-of-concept runtime transform that doesn't degrade icon quality.

### A/B compare overlay
Show original Android icon next to the iOS replacement in the dashboard. Needs: Blueprint fork for custom UI.

### CI-rendered previews per era
Render each drawable at 5 stock masks, diff against last release, flag shape-clipping regressions. Needs: headless Android rendering in CI.

### Play Store listing
Requires rotating away from committed dev keystore. Needs: dedicated signing key + Play Console account.

## Rejected (for future reference)

### IPA extraction mode for fetch_icons.py
Legal complexity of extracting from Apple IPAs. iTunes Search API already provides the real artwork at sufficient quality. The tooling exists (ipatool) but the legal risk isn't worth the marginal quality gain.

## Appendix — Sources

### Direct OSS Competitors
- https://github.com/Arcticons-Team/Arcticons — v14.5.5, 14,559 icons, GPL-3.0, Material You + Day/Night flavors, wallpapers, category tabs
- https://github.com/LawnchairLauncher/lawnicons — v2.17.1, ~7,581 icons, Material 3 Expressive, Smart Launcher support
- https://github.com/nicholasgasior/cuscon — Backgroundless glyph-only icon pack on F-Droid, 5,000+ icons

### Commercial Competitors
- Delta Icon Pack — Paid Play Store, single iOS generation at a time
- Simply Adaptive Icon Pack — 25,000+ icons, 45,000+ themed apps, Material You dynamic shapes
- Lena Adaptive (One4Studio) — 4,729 adaptive icons, dynamic system color transform
- Graphite Icon Pack v3.6.7 — Geometric language, OLED dark mode, professional aesthetic

### Platform / Standards
- https://developer.android.com/about/versions/16 — Android 16 QPR2 auto-theming for themed icons (mandatory, no opt-out)
- https://developer.android.com/develop/ui/views/launch/icon_design_adaptive — Adaptive icon spec, monochrome layer docs
- https://www.androidauthority.com/google-play-icon-theming-agreement-3597899/ — Google DDA Section 5.3 icon theming agreement
- https://www.androidauthority.com/android-17-3561251/ — Android 17 "Cinnamon Bun", June/July 2026
- https://9to5google.com/2025/09/16/android-16-auto-themed-icons-apps-cant-opt-out/ — Auto-themed icons: no developer opt-out

### iOS 26 / Liquid Glass
- https://getskyscraper.com/blog/liquid-glass-app-icon-design-ios-26-guide — Complete Liquid Glass icon design guide
- https://www.mobileaction.co/blog/apple-liquid-glass-design/ — Apple Liquid Glass design + Icon Composer tool
- https://www.macrumors.com/guide/ios-26-liquid-glass/ — iOS 26 Liquid Glass overview

### Reference Implementations
- https://github.com/jahirfiquitiva/Blueprint — Blueprint dashboard v2.5.1 (CC BY-SA 4.0)
- https://github.com/materialos/android-icon-pack — Real-world large appfilter reference
- https://github.com/amirzaidi/Launcher3 — Rootless Pixel Launcher, 6 stock icon shapes
- https://github.com/designrifts/Ultimate_Theme_UI_Template — Multi-launcher install cards pattern
- https://github.com/rektdeckard/iconpacktools — drawable.xml + icon-pack.xml generator
- https://github.com/Snoy-Kuo/android_adaptive_icon_example — Adaptive icon mask-verified pipeline

### Distribution
- https://f-droid.org/docs/Submitting_to_F-Droid/ — F-Droid submission docs
- https://apt.izzysoft.de/fdroid/ — IzzyOnDroid alternative F-Droid repo
- https://github.com/ImranR98/Obtainium — Direct GitHub Releases install
- https://f-droid.org/2026/02/24/open-letter-opposing-developer-verification.html — F-Droid open letter opposing sideloading verification
- https://android.gadgethacks.com/news/googles-new-android-sideloading-rules-start-august-2026/ — Google sideloading rules timeline

### Community / Research
- https://github.com/topics/android-icon-pack — Topic hub for appfilter strategies
- https://osmanonurkoc.github.io/AdaptiveIconsShowcase/ — Showcase site pattern
- https://www.figma.com/community/file/1544976260626797886 — Lawnicons Figma community file
