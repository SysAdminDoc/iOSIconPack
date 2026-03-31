# iOS Icon Pack - CLAUDE.md

## Overview
iOS-style icon pack for Android. All iOS generations (14-18 + 26 Liquid Glass) in one APK.
Users pick and choose which era's icons to apply per-app.

## Tech Stack
- **Dashboard**: Blueprint v2.5.1 by Jahir Fiquitiva (BottomNavigationBlueprintActivity)
- **Language**: Kotlin
- **Min SDK**: 23 / Target SDK: 36
- **Build**: Gradle 8.12, AGP 8.12.0, Kotlin 2.2.21, KSP 2.3.4
- **Package**: com.sysadmindoc.iosicons

## Architecture
Blueprint handles the entire dashboard UI (icon browsing, applying, requests).
Our job is providing the icon assets and XML configuration:

- `res/drawable/ios{ver}_{app}.xml` - Vector drawable icons (192x192 viewport, squircle path)
- `res/xml/appfilter.xml` + `assets/appfilter.xml` - Maps Android ComponentInfo to icon drawables
- `res/xml/drawable.xml` + `assets/drawable.xml` - Categorized icon list for dashboard browser
- `res/xml/appmap.xml` - Activity-to-icon mapping (alt format for some launchers)
- `res/xml/theme_resources.xml` - Launcher theme detection
- `res/values/icon_pack.xml` - Preview icons and filter categories

## Icon Naming Convention
- `ios{version}_{app_name}` - e.g. `ios18_safari`, `ios14_messages`
- `ios26_lg_{app_name}` - Liquid Glass variant

## Current State
- v1.0.0 scaffolded
- 110 placeholder icons (colored squircles) across 6 iOS eras
- 20 icons per era (14, 15, 16, 17, 18) + 10 Liquid Glass
- 214 appfilter entries mapping to popular Android apps
- AMOLED dark theme with iOS blue accent (#007AFF / #0A84FF)
- Billing/license checking disabled (free & open source)
- Supports 30+ launchers via Blueprint manifest intent-filters

## Adding New Icons
1. Create vector drawable in `res/drawable/ios{ver}_{name}.xml`
2. Add `<item drawable="ios{ver}_{name}" />` to both `res/xml/drawable.xml` AND `assets/drawable.xml`
3. Add component mapping to both `res/xml/appfilter.xml` AND `assets/appfilter.xml`
4. Update `res/xml/appmap.xml`
5. Add to appropriate arrays in `res/values/icon_pack.xml`

## Build
```bash
./gradlew assembleDebug    # Debug APK
./gradlew assembleRelease  # Release APK (needs signing config)
```

## Key Files
- `buildSrc/src/main/java/MyApp.kt` - Version info
- `app/src/main/kotlin/.../MainActivity.kt` - Dashboard config
- `app/src/main/res/values/colors.xml` - iOS-inspired color palette
- `app/src/main/res/values/blueprint_setup.xml` - Blueprint behavior config

## Next Steps
- Replace placeholder squircles with actual iOS-inspired icon art
- Add more appfilter entries (target 500+ apps)
- Add Google, Social, Games category icons
- Generate Gradle wrapper (gradlew/gradlew.bat)
- Add signing config for release builds
- Create proper app icon (ic_launcher PNGs for pre-v26)

## Version History
- v1.0.0 - Initial scaffold, 110 placeholder icons, 214 appfilter entries, Blueprint dashboard, Gradle wrapper
