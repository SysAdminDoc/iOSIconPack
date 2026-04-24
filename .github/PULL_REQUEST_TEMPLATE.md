## Summary
<!-- One or two sentences. What does this PR change and why? -->

## Checklist
- [ ] Icon drawables follow the `ios{version}_{app}` naming convention (`ios26_lg_{app}` for Liquid Glass)
- [ ] `appfilter.xml` updated in **both** `app/src/main/res/xml/` and `app/src/main/assets/`
- [ ] `drawable.xml` updated in **both** `app/src/main/res/xml/` and `app/src/main/assets/`
- [ ] `appmap.xml` and `res/values/icon_pack.xml` arrays reflect the new entries
- [ ] Local build passes: `./gradlew assembleDebug` (Windows: `JAVA_HOME="C:/Program Files/Android/Android Studio/jbr" ./gradlew assembleDebug`)
- [ ] Appfilter/drawable validator passes: `python3 scripts/validate_appfilter.py`
- [ ] No Play Store assets, screenshots, or marketing copy mention unreleased iOS versions that are not in the pack

## Era coverage
<!-- Which eras gained icons or mappings? -->

## Screenshots (for UI / theme / launcher-integration changes)
