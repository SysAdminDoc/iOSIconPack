<h1 align="center">iOS Icon Pack</h1>

<p align="center">
  <img alt="Version" src="https://img.shields.io/badge/version-v1.2.0-58A6FF?style=for-the-badge">
  <img alt="License" src="https://img.shields.io/badge/license-MIT-4ade80?style=for-the-badge">
  <img alt="Platform" src="https://img.shields.io/badge/platform-Android-58A6FF?style=for-the-badge">
  <img alt="minSdk" src="https://img.shields.io/badge/minSdk-26_(Android_8.0)-58A6FF?style=for-the-badge">
</p>

<p align="center">
  <a href="https://sysadmindoc.github.io/iOSIconPack/">
    <img alt="Icon Gallery" src="https://img.shields.io/badge/Gallery-Browse_Icons-4ade80?style=for-the-badge">
  </a>
  <a href="https://apps.obtainium.imranr.dev/redirect?r=obtainium://app/%7B%22id%22:%22com.sysadmindoc.iosicons%22,%22url%22:%22https://github.com/SysAdminDoc/iOSIconPack%22,%22author%22:%22SysAdminDoc%22,%22name%22:%22iOS%20Icon%20Pack%22,%22additionalSettings%22:%22%7B%5C%22apkFilterRegEx%5C%22:%5C%22release%5C%22%7D%22%7D">
    <img alt="Get it on Obtainium" src="https://img.shields.io/badge/Obtainium-Install-3B7DD8?style=for-the-badge">
  </a>
  <a href="https://github.com/SysAdminDoc/iOSIconPack/releases/latest">
    <img alt="GitHub Release" src="https://img.shields.io/github/v/release/SysAdminDoc/iOSIconPack?style=for-the-badge&label=Download&color=58A6FF">
  </a>
</p>

The ultimate iOS-style icon pack for Android. Every iOS generation in one app — pick and choose which era's icons to apply per-app.

## Install

**Obtainium (recommended — auto-updates):**

1. Install [Obtainium](https://github.com/ImranR98/Obtainium/releases/latest)
2. Tap this link on your phone:
   [`obtainium://add/https://github.com/SysAdminDoc/iOSIconPack`](https://apps.obtainium.imranr.dev/redirect?r=obtainium://app/%7B%22id%22:%22com.sysadmindoc.iosicons%22,%22url%22:%22https://github.com/SysAdminDoc/iOSIconPack%22,%22author%22:%22SysAdminDoc%22,%22name%22:%22iOS%20Icon%20Pack%22,%22additionalSettings%22:%22%7B%5C%22apkFilterRegEx%5C%22:%5C%22release%5C%22%7D%22%7D)
3. Install the latest APK and apply the icon pack in your launcher

**Manual:** Download the APK from [Releases](https://github.com/SysAdminDoc/iOSIconPack/releases/latest), install, then select the pack in your launcher's icon pack settings.

## Features

- **6 iOS Eras** — iOS 14, 15, 16, 17, 18, and iOS 26 Liquid Glass
- **Mix & Match** — Apply different generations to different apps
- **367 Icons + 671 appfilter entries** — 342 era variants across iOS 14, 15, 16, 17, 18, and iOS 26 Liquid Glass, plus 25 exact third-party icons
- **367 Material You themed vectors** — Android 13+ dynamic themed-icon support across every era
- **30+ Launcher Support** — Nova, Lawnchair, Smart Launcher, OnePlus, Samsung, Niagara, Microsoft Launcher, POCO, Pixel, and more
- **AMOLED Dark Theme** — Native dark mode dashboard
- **Icon Requests** — Request icons for apps not yet covered
- **Free & Open Source** — No ads, no tracking, no IAP

## iOS Generations

| Era | Style | Icons |
|-----|-------|-------|
| iOS 14 | Flat + gradient backgrounds | 57 |
| iOS 15 | Flat, subtle shadows | 57 |
| iOS 16 | Bold colors, refined squircle | 57 |
| iOS 17 | Refined flat | 57 |
| iOS 18 | Tinted/dark mode, refined gradients | 57 |
| iOS 26 | Liquid Glass — frosted translucent | 57 |

The pack applies **iOS 18** by default. Contributors can switch the active era at build time:

```bash
python3 scripts/set_era.py --list        # see active era
python3 scripts/set_era.py ios17         # switch to iOS 17
python3 scripts/set_era.py ios26         # iOS 26 Liquid Glass (partial)
python3 scripts/set_era.py ios18         # reset to default
```

## Supported Launchers

Nova, Lawnchair, Apex, Smart Launcher, OnePlus, Samsung One UI, LG Home, Sony, Projectivy, GO Launcher, ADW, Holo, Niagara, and 20+ more.

## Build

```bash
JAVA_HOME="C:/Program Files/Android/Android Studio/jbr" ./gradlew assembleDebug
JAVA_HOME="C:/Program Files/Android/Android Studio/jbr" ./gradlew assembleRelease
```

`assembleRelease` uses the committed development keystore only for local sanity
builds. Official publish builds must set `IOSICONS_PUBLISH_RELEASE=1`,
`IOSICONS_KEYSTORE_PATH`, `IOSICONS_STORE_PASSWORD`, `IOSICONS_KEY_ALIAS`,
`IOSICONS_KEY_PASSWORD`, and the documented `IOSICONS_RELEASE_CERT_SHA256`, then
run:

```bash
JAVA_HOME="C:/Program Files/Android/Android Studio/jbr" ./gradlew assembleRelease
python3 scripts/icontool.py publish-check
python3 scripts/icontool.py release-channel-check
python3 scripts/icontool.py developer-verification-check
```

## Backup Policy

iOS Icon Pack does not back up or transfer app-private data. The dashboard state
is disposable, and launcher icon choices can be reapplied from the shipped icon
catalog after reinstall. Android 11 and lower use `@xml/backup_rules`; Android
12+ uses `@xml/data_extraction_rules`.

## Contributing Icons

Use `icontool` — it wires all XML files in one command:

```bash
# Add a new iOS stock icon (PNG must already be in drawable-xxxhdpi/):
python3 scripts/icontool.py add ios18_appname \
    -c "com.example.app/com.example.app.MainActivity"

# Add a third-party icon:
python3 scripts/icontool.py add tp_appname \
    -c "com.example.app/com.example.app.MainActivity"

# Validate appfilter, drawables, and release metadata:
python3 scripts/icontool.py check

# Validate only release metadata and tag alignment:
python3 scripts/icontool.py release-check

# Validate the public GitHub release channel before publishing/install docs:
python3 scripts/icontool.py release-channel-check

# Report Android developer verification readiness for sideload/store channels:
python3 scripts/icontool.py developer-verification-check
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for the full workflow, naming conventions, and PR checklist.

## Credits

- Dashboard: [Blueprint](https://github.com/jahirfiquitiva/Blueprint) by Jahir Fiquitiva
- Built with Kotlin and the Android SDK

## License

MIT — see [LICENSE](LICENSE).
