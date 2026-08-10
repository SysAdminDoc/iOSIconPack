# Research - iOS Icon Pack

Date: 2026-07-05 - replaces all prior research.

## Executive Summary
iOS Icon Pack is a Kotlin/Android icon-pack app that uses Blueprint for the dashboard and concentrates its defensible value in a curated multi-era iOS asset catalog, launcher XML mappings, generated gallery/request surfaces, F-Droid/Fastlane metadata, and local Python validation tooling. Verified: the repo is already strong on deterministic asset generation and local checks (`scripts/icontool.py check` passes for 367 icons, 671 mappings, localization boundaries, gallery accessibility smoke, wallpaper records, preview regression, release metadata, and launcher matrix), so the highest-value direction is distribution trust and maintainer feedback loops rather than another broad dashboard rewrite. Priority opportunities: sync stale v1.2.1 working-note/blocker truth with the shipped v1.2.2 code; make stale GitHub Release/Obtainium channel state visible locally while signing remains operator-blocked; add a strict F-Droid provenance/reproducibility mode; improve launcher failure diagnostics without telemetry; create a quality-review queue for low-confidence icons; import request candidates from local/ADB package inventories; add rendered web visual smoke; test Material You/Android 16 tint contrast; add pseudo-locale localization checks; and rehearse dependency/toolchain upgrades locally before F-Droid submission.

## Product Map
- Core workflows: install the APK through GitHub/Obtainium/F-Droid-style metadata; apply the pack through Blueprint-supported launchers or direct `iosiconpack://apply/<slug>` deep links; browse icons, eras, previews, wallpapers, and request status in the app/static gallery; file structured icon requests; maintainers generate icons, XML, provenance, wallpapers, previews, and release metadata with local scripts.
- User personas: Android custom-launcher users who want iOS-style icons; maintainers adding mappings and release assets; FOSS distribution reviewers; icon contributors who need source/provenance and safe-zone guidance; power users reporting launcher-specific failures.
- Platforms and distribution: Android minSdk 26/targetSdk 36, Gradle/AGP/Kotlin/KSP in `buildSrc`, Blueprint 2.5.1 dashboard, Python/Pillow maintainer tooling, GitHub tags/releases, F-Droid metadata, Fastlane listing assets, and GitHub Pages docs under `docs/`.
- Key integrations and data flows: `app/src/main/res/xml/appfilter.xml` and `app/src/main/assets/appfilter.xml` must remain parity-mapped; `drawable.xml` and themed wrapper/vector resources feed Blueprint/launchers; `icons_raw/` plus `scripts/fetch_icons.py` and `scripts/icontool.py` generate assets; `docs/index.html` and `docs/requests.html` expose gallery/request state; `LauncherApplyActivity.kt` maps launcher slugs to package intents and store/web fallbacks.

## Competitive Landscape
- Arcticons: large FOSS icon ecosystem with 14k+ icons, request/contribution workflows, F-Droid/Play distribution, and active issue patterns around launcher compatibility and style guidance. Learn contribution scale, review queues, and compatibility triage; avoid copying its monochrome-only promise because this repo's differentiator is iOS-era visual fidelity.
- Delta Icons: mature open-source Android icon pack with high coverage, Play/F-Droid flavors, and a separate dynamic-clock flavor when launcher/API support makes one feature expensive. Learn release-channel consistency and flavor isolation for truly divergent capabilities; avoid drifting into generic pastel identity.
- Lawnicons: reference point for Material You/native themed icons, in-app request flow, icon review discussions, and launcher/theme regressions. Learn icon-review gates, themed contrast checks, and request UX; avoid Lawnchair-only coupling.
- Blueprint and CandyBar: table-stakes dashboards cover apply, icon picker, icon request, help, wallpapers, settings, and many launchers. This project already gets most dashboard value through Blueprint; avoid a fork unless an item cannot be solved through resources, scripts, or a narrow activity.
- Icon Pack Studio and One4Studio adaptive packs: commercial products sell customization, import/tweak flows, adaptive/Material You variants, frequent updates, wallpapers, widgets, and clear unsupported-launcher guidance. Learn install guidance, adaptive previews, and user-facing failure explanations; avoid ads, tracking, billing, or paid request priority because the repo states free/open-source/no IAP.
- Obtainium and F-Droid: update trust depends on predictable version tags, release APK names, metadata, signatures, reproducible inputs, and clear source-specific filters. Learn channel smoke checks and reproducibility evidence; avoid claiming a channel is current when GitHub Releases or signing state says otherwise.
- Apple Icon Composer/Liquid Glass: Apple now pushes layered icon structures with light, dark, and mono appearances. Learn layered preview discipline and refraction/specular design QA; avoid requiring Apple-only tooling in the Android build pipeline.

