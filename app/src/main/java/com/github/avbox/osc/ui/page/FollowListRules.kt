package com.github.avbox.osc.ui.page

import com.github.avbox.osc.data.FollowDays

internal object FollowListRules {

    fun effectiveDays(entry: FollowEntry, calendar: FollowCalendar? = null): Set<Int> {
        val weekday = calendar?.weekday ?: -1
        if (weekday in 0..6) return setOf(weekday)
        return FollowDays.decode(entry.follow.updateDays)
    }

    fun dayCounts(
        items: List<FollowEntry>,
        calendar: Map<Int, FollowCalendar> = emptyMap(),
    ): Map<Int, Int> =
        items.flatMap { entry ->
            effectiveDays(entry, calendar[entry.follow.id]) - entry.watchedDays
        }.groupingBy { it }.eachCount()

    fun visible(
        items: List<FollowEntry>,
        day: Int?,
        calendar: Map<Int, FollowCalendar> = emptyMap(),
    ): List<FollowEntry> =
        if (day == null) {
            items.sortedByDescending { it.follow.addedTime }
        } else {
            items.filter { day in effectiveDays(it, calendar[it.follow.id]) }
                .sortedWith(compareBy({ it.follow.updateHour }, { -it.follow.addedTime }))
        }

    fun isWatched(
        entry: FollowEntry,
        day: Int?,
        calendar: Map<Int, FollowCalendar> = emptyMap(),
    ): Boolean {
        if (day != null) return day in entry.watchedDays
        val days = effectiveDays(entry, calendar[entry.follow.id])
        return days.isNotEmpty() && entry.watchedDays.containsAll(days)
    }
}
