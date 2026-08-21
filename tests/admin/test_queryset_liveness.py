"""Worker liveness is derived from heartbeat age, not just the stored status."""

import time

import pytest

from django_celeryx.admin.queryset import _HEARTBEAT_EXPIRE_FACTOR, _is_alive, _workers_from_db
from django_celeryx.db_models import WorkerState


class TestIsAlive:
    def test_fresh_heartbeat_is_online(self):
        assert _is_alive("online", time.time(), 2.0) is True

    def test_stale_heartbeat_is_offline(self):
        stale = time.time() - 2.0 * _HEARTBEAT_EXPIRE_FACTOR - 1
        assert _is_alive("online", stale, 2.0) is False

    def test_explicit_offline_wins_over_fresh_heartbeat(self):
        assert _is_alive("offline", time.time(), 2.0) is False

    def test_missing_heartbeat_is_offline(self):
        assert _is_alive("online", None, 2.0) is False

    def test_missing_freq_uses_a_default_window(self):
        assert _is_alive("online", time.time(), None) is True


@pytest.mark.django_db
class TestWorkersFromDb:
    def test_worker_killed_without_an_offline_event_shows_offline(self):
        """Celery only emits worker-offline on a graceful shutdown."""
        now = time.time()
        WorkerState.objects.create(
            hostname="dead@host",
            status="online",
            freq=2.0,
            last_heartbeat=now - 86400,
            updated_at=now - 86400,
        )

        workers = {w.hostname: w.status for w in _workers_from_db()}

        assert workers["dead@host"] == "offline"

    def test_live_worker_stays_online(self):
        now = time.time()
        WorkerState.objects.create(
            hostname="live@host",
            status="online",
            freq=2.0,
            last_heartbeat=now,
            updated_at=now,
        )

        workers = {w.hostname: w.status for w in _workers_from_db()}

        assert workers["live@host"] == "online"
