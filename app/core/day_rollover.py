"""
Day-rollover logic.

"Today" for a given user isn't necessarily calendar midnight - each user
has a `day_start_time` (default 00:00, but configurable, e.g. 04:00 for
someone who eats late and wants that meal to count toward the prior day).

This module computes the current logical-day window on the fly at query
time. No stored "day" field, no midnight cron job - FoodLog rows are
filtered by this window whenever "today's" Remaining needs to be computed.
"""

from datetime import datetime, time, timedelta, date


def get_logical_day_bounds(day_start_time: time, now: datetime = None) -> tuple[datetime, datetime]:
    """
    Returns (window_start, window_end) - the [start, end) datetime range
    that counts as "today" for a user with the given day_start_time.

    Example: day_start_time = 04:00, now = 2026-08-22 02:30
      -> the logical day started at 2026-08-21 04:00 (yesterday's
         rollover), so window = [2026-08-21 04:00, 2026-08-22 04:00)
    """
    if now is None:
        now = datetime.utcnow()

    candidate_start = datetime.combine(now.date(), day_start_time)

    if now < candidate_start:
        # We're before today's rollover time, so we're still in the
        # logical day that started yesterday at day_start_time.
        window_start = candidate_start - timedelta(days=1)
    else:
        window_start = candidate_start

    window_end = window_start + timedelta(days=1)
    return window_start, window_end


def is_in_logical_day(timestamp: datetime, day_start_time: time, reference_now: datetime = None) -> bool:
    """Convenience check: does `timestamp` fall within the current logical day?"""
    start, end = get_logical_day_bounds(day_start_time, reference_now)
    return start <= timestamp < end
