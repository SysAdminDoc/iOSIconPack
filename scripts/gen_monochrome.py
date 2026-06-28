#!/usr/bin/env python3
"""Scaffold Android 13+ monochrome layers for every ios18_* and tp_* icon.

Android 13 introduced the `<monochrome>` layer inside `<adaptive-icon>` XML.
Launchers that support themed icons (Pixel Launcher, Lawnchair 14+) tint this
layer using the user's wallpaper-derived Material You color.

This script generates `drawable/<name>_mono.xml` files. High-visibility icons
use hand-crafted single-color vectors; any icon without a vector template falls
back to a `<bitmap>` pointing at the existing raster PNG.

Also generates `drawable/<name>_themed.xml` adaptive-icon wrappers that
reference the monochrome stub, making the icons compatible with launchers that
apply themed-icon support via adaptive-icon XML (e.g. Pixel Launcher).

Usage:
    python3 scripts/gen_monochrome.py            # generate all stubs
    python3 scripts/gen_monochrome.py --dry-run  # preview without writing
    python3 scripts/gen_monochrome.py --force    # overwrite existing stubs
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DRAWABLE_DIR = REPO_ROOT / "app" / "src" / "main" / "res" / "drawable"
PACK_DIR = REPO_ROOT / "app" / "src" / "main" / "res" / "drawable-xxxhdpi"

MONO_TEMPLATE = """\
<?xml version="1.0" encoding="utf-8"?>
<!--
    Monochrome stub for {name}.
    Replace with a hand-crafted vector <path> for better themed-icon results.
    See: https://developer.android.com/develop/ui/views/launch/icon_design_adaptive#monochrome
-->
<bitmap xmlns:android="http://schemas.android.com/apk/res/android"
    android:src="@drawable/{name}" />
"""

MONO_VECTOR_TEMPLATE = """\
<?xml version="1.0" encoding="utf-8"?>
<!-- Hand-crafted monochrome vector for {name}. -->
<vector xmlns:android="http://schemas.android.com/apk/res/android"
    android:width="192dp"
    android:height="192dp"
    android:viewportWidth="192"
    android:viewportHeight="192">
{paths}
</vector>
"""

THEMED_TEMPLATE = """\
<?xml version="1.0" encoding="utf-8"?>
<!--
    Adaptive-icon wrapper that exposes a monochrome layer for Android 13+
    themed-icon support. Launchers read this when the user enables "Themed icons".
-->
<adaptive-icon xmlns:android="http://schemas.android.com/apk/res/android">
    <background android:drawable="@color/ic_launcher_background" />
    <foreground android:drawable="@drawable/{name}" />
    <monochrome android:drawable="@drawable/{name}_mono" />
