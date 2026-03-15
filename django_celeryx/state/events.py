"""Event listener thread consuming Celery events via EventReceiver."""

from __future__ import annotations

import logging
import threading

logger = logging.getLogger(__name__)

_listener_thread: EventListener | None = None
_listener_lock = threading.Lock()


class EventListener(threading.Thread):
    """Daemon thread consuming Celery events via EventReceiver."""

    daemon = True

    def __init__(self) -> None:
        super().__init__(name="celeryx-event-listener")

    def run(self) -> None:
        """Connect to broker and consume events.

        On each event: update in-memory state (TaskStore, WorkerStore).
        Auto-reconnect with exponential backoff.
        Periodically broadcast enable_events to workers.
        """
        # TODO: Implement event consumption loop
        logger.info("CeleryX event listener started")


def start_event_listener() -> None:
    """Start the event listener thread (idempotent)."""
    global _listener_thread  # noqa: PLW0603
    with _listener_lock:
        if _listener_thread is None or not _listener_thread.is_alive():
            _listener_thread = EventListener()
            _listener_thread.start()


def stop_event_listener() -> None:
    """Stop the event listener thread."""
    global _listener_thread  # noqa: PLW0603
    with _listener_lock:
        if _listener_thread is not None:
            # TODO: Implement graceful shutdown
            _listener_thread = None
