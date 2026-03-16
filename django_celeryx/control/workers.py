"""Worker control actions: shutdown, restart pool, grow/shrink, autoscale, consumers."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def _get_celery_app() -> Any:
    from django_celeryx.helpers import get_celery_app

    return get_celery_app()


def shutdown_worker(hostname: str) -> None:
    """Shutdown a worker."""
    app = _get_celery_app()
    app.control.broadcast("shutdown", destination=[hostname])
    logger.info("Shutdown worker %s", hostname)


def pool_restart(hostname: str) -> None:
    """Restart a worker's pool."""
    app = _get_celery_app()
    app.control.pool_restart(destination=[hostname])
    logger.info("Pool restart worker %s", hostname)


def pool_grow(hostname: str, n: int = 1) -> None:
    """Grow a worker's pool by n processes."""
    app = _get_celery_app()
    app.control.pool_grow(n, destination=[hostname])
    logger.info("Pool grow worker %s by %d", hostname, n)


def pool_shrink(hostname: str, n: int = 1) -> None:
    """Shrink a worker's pool by n processes."""
    app = _get_celery_app()
    app.control.pool_shrink(n, destination=[hostname])
    logger.info("Pool shrink worker %s by %d", hostname, n)


def autoscale(hostname: str, max_concurrency: int, min_concurrency: int) -> None:
    """Set autoscale limits for a worker."""
    app = _get_celery_app()
    app.control.autoscale(max_concurrency, min_concurrency, destination=[hostname])
    logger.info("Autoscale worker %s max=%d min=%d", hostname, max_concurrency, min_concurrency)


def add_consumer(hostname: str, queue: str) -> None:
    """Add a queue consumer to a worker."""
    app = _get_celery_app()
    app.control.add_consumer(queue, destination=[hostname])
    logger.info("Add consumer %s to worker %s", queue, hostname)


def cancel_consumer(hostname: str, queue: str) -> None:
    """Cancel a queue consumer from a worker."""
    app = _get_celery_app()
    app.control.cancel_consumer(queue, destination=[hostname])
    logger.info("Cancel consumer %s from worker %s", queue, hostname)
