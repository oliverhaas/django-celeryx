"""Tests for django-celeryx admin views."""

import time
from unittest.mock import MagicMock, patch

import pytest
from django.test import Client, override_settings
from django.urls import reverse

from django_celeryx.db_models import TaskState, WorkerState


@pytest.mark.django_db
class TestTaskListView:
    """Tests for the task changelist admin view."""

    def _url(self):
        return reverse("admin:django_celeryx_task_changelist")

    def test_list_returns_200(self, admin_client):
        now = time.time()
        TaskState.objects.create(uuid="task-001", name="proj.add", state="SUCCESS", updated_at=now)
        TaskState.objects.create(uuid="task-002", name="proj.mul", state="FAILURE", updated_at=now)
        response = admin_client.get(self._url())
        assert response.status_code == 200

    def test_list_requires_auth(self):
        client = Client()
        response = client.get(self._url())
        assert response.status_code == 302
        assert "/login/" in response.url or "login" in response.url

    def test_list_shows_tasks(self, admin_client):
        TaskState.objects.create(
            uuid="task-visible-1", name="myapp.compute_sum", state="SUCCESS", updated_at=time.time()
        )
        response = admin_client.get(self._url())
        assert response.status_code == 200
        content = response.content.decode()
        assert "myapp.compute_sum" in content

    def test_list_filter_by_state(self, admin_client):
        now = time.time()
        TaskState.objects.create(uuid="task-s1", name="proj.success_task", state="SUCCESS", updated_at=now)
        TaskState.objects.create(uuid="task-f1", name="proj.failed_task", state="FAILURE", updated_at=now)
        response = admin_client.get(self._url() + "?state=SUCCESS")
        assert response.status_code == 200
        content = response.content.decode()
        assert "proj.success_task" in content
        # The failed task UUID should not appear in the result list rows
        assert "task-f1" not in content

    def test_list_search(self, admin_client):
        now = time.time()
        TaskState.objects.create(uuid="task-srch1", name="special.searchtarget", state="STARTED", updated_at=now)
        TaskState.objects.create(uuid="task-srch2", name="other.unrelated", state="STARTED", updated_at=now)
        response = admin_client.get(self._url() + "?q=searchtarget")
        assert response.status_code == 200
        content = response.content.decode()
        assert "special.searchtarget" in content
        # The unrelated task UUID should not appear in the result list rows
        assert "task-srch2" not in content

    def test_live_toggle(self, admin_client):
        TaskState.objects.create(uuid="task-live1", name="proj.task", state="SUCCESS", updated_at=time.time())
        response = admin_client.get(self._url() + "?live=on")
        assert response.status_code == 200
        content = response.content.decode()
        assert "hx-get" in content
        assert "hx-trigger" in content


@pytest.mark.django_db
class TestTaskDetailView:
    """Tests for the task detail (change) admin view."""

    def _create_task(self, **overrides):
        defaults = {
            "uuid": "detail-uuid-001",
            "name": "myapp.process_order",
            "state": "SUCCESS",
            "worker": "worker1@host",
            "args": "('arg1', 'arg2')",
            "kwargs": "{'key': 'val'}",
            "result": "42",
            "runtime": 1.234,
            "received": time.time() - 10,
            "started": time.time() - 5,
            "succeeded": time.time(),
            "updated_at": time.time(),
        }
        defaults.update(overrides)
        return TaskState.objects.create(**defaults)

    def test_detail_returns_200(self, admin_client):
        task = self._create_task()
        url = reverse("admin:django_celeryx_task_change", args=[task.uuid])
        response = admin_client.get(url)
        assert response.status_code == 200

    def test_detail_shows_fields(self, admin_client):
        task = self._create_task()
        url = reverse("admin:django_celeryx_task_change", args=[task.uuid])
        response = admin_client.get(url)
        content = response.content.decode()
        assert task.name in content
        assert task.uuid in content
        assert "worker1@host" in content
        assert "&#x27;arg1&#x27;" in content or "arg1" in content
        assert "42" in content

    def test_detail_not_found(self, admin_client):
        url = reverse("admin:django_celeryx_task_change", args=["nonexistent-uuid-999"])
        response = admin_client.get(url)
        assert response.status_code == 200
        content = response.content.decode()
        assert "Task Not Found" in content

    @patch("django_celeryx.control.tasks.get_celery_app")
    def test_revoke_action(self, mock_get_app, admin_client):
        mock_app = MagicMock()
        mock_get_app.return_value = mock_app

        task = self._create_task(uuid="revoke-uuid-001", state="STARTED")
        url = reverse("admin:django_celeryx_task_change", args=[task.uuid])
        response = admin_client.post(url, {"action": "revoke"})
        # Should redirect after POST
        assert response.status_code == 302
        mock_app.control.revoke.assert_called_once_with("revoke-uuid-001", terminate=False, signal="SIGTERM")


