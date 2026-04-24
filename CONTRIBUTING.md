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

## Appfilter + drawable wiring

Every new icon must be wired into four places:

1. `app/src/main/res/xml/appfilter.xml`
2. `app/src/main/assets/appfilter.xml` (byte-identical — Blueprint reads both)
3. `app/src/main/res/xml/drawable.xml`
4. `app/src/main/assets/drawable.xml` (byte-identical)

The validator enforces this:

```bash
python3 scripts/validate_appfilter.py
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
- [ ] All four XML files updated
- [ ] `python3 scripts/validate_appfilter.py` passes locally
- [ ] `./gradlew assembleDebug` passes locally
- [ ] Screenshots attached if you changed the dashboard / launcher integration
