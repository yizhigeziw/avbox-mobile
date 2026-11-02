package com.github.avbox.osc.util

import com.github.avbox.osc.base.App
import java.io.File

object PlaybackLog {
    private const val FILE_LOG_NAME = "preload_debug.log"
    private const val MAX_LINES = 600

    private val TAGS = arrayOf(
        "echo-timing",
        "echo-goPlayUrl",
        "echo-proxy",
        "echo-playM3u8",
        "echo-resolvePlayUrl",
        "echo-preload",
        "echo-exo-codec",
        "echo-switch",
        "echo-follow",
        "echo-tmdb",
    )

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
        val filtered = lines.filter { line -> TAGS.any { line.contains(it) } }
        if (filtered.isEmpty()) return ""
        return filtered.takeLast(MAX_LINES).joinToString("\n")
    }

    @JvmStatic
    fun clearTiming() {
        val app = App.getInstance() ?: return
        val file = File(app.filesDir, FILE_LOG_NAME)
        if (!file.exists()) return
        try {
            val kept = file.readLines().filterNot { line -> TAGS.any { line.contains(it) } }
            file.writeText(kept.joinToString("\n"))
        } catch (t: Throwable) {
            AppLog.e("PlaybackLog", t)
        }
    }
}
