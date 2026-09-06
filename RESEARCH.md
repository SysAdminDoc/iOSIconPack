# Product and Marketing Review

Date: 2026-09-06

## Positioning

iOS Icon Pack is for Android users who want the visual character of iOS without giving up launcher choice. Its strongest point is the six-era catalog. Most competing packs sell one fixed look, while this project lets people browse matching artwork from iOS 14 through iOS 18 and iOS 26 Liquid Glass.

The public pitch should lead with the product, not the maintenance tooling. Users need to see the icons and wallpapers before they read catalog internals.

## Verified product evidence

- 342 era variants, with 57 icons in each of six styles
- 25 exact icons for popular third-party apps
- 671 Android package and activity mappings
- 367 monochrome vectors for Material You themes
- 367 transparent glyph variants
- Six original wallpapers stored in the APK for offline use
- No ads, analytics, in-app purchases, billing permission, or license-check permission

The Android 15 test pass covered the dashboard, icon browser, search, launcher list, request screen, wallpaper preview, local save, and system wallpaper application. The screenshot set in `assets/screenshots/` comes from the running app.

## Competitive signal

Arcticons and Lawnicons set a high bar for open icon coverage and contribution workflows. Delta Icons shows how a focused visual identity can remain recognizable across a large catalog. Commercial packs such as Icon Pack Studio and One4Studio put visual proof, launcher guidance, and frequent artwork updates near the top of their listings.

iOS Icon Pack should not compete on raw icon count alone. Its advantage is a coherent, recognizable style across several generations. The live comparison gallery makes that difference visible.

## Marketing decisions

### Keep the existing app mark

The stacked-square mark is compact, recognizable, and readable at launcher size. It also fits the blue Android launcher artwork already shipped by the project. The README uses the matched light and dark exports for clean contrast on either GitHub theme. Decorative replacement concepts were rejected because they weakened small-size clarity.

### Show the real product

The README now opens with six verified app screenshots. They cover the dashboard and catalog first, then wallpaper preview, launcher application, and requests. This gives visitors enough evidence to understand the product before installing it.

### Replace the wallpaper set

The prior procedural backgrounds looked generic beside the icon artwork. The new set uses six distinct compositions with a shared finish. Every source is stored under `assets/wallpapers/sources/`, then cropped and compressed by the deterministic generator.

### Make the dashboard useful on first launch

The former home cards repeated placeholder Android symbols. The primary cards now open the live gallery, current signed release, and structured request form. Real catalog icons give each action a clear visual anchor.

### State launcher limits plainly

The listing should promise compatibility only where Android launchers accept icon packs. Stock Pixel Launcher does not provide a third-party pack picker. Samsung users need Theme Park. Clear guidance prevents a polished listing from creating the wrong expectation.

### Treat privacy as product proof

The inherited billing and license-check permissions did not match the project's free, open-source promise. Removing them makes the APK behavior agree with the listing copy.

## Distribution priorities

1. Keep the signed GitHub Release and Obtainium channel on the same version.
2. Submit the existing metadata to F-Droid when the maintainer account is available.
3. Prepare a Play Console listing and enroll the store build in Play App Signing if a Play release is planned.
4. Continue request-led coverage work without weakening the six-era visual standard.

## Sources

- https://github.com/Arcticons-Team/Arcticons
- https://github.com/Delta-Icons/android
- https://github.com/LawnchairLauncher/lawnicons
- https://github.com/jahirfiquitiva/Blueprint
- https://www.iconpackstudio.com/
- https://www.one4studio.com/apps/icon-packs/adaptive
- https://wiki.obtainium.imranr.dev/sources/
- https://f-droid.org/en/docs/Submitting_to_F-Droid_Quick_Start_Guide/
- https://developer.android.com/develop/ui/views/launch/icon_design_adaptive
