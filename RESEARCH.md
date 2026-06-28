# Research - iOS Icon Pack

## Executive Summary
iOS Icon Pack is an Android Blueprint-based icon pack whose strongest shape is asset discipline: 367 PNG icons, 671 component mappings, dual `res/xml` + `assets` validation, per-era browsing, Material You themed wrappers, and local-only tooling. The highest-value direction is to harden release trust and distribution before adding more artwork: fix the v1.2.0 tag/metadata mismatch, prevent accidental public releases signed with the fallback dev keystore, make backup/data extraction explicit, restore local lint/resource gates, and add launcher/gallery accessibility validation around the growing catalog. Top opportunities: P0 tag/release consistency, P0 release-signing guard, P1 backup rules, P1 lint/resource gate, P1 launcher compatibility matrix, P1 request-triage local tooling, P1 gallery accessibility pass, P2 source-art provenance manifest, P2 dependency/security update audit.

## Product Map
- Core workflows: install APK via GitHub/Obtainium/F-Droid-style metadata, apply the pack through supported launchers, browse icons by era in Blueprint, request missing icons through GitHub Issues/pages, maintain mappings through `scripts/icontool.py`.
- User personas: Android theming users who want iOS-style icons, privacy/open-source users who prefer GitHub/F-Droid distribution, contributors adding app icons and component mappings, maintainers shipping signed APK/AAB artifacts.
- Platforms and distribution: Android minSdk 26/targetSdk 36, Blueprint v2.5.1 dashboard, GitHub Releases, Obtainium link, GitHub Pages gallery, F-Droid metadata in `fdroid/metadata/com.sysadmindoc.iosicons.yml`.
- Key integrations and data flows: launcher intent filters in `app/src/main/AndroidManifest.xml`, `appfilter.xml` and `drawable.xml` copied under both `res/xml` and `assets`, GitHub Issues API in `docs/requests.html`, iTunes Search API workflow in `fetch_icons.py`, local validation through `scripts/icontool.py check`.

## Competitive Landscape
- Arcticons: large open-source Android icon pack with F-Droid presence and a mature request/contributor model. Learn scalable contribution intake and vector-first QA; avoid chasing icon count at the expense of iOS era fidelity.
- Delta Icons: open icon pack with broad coverage and alternate icons. Learn coverage breadth and discoverability; avoid letting alternates become uncurated style drift.
- Lawnicons: launcher-adjacent themed icon set optimized for monochrome/system theming. Learn strict themed-icon consistency and mapping hygiene; avoid becoming Lawnchair-specific because this pack's value is cross-launcher compatibility.
- Blueprint: active icon-pack dashboard framework already used by the repo. Keep upstream compatibility for apply/request/browse features; avoid a fork unless a future per-app era picker has a clear maintenance plan.
- CandyBar: older dashboard ecosystem with mature icon-pack conventions, now less attractive as a dependency direction. Learn from its icon request/wallpaper/Muzei patterns; avoid migrating away from Blueprint without a concrete payoff.
- Icon Pack Studio: commercial customization tool for masks, backgrounds, and user-generated packs. Learn from live preview/customization ergonomics; avoid turning this project into a generic icon designer that weakens the curated iOS-era identity.
- Obtainium/F-Droid/IzzyOnDroid: distribution comparables rather than design competitors. Learn strict tag, APK, metadata, and reproducibility expectations; avoid release metadata that points at missing tags or unsigned/dev-signed artifacts.

## Security, Privacy, and Reliability
- `fdroid/metadata/com.sysadmindoc.iosicons.yml` references `v1.2.0`, `README.md` badges advertise v1.2.0, and `buildSrc/src/main/java/MyApp.kt` is 1.2.0, but `git tag --list` only shows tags through `v1.1.9`. Verified: this can break tag-based F-Droid updates and release traceability.
- `app/build.gradle` release signing falls back to `iosicons.jks` with literal `iconpack123` passwords. Verified: useful for contributor builds, but unsafe as a publish path unless official release tasks fail closed on missing env signing and known certificate fingerprint checks.
- `app/src/main/AndroidManifest.xml` sets `android:allowBackup="true"` and `android:fullBackupContent="true"` without explicit backup/data-extraction rules. Verified: backup behavior should be intentional because Blueprint/request flows can involve installed-app selections and user settings.
- `app/src/main/res/xml/network_security_config.xml` denies cleartext traffic. Verified: keep this guard.
- `docs/requests.html` handles GitHub API rate limits with localStorage cache and a warning state. Verified: good resilience, but local duplicate/covered-request triage moved from removed GitHub Actions to no local maintainer tool.

