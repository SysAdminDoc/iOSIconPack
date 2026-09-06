package com.sysadmindoc.iosicons

import android.app.Activity
import android.app.Application
import android.os.Bundle
import android.view.WindowManager
import dev.jahir.frames.ui.FramesApplication
import dev.jahir.kuper.ui.activities.KuperViewerActivity

class MyApplication : FramesApplication() {
    override fun onCreate() {
        super.onCreate()
        registerActivityLifecycleCallbacks(
            object : Application.ActivityLifecycleCallbacks {
                override fun onActivityCreated(activity: Activity, savedInstanceState: Bundle?) =
                    allowWallpaperScreenshots(activity)

                override fun onActivityStarted(activity: Activity) = Unit

                override fun onActivityResumed(activity: Activity) =
                    allowWallpaperScreenshots(activity)

                override fun onActivityPaused(activity: Activity) = Unit

                override fun onActivityStopped(activity: Activity) = Unit

                override fun onActivitySaveInstanceState(activity: Activity, outState: Bundle) = Unit

                override fun onActivityDestroyed(activity: Activity) = Unit
            },
        )
    }

    private fun allowWallpaperScreenshots(activity: Activity) {
        if (activity is KuperViewerActivity) {
            activity.window.clearFlags(WindowManager.LayoutParams.FLAG_SECURE)
        }
    }
}
