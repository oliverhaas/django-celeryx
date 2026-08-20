"""Tests for worker control actions."""

from unittest.mock import MagicMock

import pytest

from django_celeryx.control import workers


@pytest.fixture
def app(monkeypatch):
    fake = MagicMock()
    monkeypatch.setattr(workers, "_get_celery_app", lambda: fake)
    return fake


def test_shutdown_worker_broadcasts(app):
    workers.shutdown_worker("w1@host")
    app.control.broadcast.assert_called_once_with("shutdown", destination=["w1@host"])


def test_pool_restart(app):
    workers.pool_restart("w1@host")
    app.control.pool_restart.assert_called_once_with(destination=["w1@host"])


def test_pool_grow_defaults_to_one(app):
    workers.pool_grow("w1@host")
    app.control.pool_grow.assert_called_once_with(1, destination=["w1@host"])


def test_pool_grow_with_count(app):
    workers.pool_grow("w1@host", 4)
    app.control.pool_grow.assert_called_once_with(4, destination=["w1@host"])


def test_pool_shrink(app):
    workers.pool_shrink("w1@host", 2)
    app.control.pool_shrink.assert_called_once_with(2, destination=["w1@host"])


def test_autoscale_passes_max_then_min(app):
    workers.autoscale("w1@host", 10, 2)
    app.control.autoscale.assert_called_once_with(10, 2, destination=["w1@host"])


def test_add_consumer(app):
    workers.add_consumer("w1@host", "priority")
    app.control.add_consumer.assert_called_once_with("priority", destination=["w1@host"])


def test_cancel_consumer(app):
    workers.cancel_consumer("w1@host", "priority")
    app.control.cancel_consumer.assert_called_once_with("priority", destination=["w1@host"])
