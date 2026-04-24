# Changelog

All notable changes to iOSIconPack will be documented in this file.

## [v1.1.0] — 2026-04-24

### Added
- Adaptive launcher icon refresh with dual rotated brand grid + monochrome
  themed layer for Android 13+ dynamic theming (closes the 0/110 monochrome
  coverage gap flagged in `ROADMAP.md`).
- GitHub issue templates (icon request / bug / feature) + pull-request
  template aligned with Arcticons' request funnel.
- `scripts/validate_appfilter.py` — byte-level parity check between the
  `res/xml/` and `assets/` copies of `appfilter.xml` / `drawable.xml`, with
  drawable-existence + duplicate-component guards. Wired into CI.
- Android App Bundle (`bundleRelease`) build + artifact upload, so we are
  ready for the Play Store 150MB limit once icon coverage grows.
- `CONTRIBUTING.md` describing icon conventions, appfilter wiring, and the
  release signing env vars.
- Launcher intent filters for Microsoft Launcher, Action Launcher, POCO,
  Pixel / NexusLauncher, and Niagara.

### Changed
- Signing config now reads `IOSICONS_STORE_PASSWORD` / `IOSICONS_KEY_ALIAS` /
  `IOSICONS_KEY_PASSWORD` from env (CI secrets) and falls back to the
  committed dev keystore for offline contributors only.
- CI workflow (`build.yml`) now builds both APK + AAB, caches Gradle, runs
  the appfilter validator, and supports manual release dispatch by version
  input.
- README: collapsed the duplicated branding header into a single centered
  hero; replaced the stale `v2.5.1` badge (Blueprint's version, not ours);
  corrected the License section to MIT.

### Fixed
- `ic_launcher_foreground.xml` + `ic_launcher_monochrome.xml` had duplicate
  `android:pivotX` / `android:pivotY` attributes that Android aapt2 rejects;
  collapsed to a single pivot declaration per group.

## [v1.0.0] — 2026-03-31

- Initial scaffold — Blueprint dashboard with 110 placeholder icons across
  six iOS eras.
- Gradle wrapper committed; appfilter expanded to 214 entries.
- Replaced placeholder squircles with iOS-inspired vector glyphs, then
  replaced those with real iOS app icons fetched from the Apple CDN (135
  PNGs total: 110 stock era icons + 25 third-party).
- Gradle 8.13 + AGP 8.12.0 upgrade, SplashScreen style parent fix, signing
  config wired to `iosicons.jks`.
