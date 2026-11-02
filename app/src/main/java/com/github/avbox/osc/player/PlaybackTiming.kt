package com.github.avbox.osc.player

import com.github.avbox.osc.util.AppLog

object PlaybackTiming {
    private const val TAG = "echo-timing"
    @Volatile
    private var t0 = 0L

    @Volatile
    private var lastName = ""
    private val onceTokens = java.util.Collections.synchronizedSet(mutableSetOf<String>())

    @JvmStatic
    fun start(name: String) {
        t0 = System.currentTimeMillis()
        lastName = name
        onceTokens.clear()
        AppLog.i("$TAG start $name")
    }

    @JvmStatic
    fun mark(name: String) {
        if (t0 == 0L) return
        val now = System.currentTimeMillis()
        AppLog.i("$TAG $name +${now - t0}ms (from $lastName)")
    }

    @JvmStatic
    fun markOnce(name: String, token: String) {
        if (t0 == 0L) return
        if (!onceTokens.add(token)) return
        val now = System.currentTimeMillis()
        AppLog.i("$TAG $name +${now - t0}ms (from $lastName)")
    }

    @JvmStatic
    fun reset() {
        t0 = 0L
        lastName = ""
    }
}
