"""Prometheus metrics for django-celeryx.

Metrics are only registered if ``prometheus-client`` is installed.
Install with ``pip install django-celeryx[prometheus]``.

Primary metrics (always registered):

- ``celeryx_events_total`` — Counter(worker, type, task)
- ``celeryx_task_runtime_seconds`` — Histogram(worker, task)
- ``celeryx_task_prefetch_time_seconds`` — Gauge(worker, task)
- ``celeryx_task_prefetch_count`` — Gauge(worker, task)
- ``celeryx_worker_online`` — Gauge(worker)
- ``celeryx_worker_executing_tasks`` — Gauge(worker)
- ``celeryx_tasks_total`` — Gauge of total tasks in the database
- ``celeryx_tasks_active`` — Gauge of active (non-terminal) tasks

Flower-compatible duplicates (opt-in via ``CELERYX["PROMETHEUS_FLOWER_COMPAT"] = True``):

- ``flower_events_total``
- ``flower_task_runtime_seconds``
- ``flower_task_prefetch_time_seconds``
- ``flower_task_prefetch_count``
- ``flower_worker_online``
- ``flower_worker_number_of_currently_executing_tasks``
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

_metrics: _PrometheusMetrics | None = None


class _MetricSet:
    """A set of identically-labelled metrics that can be updated together."""

    def __init__(self, *metrics: Any) -> None:
        self._metrics = metrics

    def labels(self, *args: Any) -> _LabelledSet:
        return _LabelledSet([m.labels(*args) for m in self._metrics])

    def set(self, value: float) -> None:
        for m in self._metrics:
            m.set(value)

    def inc(self, amount: float = 1) -> None:
        for m in self._metrics:
            m.inc(amount)

    def dec(self, amount: float = 1) -> None:
        for m in self._metrics:
            m.dec(amount)

    def observe(self, value: float) -> None:
        for m in self._metrics:
            m.observe(value)


class _LabelledSet:
    """Labelled metric instances that can be updated together."""

    def __init__(self, labelled: list[Any]) -> None:
        self._labelled = labelled

    def inc(self, amount: float = 1) -> None:
        for m in self._labelled:
            m.inc(amount)

    def dec(self, amount: float = 1) -> None:
        for m in self._labelled:
            m.dec(amount)

    def set(self, value: float) -> None:
        for m in self._labelled:
            m.set(value)

    def observe(self, value: float) -> None:
        for m in self._labelled:
            m.observe(value)


_RUNTIME_BUCKETS = (0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0, float("inf"))


class _PrometheusMetrics:
    """Holds all Prometheus metric objects."""

    def __init__(self) -> None:
        from prometheus_client import Counter, Gauge, Histogram

        flower_compat = self._flower_compat_enabled()

        # Primary celeryx metrics
        cx_events = Counter("celeryx_events_total", "Number of Celery events", ["worker", "type", "task"])
        cx_runtime = Histogram(
            "celeryx_task_runtime_seconds", "Task runtime", ["worker", "task"], buckets=_RUNTIME_BUCKETS
        )
        cx_prefetch_time = Gauge(
            "celeryx_task_prefetch_time_seconds", "Time between task received and started", ["worker", "task"]
        )
        cx_prefetch_count = Gauge("celeryx_task_prefetch_count", "Number of prefetched tasks", ["worker", "task"])
        cx_worker_online = Gauge("celeryx_worker_online", "Worker online status", ["worker"])
        cx_executing = Gauge("celeryx_worker_executing_tasks", "Currently executing tasks on worker", ["worker"])

        if flower_compat:
            fl_events = Counter("flower_events_total", "Number of events", ["worker", "type", "task"])
            fl_runtime = Histogram(
                "flower_task_runtime_seconds", "Task runtime in seconds", ["worker", "task"], buckets=_RUNTIME_BUCKETS
            )
            fl_prefetch_time = Gauge(
                "flower_task_prefetch_time_seconds", "Time between task received and started", ["worker", "task"]
            )
            fl_prefetch_count = Gauge("flower_task_prefetch_count", "Number of prefetched tasks", ["worker", "task"])
            fl_worker_online = Gauge("flower_worker_online", "Worker online status", ["worker"])
            fl_executing = Gauge(
                "flower_worker_number_of_currently_executing_tasks",
                "Number of currently executing tasks on worker",
                ["worker"],
            )

            self.events = _MetricSet(cx_events, fl_events)
            self.runtime = _MetricSet(cx_runtime, fl_runtime)
            self.prefetch_time = _MetricSet(cx_prefetch_time, fl_prefetch_time)
            self.number_of_prefetched_tasks = _MetricSet(cx_prefetch_count, fl_prefetch_count)
            self.worker_online = _MetricSet(cx_worker_online, fl_worker_online)
            self.worker_executing = _MetricSet(cx_executing, fl_executing)
        else:
            self.events = _MetricSet(cx_events)
            self.runtime = _MetricSet(cx_runtime)
            self.prefetch_time = _MetricSet(cx_prefetch_time)
            self.number_of_prefetched_tasks = _MetricSet(cx_prefetch_count)
            self.worker_online = _MetricSet(cx_worker_online)
            self.worker_executing = _MetricSet(cx_executing)

        # DB-derived gauges (celeryx only, no flower equivalent)
        self.tasks_total = Gauge("celeryx_tasks_total", "Total tasks in the database")
        self.tasks_active = Gauge("celeryx_tasks_active", "Active (non-terminal) tasks in the database")

    @staticmethod
    def _flower_compat_enabled() -> bool:
        try:
            from django_celeryx.settings import celeryx_settings

            return getattr(celeryx_settings, "PROMETHEUS_FLOWER_COMPAT", False)
        except Exception:
            return False


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
            metrics.worker_executing.labels(worker_name).set(num_executing)

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
