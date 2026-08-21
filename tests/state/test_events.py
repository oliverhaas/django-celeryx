"""Tests for the Celery event listener thread."""

import threading
import time
from unittest.mock import MagicMock

import pytest

from django_celeryx.db_models import TaskState, WorkerState
from django_celeryx.state import events


@pytest.fixture(autouse=True)
def _clear_state():
    events._state = None
    events._task_snapshots.clear()
    events._worker_snapshots.clear()
    yield
    events._state = None
    events._task_snapshots.clear()
    events._worker_snapshots.clear()


def _task_event(event_type, uuid, **extra):
    return {
        "type": event_type,
        "uuid": uuid,
        "hostname": "w1@host",
        "timestamp": time.time(),
        "local_received": time.time(),
        "pid": 1,
        "clock": 1,
        "utcoffset": 0,
        **extra,
    }


class TestHandleEvent:
    def test_task_received_is_buffered(self):
        events._handle_event(_task_event("task-received", "t1", name="proj.add", args="(1, 2)", kwargs="{}"))

        assert "t1" in events._task_snapshots
        assert events._task_snapshots["t1"]["name"] == "proj.add"

    def test_later_event_merges_into_existing_snapshot(self):
        events._handle_event(_task_event("task-received", "t1", name="proj.add", args="()", kwargs="{}"))
        events._handle_event(_task_event("task-succeeded", "t1", result="42", runtime=0.5))

        snap = events._task_snapshots["t1"]
        assert snap["name"] == "proj.add"
        assert snap["state"] == "SUCCESS"
        assert snap["runtime"] == 0.5

    def test_worker_event_is_buffered(self):
        events._handle_event(
            {
                "type": "worker-online",
                "hostname": "w1@host",
                "timestamp": time.time(),
                "local_received": time.time(),
                "freq": 2.0,
            },
        )

        assert events._worker_snapshots["w1@host"]["status"] == "online"


@pytest.mark.django_db
class TestFlushToDb:
    def test_flush_writes_and_clears_buffers(self):
        events._handle_event(_task_event("task-received", "t1", name="proj.add", args="()", kwargs="{}"))
        events._handle_event(
            {
                "type": "worker-online",
                "hostname": "w1@host",
                "timestamp": time.time(),
                "local_received": time.time(),
            },
        )

        events._flush_to_db()

        assert TaskState.objects.filter(uuid="t1", name="proj.add").exists()
        assert WorkerState.objects.filter(hostname="w1@host").exists()
        assert events._task_snapshots == {}
        assert events._worker_snapshots == {}

    def test_flush_on_empty_buffers_is_a_noop(self):
        events._flush_to_db()
        assert TaskState.objects.count() == 0


class TestReconnect:
    def test_consume_failure_leaves_listener_running(self, monkeypatch):
        """A broker failure must not set the listener's stop event.

        The flush timer used to share _stop_event, so shutting it down in the
        finally block of _consume_events also cancelled the reconnect loop and
        the listener never came back.
        """
        listener = events.EventListener()
        app = MagicMock()
        app.connection.side_effect = OSError("broker gone")
        monkeypatch.setattr(events, "_get_celery_app", lambda: app)

        with pytest.raises(OSError, match="broker gone"):
            listener._consume_events()

        assert not listener._stop_event.is_set()

    def test_run_retries_after_error(self, monkeypatch):
        monkeypatch.setattr(events, "_INITIAL_BACKOFF", 0.0)
        listener = events.EventListener()
        calls = []

        def failing():
            calls.append(1)
            if len(calls) >= 3:
                listener.stop()
            raise OSError("broker gone")

        monkeypatch.setattr(listener, "_consume_events", failing)
        listener.run()

        assert len(calls) == 3

    def test_run_stops_when_asked(self, monkeypatch):
        listener = events.EventListener()
        listener.stop()
        monkeypatch.setattr(listener, "_consume_events", lambda: pytest.fail("should not consume"))

        listener.run()


class TestFlushTimer:
    def test_stop_event_is_not_shared_with_listener(self):
        timer = events._FlushTimer()
        listener = events.EventListener()

        timer.stop()

        assert timer._stop_event is not listener._stop_event
        assert not listener._stop_event.is_set()

    def test_timer_flushes_until_stopped(self, monkeypatch):
        monkeypatch.setattr(events, "_FLUSH_INTERVAL", 0.01)
        monkeypatch.setattr(events.EventListener, "_setup_db_connection", staticmethod(lambda: None))
        flushed = threading.Event()
        monkeypatch.setattr(events, "_flush_to_db", flushed.set)

        timer = events._FlushTimer()
        timer.start()
        try:
            assert flushed.wait(timeout=2.0)
        finally:
            timer.stop()
            timer.join(timeout=2.0)
        assert not timer.is_alive()


class TestStartStop:
    def test_start_is_idempotent(self, monkeypatch):
        monkeypatch.setattr(events.EventListener, "run", lambda self: self._stop_event.wait(5))
        try:
            events.start_event_listener()
            first = events._listener_thread
            events.start_event_listener()
            assert events._listener_thread is first
        finally:
            events.stop_event_listener(timeout=2.0)
        assert events._listener_thread is None

    def test_stop_without_start_is_a_noop(self):
        events.stop_event_listener(timeout=0.1)
        assert events._listener_thread is None
