"""Tests for task control actions."""

from unittest.mock import MagicMock

import pytest

from django_celeryx.control import tasks


@pytest.fixture
def app(monkeypatch):
    fake = MagicMock()
    monkeypatch.setattr(tasks, "get_celery_app", lambda: fake)
    return fake


def test_revoke_task_defaults(app):
    tasks.revoke_task("abc")
    app.control.revoke.assert_called_once_with("abc", terminate=False, signal="SIGTERM")


def test_revoke_task_terminate(app):
    tasks.revoke_task("abc", terminate=True, signal="SIGKILL")
    app.control.revoke.assert_called_once_with("abc", terminate=True, signal="SIGKILL")


def test_apply_task_returns_id(app):
    app.send_task.return_value.id = "new-id"
    result = tasks.apply_task("proj.add", args=(1, 2), kwargs={"c": 3})
    assert result == "new-id"
    app.send_task.assert_called_once_with("proj.add", args=(1, 2), kwargs={"c": 3})


def test_set_rate_limit(app):
    tasks.set_rate_limit("proj.add", "10/m", destination=["w1@host"])
    app.control.rate_limit.assert_called_once_with("proj.add", "10/m", destination=["w1@host"])


def test_set_time_limit(app):
    tasks.set_time_limit("proj.add", soft=10, hard=20)
    app.control.time_limit.assert_called_once_with("proj.add", soft=10, hard=20, destination=None)


def test_abort_task(monkeypatch):
    result = MagicMock()
    from celery.contrib import abortable

    monkeypatch.setattr(abortable, "AbortableAsyncResult", lambda task_id: result)
    tasks.abort_task("abc")
    result.abort.assert_called_once_with()
