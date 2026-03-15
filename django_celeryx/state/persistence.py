"""Database persistence for event data.

Handles writing events to DB alongside in-memory stores,
replaying from DB on startup, and periodic cleanup.
Only active when CELERYX["DATABASE"] is configured.
"""

from __future__ import annotations

import logging
import time

logger = logging.getLogger(__name__)


def is_persistence_enabled() -> bool:
    """Check if database persistence is configured."""
    from django_celeryx.settings import celeryx_settings

    return celeryx_settings.DATABASE is not None


def _get_db() -> str | None:
    from django_celeryx.settings import celeryx_settings

    return celeryx_settings.DATABASE


def persist_task_event(uuid: str, **fields: object) -> None:
    """Write a task event to the database (upsert by uuid)."""
    if not is_persistence_enabled():
        return

    try:
        from django_celeryx.db_models import TaskEvent

        db = _get_db()
        now = time.time()

        existing = TaskEvent.objects.using(db).filter(uuid=uuid).first()
        if existing:
            for k, v in fields.items():
                if hasattr(existing, k) and v is not None and v != "":
                    setattr(existing, k, v)
            existing.updated_at = now
            existing.save(using=db)
        else:
            clean_fields = {k: v for k, v in fields.items() if hasattr(TaskEvent, k)}
            TaskEvent.objects.using(db).create(uuid=uuid, updated_at=now, **clean_fields)
    except Exception:
        logger.debug("Failed to persist task event %s", uuid, exc_info=True)


def persist_worker_event(hostname: str, **fields: object) -> None:
    """Write a worker event to the database (upsert by hostname)."""
    if not is_persistence_enabled():
        return

    try:
        from django_celeryx.db_models import WorkerEvent

        db = _get_db()
        now = time.time()

        existing = WorkerEvent.objects.using(db).filter(hostname=hostname).first()
        if existing:
            for k, v in fields.items():
                if hasattr(existing, k) and v is not None:
                    setattr(existing, k, v)
            existing.updated_at = now
            existing.save(using=db)
        else:
            clean_fields = {k: v for k, v in fields.items() if hasattr(WorkerEvent, k)}
            WorkerEvent.objects.using(db).create(hostname=hostname, updated_at=now, **clean_fields)
    except Exception:
        logger.debug("Failed to persist worker event %s", hostname, exc_info=True)


def replay_from_db() -> int:
    """Replay persisted events into in-memory stores on startup.

    Returns the number of tasks replayed.
    """
    if not is_persistence_enabled():
        return 0

    try:
        from django_celeryx.db_models import TaskEvent, WorkerEvent
        from django_celeryx.settings import celeryx_settings
        from django_celeryx.state.tasks import task_store
        from django_celeryx.state.workers import worker_store

        db = _get_db()
        task_count = 0

        # Replay tasks (most recent first, up to MAX_TASKS)
        for te in TaskEvent.objects.using(db).order_by("-updated_at")[: celeryx_settings.MAX_TASKS]:
            fields = {}
            for field_name in ("name", "state", "worker", "args", "kwargs", "result",
                               "exception", "traceback", "runtime", "eta", "expires",
                               "exchange", "routing_key", "retries", "parent_id", "root_id",
                               "received", "started", "succeeded", "failed", "retried_at", "revoked"):
                val = getattr(te, field_name, None)
                if val is not None and val not in ("", 0):
                    # Map retried_at back to retried for TaskInfo
                    key = "retried" if field_name == "retried_at" else field_name
                    fields[key] = val
            task_store.update(te.uuid, **fields)
            task_count += 1

        # Replay workers
        for we in WorkerEvent.objects.using(db).all():
            fields = {}
            for field_name in ("status", "active", "freq", "loadavg", "sw_ident",
                               "sw_ver", "sw_sys", "last_heartbeat"):
                val = getattr(we, field_name, None)
                if val is not None and val != "":
                    fields[field_name] = val
            worker_store.update(we.hostname, **fields)

        logger.info("Replayed %d tasks from database", task_count)
        return task_count
    except Exception:
        logger.debug("Failed to replay from database", exc_info=True)
        return 0


def cleanup_old_events() -> int:
    """Delete events older than MAX_EVENT_AGE. Returns count deleted."""
    if not is_persistence_enabled():
        return 0

    try:
        from django_celeryx.db_models import TaskEvent
        from django_celeryx.settings import celeryx_settings

        db = _get_db()
        cutoff = time.time() - celeryx_settings.MAX_EVENT_AGE
        deleted, _ = TaskEvent.objects.using(db).filter(updated_at__lt=cutoff).delete()
        if deleted:
            logger.info("Cleaned up %d old task events", deleted)
        return deleted
    except Exception:
        logger.debug("Failed to clean up old events", exc_info=True)
        return 0
