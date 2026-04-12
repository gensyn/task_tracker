"""Coordinator for the Task Tracker integration.

The TaskTrackerCoordinator is the single owner of the mutable state and all
due-date calculation logic for one Task Tracker entry.  It exposes:

* ``last_done``              – the date the task was last completed
* ``repeat_mode``            – how the next due date is calculated on completion
* ``calculate_due_date``     – compute the next due date given an effective interval
* ``async_mark_as_done``     – mark the task as done today (or as of the current
                               due date for repeat_every mode)
* ``async_set_last_done_date`` – set an explicit last-done date
* ``async_add_listener``     – register a callback that is invoked on every
                               state change (returns an unsubscribe callable)

Services and the button entity interact with the coordinator; the sensor entity
reads state from the coordinator, resolves any HA override entities to obtain the
effective interval, calls ``calculate_due_date`` with that effective interval, and
registers a listener so it is notified whenever state changes.
"""

from __future__ import annotations

import calendar
from datetime import date, timedelta
from logging import getLogger
from typing import Callable

from dateutil.relativedelta import relativedelta

from .const import (
    CONF_DAY, CONF_WEEK, CONF_MONTH, CONF_YEAR,
    CONF_REPEAT_AFTER, CONF_REPEAT_EVERY,
    CONF_REPEAT_EVERY_WEEKDAY, CONF_REPEAT_EVERY_DAY_OF_MONTH,
    CONF_REPEAT_EVERY_WEEKDAY_OF_MONTH,
)

LOGGER = getLogger(__name__)


