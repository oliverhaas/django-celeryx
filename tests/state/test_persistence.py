"""Tests for django_celeryx.state.persistence module."""

from __future__ import annotations

import time
from unittest.mock import patch

from django.test import override_settings

from django_celeryx.db_models import TaskState, WorkerState
from django_celeryx.state.persistence import (
    cleanup_old_tasks,
    persist_task_event,
    persist_worker_event,
)


class TestPersistTaskEvent:
    """Tests for persist_task_event upsert logic."""

    def test_create_new_task(self, db):
        """Creating a new task persists all provided fields."""
        persist_task_event(
            "uuid-001",
            name="proj.tasks.add",
            state="RECEIVED",
            worker="worker1@host",
            args="(1, 2)",
            kwargs="{}",
            result="",
            exception="",
            traceback="",
            runtime=None,
            eta="",
            expires="",
            exchange="celery",
            routing_key="celery",
            retries=0,
            parent_id="parent-001",
            root_id="root-001",
            received=1000.0,
            started=None,
            succeeded=None,
            failed=None,
            retried_at=None,
            revoked=None,
        )

        task = TaskState.objects.get(uuid="uuid-001")
        assert task.name == "proj.tasks.add"
        assert task.state == "RECEIVED"
        assert task.worker == "worker1@host"
        assert task.args == "(1, 2)"
        assert task.kwargs == "{}"
        assert task.exchange == "celery"
        assert task.routing_key == "celery"
        assert task.retries == 0
        assert task.parent_id == "parent-001"
        assert task.root_id == "root-001"
        assert task.received == 1000.0
        assert task.updated_at is not None

    def test_update_existing_task(self, db):
        """Updating an existing task changes only the provided fields."""
        persist_task_event(
            "uuid-002",
            name="proj.tasks.add",
            state="RECEIVED",
            worker="worker1@host",
            received=1000.0,
        )

        persist_task_event(
            "uuid-002",
            state="STARTED",
            started=1001.0,
        )

        task = TaskState.objects.get(uuid="uuid-002")
        assert task.state == "STARTED"
        assert task.started == 1001.0
        # Unchanged fields should be preserved
        assert task.name == "proj.tasks.add"
        assert task.worker == "worker1@host"
        assert task.received == 1000.0

    def test_empty_string_does_not_overwrite(self, db):
        """Empty string fields should not overwrite existing values."""
        persist_task_event(
            "uuid-003",
            name="proj.tasks.add",
            state="RECEIVED",
            worker="worker1@host",
        )

        persist_task_event(
            "uuid-003",
            name="",
            state="STARTED",
            worker="",
        )

        task = TaskState.objects.get(uuid="uuid-003")
        # State should be updated (non-empty)
        assert task.state == "STARTED"
        # Name and worker should NOT be overwritten by empty strings
        assert task.name == "proj.tasks.add"
        assert task.worker == "worker1@host"

    def test_none_fields_do_not_overwrite(self, db):
        """None fields should not overwrite existing values."""
        persist_task_event(
            "uuid-004",
            name="proj.tasks.add",
            state="SUCCESS",
            runtime=1.23,
            received=1000.0,
        )

        persist_task_event(
            "uuid-004",
            state="SUCCESS",
            runtime=None,
            received=None,
        )

        task = TaskState.objects.get(uuid="uuid-004")
        assert task.name == "proj.tasks.add"
        assert task.runtime == 1.23
        assert task.received == 1000.0


class TestPersistWorkerEvent:
    """Tests for persist_worker_event upsert logic."""

    def test_create_new_worker(self, db):
        """Creating a new worker persists all provided fields."""
        persist_worker_event(
            "worker1@host",
            status="online",
            active=5,
            freq=2.0,
            loadavg=[0.5, 1.0, 1.5],
            sw_ident="py-celery",
            sw_ver="5.3.0",
            sw_sys="Linux",
            last_heartbeat=1000.0,
        )

        worker = WorkerState.objects.get(hostname="worker1@host")
        assert worker.status == "online"
        assert worker.active == 5
        assert worker.freq == 2.0
        assert worker.loadavg == [0.5, 1.0, 1.5]
        assert worker.sw_ident == "py-celery"
        assert worker.sw_ver == "5.3.0"
        assert worker.sw_sys == "Linux"
        assert worker.last_heartbeat == 1000.0
        assert worker.updated_at is not None

    def test_update_existing_worker(self, db):
        """Updating an existing worker changes only the provided fields."""
        persist_worker_event(
            "worker2@host",
            status="online",
            active=3,
            sw_ident="py-celery",
            sw_ver="5.3.0",
        )

        persist_worker_event(
            "worker2@host",
            status="offline",
            active=0,
        )

        worker = WorkerState.objects.get(hostname="worker2@host")
        assert worker.status == "offline"
        assert worker.active == 0
        # Unchanged fields preserved
        assert worker.sw_ident == "py-celery"
        assert worker.sw_ver == "5.3.0"


