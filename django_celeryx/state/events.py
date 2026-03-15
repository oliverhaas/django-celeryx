"""Event listener thread consuming Celery events via EventReceiver."""

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


def _get_celery_app() -> Any:
    """Get the Celery app instance."""
    from django_celeryx.settings import celeryx_settings

    if celeryx_settings.CELERY_APP:
        from importlib import import_module

        module_path, attr = celeryx_settings.CELERY_APP.rsplit(".", 1)
        module = import_module(module_path)
        return getattr(module, attr)

    from celery import current_app

    return current_app


def _handle_task_event(event: dict) -> None:
    """Update TaskStore from a task event."""
    from django_celeryx.state.tasks import task_store

    uuid = event.get("uuid")
    if not uuid:
        return

    fields: dict = {}

    # Map event type to state
    event_type = event.get("type", "")
    state_map = {
        "task-sent": "PENDING",
        "task-received": "RECEIVED",
        "task-started": "STARTED",
        "task-succeeded": "SUCCESS",
        "task-failed": "FAILURE",
        "task-retried": "RETRY",
        "task-revoked": "REVOKED",
        "task-rejected": "REJECTED",
    }
    if event_type in state_map:
        fields["state"] = state_map[event_type]

    # Common fields
    for key in ("name", "args", "kwargs", "eta", "expires", "exchange", "routing_key", "retries",
                "result", "exception", "traceback", "runtime"):
        if key in event:
            fields[key] = event[key]

    # Worker hostname
    if "hostname" in event and event_type in ("task-received", "task-started"):
        fields["worker"] = event["hostname"]

    # Timestamps — map event type to timestamp field name
    timestamp_fields = {
        "task-received": "received",
        "task-started": "started",
        "task-succeeded": "succeeded",
        "task-failed": "failed",
        "task-retried": "retried",
        "task-revoked": "revoked",
    }
    if "timestamp" in event and event_type in timestamp_fields:
        fields[timestamp_fields[event_type]] = event["timestamp"]

    # Parent/root IDs
    for key in ("parent_id", "root_id"):
        if key in event:
            fields[key] = event[key]

    task_store.update(uuid, **fields)


def _handle_worker_event(event: dict) -> None:
    """Update WorkerStore from a worker event."""
    from django_celeryx.state.workers import worker_store

    hostname = event.get("hostname")
    if not hostname:
        return

    event_type = event.get("type", "")
    fields: dict = {}

    if event_type == "worker-online":
        fields["status"] = "online"
    elif event_type == "worker-offline":
        fields["status"] = "offline"
    elif event_type == "worker-heartbeat":
        fields["status"] = "online"
        for key in ("active", "freq", "loadavg", "sw_ident", "sw_ver", "sw_sys"):
            if key in event:
                fields[key] = event[key]
        if "timestamp" in event:
            fields["last_heartbeat"] = event["timestamp"]

    worker_store.update(hostname, **fields)


class EventListener(threading.Thread):
    """Daemon thread consuming Celery events via EventReceiver."""

    daemon = True

    def __init__(self) -> None:
        super().__init__(name="celeryx-event-listener")
        self._stop_event = threading.Event()

    def stop(self) -> None:
        """Signal the listener to stop."""
        self._stop_event.set()

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

        handlers = {}
        for event_type in ("task-sent", "task-received", "task-started", "task-succeeded",
                           "task-failed", "task-retried", "task-revoked", "task-rejected"):
            handlers[event_type] = _handle_task_event
        for event_type in ("worker-online", "worker-heartbeat", "worker-offline"):
            handlers[event_type] = _handle_worker_event

        last_enable_events = 0.0

        with app.connection() as connection:
            recv = app.events.Receiver(connection, handlers=handlers)
            recv.should_stop = False
            logger.info("CeleryX event listener connected, consuming events")

            # Use consume() which handles socket.timeout internally for heartbeats.
            # It yields after each event is processed. We loop indefinitely until stopped.
            for _ in recv.consume(limit=None, timeout=None):
                if self._stop_event.is_set():
                    recv.should_stop = True
                    break

                # Periodically broadcast enable_events
                now = time.monotonic()
                if now - last_enable_events > _ENABLE_EVENTS_INTERVAL:
                    try:
                        app.control.enable_events()
                    except Exception:
                        logger.debug("Failed to broadcast enable_events", exc_info=True)
                    last_enable_events = now


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
            _listener_thread.stop()
            _listener_thread = None
