package com.github.avbox.osc.util

import com.github.avbox.osc.base.App
import java.io.File

object PlaybackLog {
    private const val FILE_LOG_NAME = "preload_debug.log"
    private const val TAG = "echo-timing"
    private const val MAX_LINES = 200

    @JvmStatic
    fun readTiming(): String {
        val app = App.getInstance() ?: return ""
        val file = File(app.filesDir, FILE_LOG_NAME)
        if (!file.exists()) return ""
        val lines = try {
            file.readLines()
        } catch (t: Throwable) {
            AppLog.e("PlaybackLog", t)
            return ""
        }
        val filtered = lines.filter { it.contains(TAG) }
        if (filtered.isEmpty()) return ""
        return filtered.takeLast(MAX_LINES).joinToString("\n")
    }

    @JvmStatic
    fun clearTiming() {
        val app = App.getInstance() ?: return
        val file = File(app.filesDir, FILE_LOG_NAME)
        if (!file.exists()) return
        try {
            val kept = file.readLines().filterNot { it.contains(TAG) }
            file.writeText(kept.joinToString("\n"))
        } catch (t: Throwable) {
            AppLog.e("PlaybackLog", t)
        }
    }
}
