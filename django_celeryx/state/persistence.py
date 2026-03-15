"""Database persistence for event data.

The database is the single source of truth for all task and worker data.
Event handlers write here, admin views read from here.
"""

from __future__ import annotations

import logging
import time

logger = logging.getLogger(__name__)


def _get_db() -> str:
    from django_celeryx.settings import get_db_alias

    return get_db_alias()


def persist_task_event(uuid: str, **fields: object) -> None:
    """Write a task event to the database (upsert by uuid)."""
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


def cleanup_old_events() -> int:
    """Delete events older than MAX_EVENT_AGE. Returns count deleted."""
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


def ensure_tables() -> None:
    """Ensure celeryx database tables exist (run migrations programmatically)."""
    try:
        from django.core.management import call_command

        db = _get_db()
        call_command("migrate", "django_celeryx", database=db, verbosity=0)
    except Exception:
        logger.debug("Failed to run celeryx migrations", exc_info=True)
