# Changelog

All notable changes to iOSIconPack will be documented in this file.

## Unreleased

### Added
- Added a local release metadata guard that keeps ignored working notes and
  blocked release targets aligned with the current app version.
- Added generated release-channel status for the gallery and install docs so a
  stale GitHub Release/Obtainium channel is visible before users download.

## [v1.2.2] - 2026-07-02

### Changed
- Polished the GitHub Pages icon gallery with visible result feedback, clearer
  empty-state recovery, light/dark system colors, mobile layout checks, and
  stronger keyboard/focus states.
- Refined the live icon request dashboard with labelled controls, improved
  loading/empty/error states, cached-data fallback messaging, and responsive
  mobile layout.
- Tightened dashboard home-card copy, launcher apply recovery messages, and
  About credits.
- Added a concrete privacy policy target for the in-app request consent dialog.

## [v1.2.1] - 2026-07-02

### Added
- Local preview regression checks for full-square, circle, rounded-square, and
  squircle launcher masks.
- Local sharp, line, and filled themed-icon style prototype generation under
  `build/style-prototypes`.
- Coverage-gap scoring, icon provenance validation, and dependency advisory
  release gates.

### Fixed
- Issue-template contact links now route to enabled GitHub Issues instead of
  disabled repository Discussions.

## [v1.2.0] — 2026-06-27

### Added
- `icontool preflight` runs local validators, Gradle test/lint/release
  packaging, reports release APK size, and fails when the size budget is
  exceeded.
- `icontool launcher-compat-check` validates launcher intent filters and core
  icon-pack XML resources for Nova, Lawnchair, Smart Launcher, OnePlus,
  Samsung/ADW generic channels, Niagara, Pixel, and Holo/LauncherPro.
- `icontool request-audit` audits open `icon-request` issues or saved issue JSON
  against `appfilter.xml`, reporting already-covered, duplicate,
  needs-ComponentInfo, ready-to-map, and malformed request buckets without
  mutating GitHub.
- `icontool coverage-gap` ranks missing app packages from icon requests plus
  Arcticons, Delta Icons, Lawnicons, or supplied appfilter XML sources, with
  component guesses and existing-drawable reuse hints.
- Generated gallery accessibility smoke checks now validate search labels,
  filter pressed states, tab semantics, focus-visible support, and keyboard
  activation through the local validator path.
- `icontool maven-provenance-check` reports declared Gradle repositories,
  resolved buildscript/release artifacts, Maven source repository, license, and
  source URL metadata for F-Droid distribution review.
- `icontool dependency-audit` reports current versus latest-stable AGP, Kotlin,
  KSP, Blueprint, and Pillow versions, then queries OSV and fails on known
  advisories.
- `icontool preview-regression` renders every shipped PNG through full-square,
  circle, rounded-square, and squircle launcher masks, then fails when hashes
  drift from the accepted local baseline.
- Issue-template contact links now route to the enabled GitHub Issues surface
  instead of disabled repository Discussions.
- First-party Google app defaults now use the shipped iOS 18 Google/Chrome/Gmail/
  YouTube variants instead of generic Apple analogues or static `tp_*` icons.
- iOS 26 Liquid Glass icons now use a deterministic frosted squircle material
  pass with translucent depth, rim highlights, and clipped safe-zone corners.
- `scripts/gen_glyph_variants.py` generates 367 transparent glyph-only vector
  variants with a squircle border, exposed through the dashboard `Glyph`
  category and validated by the local drawable checks.
- `icontool style-prototypes` generates local sharp, line, and filled
  themed-icon XML variants under `build/style-prototypes` for review without
  adding shipped drawable resources.
- `app/src/main/assets/icon_provenance.json` records source URL, provider,
  shipped PNG SHA-256, license note, and era transform metadata for every
  committed icon PNG; `fetch_icons.py --provenance-check` and drawable
  validation fail when it drifts.
- `convertSvgSources` Gradle task converts raw SVG sources from
  `app/src/main/svg` into generated Android vector drawables at build time.
- `crowdin.yml` and `icontool localization-check` wire dashboard strings to a
  local Crowdin CLI workflow without committing credentials or GitHub Actions.
- Home-screen launcher apply cards route Nova, Action, Smart, OnePlus,
  Lawnchair, Niagara, Projectivy, ADW, Apex, and Samsung Theme Park through
  app-owned deep links and local launcher compatibility validation.
- `icontool placeholder` generates deterministic `ph_*` letter-tile PNGs for
  uncovered app components without adding them to the dashboard catalog.
- `icontool widget-export` builds a local zip with Kustom/KWGT image assets,
  JSON/CSV catalog metadata, and a Rainmeter skin/resource layout.
- Six committed, original WebP wallpapers cover iOS 14, 15, 16, 17, 18, and iOS
  26 Liquid Glass eras through Blueprint's raw GitHub wallpaper JSON feed.
