"""Database persistence for task and worker state.

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
    """Upsert task state in the database by uuid."""
    try:
        from django_celeryx.db_models import TaskState

        db = _get_db()
        now = time.time()

        existing = TaskState.objects.using(db).filter(uuid=uuid).first()
        if existing:
            for k, v in fields.items():
                if hasattr(existing, k) and v is not None and v != "":
                    setattr(existing, k, v)
            existing.updated_at = now
            existing.save(using=db)
        else:
            clean_fields = {k: v for k, v in fields.items() if hasattr(TaskState, k)}
            TaskState.objects.using(db).create(uuid=uuid, updated_at=now, **clean_fields)
    except Exception:
        logger.debug("Failed to persist task state %s", uuid, exc_info=True)


def persist_worker_event(hostname: str, **fields: object) -> None:
    """Upsert worker state in the database by hostname."""
    try:
        from django_celeryx.db_models import WorkerState

        db = _get_db()
        now = time.time()

        existing = WorkerState.objects.using(db).filter(hostname=hostname).first()
        if existing:
            for k, v in fields.items():
                if hasattr(existing, k) and v is not None:
                    setattr(existing, k, v)
            existing.updated_at = now
            existing.save(using=db)
        else:
            clean_fields = {k: v for k, v in fields.items() if hasattr(WorkerState, k)}
            WorkerState.objects.using(db).create(hostname=hostname, updated_at=now, **clean_fields)
    except Exception:
        logger.debug("Failed to persist worker state %s", hostname, exc_info=True)


def cleanup_old_tasks() -> int:
    """Delete tasks older than MAX_TASK_AGE and enforce MAX_TASK_COUNT. Returns count deleted."""
    try:
        from django_celeryx.db_models import TaskState
        from django_celeryx.settings import celeryx_settings

        db = _get_db()
        total_deleted = 0

        # Delete by age
        cutoff = time.time() - celeryx_settings.MAX_TASK_AGE
        deleted, _ = TaskState.objects.using(db).filter(updated_at__lt=cutoff).delete()
        total_deleted += deleted

        # Enforce count limit
        count = TaskState.objects.using(db).count()
        if count > celeryx_settings.MAX_TASK_COUNT:
            excess = count - celeryx_settings.MAX_TASK_COUNT
            oldest_ids = list(TaskState.objects.using(db).order_by("updated_at").values_list("id", flat=True)[:excess])
            if oldest_ids:
                deleted, _ = TaskState.objects.using(db).filter(id__in=oldest_ids).delete()
                total_deleted += deleted

        if total_deleted:
            logger.info("Cleaned up %d old task records", total_deleted)
        return total_deleted
    except Exception:
        logger.debug("Failed to clean up old tasks", exc_info=True)
        return 0


def ensure_tables() -> None:
    """Ensure celeryx database tables exist (run migrations programmatically)."""
    try:
        from django.core.management import call_command

        db = _get_db()
        call_command("migrate", "django_celeryx", database=db, verbosity=0)
    except Exception:
        logger.debug("Failed to run celeryx migrations", exc_info=True)
