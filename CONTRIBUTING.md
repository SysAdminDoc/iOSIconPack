# Contributing to iOS Icon Pack

Thanks for helping improve the pack. This doc covers the two most common
contributions: new icons and appfilter entries. For dashboard / build tooling
changes, open a Feature request issue first so we can agree on scope.

## Icon conventions

- **Source**: 1024x1024 PNG exported from your design tool of choice.
- **Target**: `app/src/main/res/drawable-xxxhdpi/ios{ver}_{app}.png` (192x192
  after the Gradle `processResources` pipeline optimizes it).
- **Liquid Glass variants**: `ios26_lg_{app}.png`.
- **Third-party apps without an era assignment**: `tp_{app}.png`.
- Every icon foreground must fit inside the inner **66x66dp safe-area** of the
  108x108dp canvas. Edge-to-edge art gets clipped on OEM masks (teardrop,
  circle).

## Switching eras

The pack ships six icon generations (iOS 14–18 and iOS 26 Liquid Glass). By
default the pack applies iOS 18 icons to your launcher. To switch the active
era for a build or for personal preference:

```bash
# List available eras and show which one is currently active
python3 scripts/set_era.py --list

# Switch to iOS 17
python3 scripts/set_era.py ios17

# Switch to iOS 26 Liquid Glass
# (10 icons have LG variants; the rest stay on iOS 18 automatically)
python3 scripts/set_era.py ios26

# Preview changes without writing anything
python3 scripts/set_era.py ios16 --dry-run

# Reset to the default
python3 scripts/set_era.py ios18
```

After switching, rebuild the APK:

```bash
JAVA_HOME="C:/Program Files/Android/Android Studio/jbr" ./gradlew assembleRelease
```

> **Note:** iOS 14–17 and iOS 26 LG icons are also visible in the Blueprint
> dashboard (browse-only) regardless of the active era. The active era only
> controls what gets applied automatically by your launcher.

## Appfilter + drawable wiring

Every new icon must be wired into four XML files. The `icontool` script does
this in one command instead of four manual edits.

### Using icontool (recommended)

```bash
# Add a new stock iOS icon (PNG must exist in drawable-xxxhdpi first):
python3 scripts/icontool.py add ios18_safari \
    -c "com.android.browser/com.android.browser.BrowserActivity"

# Add a third-party icon with multiple package aliases:
python3 scripts/icontool.py add tp_spotify \
    -c "com.spotify.music/com.spotify.music.MainActivity" \
    -c "com.spotify.music/com.spotify.music.SpotifyActivity"

# Alias an existing drawable to a new launcher variant (appfilter only):
python3 scripts/icontool.py link ios18_phone \
    -c "com.nothing.dialer/com.nothing.dialer.DialtactsActivity"

# Batch-import: drop PNGs in drawable-xxxhdpi/, then sync drawable.xml:
python3 scripts/icontool.py rebuild

# Preview what rebuild would change without writing:
python3 scripts/icontool.py rebuild --dry-run

# Remove a component mapping:
python3 scripts/icontool.py remove \
    -c "com.android.browser/com.android.browser.BrowserActivity"

# Validate everything after manual XML edits:
python3 scripts/icontool.py check
```

> **Note on `tp_` icons:** Third-party drawables (`tp_*`) are intentionally
> excluded from `drawable.xml` — they live only in `appfilter.xml` and on disk.
> `icontool add` handles this automatically.

### Manual wiring (if icontool is unavailable)

Four files must stay in sync — edit all four or the validator will fail:

1. `app/src/main/res/xml/appfilter.xml`
2. `app/src/main/assets/appfilter.xml` (byte-identical — Blueprint reads both)
3. `app/src/main/res/xml/drawable.xml`
4. `app/src/main/assets/drawable.xml` (byte-identical)

After manual edits, run `python3 scripts/icontool.py sync` to copy the
`res/xml/` files to `assets/` in one step.

### Validation

```bash
python3 scripts/validate_appfilter.py
# or via icontool:
python3 scripts/icontool.py check
```

CI runs the same script on every PR; PRs with missing or drifted entries fail.

## Build

```bash
# Windows (the primary dev target)
JAVA_HOME="C:/Program Files/Android/Android Studio/jbr" ./gradlew assembleDebug

# macOS / Linux
./gradlew assembleDebug
```

Release signing reads from env vars so CI never logs secrets:

```bash
IOSICONS_STORE_PASSWORD=... IOSICONS_KEY_ALIAS=... IOSICONS_KEY_PASSWORD=... \
  ./gradlew assembleRelease bundleRelease
```

Offline contributors fall back to the committed `iosicons.jks` dev keystore,
which is fine for local sanity builds but is never used to sign a GitHub
Release artifact.

## Commit style

- One commit per logical change. "Why" in the subject, not "what".
- Don't amend pushed commits. Follow-up fixes land as new commits.
- Don't add AI-agent attribution (`Co-Authored-By` trailers etc.) — the repo
  policy rejects those.

## Pull request checklist

The PR template enumerates the full list; the short version:

- [ ] Icon art follows the naming convention above
- [ ] `python3 scripts/icontool.py check` passes locally (or `validate_appfilter.py` directly)
- [ ] `./gradlew assembleDebug` passes locally
- [ ] Screenshots attached if you changed the dashboard / launcher integration
