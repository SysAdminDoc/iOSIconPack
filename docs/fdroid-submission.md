# F-Droid Submission Guide

## Prerequisites
- GitLab account (https://gitlab.com)
- Fork of https://gitlab.com/fdroiddata/fdroiddata

## Steps

### 1. Fork fdroiddata
```bash
# On GitLab, fork fdroiddata/fdroiddata to your account
```

### 2. Add metadata file
Copy `fdroid/metadata/com.sysadmindoc.iosicons.yml` from this repo into
`metadata/com.sysadmindoc.iosicons.yml` in your fdroiddata fork.

### 3. Validate locally
```bash
cd fdroiddata
fdroid readmeta
fdroid rewritemeta com.sysadmindoc.iosicons
fdroid checkupdates --allow-dirty com.sysadmindoc.iosicons
fdroid lint com.sysadmindoc.iosicons
```

### 4. Open Merge Request
- Target: `fdroiddata/fdroiddata` master branch
- Title: `Add iOS Icon Pack (com.sysadmindoc.iosicons)`
- Description: iOS-style icon pack for Android covering 6 Apple design eras.
  MIT licensed, reproducible Gradle build, no proprietary dependencies.

### 5. Checklist (from F-Droid docs)
- [x] App builds with `fdroid build -v -l com.sysadmindoc.iosicons`
- [x] No proprietary dependencies
- [x] MIT license
- [x] No tracking/analytics
- [x] Source code publicly available
- [x] AutoUpdateMode configured for tag-based updates

## IzzyOnDroid
IzzyOnDroid tracks GitHub releases directly. Requirements:
1. GitHub releases with APK artifacts attached (already done via CI)
2. F-Droid-compatible metadata in repo (already at `fdroid/metadata/`)
3. Submit via https://apt.izzysoft.de/fdroid/index/request

No additional metadata needed beyond what we already ship.