## Architecture Assessment
- `scripts/validate_appfilter.py` and `scripts/validate_drawables.py` are strong boundaries for the asset/XML model; extend them rather than adding new manual checklists.
- `app/build.gradle` has `lint.abortOnError false` and `release.shrinkResources false` despite the expanding PNG/vector catalog. Add a local release gate with lint baseline and APK size/resource reporting.
- `app/src/main/AndroidManifest.xml` contains broad launcher intent filters; add a local manifest/theme_resources/appfilter compatibility smoke matrix for Nova, Lawnchair, Smart, Samsung, OnePlus, Niagara, Pixel, and generic ADW channels.
- `docs/index.html` search/filter/tab controls lack explicit label/pressed semantics, while `docs/requests.html` has a better `aria-live` request list and explicit rate-limit state. Harden the static gallery with keyboard and screen-reader checks.
- `fetch_icons.py` and ignored `icons_raw/` preserve raw-download workflow locally, but committed PNGs do not carry source URL/hash/license/provenance metadata. Add a small provenance manifest validated alongside drawable files.
- Testing gap: Python validators exist, but there is no local command that bundles validators, lint/resource checks, release metadata checks, and launcher compatibility into one publish preflight.

## Rejected Ideas
- IPA extraction for Apple artwork: rejected from prior research and still not recommended because legal and maintenance risk outweighs value; iTunes/public artwork plus original era treatment is safer.
- GitHub Actions issue triage or release automation: rejected because repo policy requires local builds/checks and no workflow files.
- Blueprint-to-CandyBar migration: rejected because Blueprint is active in this repo and migration would trade known working behavior for churn.
- Full in-app icon design studio: rejected because Icon Pack Studio already owns that space and it would dilute the curated iOS-era pack identity.
- Multi-user/team backend: not recommended now because this is a static asset pack; GitHub Issues and local maintainer tools cover collaboration without hosting user data.
- Plugin ecosystem: not recommended now because launchers consume static icon pack resources; export formats belong as targeted roadmap items, not a generic plugin system.

## Sources
Project and local evidence:
- https://github.com/SysAdminDoc/iOSIconPack
- https://sysadmindoc.github.io/iOSIconPack/

OSS competitors and adjacent projects:
- https://github.com/Arcticons-Team/Arcticons
- https://github.com/Delta-Icons/android
- https://github.com/LawnchairLauncher/lawnicons
- https://github.com/jahirfiquitiva/Blueprint
- https://github.com/zixpo/candybar
- https://github.com/danimahardhika/candybar-library
- https://github.com/Whiskers-Apps/droid-icons

Commercial and distribution comparables:
- https://play.google.com/store/apps/details?id=ginlemon.iconpackstudio
- https://github.com/ImranR98/Obtainium
- https://f-droid.org/docs/Submitting_to_F-Droid_Quick_Start_Guide/
- https://apt.izzysoft.de/fdroid/index/request
- https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases

Platform, standards, and dependency references:
- https://developer.android.com/develop/ui/views/launch/icon_design_adaptive
- https://developer.android.com/privacy-and-security/risks/backup-best-practices
- https://developer.android.com/privacy-and-security/security-config
- https://developer.android.com/build/releases/gradle-plugin
- https://kotlinlang.org/docs/releases.html
- https://github.com/google/ksp/releases
- https://developer.apple.com/design/human-interface-guidelines/app-icons
- https://developer.apple.com/videos/play/wwdc2025/219/
- https://osv.dev/

## Open Questions
- What certificate fingerprint should be treated as the official release signing identity?
- Should Android backup preserve only harmless dashboard preferences, or should backup be disabled entirely for the icon pack?
