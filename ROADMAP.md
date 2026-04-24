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