## Security, Privacy, and Reliability
- Verified risk: `buildSrc/src/main/java/MyApp.kt`, F-Droid metadata, README, and tags are at v1.2.2, but `gh release list --repo SysAdminDoc/iOSIconPack` shows latest public GitHub Release as v1.1.9; `scripts/icontool.py release-channel-check` fails for missing v1.2.2. Manual GitHub and Obtainium installers can receive stale builds until operator publishing is resolved.
- Verified risk: `CLAUDE.md` and `Roadmap_Blocked.md` still describe v1.2.1-era build/release state while code and metadata are v1.2.2. This is ignored working-note drift, not app behavior, but it can misdirect future release work.
- Verified risk: `scripts/icontool.py developer-verification-check` reports the local v1.2.2 release APK and dev signer digest but no production signing certificate environment; Android developer verification enforcement begins September 2026 in Brazil, Indonesia, Singapore, and Thailand, then expands globally in 2027.
- Verified risk: `scripts/icontool.py maven-provenance-check` exits OK but reports many missing license/source URL metadata warnings for resolved artifacts. F-Droid/reproducible-build review will need a stricter, explainable allowlist rather than a pass with opaque warnings.
- Verified maintenance risk: `scripts/icontool.py dependency-audit` reports no core advisories, but AGP 8.12.0, Kotlin 2.2.21, KSP 2.3.4, and Pillow's broad `>=10.0.0` requirement all have newer releases available. Toolchain movement is expected before future API-level and F-Droid buildserver work.
- Missing guardrails: release-channel staleness is detectable only by running the CLI; install surfaces do not visibly distinguish "tag exists" from "APK release asset published"; launcher fallback failures do not produce a structured diagnostic payload; generated docs have static accessibility checks but no rendered mobile/dark/light visual smoke.
- Recovery and rollback needs: local release preflight should fail before publishing when version strings, tag refs, latest release, APK asset name, digest, signer digest, README/F-Droid metadata, and blocked-release notes disagree. No remote automation is needed.

## Architecture Assessment
- Boundary health: the Android app remains intentionally thin (`MainActivity.kt`, `MyApplication.kt`, `LauncherApplyActivity.kt`); most near-term value should stay in resources, generated assets, local Python validators, docs generation, and release tooling rather than a Blueprint fork.
- Refactor candidate: extend `scripts/icontool.py` release/developer-verification/provenance checks so stale working notes, missing release assets, signer mismatch, and F-Droid strict provenance warnings become deterministic local failures.
- Refactor candidate: add a telemetry-free diagnostic branch to `LauncherApplyActivity.kt` and related strings so failed launcher applies can surface launcher slug/package/fallback URL in a copyable report or prefilled issue link.
- Refactor candidate: add quality scoring near `scripts/fetch_icons.py`, provenance records, and preview regression so low-resolution sources, poor contrast, mask clipping, opaque corners, and Liquid Glass/themed variant gaps are queued before release.
- Refactor candidate: add request-import tooling that consumes ADB/package-manager dumps or saved launcher inventories, including non-ASCII labels and work-profile package identifiers, then emits local candidate mappings without sending data anywhere.
- Refactor candidate: expand `scripts/gen_gallery.py`/docs validation with rendered Playwright-style checks for `docs/index.html` and `docs/requests.html` across mobile/desktop and light/dark themes; current static smoke cannot catch clipping, overflow, or broken interactive states.
- Test/documentation gap: localization validation catches translatable boundaries, but there is no pseudo-locale round trip to expose string expansion, protected token breakage, or RTL layout pressure in generated docs/app text.
- Upgrade strategy: keep AGP/Kotlin/KSP/Pillow/Blueprint version changes behind a local rehearsal command that runs Gradle build/lint, `scripts/icontool.py check`, Maven provenance, release metadata, and F-Droid metadata smoke before any version bump lands.