</adaptive-icon>
"""

MONO_VECTOR_PATHS: dict[str, tuple[str, ...]] = {
    "ios18_appstore": (
        '<path android:fillColor="#00000000" android:strokeColor="#FFFFFFFF" android:strokeWidth="13" android:strokeLineCap="round" android:strokeLineJoin="round" android:pathData="M72,132 L96,58 L120,132" />',
        '<path android:fillColor="#00000000" android:strokeColor="#FFFFFFFF" android:strokeWidth="13" android:strokeLineCap="round" android:pathData="M58,112 H134" />',
        '<path android:fillColor="#00000000" android:strokeColor="#FFFFFFFF" android:strokeWidth="13" android:strokeLineCap="round" android:pathData="M79,58 L63,82 M113,58 L129,82" />',
    ),
    "ios18_calculator": (
        '<path android:fillColor="#00000000" android:strokeColor="#FFFFFFFF" android:strokeWidth="10" android:strokeLineJoin="round" android:pathData="M58,36 H134 C142,36 148,42 148,50 V142 C148,150 142,156 134,156 H58 C50,156 44,150 44,142 V50 C44,42 50,36 58,36 Z" />',
        '<path android:fillColor="#FFFFFFFF" android:pathData="M60,54 H132 V78 H60 Z M63,96 H78 V111 H63 Z M89,96 H104 V111 H89 Z M115,96 H130 V111 H115 Z M63,122 H78 V137 H63 Z M89,122 H104 V137 H89 Z M115,122 H130 V137 H115 Z" />',
    ),
    "ios18_calendar": (
        '<path android:fillColor="#00000000" android:strokeColor="#FFFFFFFF" android:strokeWidth="10" android:strokeLineJoin="round" android:pathData="M48,48 H144 V148 H48 Z" />',
        '<path android:fillColor="#FFFFFFFF" android:pathData="M48,48 H144 V76 H48 Z M66,34 H78 V58 H66 Z M114,34 H126 V58 H114 Z M68,94 H84 V110 H68 Z M92,94 H108 V110 H92 Z M116,94 H132 V110 H116 Z M68,120 H84 V136 H68 Z M92,120 H108 V136 H92 Z M116,120 H132 V136 H116 Z" />',
    ),
    "ios18_camera": (
        '<path android:fillColor="#00000000" android:strokeColor="#FFFFFFFF" android:strokeWidth="11" android:strokeLineJoin="round" android:pathData="M42,66 H70 L80,52 H112 L122,66 H150 C158,66 164,72 164,80 V134 C164,142 158,148 150,148 H42 C34,148 28,142 28,134 V80 C28,72 34,66 42,66 Z" />',
        '<path android:fillColor="#00000000" android:strokeColor="#FFFFFFFF" android:strokeWidth="11" android:pathData="M96,84 C112,84 124,96 124,112 C124,128 112,140 96,140 C80,140 68,128 68,112 C68,96 80,84 96,84 Z" />',
    ),
    "ios18_clock": (
        '<path android:fillColor="#00000000" android:strokeColor="#FFFFFFFF" android:strokeWidth="11" android:pathData="M96,36 C129,36 156,63 156,96 C156,129 129,156 96,156 C63,156 36,129 36,96 C36,63 63,36 96,36 Z" />',
        '<path android:fillColor="#00000000" android:strokeColor="#FFFFFFFF" android:strokeWidth="11" android:strokeLineCap="round" android:pathData="M96,58 V98 L124,116" />',
    ),
    "ios18_compass": (
        '<path android:fillColor="#00000000" android:strokeColor="#FFFFFFFF" android:strokeWidth="10" android:pathData="M96,36 C129,36 156,63 156,96 C156,129 129,156 96,156 C63,156 36,129 36,96 C36,63 63,36 96,36 Z" />',
        '<path android:fillColor="#FFFFFFFF" android:fillType="evenOdd" android:pathData="M122,54 L104,111 L70,138 L88,81 Z M99,90 L92,112 L105,101 Z" />',
    ),
    "ios18_facetime": (
        '<path android:fillColor="#FFFFFFFF" android:pathData="M42,62 H112 C123,62 132,71 132,82 V126 C132,137 123,146 112,146 H42 C31,146 22,137 22,126 V82 C22,71 31,62 42,62 Z M132,90 L166,70 V138 L132,118 Z" />',
    ),
    "ios18_files": (
        '<path android:fillColor="#00000000" android:strokeColor="#FFFFFFFF" android:strokeWidth="10" android:strokeLineJoin="round" android:pathData="M30,64 H76 L90,80 H162 V140 C162,148 156,154 148,154 H44 C36,154 30,148 30,140 Z" />',
        '<path android:fillColor="#FFFFFFFF" android:pathData="M34,54 H74 L86,68 H148 C154,68 160,74 160,80 H90 L76,64 H34 Z" />',
    ),
    "ios18_health": (
        '<path android:fillColor="#FFFFFFFF" android:pathData="M96,148 C75,130 52,112 43,94 C31,71 45,48 68,48 C81,48 90,55 96,66 C102,55 111,48 124,48 C147,48 161,71 149,94 C140,112 117,130 96,148 Z" />',
    ),
    "ios18_mail": (
        '<path android:fillColor="#00000000" android:strokeColor="#FFFFFFFF" android:strokeWidth="10" android:strokeLineJoin="round" android:pathData="M36,58 H156 V134 H36 Z" />',
        '<path android:fillColor="#00000000" android:strokeColor="#FFFFFFFF" android:strokeWidth="10" android:strokeLineCap="round" android:strokeLineJoin="round" android:pathData="M40,64 L96,104 L152,64 M42,130 L78,98 M150,130 L114,98" />',
    ),
    "ios18_maps": (
        '<path android:fillColor="#00000000" android:strokeColor="#FFFFFFFF" android:strokeWidth="9" android:strokeLineJoin="round" android:pathData="M38,52 L76,38 L116,52 L154,38 V140 L116,154 L76,140 L38,154 Z" />',
        '<path android:fillColor="#FFFFFFFF" android:fillType="evenOdd" android:pathData="M106,58 C123,58 136,71 136,88 C136,111 106,138 106,138 C106,138 76,111 76,88 C76,71 89,58 106,58 Z M106,76 C99,76 94,81 94,88 C94,95 99,100 106,100 C113,100 118,95 118,88 C118,81 113,76 106,76 Z" />',
    ),
    "ios18_messages": (
        '<path android:fillColor="#FFFFFFFF" android:pathData="M48,52 H144 C157,52 168,63 168,76 V116 C168,129 157,140 144,140 H92 L56,164 V140 H48 C35,140 24,129 24,116 V76 C24,63 35,52 48,52 Z" />',
    ),
    "ios18_music": (
        '<path android:fillColor="#FFFFFFFF" android:pathData="M76,54 L136,42 V114 C136,130 122,142 106,142 C94,142 84,136 84,126 C84,114 96,106 112,106 C116,106 120,107 124,108 V70 L88,78 V126 C88,142 74,154 58,154 C46,154 36,148 36,138 C36,126 48,118 64,118 C68,118 72,119 76,120 Z" />',
    ),
    "ios18_notes": (
        '<path android:fillColor="#00000000" android:strokeColor="#FFFFFFFF" android:strokeWidth="10" android:strokeLineJoin="round" android:pathData="M48,40 H144 V152 H48 Z" />',
        '<path android:fillColor="#FFFFFFFF" android:pathData="M48,40 H144 V70 H48 Z M64,88 H128 V98 H64 Z M64,112 H128 V122 H64 Z M64,136 H108 V146 H64 Z" />',
    ),
    "ios18_phone": (
        '<path android:fillColor="#FFFFFFFF" android:pathData="M66,34 C58,38 48,52 48,68 C48,104 88,144 124,144 C140,144 154,134 158,126 L142,104 C138,99 130,98 126,103 L116,114 C99,107 85,93 78,76 L89,66 C94,62 93,54 88,50 Z" />',
    ),
    "ios18_photos": (
        '<path android:fillColor="#FFFFFFFF" android:pathData="M96,28 L113,70 L96,88 L79,70 Z M96,104 L113,122 L96,164 L79,122 Z M28,96 L70,79 L88,96 L70,113 Z M104,96 L122,79 L164,96 L122,113 Z M48,48 L88,65 L88,90 L64,90 Z M144,48 L128,90 L104,90 L104,65 Z M48,144 L64,102 L88,102 L88,127 Z M144,144 L104,127 L104,102 L128,102 Z" />',
    ),
    "ios18_safari": (
        '<path android:fillColor="#00000000" android:strokeColor="#FFFFFFFF" android:strokeWidth="10" android:pathData="M96,36 C129,36 156,63 156,96 C156,129 129,156 96,156 C63,156 36,129 36,96 C36,63 63,36 96,36 Z" />',
        '<path android:fillColor="#FFFFFFFF" android:fillType="evenOdd" android:pathData="M122,58 L105,106 L70,134 L87,86 Z M99,92 L93,110 L106,100 Z" />',
    ),
    "ios18_settings": (
        '<path android:fillColor="#00000000" android:strokeColor="#FFFFFFFF" android:strokeWidth="11" android:pathData="M96,72 C109,72 120,83 120,96 C120,109 109,120 96,120 C83,120 72,109 72,96 C72,83 83,72 96,72 Z" />',
        '<path android:fillColor="#00000000" android:strokeColor="#FFFFFFFF" android:strokeWidth="10" android:strokeLineCap="round" android:pathData="M96,38 V58 M96,134 V154 M38,96 H58 M134,96 H154 M55,55 L70,70 M122,122 L137,137 M137,55 L122,70 M70,122 L55,137" />',
    ),
    "ios18_wallet": (
        '<path android:fillColor="#00000000" android:strokeColor="#FFFFFFFF" android:strokeWidth="10" android:strokeLineJoin="round" android:pathData="M38,58 H154 V138 C154,146 148,152 140,152 H52 C44,152 38,146 38,138 Z" />',
        '<path android:fillColor="#FFFFFFFF" android:pathData="M48,42 H132 C140,42 146,48 146,56 V66 H48 Z M38,82 H154 V98 H38 Z M116,116 H140 V128 H116 Z" />',
    ),
    "ios18_weather": (
        '<path android:fillColor="#FFFFFFFF" android:pathData="M72,42 C88,42 101,55 101,71 C101,87 88,100 72,100 C56,100 43,87 43,71 C43,55 56,42 72,42 Z M68,18 H76 V34 H68 Z M68,108 H76 V124 H68 Z M19,67 H35 V75 H19 Z M109,67 H125 V75 H109 Z M33,27 L45,39 L39,45 L27,33 Z M105,27 L117,33 L105,45 L99,39 Z" />',
        '<path android:fillColor="#FFFFFFFF" android:pathData="M82,90 C88,73 104,62 123,62 C145,62 164,80 164,103 C164,125 146,142 124,142 H66 C48,142 34,129 34,112 C34,95 48,82 65,82 C72,82 78,85 82,90 Z" />',
    ),
    "tp_amazon": (
        '<path android:fillColor="#FFFFFFFF" android:pathData="M52,54 H136 V78 H76 V92 H128 V116 H76 V138 H52 Z" />',
        '<path android:fillColor="#00000000" android:strokeColor="#FFFFFFFF" android:strokeWidth="10" android:strokeLineCap="round" android:pathData="M58,146 C82,162 123,162 148,142" />',
    ),
    "tp_chrome": (
        '<path android:fillColor="#00000000" android:strokeColor="#FFFFFFFF" android:strokeWidth="11" android:pathData="M96,36 C129,36 156,63 156,96 C156,129 129,156 96,156 C63,156 36,129 36,96 C36,63 63,36 96,36 Z" />',
        '<path android:fillColor="#00000000" android:strokeColor="#FFFFFFFF" android:strokeWidth="10" android:pathData="M96,74 C108,74 118,84 118,96 C118,108 108,118 96,118 C84,118 74,108 74,96 C74,84 84,74 96,74 Z" />',
        '<path android:fillColor="#00000000" android:strokeColor="#FFFFFFFF" android:strokeWidth="9" android:strokeLineCap="round" android:pathData="M96,74 L132,48 M75,110 L50,66 M118,96 H154" />',
    ),
    "tp_discord": (
        '<path android:fillColor="#00000000" android:strokeColor="#FFFFFFFF" android:strokeWidth="11" android:strokeLineJoin="round" android:pathData="M56,64 C74,54 118,54 136,64 L148,132 C126,148 66,148 44,132 Z" />',
        '<path android:fillColor="#FFFFFFFF" android:pathData="M74,92 C81,92 86,97 86,104 C86,111 81,116 74,116 C67,116 62,111 62,104 C62,97 67,92 74,92 Z M118,92 C125,92 130,97 130,104 C130,111 125,116 118,116 C111,116 106,111 106,104 C106,97 111,92 118,92 Z" />',
    ),
    "tp_facebook": (
        '<path android:fillColor="#FFFFFFFF" android:pathData="M106,158 H78 V102 H58 V78 H78 V62 C78,39 92,26 114,26 C125,26 135,28 135,28 V52 H123 C111,52 106,59 106,67 V78 H133 L129,102 H106 Z" />',
    ),
    "tp_gmail": (
        '<path android:fillColor="#00000000" android:strokeColor="#FFFFFFFF" android:strokeWidth="11" android:strokeLineJoin="round" android:pathData="M36,58 H156 V134 H36 Z" />',
        '<path android:fillColor="#00000000" android:strokeColor="#FFFFFFFF" android:strokeWidth="13" android:strokeLineCap="round" android:strokeLineJoin="round" android:pathData="M42,64 L96,106 L150,64" />',
    ),
    "tp_google_maps": (
        '<path android:fillColor="#FFFFFFFF" android:fillType="evenOdd" android:pathData="M96,30 C125,30 148,53 148,82 C148,122 96,164 96,164 C96,164 44,122 44,82 C44,53 67,30 96,30 Z M96,62 C85,62 76,71 76,82 C76,93 85,102 96,102 C107,102 116,93 116,82 C116,71 107,62 96,62 Z" />',
    ),
    "tp_instagram": (
        '<path android:fillColor="#00000000" android:strokeColor="#FFFFFFFF" android:strokeWidth="12" android:strokeLineJoin="round" android:pathData="M58,42 H134 C143,42 150,49 150,58 V134 C150,143 143,150 134,150 H58 C49,150 42,143 42,134 V58 C42,49 49,42 58,42 Z" />',
        '<path android:fillColor="#00000000" android:strokeColor="#FFFFFFFF" android:strokeWidth="12" android:pathData="M96,72 C109,72 120,83 120,96 C120,109 109,120 96,120 C83,120 72,109 72,96 C72,83 83,72 96,72 Z" />',
        '<path android:fillColor="#FFFFFFFF" android:pathData="M128,58 C132,58 135,61 135,65 C135,69 132,72 128,72 C124,72 121,69 121,65 C121,61 124,58 128,58 Z" />',
    ),
    "tp_netflix": (
        '<path android:fillColor="#FFFFFFFF" android:pathData="M58,36 H82 V156 H58 Z M110,36 H134 V156 H110 Z M82,36 L134,156 H110 L58,36 Z" />',
    ),
    "tp_paypal": (
        '<path android:fillColor="#FFFFFFFF" android:fillType="evenOdd" android:pathData="M60,36 H112 C136,36 150,50 146,72 C142,96 124,108 96,108 H82 L74,156 H50 Z M84,58 L79,88 H100 C113,88 121,82 123,72 C125,63 119,58 107,58 Z" />',
    ),
    "tp_pinterest": (
        '<path android:fillColor="#FFFFFFFF" android:pathData="M96,32 C66,32 46,52 46,79 C46,97 56,112 72,118 L78,96 C72,92 69,86 69,78 C69,62 80,52 96,52 C113,52 124,63 124,80 C124,101 115,116 102,116 C93,116 88,110 90,102 L96,78 H120 L108,125 C102,148 90,160 76,164 L84,124 C75,120 68,113 64,104 C60,96 58,88 58,80 C58,52 76,32 96,32 Z" />',
    ),
    "tp_reddit": (
        '<path android:fillColor="#00000000" android:strokeColor="#FFFFFFFF" android:strokeWidth="10" android:strokeLineCap="round" android:pathData="M74,62 L86,40 L116,48" />',
        '<path android:fillColor="#FFFFFFFF" android:pathData="M118,42 C125,42 130,47 130,54 C130,61 125,66 118,66 C111,66 106,61 106,54 C106,47 111,42 118,42 Z M54,88 C62,74 78,66 96,66 C114,66 130,74 138,88 C149,88 158,97 158,108 C158,118 151,126 142,128 C132,142 115,150 96,150 C77,150 60,142 50,128 C41,126 34,118 34,108 C34,97 43,88 54,88 Z M74,104 C81,104 86,109 86,116 C86,123 81,128 74,128 C67,128 62,123 62,116 C62,109 67,104 74,104 Z M118,104 C125,104 130,109 130,116 C130,123 125,128 118,128 C111,128 106,123 106,116 C106,109 111,104 118,104 Z" />',
    ),
    "tp_robinhood": (
        '<path android:fillColor="#FFFFFFFF" android:pathData="M48,128 C86,118 117,88 136,42 C118,54 96,58 74,58 C82,68 92,74 105,76 C88,88 69,96 48,98 C58,106 72,111 88,112 C76,122 62,128 48,128 Z M124,78 L146,68 L136,94 Z" />',
    ),
    "tp_shazam": (
        '<path android:fillColor="#00000000" android:strokeColor="#FFFFFFFF" android:strokeWidth="12" android:strokeLineCap="round" android:pathData="M92,66 C108,50 132,50 146,64 C160,78 160,101 144,116 L124,136 M100,126 C84,142 60,142 46,128 C32,114 32,91 48,76 L68,56 M76,108 L116,68 M116,84 L76,124" />',
    ),
    "tp_slack": (
        '<path android:fillColor="#FFFFFFFF" android:pathData="M70,28 C79,28 86,35 86,44 V70 H60 C51,70 44,63 44,54 C44,45 51,38 60,38 H70 Z M108,28 C117,28 124,35 124,44 V82 H150 C159,82 166,89 166,98 C166,107 159,114 150,114 H108 Z M42,84 H84 V150 C84,159 77,166 68,166 C59,166 52,159 52,150 V124 H42 C33,124 26,117 26,108 C26,99 33,92 42,92 Z M108,122 H132 C141,122 148,129 148,138 C148,147 141,154 132,154 H122 V164 C122,173 115,180 106,180 C97,180 90,173 90,164 V122 Z" />',
    ),
    "tp_snapchat": (
        '<path android:fillColor="#FFFFFFFF" android:pathData="M96,32 C121,32 138,50 138,78 V100 C138,108 148,114 160,116 C157,126 148,132 136,134 C132,144 116,152 96,152 C76,152 60,144 56,134 C44,132 35,126 32,116 C44,114 54,108 54,100 V78 C54,50 71,32 96,32 Z" />',
    ),
    "tp_spotify": (
        '<path android:fillColor="#00000000" android:strokeColor="#FFFFFFFF" android:strokeWidth="11" android:pathData="M96,36 C129,36 156,63 156,96 C156,129 129,156 96,156 C63,156 36,129 36,96 C36,63 63,36 96,36 Z" />',
        '<path android:fillColor="#00000000" android:strokeColor="#FFFFFFFF" android:strokeWidth="10" android:strokeLineCap="round" android:pathData="M66,80 C91,72 119,76 139,88 M70,102 C91,96 115,99 132,109 M76,123 C92,119 108,121 122,130" />',
    ),
    "tp_strava": (
        '<path android:fillColor="#FFFFFFFF" android:pathData="M82,34 L126,124 H102 L82,82 L62,124 H38 Z M126,124 L154,158 H132 L118,140 Z" />',
    ),
    "tp_telegram": (
        '<path android:fillColor="#FFFFFFFF" android:pathData="M160,42 L132,154 L91,122 L70,144 L76,112 L34,96 Z M80,108 L126,68 L92,118 Z" />',
    ),
    "tp_tiktok": (
        '<path android:fillColor="#FFFFFFFF" android:pathData="M96,36 H120 C123,58 138,72 160,75 V99 C145,99 132,94 120,84 V124 C120,145 104,160 82,160 C61,160 46,146 46,127 C46,108 61,94 82,94 C87,94 91,95 96,97 Z M96,121 C92,118 88,116 82,116 C75,116 70,121 70,128 C70,135 75,140 82,140 C90,140 96,134 96,124 Z" />',
    ),
    "tp_twitter": (
        '<path android:fillColor="#FFFFFFFF" android:pathData="M46,38 H74 L100,76 L130,38 H160 L114,92 L162,154 H134 L104,112 L70,154 H40 L90,96 Z" />',
    ),
    "tp_uber": (
        '<path android:fillColor="#FFFFFFFF" android:pathData="M52,42 H76 V104 C76,122 84,132 96,132 C108,132 116,122 116,104 V42 H140 V106 C140,138 123,158 96,158 C69,158 52,138 52,106 Z" />',
    ),
    "tp_venmo": (
        '<path android:fillColor="#FFFFFFFF" android:pathData="M44,44 H72 L94,124 C110,98 120,70 120,44 H148 C148,86 128,126 100,154 H76 Z" />',
    ),
    "tp_whatsapp": (
        '<path android:fillColor="#00000000" android:strokeColor="#FFFFFFFF" android:strokeWidth="10" android:strokeLineJoin="round" android:pathData="M96,40 C127,40 152,65 152,96 C152,127 127,152 96,152 C86,152 77,150 68,145 L44,152 L51,128 C44,119 40,108 40,96 C40,65 65,40 96,40 Z" />',
        '<path android:fillColor="#FFFFFFFF" android:pathData="M75,68 C69,72 68,82 72,93 C79,112 96,129 116,136 C127,140 136,138 141,132 L130,115 C126,110 120,113 116,118 C104,113 95,104 90,92 C95,88 98,82 93,78 Z" />',
    ),
    "tp_youtube": (
        '<path android:fillColor="#FFFFFFFF" android:fillType="evenOdd" android:pathData="M44,60 H148 C159,60 166,68 168,80 C170,91 170,101 168,112 C166,124 159,132 148,132 H44 C33,132 26,124 24,112 C22,101 22,91 24,80 C26,68 33,60 44,60 Z M84,82 V112 L116,97 Z" />',
    ),
    "tp_zoom": (
        '<path android:fillColor="#FFFFFFFF" android:pathData="M42,62 H112 C123,62 132,71 132,82 V126 C132,137 123,146 112,146 H42 C31,146 22,137 22,126 V82 C22,71 31,62 42,62 Z M132,90 L166,70 V138 L132,118 Z" />',
    ),
}

MONO_VECTOR_PATHS.update({
    "ios18_google_classroom": (
        '<path android:fillColor="#00000000" android:strokeColor="#FFFFFFFF" android:strokeWidth="10" android:strokeLineJoin="round" android:pathData="M34,48 H158 V136 H34 Z" />',
        '<path android:fillColor="#FFFFFFFF" android:pathData="M66,76 C75,76 82,83 82,92 C82,101 75,108 66,108 C57,108 50,101 50,92 C50,83 57,76 66,76 Z M98,78 H140 V90 H98 Z M98,104 H132 V116 H98 Z M52,118 C60,112 72,112 80,118 L88,128 H44 Z" />',
    ),
    "ios18_google_docs": (
        '<path android:fillColor="#00000000" android:strokeColor="#FFFFFFFF" android:strokeWidth="10" android:strokeLineJoin="round" android:pathData="M56,34 H118 L146,62 V158 H56 Z M118,34 V62 H146" />',
        '<path android:fillColor="#FFFFFFFF" android:pathData="M74,82 H128 V94 H74 Z M74,106 H128 V118 H74 Z M74,130 H114 V142 H74 Z" />',
    ),
    "ios18_google_drive": (
        '<path android:fillColor="#FFFFFFFF" android:fillType="evenOdd" android:pathData="M82,36 H110 L158,120 L144,144 H48 L34,120 Z M90,60 L58,116 H86 L116,60 Z M106,72 L134,120 H104 L76,120 Z" />',
    ),
    "ios18_google_keep": (
        '<path android:fillColor="#FFFFFFFF" android:fillType="evenOdd" android:pathData="M96,34 C123,34 144,55 144,82 C144,100 135,114 122,124 V146 H70 V124 C57,114 48,100 48,82 C48,55 69,34 96,34 Z M82,82 C82,74 88,68 96,68 C104,68 110,74 110,82 C110,90 104,96 96,96 C88,96 82,90 82,82 Z M76,156 H116 V168 H76 Z" />',
    ),
    "ios18_google_one": (
        '<path android:fillColor="#00000000" android:strokeColor="#FFFFFFFF" android:strokeWidth="11" android:pathData="M96,36 C129,36 156,63 156,96 C156,129 129,156 96,156 C63,156 36,129 36,96 C36,63 63,36 96,36 Z" />',
        '<path android:fillColor="#FFFFFFFF" android:pathData="M88,70 L112,58 V134 H88 V84 L74,91 L66,75 Z" />',
    ),
    "ios18_google_search": (
        '<path android:fillColor="#00000000" android:strokeColor="#FFFFFFFF" android:strokeWidth="13" android:pathData="M84,44 C106,44 124,62 124,84 C124,106 106,124 84,124 C62,124 44,106 44,84 C44,62 62,44 84,44 Z" />',
        '<path android:fillColor="#00000000" android:strokeColor="#FFFFFFFF" android:strokeWidth="13" android:strokeLineCap="round" android:pathData="M114,114 L150,150" />',
    ),
    "ios18_google_sheets": (
        '<path android:fillColor="#00000000" android:strokeColor="#FFFFFFFF" android:strokeWidth="10" android:strokeLineJoin="round" android:pathData="M56,34 H118 L146,62 V158 H56 Z M118,34 V62 H146" />',
        '<path android:fillColor="#FFFFFFFF" android:pathData="M72,82 H132 V94 H72 Z M72,106 H132 V118 H72 Z M72,130 H132 V142 H72 Z M90,82 H100 V142 H90 Z M112,82 H122 V142 H112 Z" />',
    ),
    "ios18_google_slides": (
        '<path android:fillColor="#00000000" android:strokeColor="#FFFFFFFF" android:strokeWidth="10" android:strokeLineJoin="round" android:pathData="M56,34 H118 L146,62 V158 H56 Z M118,34 V62 H146" />',
        '<path android:fillColor="#FFFFFFFF" android:pathData="M74,82 H128 V124 H74 Z M86,134 H116 V146 H86 Z" />',
    ),
    "ios18_google_translate": (
        '<path android:fillColor="#00000000" android:strokeColor="#FFFFFFFF" android:strokeWidth="10" android:strokeLineJoin="round" android:pathData="M38,50 H112 V120 H38 Z M80,72 H144 V142 H80 Z" />',
        '<path android:fillColor="#FFFFFFFF" android:pathData="M58,66 H70 L88,108 H76 L73,98 H55 L52,108 H40 Z M58,88 H70 L64,72 Z M98,92 H130 V104 H118 C116,112 112,119 106,124 L128,136 H106 L96,130 L86,136 H70 L94,122 C88,116 84,110 82,104 H94 C96,109 99,113 104,116 C108,112 111,108 112,104 H98 Z" />',
    ),
})

MONO_VECTOR_ALIASES: dict[str, str] = {
    "ios18_amazon": "tp_amazon",
    "ios18_chrome": "tp_chrome",
    "ios18_discord": "tp_discord",
    "ios18_facebook": "tp_facebook",
    "ios18_gmail": "tp_gmail",
    "ios18_google_calendar": "ios18_calendar",
    "ios18_google_maps": "tp_google_maps",
    "ios18_google_meet": "tp_zoom",
    "ios18_google_photos": "ios18_photos",
    "ios18_instagram": "tp_instagram",
    "ios18_netflix": "tp_netflix",
    "ios18_paypal": "tp_paypal",
    "ios18_pinterest": "tp_pinterest",
    "ios18_reddit": "tp_reddit",
    "ios18_robinhood": "tp_robinhood",
    "ios18_shazam": "tp_shazam",
    "ios18_slack": "tp_slack",
    "ios18_snapchat": "tp_snapchat",
    "ios18_spotify": "tp_spotify",
    "ios18_strava": "tp_strava",
    "ios18_telegram": "tp_telegram",
    "ios18_tiktok": "tp_tiktok",
    "ios18_twitter": "tp_twitter",
    "ios18_uber": "tp_uber",
    "ios18_venmo": "tp_venmo",
    "ios18_whatsapp": "tp_whatsapp",
    "ios18_youtube": "tp_youtube",
    "ios18_zoom": "tp_zoom",
}


def _vector_paths_for(name: str) -> tuple[str, ...] | None:
    paths = MONO_VECTOR_PATHS.get(name)
    if paths is None:
        alias = MONO_VECTOR_ALIASES.get(name)
        if alias is not None:
            paths = MONO_VECTOR_PATHS[alias]
    return paths


def _mono_content(name: str) -> str:
    paths = _vector_paths_for(name)
    if paths is None:
        return MONO_TEMPLATE.format(name=name)
    rendered_paths = "\n".join(f"    {path}" for path in paths)
    return MONO_VECTOR_TEMPLATE.format(name=name, paths=rendered_paths)


def _target_icons() -> list[str]:
    """Return sorted list of drawable names to generate mono stubs for."""
    names: list[str] = []
    for p in sorted(PACK_DIR.glob("*.png")):
        stem = p.stem
        if stem.startswith("ios18_") or stem.startswith("tp_"):
            names.append(stem)
    return names


def _write(path: Path, content: str, dry_run: bool, force: bool) -> bool:
    if path.exists() and not force:
        return False
    if dry_run:
        action = "overwrite" if path.exists() else "create"
        print(f"  [dry-run] would {action} {path.relative_to(REPO_ROOT)}")
        return True
    path.write_text(content, encoding="utf-8")
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview changes without writing files")
    parser.add_argument("--force", action="store_true",
                        help="Overwrite existing stub files")
    parser.add_argument("--force-mono", action="store_true",
                        help="Overwrite only existing monochrome files")
    args = parser.parse_args(argv)

    DRAWABLE_DIR.mkdir(parents=True, exist_ok=True)

    icons = _target_icons()
    if not icons:
        print("No ios18_* or tp_* icons found in drawable-xxxhdpi/.", file=sys.stderr)
        return 1
    vector_count = sum(1 for name in icons if _vector_paths_for(name) is not None)
    fallback_count = len(icons) - vector_count

    created_mono = 0
    created_themed = 0
    skipped = 0

    for name in icons:
        mono_path = DRAWABLE_DIR / f"{name}_mono.xml"
        themed_path = DRAWABLE_DIR / f"{name}_themed.xml"

        w_mono = _write(
            mono_path,
            _mono_content(name),
            args.dry_run,
            args.force or args.force_mono,
        )
        w_themed = _write(themed_path, THEMED_TEMPLATE.format(name=name), args.dry_run, args.force)

        if w_mono:
            created_mono += 1
        else:
            skipped += 1
        if w_themed:
            created_themed += 1

    if not args.dry_run:
        print(
            f"gen_monochrome: {created_mono} mono files "
            f"({vector_count} vector-backed, {fallback_count} bitmap fallback) + "
            f"{created_themed} themed wrappers written"
            f"{f', {skipped} skipped (already exist; use --force to overwrite)' if skipped else ''}."
        )
        if fallback_count:
            print()
            print("Next steps:")
            print("  1. Add vector templates for remaining bitmap fallbacks.")
            print("     Reference: https://developer.android.com/develop/ui/views/launch/icon_design_adaptive#monochrome")
            print("  2. Test on a Pixel device with 'Themed icons' enabled in Wallpaper & Style settings.")
            print("  3. Run `python scripts/icontool.py check` to confirm assets are valid.")
    else:
        print(
            f"[dry-run] would write {created_mono} mono files "
            f"({vector_count} vector-backed, {fallback_count} bitmap fallback) + "
            f"{created_themed} themed wrappers."
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
