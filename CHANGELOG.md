# Changelog

All notable changes to iOSIconPack will be documented in this file.

## [v1.1.5] — 2026-04-25

### Added
- `scripts/icontool.py rebuild` — batch-sync subcommand. Scans `drawable-xxxhdpi/`
  for PNG files and `drawable/` for vector drawables, then adds any missing entries
  to `drawable.xml` under the correct era category section. Supports `--prune` to
  remove stale entries for files deleted from disk, and `--dry-run` to preview
  changes without writing. Excludes `tp_*` icons (appfilter-only by design).
- `docs/requests.html` — live icon request dashboard on GitHub Pages.
  Reads open GitHub Issues via the REST API, sorted by 👍 votes by default.
  Features: search, label filter, sort (votes / newest / oldest / most-discussed),
  paginated load-more, skeleton loader, 5-minute localStorage cache with stale
  fallback on rate limit, and a direct "Request Icon" button linking to the
  `icon-request.yml` issue template.
- `docs/index.html` — added "Requests" link in header nav pointing to the new
  requests dashboard.
- `.github/workflows/build.yml` — per-era APK loop. Loops `set_era.py` through
  all 6 eras (ios14–ios18, ios26), builds a signed APK per era, and publishes
  each as `iOSIconPack-v{VERSION}-{ERA}.apk` to the GitHub Release alongside the
  ios18 AAB.
- `app/src/main/res/xml/appfilter.xml` — 92 additional component mappings:
  browser alternatives (Firefox, Brave, Opera, Kiwi, Vivaldi, Tor), music
  streaming (Amazon Music, TIDAL, Deezer, Apple Music, Pandora, iHeart), gallery
  apps (Samsung, OnePlus), and popular social/utility third-party icons
  (YouTube, Gmail, Chrome variants, Discord, Facebook, Netflix, Snapchat,
  TikTok, Zoom, PayPal, Robinhood, Strava, Spotify Free).


### Added
- `scripts/set_era.py` — era-switching CLI. Remaps every drawable reference in
  `appfilter.xml` from one iOS design generation to another with a single
  command. Supports all six eras: ios14, ios15, ios16, ios17, ios18 (default),
  and ios26 (Liquid Glass). The iOS 26 switch is partial by design — only the
  10 icons that have a Liquid Glass variant are remapped; the rest stay on
  iOS 18. Includes `--dry-run` and `--list` flags. Both `res/xml/` and
  `assets/` copies are updated atomically.
- `scripts/gen_gallery.py` + `docs/index.html` — GitHub Pages icon browser.
  Dark-theme single-page gallery with era filter tabs, search, and per-icon
  component count badges. Images load from GitHub raw URLs (no asset copying).
  CI validates `docs/index.html` is up-to-date on every master push via
  `gen_gallery.py --check`. Live at https://sysadmindoc.github.io/iOSIconPack/

### Changed
- `README.md` — added Gallery badge, Obtainium install badge and instructions,
  era-switching quick-start, updated Contributing section to reference icontool
  instead of the old manual four-file workflow.
- `.github/workflows/ci.yml` — added gallery staleness check step.

## [v1.1.3] — 2026-04-24

### Added
- `scripts/icontool.py` — contributor CLI that collapses the four-file manual
  XML wiring workflow into a single command. Supports `add`, `link`, `remove`,
  `sync`, and `check` subcommands. Atomic writes via temp-file + `os.replace`
  to prevent partial-write drift between `res/xml/` and `assets/` copies.
  Third-party (`tp_*`) icons are excluded from `drawable.xml` automatically.
  New categories are inserted at the correct era position in `drawable.xml`
  without manual ordering.
- `.github/workflows/ci.yml` — CI workflow that runs `validate_appfilter.py`
  then `assembleDebug` on every pull request and push to master. Uploads the
  debug APK as a build artifact (7-day retention) for quick reviewer testing.
- `fdroid/metadata/com.sysadmindoc.iosicons.yml` — F-Droid build metadata
  ready for submission to the fdroiddata repository.
- `fastlane/metadata/android/en-US/` — store listing copy (title,
  short description, full description) consumed by F-Droid and compatible
  with Google Play publishing via fastlane.

### Changed
- `CONTRIBUTING.md` — replaced the four-step manual XML edit section with
  `icontool` examples; kept the manual fallback path for reference.
- `.github/PULL_REQUEST_TEMPLATE.md` — PR checklist updated to reference
  `icontool check` instead of the old per-file manual steps.

## [v1.1.2] — 2026-04-24

### Changed
- `minSdk` bumped from 23 to 26 (Android 8.0). Adaptive icons are a
  mandatory feature of the pack and Android 13+ themed icons need API 33;
  both were already above the old floor. Aligns with the project stack
  convention (minSdk 26 unless a specific need for lower).

### Removed
- `app/src/main/res/drawable/ic_launcher_background.xml` — orphan since
  v1.1.0 when the adaptive icon switched to `@color/ic_launcher_background`
  in `ic_launcher_colors.xml`. Kept no references; dropped to avoid the
  namespace collision where a drawable and a color share the same id.

### Fixed
- README feature list no longer claims an "Auto-generated placeholders"
  feature that does not exist. The placeholder engine is on the roadmap
  but was not shipped. Replaced that bullet with the accurate list of
  new launcher integrations.

## [v1.1.1] — 2026-04-24

### Added
- `fetch_icons.py` CLI flags — `--only`, `--tp-only`, `--era`, `--dry-run`,
  `--validate` — the validator subcommand reports every icon on disk that
  lacks an appfilter mapping so dead-weight art does not ship in the APK.
- `requirements.txt` pinning Pillow, referenced from CONTRIBUTING.md.
- 36 new `appfilter.xml` entries for popular apps that were previously
  unmapped: Threads, X, BeReal, Threema, Signal, Session, Microsoft Teams,
  Jerboa (Lemmy), Mastodon, Elk, Bluesky, Lyft, DoorDash, Grubhub, Cash
  App, Audible, Kindle, GitHub mobile, Obsidian, Google Keep, Notion,
  Bear, Todoist, Google Calendar, Outlook, Yahoo Mail, Proton Mail,
  1Password, Bitwarden, KeePassDX, Duolingo, Khan Academy, etc.

### Changed
- 30 existing `appfilter.xml` mappings redirected from generic `ios18_*`
  glyphs to the dedicated `tp_*` PNGs (Instagram, WhatsApp, Telegram,
  Discord, Spotify, Netflix, YouTube + ReVanced/Vanced, Twitter, TikTok,
  Snapchat, Facebook / Messenger, Chrome, Gmail, Google Maps, Uber /
  Uber Eats, Reddit, Slack, Zoom, Pinterest, Amazon Shopping, PayPal,
  Venmo, Robinhood, Strava, Shazam). The third-party art had shipped in
  the APK for a release but was dead weight — no component pointed to
  it.
- `fetch_icons.py` no longer bootstraps Pillow at runtime. It now fails
  fast with a clear instruction to `pip install -r requirements.txt`,
  consistent with the rest of the project's tooling.
- `fetch_icons.py` writes third-party icons under the canonical `tp_`
  prefix (was `3p_`, which did not match any drawable on disk — another
  latent bug).

### Fixed
- `.gitignore` no longer excludes `fetch_icons.py`; the script is part
  of the supported contributor toolchain now that the auto-install
  pattern has been removed.

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