## Rejected Ideas
- Premium icon requests or paid priority queues: sourced from CandyBar/Icon Pack Studio/One4Studio patterns; rejected because the repo promises no ads, tracking, or IAP and uses GitHub/FOSS distribution.
- Full Icon Pack Studio-style in-app editor/importer: sourced from Icon Pack Studio; rejected because it would turn a curated iOS-era pack into a general icon factory and add high maintenance cost.
- Immediate Blueprint fork for per-app era picker, shape-mask preview, or Figma-driven design surface: sourced from existing blocked roadmap and dashboard competitors; rejected for active planning because those items are blocked or high-maintenance until release/distribution truth is stable.
- Blindly chasing Arcticons/Delta icon counts: sourced from competitor coverage; rejected as a primary strategy because this project wins by recognizable iOS-style quality and multi-era assets, not raw icon volume.
- GitHub Actions, Dependabot, or Renovate automation: sourced from common OSS practice; rejected by repo/global policy. Local commands and manually pushed releases are the compatible path.
- Dynamic-clock flavor now: sourced from Delta's separate flavor; rejected until launcher demand appears because this repo's current value is static multi-era icon coverage and themed variants.
- Multi-user/cloud sync/plugin ecosystem: sourced from adjacent dashboard/customization products; rejected because the app stores no user account data and plugin loading would add privacy, support, and supply-chain risk without solving current distribution gaps.

## Sources
OSS competitors and dashboards
https://github.com/SysAdminDoc/iOSIconPack/releases
https://github.com/Arcticons-Team/Arcticons
https://arcticons.com/
https://github.com/Delta-Icons/android
https://github.com/LawnchairLauncher/lawnicons
https://github.com/jahirfiquitiva/Blueprint
https://github.com/zixpo/candybar
https://github.com/MiepHD/cuscon

Commercial and community signal
https://play.google.com/store/apps/details?hl=en-US&id=ginlemon.iconpackstudio
https://www.iconpackstudio.com/ips-exporter
https://www.one4studio.com/apps/icon-packs/adaptive
https://help.niagaralauncher.app/article/150-list-of-android-material-you-icon-packs
https://www.reddit.com/r/androidapps/comments/ubhzk4/what_are_your_favorite_icon_packs_for_android/

Platform and distribution
https://developer.android.com/develop/ui/compose/system/icon_design_adaptive
https://developer.android.com/developer-verification
https://support.google.com/android-developer-console/answer/16561738?hl=en
https://developer.apple.com/icon-composer/
https://developer.apple.com/videos/play/wwdc2025/361/
https://f-droid.org/en/docs/Reproducible_Builds/
https://f-droid.org/en/docs/Build_Metadata_Reference/
https://f-droid.org/en/docs/Submitting_to_F-Droid_Quick_Start_Guide/
https://forum.f-droid.org/t/app-icon-upgrades/10678
https://wiki.obtainium.imranr.dev/sources/
https://wiki.obtainium.imranr.dev/app_tracking/

Dependencies and advisories
https://developer.android.com/build/releases/about-agp
https://developer.android.com/build/releases/agp-9-2-0-release-notes
https://kotlinlang.org/docs/whatsnew24.html
https://github.com/google/ksp/releases
https://pillow.readthedocs.io/en/stable/releasenotes/index.html
https://osv.dev/

## Open Questions
- Needs live validation: which production signing certificate and Android developer verification identity will be used for official GitHub/Play/F-Droid-facing releases?
- Needs live validation: whether a local importable design-template artifact is acceptable as a substitute for the currently blocked Figma community-file work.
