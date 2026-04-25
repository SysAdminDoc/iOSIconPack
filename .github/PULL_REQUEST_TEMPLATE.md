## Summary
<!-- One or two sentences. What does this PR change and why? -->

## Checklist
- [ ] Icon drawables follow the naming convention (`ios{ver}_{app}`, `ios26_lg_{app}`, `tp_{app}`)
- [ ] XML wiring done via `python3 scripts/icontool.py add <drawable> -c <component>` (or `link` for aliases)
- [ ] `python3 scripts/icontool.py check` passes locally
- [ ] Local build passes: `./gradlew assembleDebug`
- [ ] No Play Store assets, screenshots, or marketing copy mention unreleased iOS versions that are not in the pack

## Era coverage
<!-- Which eras gained icons or mappings? -->

## Screenshots (for UI / theme / launcher-integration changes)
