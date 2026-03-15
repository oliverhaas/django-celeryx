"""Task control actions: revoke, terminate, abort, apply, rate-limit, timeout."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def _get_celery_app() -> Any:
    """Get the Celery app instance."""
    from django_celeryx.settings import celeryx_settings

    if celeryx_settings.CELERY_APP:
        from importlib import import_module

        module_path, attr = celeryx_settings.CELERY_APP.rsplit(".", 1)
        module = import_module(module_path)
        return getattr(module, attr)

    # Auto-detect from Django settings
    from django.conf import settings

    if hasattr(settings, "CELERY_APP"):
        return settings.CELERY_APP  # type: ignore[misc]

    # Try the common pattern: <project>.celery.app
    from celery import current_app

    return current_app


def revoke_task(task_id: str, *, terminate: bool = False, signal: str = "SIGTERM") -> None:
    """Revoke a task, optionally terminating it."""
    app = _get_celery_app()
    app.control.revoke(task_id, terminate=terminate, signal=signal)
    logger.info("Revoked task %s (terminate=%s, signal=%s)", task_id, terminate, signal)


def abort_task(task_id: str) -> None:
    """Abort an abortable task."""
    from celery.contrib.abortable import AbortableAsyncResult

    result = AbortableAsyncResult(task_id)
    result.abort()
    logger.info("Aborted task %s", task_id)


def apply_task(name: str, args: tuple[Any, ...] | None = None, kwargs: dict[str, Any] | None = None) -> str:
    """Send a task by name. Returns task ID."""
    app = _get_celery_app()
    result = app.send_task(name, args=args, kwargs=kwargs)
    logger.info("Applied task %s -> %s", name, result.id)
    return result.id


def set_rate_limit(
    task_name: str,
    rate: str,
    *,
    destination: list[str] | None = None,
) -> None:
    """Set rate limit for a task type."""
    app = _get_celery_app()
    app.control.rate_limit(task_name, rate, destination=destination)
    logger.info("Set rate limit %s=%s (destination=%s)", task_name, rate, destination)


def set_time_limit(
    task_name: str,
    *,
    soft: float | None = None,
    hard: float | None = None,
    destination: list[str] | None = None,
) -> None:
    """Set time limit for a task type."""
    app = _get_celery_app()
    app.control.time_limit(task_name, soft=soft, hard=hard, destination=destination)
    logger.info("Set time limit %s soft=%s hard=%s (destination=%s)", task_name, soft, hard, destination)
