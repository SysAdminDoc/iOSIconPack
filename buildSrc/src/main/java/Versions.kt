@file:Suppress("unused")

object Versions {
    // Plugins
    const val gradle = "8.12.0"
    const val kotlin = "2.2.21"
    const val ksp = "2.3.4"

    // App
    // minSdk 26 (Android 8.0) — adaptive icons are a mandatory feature of the
    // pack, and Android 13+ themed icons require the monochrome layer introduced
    // in API 33. API 23 is below both thresholds. Stack convention is 26.
    const val minSdk = 26
    const val targetSdk = 36
    const val buildTools = "36.0.0"

    // Blueprint
    const val blueprint = "2.5.1"
}
