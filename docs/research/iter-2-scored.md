# iter-2 Scored Items — 2026-04-25

## Now Tier

- name: F-Droid metadata for submission
  one_line: Add fdroiddata-compatible metadata YAML to enable F-Droid distribution
  sources: [https://f-droid.org/docs/Submitting_to_F-Droid/]
  category: distribution/packaging
  prevalence: table-stakes
  fit: { score: align, reasoning: "Free open-source app, reproducible build — perfect F-Droid candidate" }
  impact: { score: 5, reasoning: "Opens largest alternative Android app store for privacy-first users" }
  effort: { score: 1, reasoning: "Metadata YAML + screenshots only" }
  risk: { score: low, reasoning: "No code changes required" }
  novelty: { score: parity, reasoning: "All major OSS icon packs are on F-Droid" }
  tier: Now
  priority: P1

- name: Fix CLAUDE.md doc drift
  one_line: Update stale appfilter count (247→451) and version state in working notes
  sources: [internal]
  category: docs
  prevalence: table-stakes
  fit: { score: align }
  impact: { score: 2, reasoning: "Prevents confusion in future factory runs" }
  effort: { score: 1, reasoning: "Text edits only" }
  risk: { score: low }
  novelty: { score: parity }
  tier: Now
  priority: P1

## Next Tier

- name: Expand icon coverage to 50+ per era
  one_line: Add more iOS-era-specific icon assets for top Play Store apps
  sources: [https://github.com/Donnnno/Arcticons]
  category: UX
  prevalence: table-stakes
  fit: { score: align, reasoning: "Core value proposition of the pack" }
  impact: { score: 5 }
  effort: { score: 4, reasoning: "Requires fetching, color-grading, and mapping per icon per era" }
  risk: { score: low }
  novelty: { score: parity }
  tier: Next
  priority: P0

- name: Hand-crafted monochrome vectors for top 25 icons
  one_line: Replace bitmap monochrome stubs with proper single-color vectors
  sources: [https://developer.android.com/about/versions/16]
  category: UX
  prevalence: emerging
  fit: { score: align }
  impact: { score: 3, reasoning: "Android 16 auto-theming reduces urgency but quality gap remains" }
  effort: { score: 3, reasoning: "25 hand-drawn vector paths" }
  risk: { score: low }
  novelty: { score: differentiator }
  tier: Next
  priority: P1

## Later Tier

- name: Glyph-only (backgroundless) variant
  one_line: Transparent-background icon set with border stroke for wallpaper readability
  sources: [https://github.com/nicholasgasior/cuscon]
  category: UX
  tier: Later
  priority: P2

- name: Per-app era picker
  one_line: Blueprint UI for choosing which iOS era to apply per app
  sources: [https://github.com/jahirfiquitiva/Blueprint]
  category: UX
  tier: Later
  priority: P0 (blocked on Blueprint fork)

- name: Shape-mask preview
  one_line: Dashboard preview of icons in different launcher mask shapes
  sources: [https://github.com/amirzaidi/Launcher3]
  category: UX
  tier: Later
  priority: P1

## Rejected

- name: IPA extraction mode for fetch_icons.py
  reasoning: Legal complexity of extracting from Apple IPAs; iTunes Search API already provides the real artwork
  tier: Rejected
