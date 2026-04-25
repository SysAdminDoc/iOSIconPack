# iOS Icon Pack Roadmap

Forward-looking scope for the Android iOS-style icon pack (Blueprint dashboard, 6 eras, Kotlin/AMOLED).

## Planned Features

### Icon Coverage
- Expand each iOS era from 20 to 100+ app icons (Blueprint appfilter updates for top-1000 Play Store apps per-era).
- Auto-generated placeholder icons (colored letter tile matching the app's brand color) for uncovered packages.
- Themed icons for each era matching the Android 13+ dynamic theming API.
- First-party Google apps parity across all 6 eras (one of the bigger coverage gaps).

### Mix & Match Engine
- Per-app era picker surfaced in the Blueprint request UI (currently the app assumes one era applied globally).
- Preview pane that renders the home screen with the selected era before applying.
- Random-era mode for novelty.
- A/B compare overlay that shows original icon next to the iOS replacement.

### Build & Asset Pipeline
- `fetch_icons.py` improvements: extract icons directly from IPA files (open source, no scraping) instead of web sources.
- Vector drawable validator that fails the build when a `<path>` is malformed.
- Automated squircle-compliance check: every icon must match the iOS `continuous` corner-radius curve within tolerance.
- Asset optimization pass: strip metadata, deduplicate paths, verify file sizes under a budget.

### Launcher Integration
- First-class Niagara Launcher support (currently missing from the supported list).
- Dynamic-color integration with Material You: render era-appropriate tints from the system wallpaper.
- Adaptive-icon mode with per-era background colors.
- iOS-style dock emulation guide for each supported launcher.

## Competitive Research
- **CandyCons Unwrapped / Pixel Icon Pack / Whicons** — Blueprint dashboard reference; iOSIconPack already uses Blueprint v2.5.1, stay on the upstream train.
- **Delta Icon Pack (iOS 16/17 ports)** — Play Store competitor; iOSIconPack wins on era breadth (14 through 26 Liquid Glass).
- **Lawnicons** — F-Droid / open-source icon pack for Lawnchair; worth collaborating via shared appfilter format.
- **Icon-request bot (Telegram)** — several packs use a bot to accept community requests; consider a GitHub Issues template instead for traceability.

## Nice-to-Haves
- Export as KWGT/Rainmeter icon sets for cross-platform homescreen customizers.
- Publish an iOS-era "widget skin" for the top Android widget frameworks (KWGT, KLWP).
- Community-submitted Liquid Glass era icons with a review workflow.
- Wallpaper pack per era matching the stock iOS 14-26 default backgrounds (licensing permitting; use AI-generated "inspired-by" alternatives otherwise).
- Companion Play Store listing localizations (10+ languages).
- Automated test that renders every icon at 48dp/72dp/96dp/144dp/192dp and asserts no aliasing.

## Open-Source Research (Round 2)

### Related OSS Projects
- https://github.com/Donnnno/Arcticons — Arcticons, top OSS line-based icon pack; Material You adaptive variant; canonical reference for dashboard + appfilter management at scale
- https://github.com/osmanonurkoc/papirusadaptive — Papirus Adaptive (Linux Papirus port), clean example of adaptive mask handling across OEM launcher shapes
- https://github.com/japalekhin/adaptive-icons-guide — PSD template + docs on adaptive-icon masks (square, rounded square, squircle, teardrop, circle) — CC BY-ND 4.0
- https://github.com/amirzaidi/Launcher3 — Rootless Pixel Launcher (Launcher3 fork) — reference icon-shape options (squircle/square/rounded/circle/teardrop/cylinder) plus adaptive-icon-pack loader
- https://github.com/designrifts/Ultimate_Theme_UI_Template — Open-source icon pack + theme template with multi-launcher cards (Nova, Action, Apex, ADWEX, Smart, Go)
- https://github.com/topics/android-icon-pack — topic hub — good for browsing appfilter strategies across dozens of packs
- https://osmanonurkoc.github.io/AdaptiveIconsShowcase/ — Showcase site pattern (screenshots, install instructions per launcher) — good template for the project's own landing page

### Features to Borrow
- Material You dynamic-color variant per era (Arcticons) — lets users tint iOS 18/26 icons to their wallpaper while keeping shape
- Icon request funnel that actually closes the loop (Arcticons' issue-template + tracker) — replace our placeholder "request icons" with a GitHub-issue form and auto-labeling bot
- Per-launcher install cards with pre-baked intents (Ultimate_Theme_UI_Template) — one-tap apply for Nova/Action/Smart/OnePlus/Samsung instead of generic docs
- Shape-mask preview in the dashboard (Launcher3 shape options) — let users see each era rendered in square/rounded/squircle/teardrop before applying
- IconPackManager library parity (launcher-icon topic) — make sure our appfilter.xml is readable by the standard IconPackManager so any third-party launcher that ships it works out of the box
- Showcase-site auto-generator from appfilter (AdaptiveIconsShowcase pattern) — CI step that regenerates GitHub Pages gallery on every release
- AMOLED-aware "True Black" dashboard variant (carries forward our AMOLED theme, matches Arcticons' dark mode polish)

### Patterns & Architectures Worth Studying
- `appfilter.xml` + `drawable.xml` + `theme_config.xml` triad — canonical Android icon-pack manifest stack; OSS packs like Arcticons and Papirus Adaptive show how to keep them in sync via CI (e.g., lint that every `<item>` in appfilter has a corresponding drawable)
- Adaptive icon mask layering — foreground vector + background layer per Android 8.0 spec, with OEM masks (squircle on Samsung, circle on Pixel) applied at runtime — critical to test render on multiple masks before shipping
- Dashboard-as-library (Blueprint, CandyBar) — drop-in dashboard engines mean your value is the icon art + metadata, not the scaffolding; budget development effort on art and appfilter coverage accordingly
- CI-generated previews per era — render each drawable at the 5 stock masks, diff against last release, flag shape-clipping regressions before publish

## Open-Source Research (Round 4)

Fresh research pass — April 2026. Items that don't duplicate earlier rounds.

### New Competitive Landscape Findings

| Project | Stars | Strategy | What iOSIconPack beats them on |
|---------|-------|----------|-------------------------------|
| Arcticons | 1,435 | 14,000+ handcrafted monotone line icons; GPL-3.0 | Era specificity — Arcticons has one style; iOSIconPack has 6 distinct iOS eras |
| Lawnicons | Active on Play Store | Themed-icon addon for Lawnchair; community-contributed SVGs; Figma guidelines | Standalone app; works on any launcher; has era concept |
| Cuscon | Active on F-Droid | 5,000+ backgroundless icons (glyph only, black stroke, full color) | Squircle shape; era authenticity; dedicated iOS aesthetic |
| Delta (iOS ports) | Paid Play Store | Single iOS generation at a time | 6 eras in one free pack |

### Lawnicons Architecture — What to Borrow

**`icontool.py`** — Lawnicons ships a CLI tool that manages the whole contributor workflow in one script:
- `icontool add <svg> <ComponentInfo{pkg/activity}> <name>` — copies SVG into the `svgs/` folder, injects a new alphabetically-sorted `<item>` into `appfilter.xml`
- `icontool link <svg> <ComponentInfo{}>` — aliases an existing drawable to a second component (avoids duplicate assets for app variants like YouTube/YouTube Music)
- `icontool remove <ComponentInfo{}>` — removes the component mapping; optional `--delete-svg` flag cleans up the asset too
- Auto-sorts `appfilter.xml` alphabetically by `name=""` attribute on every write

**Action item**: Port this pattern to iOSIconPack as `scripts/icontool.py` with an extra `--era` flag so contributors can specify which era's prefix (`ios14_`, `ios15_`, etc.) to target. The current workflow requires four manual XML edits per icon — the tool should collapse that to one command.

**`svg-processor/`** — Lawnicons has a separate Kotlin Gradle module that processes raw SVGs into Android-compatible vector drawables at build time (strips unsupported SVG features, normalizes viewport). Reference: https://github.com/LawnchairLauncher/lawnicons/tree/develop/svg-processor. This is worth adapting once iOSIconPack's icon count exceeds ~500 and manual vector drawable conversion becomes a bottleneck.

**Figma community file** — Lawnicons published a Figma file at https://www.figma.com/community/file/1544976260626797886 covering canvas (192×192 px), stroke weight (12px center = 148×148 content area), and common mistakes. iOSIconPack should create its own Figma community file per era documenting: squircle corner-radius spec, era-specific color palette, gradient style, and safe-zone overlay. This makes community contributions dramatically easier.

**Icon request web dashboard** — Lawnicons hosts a Vercel dashboard at `lawnicons-requests.vercel.app` (backed by GitHub Issues API) showing every open request with vote count and install count. Build a similar page for iOSIconPack — even a static GitHub Pages site that reads Issues via the GitHub REST API would serve as a triage view and shows users their requests are tracked.

**Crowdin localization** — Lawnicons uses `crowdin.yml` for dashboard string translation. Once the Blueprint dashboard has more string resources, wire Crowdin to automatically open translation PRs for new strings. Low effort, high visibility for international users.

### Android Platform Updates — Action Items

**Android 16 QPR2 auto-theming (new, April 2026)**: Starting with Android 16 QPR2, the system automatically generates a themed icon for apps that do *not* ship a `monochrome` layer — the platform derives one from the adaptive icon foreground. This was previously only possible if the app provided its own monochrome layer. Implications:
- The urgency of adding manual monochrome drawables is reduced; the auto-generated one is acceptable for most users
- For quality, hand-crafted `ios_{name}_mono` layers are still preferred (the auto-generated version often has artifacts around gradient paths)
- Priority order: ship hand-crafted monochrome for the 25 third-party icons first (these have the most visibility), then the 19 stock Apple icons, then era duplicates

**`<monochrome>` in adaptive-icon XML** (existing roadmap item, now with clear priority):
```xml
<!-- ic_launcher.xml -->
<adaptive-icon>
  <background android:drawable="@color/ic_launcher_background"/>
  <foreground android:drawable="@drawable/ic_launcher_foreground"/>
  <monochrome android:drawable="@drawable/ic_launcher_monochrome"/>
</adaptive-icon>
```
The `<monochrome>` tag is separate from the appfilter icons — it controls the app's own launcher icon theming, not the replacement icons. Both need to exist independently.

### Backgroundless / Glyph-Only Variant

Cuscon proves there is demand for icon packs that present the glyph without a background tile. For iOSIconPack, a "glyph mode" could be implemented as an alternate set of drawables that:
- Use a fully transparent background layer
- Keep only the foreground glyph (the iOS app symbol)
- Add a thin (4dp) border stroke matching the era's accent color so the icon reads on both light and dark wallpapers
- Ship in a separate `flavor` build variant (`glyph` vs `squircle`) or as a toggle in the dashboard settings

This is lower effort than it sounds: the foreground layer already exists for every icon; a new background layer that is `@android:color/transparent` plus a stroke drawable is all that's needed. Cuscon's popularity on F-Droid (~5000 icons, actively updated) confirms the audience is real.

### `fetch_icons.py` Improvements

The current script fetches icons from the iTunes Search API, which returns the App Store artwork (the real iOS icon). New ideas:
- **IPA extraction mode** — Apple publishes `.ipa` files for open-source apps (TestFlight public betas for some apps). For first-party Apple apps available through Apple Configurator 2, the IPA contains `AppIcon*.png` assets in the `.app` bundle. An IPA-extract mode would pull the actual shipped icon rather than the App Store CDN thumbnail, guaranteeing pixel-for-pixel accuracy. Reference tooling: `Bagbag/ipatool`, `majd/ipatool-py`.
- **Per-era color grading** — after downloading the raw 1024×1024 PNG, apply a post-processing pass that adjusts saturation/contrast to match each era's aesthetic (iOS 14: +15% saturation; iOS 17: desaturated flat; iOS 18: dark-mode-ready). Pillow + NumPy can do this in ~5 lines.
- **Hash-based cache invalidation** — currently raw PNGs are cached forever; add SHA-256 check against the server `ETag` so icons refresh when Apple updates them.

### Distribution Channels to Add

| Channel | Effort | Audience |
|---------|--------|----------|
| F-Droid | Low — submit `fdroiddata` metadata YAML | Privacy-first Android users who avoid Play Store |
| Obtainium | Zero — just document the GitHub Releases URL | Power users; already common for icon packs |
| IzzyOnDroid | Low — similar to F-Droid metadata | Active community that tracks GitHub-native releases |
| GitHub Pages showcase | Medium — CI-generated gallery | Contributors and casual browsers |

F-Droid is the highest-priority new channel: Arcticons and Lawnicons and Cuscon are all on F-Droid with high download counts. The iOSIconPack build is already reproducible (no Play Store dependencies) so the metadata YAML is the only barrier.

### Design System / Figma Deliverables

One-time effort, high long-term contributor value:

- **Era style guides** — one Figma frame per era showing: exact squircle path, corner-radius formula, color palette swatches, gradient angle, shadow style, and a reference grid of 8 existing icons at correct size
- **Contribution template** — 192×192 px Artboard with safe-zone guides, the iOS squircle clip mask, and a "your icon here" placeholder layer
- **Era comparison grid** — side-by-side of the same 10 apps across all 6 eras to make the design language differences obvious to new contributors

Publish as a Figma Community file and link from CONTRIBUTING.md. Arcticons' Figma file is credited with making their contributor onboarding dramatically faster.

## Implementation Deep Dive (Round 3)

### Reference Implementations to Study
- **jahirfiquitiva/Blueprint/sample/src/main/res/xml/appfilter.xml** — https://github.com/jahirfiquitiva/Blueprint/blob/sample/src/main/res/xml/appfilter.xml — reference dual-location appfilter (res/xml + assets/ required). iOSIconPack already follows this; verify on every release.
- **jahirfiquitiva/Blueprint/wiki/How-to-create-and-setup-an-icon-pack** — https://github.com/jahirfiquitiva/Blueprint/wiki/How-to-create-and-setup-an-icon-pack — canonical setup; note the "download sample branch, not releases zip" gotcha that trips most new icon-pack devs.
- **materialos/android-icon-pack/app/src/main/assets/appfilter.xml** — https://github.com/materialos/android-icon-pack/blob/master/app/src/main/assets/appfilter.xml — real-world large appfilter as reference for iOSIconPack's "500+ apps" target. Also shows Polar dashboard coexistence pattern.
- **rektdeckard/iconpacktools** — https://github.com/rektdeckard/iconpacktools — generates `drawable.xml` and `icon-pack.xml` from a directory. Replaces iOSIconPack's manual maintenance of both XML files.
- **rektdeckard/gist bash scripts** — https://gist.github.com/rektdeckard/2c20220b866a3b7efb2465e5172b6c24 — bash variant for CI integration; maps appfilter.xml → other formats (appmap.xml, theme_resources.xml). Directly addresses iOSIconPack's build pipeline item "appfilter validator".
- **Donnnno/Arcticons/app/src/main/java/com/donnnno/arcticons/apps/IconsFragment.kt** — https://github.com/Donnnno/Arcticons — issue-template for icon requests + auto-labeling. Blueprint for iOSIconPack's "Icon-request funnel that actually closes the loop" roadmap item.
- **Donnnno/Arcticons/.github/workflows/generate-icons.yml** — https://github.com/Donnnno/Arcticons — CI that regenerates drawables/appfilter. Template for iOSIconPack's "CI step that regenerates GitHub Pages gallery on every release".
- **Snoy-Kuo/android_adaptive_icon_example** — https://github.com/Snoy-Kuo/android_adaptive_icon_example — adaptive icon mask-line-verified SVG → vector drawable pipeline. Critical reference before expanding to 100+ icons per era.
- **amirzaidi/Launcher3/src/com/android/launcher3/graphics/IconShape.java** — https://github.com/amirzaidi/Launcher3 — 6 stock icon shapes (square, rounded square, squircle, teardrop, circle, cylinder) in Launcher3. Reference for iOSIconPack's "shape-mask preview in dashboard".

### Known Pitfalls from Similar Projects
- **Blueprint releases zip is NOT the correct download** — Blueprint wiki — users keep downloading the release zip instead of the sample branch. Common 404/build failure. Document clearly in iOSIconPack's contributing guide.
- **Blueprint is CC BY-SA 4.0 — fork-only, no commercial restrictions** — iOSIconPack already complies (open-source), but any downstream app bundling Blueprint code must also be CC BY-SA.
- **Adaptive icon foreground must fit in inner 66×66dp of 108×108dp canvas** — outer 18dp reserved for parallax + mask. Icons that fill edge-to-edge get clipped on OEM masks (teardrop cuts corners hard). Verify iOSIconPack's 192×192 viewport scales correctly: 66/108 = 61% safe area.
- **Monochrome themed-icon layer needed for Android 13+ theming** — iOSIconPack roadmap mentions this; every adaptive-icon XML must add `<monochrome android:drawable="@drawable/ios_{name}_mono"/>`. Currently 0/110 icons have this.
- **`appfilter.xml` must exist in BOTH `res/xml/` AND `assets/`** — Blueprint reads both; iOSIconPack already follows but drift between the two is a frequent regression source. Add a CI check.
- **Vector drawable `<gradient>` tag unsupported on API < 24** — iOSIconPack `minSdk=23` includes API 23. Either bump `minSdk` to 24 or avoid gradient tags in drawables.
- **Gradle `AGP 8.12.0` requires Gradle 8.13+, not 8.12** — iOSIconPack CLAUDE.md already notes this. Lock in via wrapper properties.
- **Blueprint + Frames combined APK hits Play Store 150MB limit with 500+ icons at 2 eras** — iOSIconPack has 6 eras + 500 target = 3000 icons. Must use AAB (Android App Bundle) from the start; APK alone will be rejected.
- **Themed icon style variants (sharp/line/filled) compound with era count** — 6 eras × 3 styles = 18 variants per app = untenable manual maintenance. Use style as a runtime transform (tint + opacity), not a separate drawable.
- **Blueprint 2.5.1 BottomNavigationBlueprintActivity class was renamed in 2.6+** — don't upgrade Blueprint without testing MainActivity bindings.

### Library Integration Checklist
- **Blueprint Dashboard (Jahir Fiquitiva)** — no Maven; vendor `Blueprint/sample/` branch code into `app/src/main/kotlin/`. Entry: `class MainActivity : BottomNavigationBlueprintActivity()` + `res/values/blueprint_setup.xml` for config. Gotcha: styles parent must be `Frames.SplashScreen`, NOT `Blueprint.SplashScreen` (Blueprint style inherits from Frames). iOSIconPack's CLAUDE.md already documents this — lock it in.
- **iconpacktools (rektdeckard CLI)** — `pip install iconpacktools` — entry: `iconpacktools generate-drawable --input app/src/main/res/drawable/ --output app/src/main/res/xml/drawable.xml`. Gotcha: the tool groups by filename prefix; iOSIconPack's `ios{ver}_{name}` convention means groups split by era — desired behavior.
- **Android Gradle Plugin adaptive-icon lint** — `com.android.tools.build:gradle:8.12.0` — entry: `android { lint { warningsAsErrors true; disable("MissingTranslation"); fatal("IconLauncherShape") } }`. Gotcha: `IconLauncherShape` lint will flag all 110 non-adaptive icons as warnings; gate the fatal on only new drawables via baseline XML (`./gradlew updateLintBaseline`).


