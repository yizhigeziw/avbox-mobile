package com.github.avbox.osc.api

import com.github.avbox.osc.bean.TmdbDetail
import com.github.avbox.osc.util.AppLog
import com.github.avbox.osc.util.KV
import com.github.avbox.osc.util.KVKeys
import java.util.concurrent.ConcurrentHashMap
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.sync.Semaphore
import kotlinx.coroutines.sync.withPermit

object TmdbCalendar {

    private const val TTL_MS = 30L * 60 * 1000
    private const val MAX_CONCURRENT = 3

    private val semaphore = Semaphore(MAX_CONCURRENT)

    private val cache = ConcurrentHashMap<String, Entry>()

    private class Entry(val at: Long, val detail: TmdbDetail?)

    fun isConfigured(): Boolean = readApiKey().isNotBlank()

    suspend fun resolve(name: String?, year: Int): TmdbDetail? {
        val apiKey = readApiKey()
        if (apiKey.isBlank()) return null
        val query = TmdbApi.searchQuery(name)
        if (query.isBlank()) return null
        val cacheKey = TmdbApi.normalizeForMatch(name) + "|" + year
        cache[cacheKey]?.let { if (System.currentTimeMillis() - it.at < TTL_MS) return it.detail }
        val detail = fetch(apiKey, readApiBase(), query, name, year)
        cache[cacheKey] = Entry(System.currentTimeMillis(), detail)
        return detail
    }

    private suspend fun fetch(
        apiKey: String,
        apiBase: String,
        query: String,
        name: String?,
        year: Int,
    ): TmdbDetail? = semaphore.withPermit {
        try {
            val client = TmdbApi.DefaultTmdbClient()
            val hits = client.search(apiKey, apiBase, query)
            val best = TmdbApi.pickBest(hits, name, year, tvOnly = true)
                ?: hits.firstOrNull { it.mediaType == TmdbApi.MEDIA_TV && it.posterPath.isNotEmpty() }
            AppLog.i(
                "echo-follow tmdb q=$query hits=${hits.size} best=${best?.id ?: 0} media=${best?.mediaType ?: "-"}",
            )
            if (best == null) return@withPermit null
            val detail = client.detail(apiKey, apiBase, best.mediaType, best.id)
            val next = detail?.nextEpisode
            AppLog.i(
                "echo-follow tmdb id=${best.id} status=${detail?.status ?: "-"} " +
                    "next=${next?.airDate ?: "-"} S${next?.seasonNumber ?: 0}E${next?.episodeNumber ?: 0}",
            )
            detail
        } catch (e: CancellationException) {
            throw e
        } catch (e: Exception) {
            AppLog.i("echo-follow tmdb fail q=$query msg=${e.message}")
            null
        }
    }

    private fun readApiKey(): String = try {
        KV.get(KVKeys.TMDB_API_KEY, "").trim()
    } catch (e: Exception) {
        AppLog.e("TmdbCalendar", e)
        ""
    }

    private fun readApiBase(): String = try {
        KV.get(KVKeys.TMDB_API_BASE, "")
    } catch (e: Exception) {
        AppLog.e("TmdbCalendar", e)
        ""
    }
}
