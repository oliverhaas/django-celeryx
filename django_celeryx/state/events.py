"""Event listener thread consuming Celery events via EventReceiver.

Uses celery.events.state.State for event merging and state machine transitions.
Snapshots are taken immediately at event time (not at flush time) to avoid
data loss from State's in-memory eviction. A flush timer periodically writes
the buffered snapshots to the database.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Any

logger = logging.getLogger(__name__)

_listener_thread: EventListener | None = None
_listener_lock = threading.Lock()

# Backoff constants
_INITIAL_BACKOFF = 1.0
_MAX_BACKOFF = 60.0
_BACKOFF_MULTIPLIER = 2.0

# How often to broadcast enable_events (seconds)
_ENABLE_EVENTS_INTERVAL = 60.0

# Run cleanup every hour
_CLEANUP_INTERVAL = 3600.0

# How often to flush snapshots to the database (seconds)
_FLUSH_INTERVAL = 0.5


def _get_celery_app() -> Any:
    from django_celeryx.helpers import get_celery_app

    return get_celery_app()


# --- State + snapshot buffer ---

_state_lock = threading.Lock()
_state: Any = None  # celery.events.state.State

# Snapshot buffers: keyed by uuid/hostname, values are field dicts.
# Later events overwrite earlier snapshots for the same key.
_task_snapshots: dict[str, dict[str, Any]] = {}
_worker_snapshots: dict[str, dict[str, Any]] = {}

_TASK_ATTRS = (
    "name",
    "args",
    "kwargs",
    "eta",
    "expires",
    "exchange",
    "routing_key",
    "retries",
    "result",
    "exception",
    "traceback",
    "runtime",
    "worker",
    "parent_id",
    "root_id",
)
_TASK_TIMESTAMPS = ("received", "started", "succeeded", "failed", "retried", "revoked")
_WORKER_ATTRS = ("active", "freq", "loadavg", "sw_ident", "sw_ver", "sw_sys")


def _get_state() -> Any:
    """Get or create the shared State instance."""
    global _state  # noqa: PLW0603
    if _state is None:
        from celery.events.state import State

        _state = State()
    return _state


def _snapshot_task(task: Any) -> dict[str, Any]:
    """Extract persistable fields from a celery State Task object."""
    fields: dict[str, Any] = {}
    if task.state:
        fields["state"] = task.state
    for attr in _TASK_ATTRS:
        val = getattr(task, attr, None)
        if val is not None:
            fields[attr] = val.hostname if attr == "worker" and hasattr(val, "hostname") else val
    for attr in _TASK_TIMESTAMPS:
        val = getattr(task, attr, None)
        if val is not None:
            fields[attr] = val
    return fields


def _snapshot_worker(worker: Any) -> dict[str, Any]:
    """Extract persistable fields from a celery State Worker object."""
    fields: dict[str, Any] = {}
    if worker.status_string:
        fields["status"] = "online" if worker.alive else "offline"
    for attr in _WORKER_ATTRS:
        val = getattr(worker, attr, None)
        if val is not None:
            fields[attr] = val
    if worker.heartbeat_expires is not None:
        fields["last_heartbeat"] = getattr(worker, "timestamp", None) or time.time()
    return fields


def _handle_event(event: dict) -> None:
    """Feed event into celery State and snapshot immediately.

    The snapshot is taken right after State processes the event, so we
    capture the merged state before State can evict the task from memory.
    Later events for the same uuid overwrite the snapshot (last write wins).
    """
    with _state_lock:
        state = _get_state()
        (obj, _created), _group = state.event(event)

        if hasattr(obj, "uuid"):
            # Snapshot immediately — merge with any existing buffered snapshot
            snap = _task_snapshots.get(obj.uuid, {})
            snap.update(_snapshot_task(obj))
            _task_snapshots[obj.uuid] = snap
        elif hasattr(obj, "hostname"):
            snap = _worker_snapshots.get(obj.hostname, {})
            snap.update(_snapshot_worker(obj))
            _worker_snapshots[obj.hostname] = snap

    # Update Prometheus metrics (outside lock — metrics are thread-safe)
    from django_celeryx.metrics import update_metrics_from_event

    update_metrics_from_event(event, _get_state())


def _flush_to_db() -> None:
    """Write buffered snapshots to the database."""
    from django_celeryx.state.persistence import persist_task_event, persist_worker_event

    # Swap out buffers under lock (fast — just dict swap)
    with _state_lock:
        tasks = _task_snapshots.copy()
        _task_snapshots.clear()
        workers = _worker_snapshots.copy()
        _worker_snapshots.clear()

    # Write to DB outside the lock
    for uuid, fields in tasks.items():
        try:
            persist_task_event(uuid, **fields)
        except Exception:
            logger.debug("Failed to persist task %s", uuid, exc_info=True)

    for hostname, fields in workers.items():
        try:
            persist_worker_event(hostname, **fields)
        except Exception:
            logger.debug("Failed to persist worker %s", hostname, exc_info=True)


class EventListener(threading.Thread):
    """Daemon thread consuming Celery events via EventReceiver."""

    daemon = True

    def __init__(self) -> None:
        super().__init__(name="celeryx-event-listener")
        self._stop_event = threading.Event()

    def stop(self) -> None:
        """Signal the listener to stop."""
        self._stop_event.set()

    @staticmethod
    def _setup_db_connection() -> None:
        """Ensure SQLite WAL mode and busy_timeout on this thread's connection."""
        try:
            from django.db import connections

            from django_celeryx.settings import get_db_alias

            conn = connections[get_db_alias()]
            conn.ensure_connection()
            if conn.vendor == "sqlite":
                cursor = conn.cursor()
                cursor.execute("PRAGMA journal_mode=WAL;")
                cursor.execute("PRAGMA busy_timeout=5000;")
        except Exception:
            logger.debug("Failed to set SQLite pragmas", exc_info=True)

    def run(self) -> None:
        """Connect to broker and consume events with auto-reconnect."""
        backoff = _INITIAL_BACKOFF

        while not self._stop_event.is_set():
            try:
                self._consume_events()
                backoff = _INITIAL_BACKOFF
            except Exception:
                logger.exception("Event listener error, reconnecting in %.1fs", backoff)
                self._stop_event.wait(backoff)
                backoff = min(backoff * _BACKOFF_MULTIPLIER, _MAX_BACKOFF)

    def _consume_events(self) -> None:
        """Connect and consume events until disconnected or stopped."""
        app = _get_celery_app()

        logger.info("CeleryX event listener connecting to broker")

        last_enable_events = 0.0
        last_cleanup = time.monotonic()

        # Start flush timer
        flush_timer = _FlushTimer(self._stop_event)
        flush_timer.start()

        try:
            with app.connection() as connection:
                recv = app.events.Receiver(
                    connection,
                    handlers={"*": _handle_event},
                )
                recv.should_stop = False
                logger.info("CeleryX event listener connected, consuming events")

                for _ in recv.consume(limit=None, timeout=None):
                    if self._stop_event.is_set():
                        recv.should_stop = True
                        break

                    now = time.monotonic()

                    if now - last_enable_events > _ENABLE_EVENTS_INTERVAL:
                        try:
                            app.control.enable_events()
                        except Exception:
                            logger.debug("Failed to broadcast enable_events", exc_info=True)
                        last_enable_events = now

                    if now - last_cleanup > _CLEANUP_INTERVAL:
                        try:
                            from django_celeryx.state.persistence import cleanup_old_tasks

                            cleanup_old_tasks()
                        except Exception:
                            logger.debug("Failed to run cleanup", exc_info=True)
                        last_cleanup = now
        finally:
            flush_timer.stop()
            _flush_to_db()  # Final flush


class _FlushTimer(threading.Thread):
    """Daemon thread that periodically flushes snapshots to the database."""

    daemon = True

    def __init__(self, stop_event: threading.Event) -> None:
        super().__init__(name="celeryx-flush-timer")
        self._stop_event = stop_event

    def stop(self) -> None:
        self._stop_event.set()

    def run(self) -> None:
        EventListener._setup_db_connection()

        while not self._stop_event.wait(_FLUSH_INTERVAL):
            try:
                _flush_to_db()
            except Exception:
                logger.debug("Flush timer error", exc_info=True)


def start_event_listener() -> None:
    """Start the event listener thread (idempotent)."""
    global _listener_thread  # noqa: PLW0603
    with _listener_lock:
        if _listener_thread is None or not _listener_thread.is_alive():
            _listener_thread = EventListener()
            _listener_thread.start()


def stop_event_listener(timeout: float = 5.0) -> None:
    """Stop the event listener thread and wait for it to finish."""
    global _listener_thread  # noqa: PLW0603
    with _listener_lock:
        if _listener_thread is not None:
            _listener_thread.stop()
            _listener_thread.join(timeout=timeout)
            _listener_thread = None
