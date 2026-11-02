package com.github.avbox.osc.ui.page

import com.github.avbox.osc.bean.TmdbDetail
import java.time.LocalDate
import java.util.Locale

internal data class FollowCalendar(
    val airDate: String = "",
    val weekday: Int = -1,
    val seasonNumber: Int = 0,
    val episodeNumber: Int = 0,
    val ended: Boolean = false,
) {
    val hasNext: Boolean get() = airDate.isNotEmpty()

    val episodeLabel: String
        get() = if (seasonNumber > 0 && episodeNumber > 0) {
            String.format(Locale.ROOT, "S%02dE%02d", seasonNumber, episodeNumber)
        } else {
            ""
        }

    fun isToday(): Boolean = hasNext && airDate == LocalDate.now().toString()

    companion object {
        fun from(detail: TmdbDetail?): FollowCalendar? {
            if (detail == null) return null
            val next = detail.nextEpisode
            if (next != null && next.airDate.isNotEmpty()) {
                val weekday = weekdayOf(next.airDate)
                if (weekday != null) {
                    return FollowCalendar(
                        airDate = next.airDate,
                        weekday = weekday,
                        seasonNumber = next.seasonNumber,
                        episodeNumber = next.episodeNumber,
                    )
                }
            }
            val status = detail.status.orEmpty()
            if (status.equals("Ended", true) || status.equals("Canceled", true)) {
                return FollowCalendar(ended = true)
            }
            return null
        }

        private fun weekdayOf(airDate: String): Int? = try {
            LocalDate.parse(airDate).dayOfWeek.value - 1
        } catch (e: Exception) {
            null
        }
    }
}