@pytest.mark.django_db
class TestWorkerListView:
    """Tests for the worker changelist admin view."""

    def _url(self):
        return reverse("admin:django_celeryx_worker_changelist")

    @patch("django_celeryx.admin.queryset.get_celery_app")
    def test_list_returns_200(self, mock_get_app, admin_client):
        mock_app = MagicMock()
        mock_app.control.inspect.return_value.stats.return_value = {}
        mock_get_app.return_value = mock_app

        now = time.time()
        WorkerState.objects.create(hostname="worker1@host", status="online", updated_at=now)
        WorkerState.objects.create(hostname="worker2@host", status="offline", updated_at=now)
        response = admin_client.get(self._url())
        assert response.status_code == 200

    @patch("django_celeryx.admin.queryset.get_celery_app")
    def test_list_shows_summary_counts(self, mock_get_app, admin_client):
        mock_app = MagicMock()
        mock_app.control.inspect.return_value.stats.return_value = {}
        mock_get_app.return_value = mock_app

        now = time.time()
        WorkerState.objects.create(hostname="worker1@host", status="online", updated_at=now)
        TaskState.objects.create(uuid="t1", name="a.task", state="SUCCESS", worker="worker1@host", updated_at=now)
        TaskState.objects.create(uuid="t2", name="a.task", state="SUCCESS", worker="worker1@host", updated_at=now)
        TaskState.objects.create(uuid="t3", name="a.task", state="FAILURE", worker="worker1@host", updated_at=now)

        response = admin_client.get(self._url())
        assert response.status_code == 200
        content = response.content.decode()
        # total_processed = 3
        assert ">3<" in content or ">3</code>" in content

    @patch("django_celeryx.admin.queryset.get_celery_app")
    def test_monitoring_since(self, mock_get_app, admin_client):
        mock_app = MagicMock()
        mock_app.control.inspect.return_value.stats.return_value = {}
        mock_get_app.return_value = mock_app

        # Create a task with a known timestamp
        ts = 1700000000.0  # 2023-11-14 22:13:20 UTC
        WorkerState.objects.create(hostname="w1@host", status="online", updated_at=ts)
        TaskState.objects.create(uuid="old-task", name="a.task", state="SUCCESS", updated_at=ts)

        response = admin_client.get(self._url())
        assert response.status_code == 200
        content = response.content.decode()
        assert "Monitoring since" in content
        assert "2023-11-14" in content


@pytest.mark.django_db
class TestWorkerDetailView:
    """Tests for the worker detail (change) admin view."""

    def _create_worker(self, hostname="detail-worker@host"):
        return WorkerState.objects.create(
            hostname=hostname,
            status="online",
            active=2,
            sw_ident="py-celery",
            sw_ver="5.3.0",
            sw_sys="Linux",
            updated_at=time.time(),
        )

    @patch("django_celeryx.admin.views.worker_detail._inspect_worker")
    def test_detail_returns_200(self, mock_inspect, admin_client):
        mock_inspect.return_value = {}
        worker = self._create_worker()
        url = reverse("admin:django_celeryx_worker_change", args=[worker.hostname])
        response = admin_client.get(url)
        assert response.status_code == 200

    @patch("django_celeryx.admin.views.worker_detail._inspect_worker")
    def test_tabs(self, mock_inspect, admin_client):
        mock_inspect.return_value = {
            "pool": {},
            "queues": [],
            "total": {},
            "active": [],
            "scheduled": [],
            "reserved": [],
            "revoked": [],
            "registered": [],
            "conf": {},
            "rusage": {},
            "broker": {},
            "pid": None,
            "uptime": None,
            "clock": None,
            "prefetch_count": None,
        }
        worker = self._create_worker()
        base_url = reverse("admin:django_celeryx_worker_change", args=[worker.hostname])

        for tab in ("pool", "queues", "tasks", "limits", "config", "stats"):
            response = admin_client.get(base_url + f"?tab={tab}")
            assert response.status_code == 200, f"Tab '{tab}' did not return 200"
            content = response.content.decode()
            # The current tab link should be bold/underlined (style contains font-weight:bold)
            assert f'href="?tab={tab}"' in content


@pytest.mark.django_db
class TestQueueListView:
    """Tests for the queue changelist admin view."""

    @patch("django_celeryx.admin.queryset.get_celery_app")
    def test_list_returns_200(self, mock_get_app, admin_client):
        mock_app = MagicMock()
        mock_app.control.inspect.return_value.active_queues.return_value = {}
        mock_get_app.return_value = mock_app

        url = reverse("admin:django_celeryx_queue_changelist")
        response = admin_client.get(url)
        assert response.status_code == 200


