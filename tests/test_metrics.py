"""Tests for Prometheus metrics."""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _reset_metrics():
    """Reset the metrics singleton and collector registry between tests."""
    import prometheus_client

    import django_celeryx.metrics as m

    old = m._metrics
    m._metrics = None

    # Unregister all collectors so metrics can be re-created
    import contextlib

    collectors = list(prometheus_client.REGISTRY._names_to_collectors.values())
    for collector in set(collectors):
        with contextlib.suppress(Exception):
            prometheus_client.REGISTRY.unregister(collector)

    yield
    m._metrics = old


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


def test_update_metrics_from_task_event():
    from unittest.mock import MagicMock

    from django_celeryx.metrics import get_metrics, update_metrics_from_event

    metrics = get_metrics()

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

    # Check event counter incremented
    assert metrics.events.labels("worker-1", "task-started", "my.task")._value.get() > 0


def test_update_metrics_from_worker_event():
    from unittest.mock import MagicMock

    from django_celeryx.metrics import get_metrics, update_metrics_from_event

    metrics = get_metrics()
    state = MagicMock()
    state.tasks = {}

    event = {
        "type": "worker-online",
        "hostname": "worker-1",
    }
    update_metrics_from_event(event, state)
    assert metrics.worker_online.labels("worker-1")._value.get() == 1.0

    event = {
        "type": "worker-offline",
        "hostname": "worker-1",
    }
    update_metrics_from_event(event, state)
    assert metrics.worker_online.labels("worker-1")._value.get() == 0.0


def test_update_metrics_runtime_histogram():
    from unittest.mock import MagicMock

    from django_celeryx.metrics import get_metrics, update_metrics_from_event

    metrics = get_metrics()
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

    assert metrics.runtime.labels("worker-1", "my.task")._sum.get() == 1.5


def test_metrics_view():
    from django.test import RequestFactory

    from django_celeryx.metrics import metrics_view

    factory = RequestFactory()
    request = factory.get("/celeryx/metrics/")
    response = metrics_view(request)
    assert response.status_code == 200
    content = response.content.decode()
    assert "flower_events_total" in content or "celeryx_tasks_total" in content