- 232 new per-era app variants for popular third-party and Google apps.
- iOS 26 Liquid Glass coverage expanded to 57 icons.
- 367 hand-crafted monochrome vector layers for Android 13+ themed icons.
- Era-specific Material You tint resources for every adaptive themed wrapper.
- Local release metadata consistency check for version, README badge, F-Droid
  metadata, dashboard changelog, and git tag alignment.
- Local GitHub release-channel check for latest release tag, APK asset name,
  asset digest, and non-app version release drift.
- Local Android developer verification readiness report for package identity,
  signing certificate hash, install channels, enforcement timeline, and
  operator next actions.
- Publish release signing guard that requires maintainer env signing inputs,
  rejects the committed dev keystore, and verifies the APK certificate SHA-256
  fingerprint before publication.
- Explicit no-backup/no-device-transfer XML rules for Android 11- and Android
  12+ backup paths.

### Changed
- Release lint is fail-closed again, and release builds now enable resource
  shrinking with an explicit icon-pack keep file for dynamically referenced
  launcher/dashboard resources.
- The local release APK size gate is now 13 MiB to cover the bundled wallpaper
  pack while still failing on unexpected asset growth.
- Wallpaper entry points are backed by committed original assets; drawable
  validation now fails on missing launcher resource references, empty advertised
  wallpaper surfaces, or stale local wallpaper JSON metadata.
- The Frames `json_url` wallpaper feed now loads from the bundled asset catalog
  with local asset URLs, so the dashboard wallpaper tab does not depend on
  GitHub Raw at runtime.
- Contributor, gallery, and distribution docs now describe local validation and
  release commands only; stale current-process CI/GitHub Actions claims were
  removed.
- Every iOS era now has 57 icons; total PNG coverage is 367 icons.
- `set_era.py` now remaps `tp_*` entries when matching per-era variants exist.
- `icontool rebuild` now syncs `icon_pack.xml` so Blueprint filters stay current.
- `gen_monochrome.py` now emits vector-backed mono layers where templates exist,
  and reports bitmap fallback counts explicitly.
- Themed-icon wrappers now use era-specific dynamic color background tokens
  instead of the shared launcher background color.
- Drawable validation now skips the warning-only full squircle scan by default on
  large icon sets; set `IOSICONS_FULL_SQUIRCLE_CHECK=1` for the full scan.

### Fixed
- Removed a duplicate Signal routing component that mapped to both WhatsApp and
  Messages.
- Removed the stray public `v2.5.1` release/tag hazard and added a local guard
  that rejects future `v*` tags whose tagged app version does not match.

## [v1.1.9] — 2026-04-25

### Added
- 54 new appfilter component mappings (618->672): AI assistants (ChatGPT,
  Claude, Perplexity), productivity (Notion, Canva, Adobe Reader/Lightroom/Scan),
  streaming (Paramount+, Pluto TV, Deezer), dating (Tinder, Bumble, Badoo),
  secure messaging (Signal), fitness (Nike, MyFitnessPal, Peloton), privacy
  (ProtonMail, ProtonVPN, ProtonPass), crypto (Binance, Coinbase, Cash App),
  Samsung system (My Files, Clock, Calendar, Device Care, Routines, Reminder),
  OEM launchers (Pixel, LG, OnePlus, Xiaomi, Oppo, Vivo), Google extras
  (Gboard, Google One, Cloud Console), Motorola system, Shopping (Shopify).
- F-Droid submission guide (`docs/fdroid-submission.md`) with fdroiddata MR
  checklist and IzzyOnDroid submission instructions.
- Research delta scan iter-5 (`docs/research/iter-5-sources.md`).

### Changed
- F-Droid metadata description updated (670+ component entries).

## [v1.1.8] — 2026-04-25

### Added
- Gallery **Compare Eras** tab — side-by-side grid of every stock iOS app across
  all 6 design eras (iOS 14 → iOS 18 → iOS 26 Liquid Glass). Era columns are
  colour-coded; Liquid Glass column present only for the 10 Liquid Glass subset
  apps. Implemented in `gen_gallery.py` (`_comparison_html()`, `_base_app_names()`).
- `icontool stats` subcommand — prints per-era icon counts, component-mapping
  counts, and top-N drawables by mapping (default top 10, `--top N` to override).
- Squircle corner compliance check in `validate_drawables.py` (`check_squircle_corners()`).
  Requires Pillow; skips gracefully when not installed. WARN-only (exits 0).
  Reports summary count of icons with opaque corners; notes expected behaviour for
  Apple-sourced icons whose squircle mask is applied by the launcher at runtime.

### Changed
- `gen_gallery.py`: added tab-bar nav (Browse / Compare Eras / Requests ↗),
  `_js()` extended with tab-switching logic that hides search+filter bar in
  Compare view. `PACK_DIR` and `COMPARE_ERAS` / `PREFIX_TO_ERA` constants added.
- `validate_drawables.py`: squircle check integrated; output unchanged on pass
  (still shows `OK (135 PNGs …)`), squircle summary line appended if Pillow present.
- `scripts/icontool.py`: `stats` subcommand wired into `_build_parser()`.

## [v1.1.7] — 2026-04-25