class TaskTrackerCoordinator:
    """Per-entry coordinator that owns mutable state for one Task Tracker task."""

    def __init__(
        self,
        entry_id: str,
        repeat_mode: str = CONF_REPEAT_AFTER,
        repeat_every_type: str | None = None,
        repeat_weekday: str | None = None,
        repeat_weeks_interval: int = 1,
        repeat_month_day: int = 1,
        repeat_nth_occurrence: str = "1",
    ) -> None:
        """Initialise the coordinator."""
        self.entry_id = entry_id
        self.last_done: date = date(1970, 1, 1)
        self.repeat_mode: str = repeat_mode
        self.repeat_every_type: str | None = repeat_every_type
        self.repeat_weekday: str | None = repeat_weekday
        self.repeat_weeks_interval: int = max(1, repeat_weeks_interval or 1)
        self.repeat_month_day: int = max(1, min(31, repeat_month_day or 1))
        self.repeat_nth_occurrence: str = (
            repeat_nth_occurrence
            if repeat_nth_occurrence in ("1", "2", "3", "4", "last")
            else "1"
        )
        self._listeners: list[Callable[[], None]] = []

    def async_add_listener(self, update_callback: Callable[[], None]) -> Callable[[], None]:
        """Register *update_callback*; returns a callable that removes it."""
        self._listeners.append(update_callback)

        def remove_listener() -> None:
            self._listeners.remove(update_callback)

        return remove_listener

    def _async_notify_listeners(self) -> None:
        """Notify all registered listeners of a state change."""
        for listener in list(self._listeners):
            listener()

    async def async_mark_as_done(self) -> None:
        """Mark the task as done and notify listeners.

        In ``repeat_after`` mode (default) the last-done date is set to today,
        so the next due date is calculated relative to the actual completion date.

        In ``repeat_every`` mode the last-done date is set to the current computed
        due date, so the task keeps its fixed calendar schedule regardless of when
        it was completed.
        """
        if self.repeat_mode == CONF_REPEAT_EVERY:
            self.last_done = self._calculate_repeat_every_due_date()
        else:
            self.last_done = date.today()
        self._async_notify_listeners()

    async def async_set_last_done_date(self, new_date: date) -> None:
        """Set the last-done date and notify listeners."""
        self.last_done = new_date
        self._async_notify_listeners()

    # ------------------------------------------------------------------
    # Due-date calculation
    # ------------------------------------------------------------------

    def calculate_due_date(self, interval_value: int, interval_type: str) -> date:
        """Return the due date computed from ``last_done`` and the given interval.

        The *interval_value* / *interval_type* pair is only used in
        ``repeat_after`` mode.  In ``repeat_every`` mode the schedule is driven
        entirely by the repeat_every_* configuration stored on this coordinator.
        """
        if self.repeat_mode == CONF_REPEAT_EVERY:
            return self._calculate_repeat_every_due_date()
        # repeat_after (completion-coupled)
        if interval_type == CONF_WEEK:
            return self.last_done + relativedelta(weeks=interval_value)
        if interval_type == CONF_MONTH:
            return self.last_done + relativedelta(months=interval_value)
        if interval_type == CONF_YEAR:
            return self.last_done + relativedelta(years=interval_value)
        return self.last_done + relativedelta(days=interval_value)

    def _calculate_repeat_every_due_date(self) -> date:
        """Calculate due date for the active repeat_every schedule sub-type."""
        last = self.last_done
        etype = self.repeat_every_type
        if etype == CONF_REPEAT_EVERY_WEEKDAY:
            return self._calc_next_weekday(
                last, self.repeat_weekday or "monday", self.repeat_weeks_interval
            )
        if etype == CONF_REPEAT_EVERY_DAY_OF_MONTH:
            return self._calc_next_day_of_month(last, self.repeat_month_day)
        if etype == CONF_REPEAT_EVERY_WEEKDAY_OF_MONTH:
            return self._calc_next_weekday_of_month(
                last, self.repeat_weekday or "monday", self.repeat_nth_occurrence
            )
        # Unrecognised sub-type: fall back to a 7-day interval
        return last + relativedelta(days=7)

    @staticmethod
    def _weekday_number(weekday_name: str) -> int:
        """Convert a weekday name to Python weekday number (0 = Monday, 6 = Sunday)."""
        return {
            "monday": 0, "tuesday": 1, "wednesday": 2,
            "thursday": 3, "friday": 4, "saturday": 5, "sunday": 6,
        }[weekday_name]

    def _calc_next_weekday(self, last: date, weekday_name: str, weeks_interval: int) -> date:
        """Return the next due date for 'every N weeks on *weekday_name*'.

        When *last* already falls on the target weekday the schedule advances by
        *weeks_interval* full weeks.  Otherwise the very next occurrence of that
        weekday is found and then (weeks_interval - 1) additional weeks are added
        so the spacing after the first completion is always consistent.
        """
        target = self._weekday_number(weekday_name)
        days_ahead = (target - last.weekday()) % 7
        if days_ahead == 0:
            return last + timedelta(weeks=weeks_interval)
        return last + timedelta(days=days_ahead) + timedelta(weeks=weeks_interval - 1)

    @staticmethod
    def _calc_next_day_of_month(last: date, day: int) -> date:
        """Return the next occurrence of *day* of the month strictly after *last*."""
        last_day_of_month = calendar.monthrange(last.year, last.month)[1]
        candidate = last.replace(day=min(day, last_day_of_month))
        if candidate > last:
            return candidate
        # Advance to next month
        next_month = last.replace(day=1) + relativedelta(months=1)
        last_day_of_next = calendar.monthrange(next_month.year, next_month.month)[1]
        return next_month.replace(day=min(day, last_day_of_next))

    @staticmethod
    def _get_nth_weekday_of_month(year: int, month: int, target_weekday: int, nth: int) -> date | None:
        """Return the *nth* occurrence of *target_weekday* in *year*/*month*.

        Returns ``None`` when the requested occurrence does not exist (e.g. a
        5th Monday in a month that only has four).  Use nth == -1 for the last
        occurrence.
        """
        if nth == -1:
            last_day = calendar.monthrange(year, month)[1]
            d = date(year, month, last_day)
            while d.weekday() != target_weekday:
                d -= timedelta(days=1)
            return d
        first_day = date(year, month, 1)
        days_ahead = (target_weekday - first_day.weekday()) % 7
        first_occurrence = first_day + timedelta(days=days_ahead)
        result = first_occurrence + timedelta(weeks=nth - 1)
        return result if result.month == month else None

    def _calc_next_weekday_of_month(self, last: date, weekday_name: str, nth_str: str) -> date:
        """Return the next *nth* weekday-of-month occurrence strictly after *last*."""
        target = self._weekday_number(weekday_name)
        nth = -1 if nth_str == "last" else int(nth_str)
        # Try the current month
        occurrence = self._get_nth_weekday_of_month(last.year, last.month, target, nth)
        if occurrence is not None and occurrence > last:
            return occurrence
        # Advance month by month until a valid occurrence is found
        candidate_month = last.replace(day=1) + relativedelta(months=1)
        for _ in range(24):  # safety cap of 24 months
            occurrence = self._get_nth_weekday_of_month(
                candidate_month.year, candidate_month.month, target, nth
            )
            if occurrence is not None:
                return occurrence
            candidate_month += relativedelta(months=1)
        # Unreachable in practice; last-resort fallback
        return last + relativedelta(months=1)
