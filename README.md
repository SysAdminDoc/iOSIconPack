# iOS Icon Pack

![Version](https://img.shields.io/badge/version-v2.5.1-blue) ![License](https://img.shields.io/badge/license-MIT-green) ![Platform](https://img.shields.io/badge/platform-Kotlin-lightgrey)

The ultimate iOS-style icon pack for Android. Every iOS generation in one app - pick and choose which era's icons to apply per-app.

## Features

- **6 iOS Eras** - iOS 14, 15, 16, 17, 18, and iOS 26 Liquid Glass
- **Mix & Match** - Apply different generations to different apps
- **110+ Icons** - 20 per era covering the most popular apps
- **30+ Launcher Support** - Nova, Lawnchair, Smart Launcher, OnePlus, Samsung, and more
- **AMOLED Dark Theme** - Native dark mode dashboard
- **Icon Requests** - Request icons for apps not yet covered
- **Free & Open Source** - No ads, no tracking, no IAP

## iOS Generations

| Era | Style | Icons |
|-----|-------|-------|
| iOS 14 | Flat + gradient backgrounds | 20 |
| iOS 15 | Flat, subtle shadows | 20 |
| iOS 16 | Bold colors, refined squircle | 20 |
| iOS 17 | Refined flat | 20 |
| iOS 18 | Tinted/dark mode, refined gradients | 20 |
| iOS 26 | Liquid Glass - frosted translucent | 10 |

## Supported Launchers

Nova, Lawnchair, Apex, Smart Launcher, OnePlus, Samsung One UI, LG Home, Sony, Projectivy, GO Launcher, ADW, Holo, and 20+ more.

## Build

```bash
./gradlew assembleDebug
```

## Contributing Icons

1. Design your icon as a 192x192 SVG with the iOS squircle shape
2. Convert to Android Vector Drawable XML
3. Place in `app/src/main/res/drawable/` following naming: `ios{ver}_{app}.xml`
4. Update `appfilter.xml`, `drawable.xml`, `appmap.xml`, and `icon_pack.xml`
5. Submit a PR

## Credits

- Dashboard: [Blueprint](https://github.com/jahirfiquitiva/Blueprint) by Jahir Fiquitiva
- Built with Kotlin and Android SDK

## License

Apache License 2.0
