package com.sysadmindoc.iosicons

import android.app.Activity
import android.content.ActivityNotFoundException
import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.net.Uri
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
            Toast.makeText(this, R.string.launcher_apply_unknown, Toast.LENGTH_SHORT).show()
            return
        }

        target.noticeResId?.let { message ->
            Toast.makeText(this, message, Toast.LENGTH_LONG).show()
        }

        val applyIntent = target.intentFactory(this)
        try {
            startActivity(applyIntent)
        } catch (_: ActivityNotFoundException) {
            openFallback(target)
        } catch (_: SecurityException) {
            openFallback(target)
        }
    }

    private fun openFallback(target: ApplyTarget) {
        Toast.makeText(
            this,
            getString(R.string.launcher_apply_unavailable, target.label),
            Toast.LENGTH_LONG,
        ).show()

        val fallbackIntent = when {
            target.fallbackPackage != null -> Intent(
                Intent.ACTION_VIEW,
                Uri.parse("market://details?id=${target.fallbackPackage}"),
            )
            target.fallbackUrl != null -> Intent(Intent.ACTION_VIEW, Uri.parse(target.fallbackUrl))
            else -> null
        } ?: return

        try {
            startActivity(fallbackIntent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
        } catch (_: ActivityNotFoundException) {
            if (target.fallbackPackage != null) {
                startActivity(
                    Intent(
                        Intent.ACTION_VIEW,
                        Uri.parse("https://play.google.com/store/apps/details?id=${target.fallbackPackage}"),
                    ).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK),
                )
            }
        }
    }

    private data class ApplyTarget(
        val label: String,
        val fallbackPackage: String? = null,
        val fallbackUrl: String? = null,
        val noticeResId: Int? = null,
        val intentFactory: (Context) -> Intent,
    )

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
