"""Coordinator for the Task Tracker integration.

The TaskTrackerCoordinator is the single owner of the mutable state for one
Task Tracker entry.  It exposes:

* ``last_done``              – the date the task was last completed
* ``due_date``               – the current computed due date (kept in sync by the sensor)
* ``repeat_mode``            – how the next due date is calculated on completion
* ``async_mark_as_done``     – mark the task as done today (or as of due_date for
                               repeat_every mode)
* ``async_set_last_done_date`` – set an explicit last-done date
* ``async_add_listener``     – register a callback that is invoked on every
                               state change (returns an unsubscribe callable)

Services and the button entity interact with the coordinator; the sensor entity
reads state from the coordinator and registers a listener so it is notified
whenever state changes.
"""

from __future__ import annotations

from datetime import date
from logging import getLogger
from typing import Callable

from .const import CONF_REPEAT_AFTER, CONF_REPEAT_EVERY

LOGGER = getLogger(__name__)


class TaskTrackerCoordinator:
    """Per-entry coordinator that owns mutable state for one Task Tracker task."""

    def __init__(self, entry_id: str) -> None:
        """Initialise the coordinator."""
        self.entry_id = entry_id
        self.last_done: date = date(1970, 1, 1)
        # due_date and repeat_mode are kept up-to-date by the sensor so that
        # callers such as the button and service can use them without needing
        # direct access to the sensor entity.
        self.due_date: date | None = None
        self.repeat_mode: str = CONF_REPEAT_AFTER
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

        In ``repeat_every`` mode the last-done date is set to the current
        ``due_date`` (the most recently scheduled date), so the task keeps its
        fixed calendar schedule regardless of when it was completed.  If
        ``due_date`` has not yet been set by the sensor, today is used as a
        fallback.
        """
        if self.repeat_mode == CONF_REPEAT_EVERY and self.due_date is not None:
            self.last_done = self.due_date
        else:
            self.last_done = date.today()
        self._async_notify_listeners()

    async def async_set_last_done_date(self, new_date: date) -> None:
        """Set the last-done date and notify listeners."""
        self.last_done = new_date
        self._async_notify_listeners()