### Added
- `scripts/gen_monochrome.py` — scaffolds Android 13+ themed-icon stubs.
  Generates `drawable/<name>_mono.xml` (bitmap placeholder referencing the
  existing PNG) and `drawable/<name>_themed.xml` (adaptive-icon wrapper with
  `<monochrome>` layer) for every `ios18_*` and `tp_*` icon. 90 XML files
  created total (45 mono + 45 themed). Replace `_mono.xml` `<bitmap>` stubs
  with hand-crafted vectors for higher quality. Run with `--force` to regenerate
  after adding new icons.
- `.github/workflows/issue-triage.yml` — auto-comments on every new icon
  request issue. Parses the package name from the structured form, checks
  `appfilter.xml` for coverage, and replies with either "Already covered" +
  matched drawable list, or "Queued" + adb ComponentInfo tip. Adds the
  `already-covered` label when the app is mapped.
- `already-covered` GitHub label (blue) for quick maintainer triage.

### Changed
- `fetch_icons.py`:
  - Per-era color grading via `PIL.ImageEnhance` — each era now gets a
    distinct Saturation/Contrast/Brightness pass (`ios14`: richest; `ios17`:
    flat/desaturated; `ios26_lg`: frosted/cool; `tp`: identity/no grade).
  - SHA-256 hash cache (`icons_raw/.hash_cache.json`) skips re-downloading
    raw files that haven't changed since the last run.
  - `--list` flag prints all known icon names and exits.
- `scripts/icontool.py` — `check` subcommand now runs both
  `validate_appfilter.py` and `validate_drawables.py` in sequence.
- `scripts/validate_drawables.py` — output now distinguishes pure vectors,
  monochrome stubs, and themed wrappers in the summary line.


### Added
- `scripts/validate_drawables.py` — CI asset validator. Checks every PNG in
  `drawable-xxxhdpi/` is exactly 192x192 px, a valid PNG, and under 200 KB.
  Also validates every vector drawable in `drawable/` parses as valid XML, and
  every `drawable.xml` entry has a corresponding file on disk. Integrated into
  `.github/workflows/ci.yml` and `icontool check`.
- `icontool check` now runs both `validate_appfilter.py` and
  `validate_drawables.py` in a single command.

### Changed
- `app/src/main/res/xml/appfilter.xml` — 112 additional component mappings
  across all 20 iOS 18 icon drawables:
  - **ios18_mail**: Outlook, ProtonMail, Tutanota, Yahoo Mail, AquaMail, K-9,
    Thunderbird, Samsung Mail, Fastmail, Gmail conversation view
  - **ios18_messages**: Signal, Viber, Skype, Google Messages, Samsung Messages,
    Line, Telegram web/plus, WhatsApp Business, Huawei Messages
  - **ios18_calendar**: Google Calendar, Samsung, MIUI, OnePlus, Huawei, HTC,
    Business Calendar, Outlook Calendar
  - **ios18_maps**: Google Maps, Waze, HERE Maps, Maps.me, OsmAnd, Organic
    Maps, Yandex Maps
  - **ios18_phone**: Google Dialer, Samsung, Huawei, Motorola, LG, HTC
  - **ios18_clock**: Google Clock, Samsung, OnePlus, MIUI, Huawei, LG
  - **ios18_camera**: Google Camera (Pixel+Ego), Samsung, MIUI, OnePlus,
    Huawei, Motorola, LG, AOSP Snap
  - **ios18_notes**: Google Keep, Evernote, Notion, Samsung Notes, OneNote,
    SimpleNote, Joplin, MIUI Notes, Huawei Notepad
  - **ios18_calculator**: Google, Samsung, OnePlus, MIUI, Huawei, LG
  - **ios18_settings**: Stock AOSP, Samsung, MIUI, Huawei, OnePlus
  - **ios18_weather**: AccuWeather, Weather Channel, Yahoo Weather, Breezy
    Weather, Samsung Weather, MIUI Weather, Huawei Weather
  - **ios18_health**: Google Fit, Samsung Health, MyFitnessPal, Fitbit,
    Garmin Connect, Runkeeper, Nike Run Club, Zepp, Polar Flow
  - **ios18_wallet**: Google Wallet, Samsung Pay, Cash App, Coinbase, Luno,
    Blockchain
  - **ios18_files**: Google Files, Solid Explorer, Total Commander, Amaze,
    FX Explorer, Samsung My Files, MIUI Explorer, Huawei Files
  - **ios18_appstore**: Samsung Galaxy Store, Amazon Appstore, Huawei
    AppGallery, Aptoide, F-Droid, Google Play, MIUI
  - **ios18_facetime**: Google Meet, Google Duo/Meet, Teams, Webex,
    GoToMeeting, BlueJeans, Wire
  - **ios18_compass**: generic, Axie Pro, Samsung, Huawei
  - **tp_google_maps**, **tp_pinterest**, **tp_shazam**, **tp_slack**,
    **tp_reddit**, **tp_amazon**, **tp_uber**: additional package variants


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
