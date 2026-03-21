"""Prometheus metrics compatible with Flower's metric names.

Metrics are only registered if ``prometheus-client`` is installed.
Install with ``pip install django-celeryx[prometheus]``.

Flower-compatible metrics:

- ``flower_events_total`` — Counter(worker, type, task)
- ``flower_task_runtime_seconds`` — Histogram(worker, task)
- ``flower_task_prefetch_time_seconds`` — Gauge(worker, task)
- ``flower_task_prefetch_count`` — Gauge(worker, task)
- ``flower_worker_online`` — Gauge(worker)
- ``flower_worker_number_of_currently_executing_tasks`` — Gauge(worker)

Additional celeryx-specific metrics:

- ``celeryx_tasks_total`` — Gauge of total tasks in the database
- ``celeryx_tasks_active`` — Gauge of active (non-terminal) tasks
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

_metrics: _PrometheusMetrics | None = None


class _PrometheusMetrics:
    """Holds all Prometheus metric objects."""

    def __init__(self) -> None:
        from prometheus_client import Counter, Gauge, Histogram

        # Flower-compatible metrics
        self.events = Counter(
            "flower_events_total",
            "Number of events",
            ["worker", "type", "task"],
        )
        self.runtime = Histogram(
            "flower_task_runtime_seconds",
            "Task runtime in seconds",
            ["worker", "task"],
            buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0, float("inf")),
        )
        self.prefetch_time = Gauge(
            "flower_task_prefetch_time_seconds",
            "Time between task received and started",
            ["worker", "task"],
        )
        self.number_of_prefetched_tasks = Gauge(
            "flower_task_prefetch_count",
            "Number of prefetched tasks",
            ["worker", "task"],
        )
        self.worker_online = Gauge(
            "flower_worker_online",
            "Worker online status",
            ["worker"],
        )
        self.worker_number_of_currently_executing_tasks = Gauge(
            "flower_worker_number_of_currently_executing_tasks",
            "Number of currently executing tasks on worker",
            ["worker"],
        )

        # Additional celeryx metrics
        self.tasks_total = Gauge(
            "celeryx_tasks_total",
            "Total tasks in the database",
        )
        self.tasks_active = Gauge(
            "celeryx_tasks_active",
            "Active (non-terminal) tasks in the database",
        )


def get_metrics() -> _PrometheusMetrics | None:
    """Get or create metrics. Returns None if prometheus_client is not installed."""
    global _metrics  # noqa: PLW0603
    if _metrics is not None:
        return _metrics
    try:
        _metrics = _PrometheusMetrics()
    except ImportError:
        logger.debug("prometheus-client not installed, metrics disabled")
        return None
    return _metrics


def update_metrics_from_event(event: dict[str, Any], state: Any) -> None:  # noqa: C901
    """Update Prometheus metrics from a Celery event.

    Called from the event handler after State.event() processes the event.
    Mirrors Flower's EventsState.event() metric instrumentation.
    """
    metrics = get_metrics()
    if metrics is None:
        return

    worker_name = event.get("hostname", "")
    event_type = event.get("type", "")

    if event_type.startswith("task-"):
        task_id = event.get("uuid", "")
        task = state.tasks.get(task_id)
        task_name = event.get("name", "")
        if not task_name and task is not None:
            task_name = getattr(task, "name", "") or ""

        metrics.events.labels(worker_name, event_type, task_name).inc()

        runtime = event.get("runtime")
        if runtime:
            metrics.runtime.labels(worker_name, task_name).observe(runtime)

        if task is not None:
            task_started = getattr(task, "started", None)
            task_received = getattr(task, "received", None)

            if event_type == "task-received" and not getattr(task, "eta", None) and task_received:
                metrics.number_of_prefetched_tasks.labels(worker_name, task_name).inc()

            if event_type == "task-started" and not getattr(task, "eta", None) and task_started and task_received:
                metrics.prefetch_time.labels(worker_name, task_name).set(task_started - task_received)
                metrics.number_of_prefetched_tasks.labels(worker_name, task_name).dec()

            if (
                event_type in ("task-succeeded", "task-failed")
                and not getattr(task, "eta", None)
                and task_started
                and task_received
            ):
                metrics.prefetch_time.labels(worker_name, task_name).set(0)

    elif event_type == "worker-online":
        metrics.worker_online.labels(worker_name).set(1)

    elif event_type == "worker-heartbeat":
        metrics.worker_online.labels(worker_name).set(1)
        num_executing = event.get("active")
        if num_executing is not None:
            metrics.worker_number_of_currently_executing_tasks.labels(worker_name).set(num_executing)

    elif event_type == "worker-offline":
        metrics.worker_online.labels(worker_name).set(0)


def metrics_view(request: Any) -> Any:  # noqa: ARG001
    """Django view that serves Prometheus metrics in text format."""
    from django.http import HttpResponse

    try:
        from prometheus_client import generate_latest
    except ImportError:
        return HttpResponse(
            "prometheus-client not installed. Install with: pip install django-celeryx[prometheus]",
            status=501,
            content_type="text/plain",
        )

    # Update DB-derived gauges before generating output
    _update_db_gauges()

    return HttpResponse(
        generate_latest(),
        content_type="text/plain; version=0.0.4; charset=utf-8",
    )


def _update_db_gauges() -> None:
    """Update gauges that are derived from database state."""
    metrics = get_metrics()
    if metrics is None:
        return
    try:
        from django_celeryx.db_models import TaskState
        from django_celeryx.settings import get_db_alias

        db = get_db_alias()
        metrics.tasks_total.set(TaskState.objects.using(db).count())
        metrics.tasks_active.set(
            TaskState.objects.using(db).filter(state__in=("PENDING", "RECEIVED", "STARTED", "RETRY")).count()
        )
    except Exception:
        logger.debug("Failed to update DB gauges", exc_info=True)