@pytest.mark.django_db
class TestRegisteredTaskListView:
    """Tests for the registered task changelist admin view."""

    @patch("django_celeryx.admin.queryset.get_celery_app")
    def test_list_returns_200(self, mock_get_app, admin_client):
        mock_app = MagicMock()
        mock_app.control.inspect.return_value.registered.return_value = {}
        mock_app.tasks = {}
        mock_get_app.return_value = mock_app

        url = reverse("admin:django_celeryx_registeredtask_changelist")
        response = admin_client.get(url)
        assert response.status_code == 200


@pytest.mark.django_db
class TestApplyTaskView:
    """Tests for the send/apply task view."""

    def test_apply_form_returns_200(self, admin_client):
        url = reverse("admin:django_celeryx_task_apply")
        response = admin_client.get(url)
        assert response.status_code == 200
        assert b"Send Task" in response.content

    def test_apply_requires_auth(self, db):
        client = Client()
        url = reverse("admin:django_celeryx_task_apply")
        response = client.get(url)
        assert response.status_code == 302

    @patch("django_celeryx.control.tasks.apply_task")
    def test_apply_post_sends_task(self, mock_apply, admin_client):
        mock_apply.return_value = "abc-12345678"
        url = reverse("admin:django_celeryx_task_apply")
        response = admin_client.post(url, {"task_name": "my.task", "args": "[1, 2]", "kwargs": '{"x": 3}'})
        assert response.status_code == 302
        mock_apply.assert_called_once_with("my.task", args=(1, 2), kwargs={"x": 3})

    def test_apply_post_empty_name_shows_error(self, admin_client):
        url = reverse("admin:django_celeryx_task_apply")
        response = admin_client.post(url, {"task_name": "", "args": "", "kwargs": ""})
        assert response.status_code == 302

    def test_apply_post_invalid_json_shows_error(self, admin_client):
        url = reverse("admin:django_celeryx_task_apply")
        response = admin_client.post(url, {"task_name": "my.task", "args": "not json"})
        assert response.status_code == 302

    def test_task_list_has_send_task_link(self, admin_client):
        url = reverse("admin:django_celeryx_task_changelist")
        response = admin_client.get(url)
        assert b"Send Task" in response.content


@pytest.mark.django_db
class TestDashboardView:
    """Tests for the dashboard view with Pygal charts."""

    def test_dashboard_returns_200_empty(self, admin_client):
        url = reverse("admin:django_celeryx_dashboard_changelist")
        response = admin_client.get(url)
        assert response.status_code == 200
        assert b"Dashboard" in response.content

    def test_dashboard_shows_stats(self, admin_client):
        now = time.time()
        TaskState.objects.create(uuid="d1", name="a.task", state="SUCCESS", runtime=0.5, updated_at=now)
        TaskState.objects.create(uuid="d2", name="a.task", state="SUCCESS", runtime=1.5, updated_at=now)
        TaskState.objects.create(uuid="d3", name="b.task", state="FAILURE", updated_at=now)

        url = reverse("admin:django_celeryx_dashboard_changelist")
        response = admin_client.get(url)
        assert response.status_code == 200
        content = response.content.decode()
        assert "Success Rate" in content
        assert "66.7%" in content

    def test_dashboard_has_svg_charts(self, admin_client):
        now = time.time()
        TaskState.objects.create(uuid="c1", name="x.task", state="SUCCESS", updated_at=now)
        TaskState.objects.create(uuid="c2", name="x.task", state="FAILURE", updated_at=now)

        url = reverse("admin:django_celeryx_dashboard_changelist")
        response = admin_client.get(url)
        content = response.content.decode()
        assert "<svg" in content

    def test_dashboard_requires_auth(self, db):
        client = Client()
        url = reverse("admin:django_celeryx_dashboard_changelist")
        response = client.get(url)
        assert response.status_code == 302


@pytest.mark.django_db
class TestNaturalTime:
    """Tests for the NATURAL_TIME setting."""

    @override_settings(CELERYX={"EVENT_LISTENER_AUTOSTART": False, "DATABASE": "default", "NATURAL_TIME": True})
    def test_natural_time_shows_relative(self, admin_client):
        from django_celeryx.settings import celeryx_settings

        celeryx_settings.reload()
        try:
            now = time.time()
            TaskState.objects.create(uuid="nt1", name="nat.task", state="SUCCESS", received=now - 120, updated_at=now)
            url = reverse("admin:django_celeryx_task_changelist")
            response = admin_client.get(url)
            content = response.content.decode()
            assert "ago" in content
        finally:
            celeryx_settings.reload()

    def test_absolute_time_by_default(self, admin_client):
        now = time.time()
        TaskState.objects.create(uuid="nt2", name="abs.task", state="SUCCESS", received=now, updated_at=now)
        url = reverse("admin:django_celeryx_task_changelist")
        response = admin_client.get(url)
        content = response.content.decode()
        assert "ago" not in content or "Monitoring since" in content.split("ago")[0]
