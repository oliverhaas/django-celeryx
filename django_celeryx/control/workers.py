"""Worker control actions: shutdown, restart pool, grow/shrink, autoscale, consumers."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def _get_celery_app() -> Any:
    from django_celeryx.helpers import get_celery_app

    return get_celery_app()


def _reply_timeout() -> float:
    from django_celeryx.settings import celeryx_settings

    return float(celeryx_settings.INSPECT_TIMEOUT)


def reply_error(replies: list[dict[str, Any]] | None) -> str | None:
    """Return the first error a worker reported, or None if all replies are ok.

    Control commands are broadcasts. Without reply=True a command that the
    worker rejects (shrinking a busy pool, for example) looks like a success.
    """
    for reply in replies or []:
        for response in reply.values():
            if isinstance(response, dict) and "error" in response:
                return str(response["error"])
    return None


def shutdown_worker(hostname: str) -> None:
    """Shutdown a worker."""
    app = _get_celery_app()
    app.control.broadcast("shutdown", destination=[hostname])
    logger.info("Shutdown worker %s", hostname)


def pool_restart(hostname: str) -> list[dict[str, Any]]:
    """Restart a worker's pool."""
    app = _get_celery_app()
    replies = app.control.pool_restart(destination=[hostname], reply=True, timeout=_reply_timeout())
    logger.info("Pool restart worker %s", hostname)
    return replies or []


def pool_grow(hostname: str, n: int = 1) -> list[dict[str, Any]]:
    """Grow a worker's pool by n processes."""
    app = _get_celery_app()
    replies = app.control.pool_grow(n, destination=[hostname], reply=True, timeout=_reply_timeout())
    logger.info("Pool grow worker %s by %d", hostname, n)
    return replies or []


def pool_shrink(hostname: str, n: int = 1) -> list[dict[str, Any]]:
    """Shrink a worker's pool by n processes."""
    app = _get_celery_app()
    replies = app.control.pool_shrink(n, destination=[hostname], reply=True, timeout=_reply_timeout())
    logger.info("Pool shrink worker %s by %d", hostname, n)
    return replies or []


def autoscale(hostname: str, max_concurrency: int, min_concurrency: int) -> list[dict[str, Any]]:
    """Set autoscale limits for a worker."""
    app = _get_celery_app()
    replies = app.control.autoscale(
        max_concurrency,
        min_concurrency,
        destination=[hostname],
        reply=True,
        timeout=_reply_timeout(),
    )
    logger.info("Autoscale worker %s max=%d min=%d", hostname, max_concurrency, min_concurrency)
    return replies or []


def add_consumer(hostname: str, queue: str) -> list[dict[str, Any]]:
    """Add a queue consumer to a worker."""
    app = _get_celery_app()
    replies = app.control.add_consumer(queue, destination=[hostname], reply=True, timeout=_reply_timeout())
    logger.info("Add consumer %s to worker %s", queue, hostname)
    return replies or []


def cancel_consumer(hostname: str, queue: str) -> list[dict[str, Any]]:
    """Cancel a queue consumer from a worker."""
    app = _get_celery_app()
    replies = app.control.cancel_consumer(queue, destination=[hostname], reply=True, timeout=_reply_timeout())
    logger.info("Cancel consumer %s from worker %s", queue, hostname)
    return replies or []