class TestCleanupOldTasks:
    """Tests for cleanup_old_tasks age and count enforcement."""

    def test_cleanup_by_age(self, db):
        """Tasks older than MAX_TASK_AGE are deleted."""
        from django_celeryx.settings import celeryx_settings

        now = time.time()

        # Create old tasks (updated_at well before cutoff)
        TaskState.objects.create(uuid="old-1", state="SUCCESS", updated_at=now - 100)
        TaskState.objects.create(uuid="old-2", state="SUCCESS", updated_at=now - 50)
        # Create recent task
        TaskState.objects.create(uuid="new-1", state="SUCCESS", updated_at=now)

        with override_settings(
            CELERYX={
                "EVENT_LISTENER_AUTOSTART": False,
                "DATABASE": "default",
                "MAX_TASK_AGE": 10,
                "MAX_TASK_COUNT": 100_000,
            }
        ):
            celeryx_settings.reload()
            deleted = cleanup_old_tasks()

        celeryx_settings.reload()

        assert deleted == 2
        assert TaskState.objects.count() == 1
        assert TaskState.objects.filter(uuid="new-1").exists()

    def test_cleanup_by_count(self, db):
        """Oldest tasks are pruned when MAX_TASK_COUNT is exceeded."""
        from django_celeryx.settings import celeryx_settings

        now = time.time()

        # Create 5 tasks, limit is 3
        for i in range(5):
            TaskState.objects.create(
                uuid=f"task-{i}",
                state="SUCCESS",
                updated_at=now + i,
            )

        with override_settings(
            CELERYX={
                "EVENT_LISTENER_AUTOSTART": False,
                "DATABASE": "default",
                "MAX_TASK_AGE": 86400,
                "MAX_TASK_COUNT": 3,
            }
        ):
            celeryx_settings.reload()
            deleted = cleanup_old_tasks()

        celeryx_settings.reload()

        assert deleted == 2
        assert TaskState.objects.count() == 3
        # The 2 oldest should have been removed
        assert not TaskState.objects.filter(uuid="task-0").exists()
        assert not TaskState.objects.filter(uuid="task-1").exists()
        # The 3 newest should remain
        assert TaskState.objects.filter(uuid="task-2").exists()
        assert TaskState.objects.filter(uuid="task-3").exists()
        assert TaskState.objects.filter(uuid="task-4").exists()


class TestConcurrentCreate:
    """Tests for IntegrityError fallback path on concurrent creates."""

    def test_integrity_error_fallback(self, db):
        """When create() hits IntegrityError, the fallback update() path succeeds."""
        from django.db import IntegrityError

        # Pre-create a task
        TaskState.objects.create(
            uuid="uuid-concurrent",
            name="original",
            state="PENDING",
            updated_at=1000.0,
        )

        # Patch the manager's create to raise IntegrityError, simulating a race
        # where filter().update() returned 0 but another thread inserted first.
        with patch("django_celeryx.db_models.TaskState.objects") as mock_mgr:
            mock_qs = mock_mgr.using.return_value
            # First filter().update() returns 0 (row not found),
            # second filter().update() returns 1 (fallback succeeds)
            mock_qs.filter.return_value.update.side_effect = [0, 1]
            # create() raises IntegrityError
            mock_qs.create.side_effect = IntegrityError("UNIQUE constraint failed")

            persist_task_event("uuid-concurrent", state="STARTED")

            # Verify the fallback path: filter().update() was called twice
            assert mock_qs.filter.return_value.update.call_count == 2
            assert mock_qs.create.call_count == 1

    def test_duplicate_persist_does_not_raise(self, db):
        """Persisting the same uuid twice sequentially never raises."""
        persist_task_event("uuid-dup", name="task-1", state="RECEIVED")
        persist_task_event("uuid-dup", name="task-1", state="STARTED")

        assert TaskState.objects.filter(uuid="uuid-dup").count() == 1
        task = TaskState.objects.get(uuid="uuid-dup")
        assert task.state == "STARTED"
