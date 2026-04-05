"""Tests for Prometheus metrics."""

from __future__ import annotations

import contextlib

import pytest

prometheus_client = pytest.importorskip("prometheus_client")


@pytest.fixture(autouse=True)
def _reset_metrics():
    """Reset the metrics singleton and collector registry between tests."""
    import django_celeryx.metrics as m

    old = m._metrics
    m._metrics = None

    collectors = list(prometheus_client.REGISTRY._names_to_collectors.values())
    for collector in set(collectors):
        with contextlib.suppress(Exception):
            prometheus_client.REGISTRY.unregister(collector)

    yield
    m._metrics = old


def _get_counter_value(name, labels):
    """Get the current value of a prometheus Counter."""
    return prometheus_client.REGISTRY.get_sample_value(f"{name}_total", labels) or 0


def _get_gauge_value(name, labels=None):
    """Get the current value of a prometheus Gauge."""
    return prometheus_client.REGISTRY.get_sample_value(name, labels or {}) or 0


def _get_histogram_sum(name, labels):
    """Get the sum of a prometheus Histogram."""
    return prometheus_client.REGISTRY.get_sample_value(f"{name}_sum", labels) or 0


def test_get_metrics_returns_instance():
    from django_celeryx.metrics import get_metrics

    metrics = get_metrics()
    assert metrics is not None
    assert hasattr(metrics, "events")
    assert hasattr(metrics, "runtime")
    assert hasattr(metrics, "worker_online")


def test_get_metrics_is_singleton():
    from django_celeryx.metrics import get_metrics

    m1 = get_metrics()
    m2 = get_metrics()
    assert m1 is m2


def test_celeryx_metrics_registered_by_default():
    from django_celeryx.metrics import get_metrics

    get_metrics()
    # celeryx metrics should exist
    names = {m.name for m in prometheus_client.REGISTRY.collect() if hasattr(m, "name")}
    assert "django_celeryx_events" in names
    assert "django_celeryx_task_runtime_seconds" in names
    assert "django_celeryx_worker_online" in names
    # flower metrics should NOT exist by default
    assert "flower_events" not in names


def test_update_metrics_from_task_event():
    from unittest.mock import MagicMock

    from django_celeryx.metrics import update_metrics_from_event

    state = MagicMock()
    task_mock = MagicMock()
    task_mock.name = "my.task"
    task_mock.started = 100.5
    task_mock.received = 100.0
    task_mock.eta = None
    state.tasks = {"abc-123": task_mock}

    event = {
        "type": "task-started",
        "uuid": "abc-123",
        "hostname": "worker-1",
    }
    update_metrics_from_event(event, state)

    val = _get_counter_value("django_celeryx_events", {"worker": "worker-1", "type": "task-started", "task": "my.task"})
    assert val > 0


def test_update_metrics_from_worker_event():
    from unittest.mock import MagicMock

    from django_celeryx.metrics import update_metrics_from_event

    state = MagicMock()
    state.tasks = {}

    event = {"type": "worker-online", "hostname": "worker-1"}
    update_metrics_from_event(event, state)
    assert _get_gauge_value("django_celeryx_worker_online", {"worker": "worker-1"}) == 1.0

    event = {"type": "worker-offline", "hostname": "worker-1"}
    update_metrics_from_event(event, state)
    assert _get_gauge_value("django_celeryx_worker_online", {"worker": "worker-1"}) == 0.0


def test_update_metrics_runtime_histogram():
    from unittest.mock import MagicMock

    from django_celeryx.metrics import update_metrics_from_event

    state = MagicMock()
    task_mock = MagicMock()
    task_mock.name = "my.task"
    task_mock.started = 100.0
    task_mock.received = 99.5
    task_mock.eta = None
    state.tasks = {"abc-123": task_mock}

    event = {
        "type": "task-succeeded",
        "uuid": "abc-123",
        "hostname": "worker-1",
        "runtime": 1.5,
    }
    update_metrics_from_event(event, state)

    assert _get_histogram_sum("django_celeryx_task_runtime_seconds", {"worker": "worker-1", "task": "my.task"}) == 1.5


def test_metrics_view():
    from django.test import RequestFactory

    from django_celeryx.metrics import metrics_view

    factory = RequestFactory()
    request = factory.get("/celeryx/metrics/")
    response = metrics_view(request)
    assert response.status_code == 200
    content = response.content.decode()
    assert "django_celeryx_events" in content
