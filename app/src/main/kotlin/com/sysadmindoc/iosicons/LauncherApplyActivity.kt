package com.sysadmindoc.iosicons

import android.app.Activity
import android.content.ActivityNotFoundException
import android.content.ClipData
import android.content.ClipboardManager
import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.widget.Toast
import java.util.Locale

class LauncherApplyActivity : Activity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        route(intent)
        finish()
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        route(intent)
        finish()
    }

    private fun route(sourceIntent: Intent?) {
        val slug = sourceIntent?.data?.lastPathSegment?.lowercase(Locale.US)
        val target = APPLY_TARGETS[slug]
        if (target == null) {
            copyDiagnostics(
                ApplyFailureDiagnostic(
                    slug = slug ?: "missing",
                    targetLabel = "Unknown launcher",
                    targetPackage = "unknown",
                    resolvedFallback = "none",
                    failure = "unknown launcher shortcut",
                    applyIntentSummary = "none",
                ),
            )
            Toast.makeText(this, R.string.launcher_apply_unknown_report, Toast.LENGTH_SHORT).show()
            return
        }

        target.noticeResId?.let { message ->
            Toast.makeText(this, message, Toast.LENGTH_LONG).show()
        }

        val applyIntent = target.intentFactory(this)
        try {
            startActivity(applyIntent)
        } catch (error: ActivityNotFoundException) {
            handleApplyFailure(slug, target, applyIntent, error::class.java.simpleName)
        } catch (error: SecurityException) {
            handleApplyFailure(slug, target, applyIntent, error::class.java.simpleName)
        }
    }

    private fun handleApplyFailure(
        slug: String?,
        target: ApplyTarget,
        applyIntent: Intent,
        failure: String,
    ) {
        copyDiagnostics(
            ApplyFailureDiagnostic(
                slug = slug ?: "missing",
                targetLabel = target.label,
                targetPackage = target.targetPackage ?: "unknown",
                resolvedFallback = target.fallbackDescription(),
                failure = failure,
                applyIntentSummary = applyIntent.diagnosticSummary(),
            ),
        )
        openFallback(target, copiedDiagnostics = true)
    }

    private fun openFallback(target: ApplyTarget, copiedDiagnostics: Boolean) {
        Toast.makeText(
            this,
            getString(
                if (copiedDiagnostics) {
                    R.string.launcher_apply_unavailable_report
                } else {
                    R.string.launcher_apply_unavailable
                },
                target.label,
            ),
            Toast.LENGTH_LONG,
        ).show()

        for (fallbackIntent in target.fallbackIntents()) {
            try {
                startActivity(fallbackIntent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
                return
            } catch (_: ActivityNotFoundException) {
                continue
            } catch (_: SecurityException) {
                continue
            }
        }
    }

    private fun copyDiagnostics(report: ApplyFailureDiagnostic) {
        val clipboard = getSystemService(Context.CLIPBOARD_SERVICE) as? ClipboardManager ?: return
        clipboard.setPrimaryClip(
            ClipData.newPlainText(
                getString(R.string.launcher_apply_diagnostics_clip_label),
                report.toClipboardText(this),
            ),
        )
    }

    private data class ApplyTarget(
        val label: String,
        val fallbackPackage: String? = null,
        val fallbackUrl: String? = null,
        val targetPackage: String? = fallbackPackage,
        val noticeResId: Int? = null,
        val intentFactory: (Context) -> Intent,
    )

    private data class ApplyFailureDiagnostic(
        val slug: String,
        val targetLabel: String,
        val targetPackage: String,
        val resolvedFallback: String,
        val failure: String,
        val applyIntentSummary: String,
    ) {
        fun toClipboardText(context: Context): String = buildString {
            appendLine("iOS Icon Pack launcher apply diagnostics")
            appendLine("App version: ${BuildConfig.VERSION_NAME} (${BuildConfig.VERSION_CODE})")
            appendLine(
                "Android: ${Build.VERSION.RELEASE} (API ${Build.VERSION.SDK_INT}); " +
                    "${Build.MANUFACTURER} ${Build.MODEL}",
            )
            appendLine("App package: ${context.packageName}")
            appendLine("Launcher slug: $slug")
            appendLine("Launcher target: $targetLabel")
            appendLine("Target package: $targetPackage")
            appendLine("Resolved fallback: $resolvedFallback")
            appendLine("Failure: $failure")
            appendLine("Apply intent: $applyIntentSummary")
            appendLine("Telemetry: not sent; this report was copied locally from the device.")
        }
    }

    private fun Intent.diagnosticSummary(): String {
        val parts = mutableListOf<String>()
        action?.let { parts += "action=$it" }
        getPackage()?.let { parts += "package=$it" }
        component?.let { parts += "component=${it.flattenToShortString()}" }
        dataString?.let { parts += "data=$it" }
        return parts.ifEmpty { listOf("empty intent") }.joinToString(", ")
    }

    private fun ApplyTarget.fallbackDescription(): String = when {
        fallbackPackage != null -> "market://details?id=$fallbackPackage; " +
            "https://play.google.com/store/apps/details?id=$fallbackPackage"
        fallbackUrl != null -> fallbackUrl
        else -> "none"
    }

    private fun ApplyTarget.fallbackIntents(): List<Intent> = when {
        fallbackPackage != null -> listOf(
            Intent(Intent.ACTION_VIEW, Uri.parse("market://details?id=$fallbackPackage")),
            Intent(
                Intent.ACTION_VIEW,
                Uri.parse("https://play.google.com/store/apps/details?id=$fallbackPackage"),
            ),
        )
        fallbackUrl != null -> listOf(Intent(Intent.ACTION_VIEW, Uri.parse(fallbackUrl)))
        else -> emptyList()
    }

    private companion object {
        private const val SAMSUNG_THEME_PARK_URL =
            "https://www.one4studio.com/blog/custom-packs-samsung-oneui"

        private fun Intent.newTask(): Intent = addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)

        private fun launchIntent(context: Context, packageName: String): Intent =
            context.packageManager.getLaunchIntentForPackage(packageName)
                ?: Intent(Intent.ACTION_VIEW, Uri.parse("market://details?id=$packageName"))

        private val APPLY_TARGETS: Map<String, ApplyTarget> = mapOf(
            "nova" to ApplyTarget(
                label = "Nova Launcher",
                fallbackPackage = "com.teslacoilsw.launcher",
            ) { context ->
                Intent("com.teslacoilsw.launcher.APPLY_ICON_THEME")
                    .setPackage("com.teslacoilsw.launcher")
                    .putExtra("com.teslacoilsw.launcher.extra.ICON_THEME_TYPE", "GO")
                    .putExtra("com.teslacoilsw.launcher.extra.ICON_THEME_PACKAGE", context.packageName)
                    .newTask()
            },
            "action" to ApplyTarget(
                label = "Action Launcher",
                fallbackPackage = "com.actionlauncher.playstore",
            ) { context ->
                launchIntent(context, "com.actionlauncher.playstore")
                    .putExtra("apply_icon_pack", context.packageName)
                    .newTask()
            },
            "smart" to ApplyTarget(
                label = "Smart Launcher",
                fallbackPackage = "ginlemon.flowerfree",
            ) { context ->
                Intent("ginlemon.smartlauncher.setGSLTHEME")
                    .putExtra("package", context.packageName)
                    .newTask()
            },
            "oneplus" to ApplyTarget(
                label = "OnePlus Launcher",
                fallbackPackage = "net.oneplus.launcher",
            ) {
                Intent()
                    .setComponent(
                        ComponentName(
                            "net.oneplus.launcher",
                            "net.oneplus.launcher.IconPackSelectorActivity",
                        ),
                    )
                    .newTask()
            },
            "lawnchair" to ApplyTarget(
                label = "Lawnchair",
                fallbackPackage = "app.lawnchair",
            ) { context ->
                Intent("ch.deletescape.lawnchair.APPLY_ICONS")
                    .putExtra("packageName", context.packageName)
                    .newTask()
            },
            "niagara" to ApplyTarget(
                label = "Niagara Launcher",
                fallbackPackage = "bitpit.launcher",
            ) { context ->
                Intent("bitpit.launcher.APPLY_ICONS")
                    .setPackage("bitpit.launcher")
                    .putExtra("packageName", context.packageName)
                    .newTask()
            },
            "projectivy" to ApplyTarget(
                label = "Projectivy Launcher",
                fallbackPackage = "com.spocky.projengmenu",
            ) { context ->
                Intent("com.spocky.projengmenu.APPLY_ICONPACK")
                    .setPackage("com.spocky.projengmenu")
                    .putExtra("com.spocky.projengmenu.extra.ICONPACK_PACKAGENAME", context.packageName)
                    .newTask()
            },
            "adw" to ApplyTarget(
                label = "ADW Launcher",
                fallbackPackage = "org.adw.launcher",
            ) { context ->
                Intent("org.adw.launcher.SET_THEME")
                    .putExtra("org.adw.launcher.theme.NAME", context.packageName)
                    .newTask()
            },
            "apex" to ApplyTarget(
                label = "Apex Launcher",
                fallbackPackage = "com.anddoes.launcher",
            ) { context ->
                Intent("com.anddoes.launcher.SET_THEME")
                    .putExtra("com.anddoes.launcher.THEME_PACKAGE_NAME", context.packageName)
                    .newTask()
            },
            "samsung" to ApplyTarget(
                label = "Samsung Theme Park",
                fallbackUrl = SAMSUNG_THEME_PARK_URL,
                targetPackage = "com.samsung.android.themedesigner or com.samsung.android.goodlock",
                noticeResId = R.string.launcher_apply_samsung_notice,
            ) { context ->
                context.packageManager.getLaunchIntentForPackage("com.samsung.android.themedesigner")
                    ?: context.packageManager.getLaunchIntentForPackage("com.samsung.android.goodlock")
                    ?: Intent(Intent.ACTION_VIEW, Uri.parse(SAMSUNG_THEME_PARK_URL))
                        .newTask()
            },
        )
    }
}
