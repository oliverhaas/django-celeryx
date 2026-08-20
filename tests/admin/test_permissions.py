"""Tests that control actions require the change permission, not just staff access.

AdminSite.admin_view() only checks is_active and is_staff, so every custom view
has to check model permissions itself.
"""

import time

import pytest
from django.contrib.auth.models import Permission, User
from django.test import Client
from django.urls import reverse

from django_celeryx.db_models import TaskState, WorkerState


@pytest.fixture
def viewer_client(db):
    """A staff user with view-only permissions on tasks and workers."""
    user = User.objects.create_user(
        username="viewer",
        email="viewer@example.com",
        password="password",  # noqa: S106
        is_staff=True,
    )
    perms = Permission.objects.filter(
        content_type__app_label="django_celeryx",
        codename__in=["view_task", "view_worker", "view_queue", "view_registeredtask", "view_dashboard"],
    )
    assert perms.exists()
    user.user_permissions.set(perms)
    client = Client()
    client.force_login(user)
    return client


@pytest.fixture
def controller_client(db):
    """A staff user with view and change permissions on tasks and workers."""
    user = User.objects.create_user(
        username="controller",
        email="controller@example.com",
        password="password",  # noqa: S106
        is_staff=True,
    )
    user.user_permissions.set(
        Permission.objects.filter(
            content_type__app_label="django_celeryx",
            codename__in=[
                "view_task",
                "change_task",
                "view_worker",
                "change_worker",
                "view_queue",
                "view_registeredtask",
                "view_dashboard",
            ],
        ),
    )
    client = Client()
    client.force_login(user)
    return client


@pytest.fixture
def task(db):
    return TaskState.objects.create(uuid="perm-task", name="proj.add", state="STARTED", updated_at=time.time())


@pytest.fixture
def worker(db):
    return WorkerState.objects.create(hostname="perm@host", status="online", updated_at=time.time())


class TestApplyTaskView:
    def test_viewer_is_denied(self, viewer_client):
        response = viewer_client.get(reverse("admin:django_celeryx_task_apply"))
        assert response.status_code == 403

    def test_controller_is_allowed(self, controller_client):
        response = controller_client.get(reverse("admin:django_celeryx_task_apply"))
        assert response.status_code == 200

    def test_viewer_post_is_denied(self, viewer_client):
        response = viewer_client.post(
            reverse("admin:django_celeryx_task_apply"),
            {"task_name": "proj.add", "args": "[]", "kwargs": "{}"},
        )
        assert response.status_code == 403


class TestTaskDetailView:
    def test_viewer_can_read(self, viewer_client, task):
        url = reverse("admin:django_celeryx_task_change", args=[task.uuid])
        response = viewer_client.get(url)
        assert response.status_code == 200
        assert response.context["can_control"] is False

    def test_controller_can_control(self, controller_client, task):
        url = reverse("admin:django_celeryx_task_change", args=[task.uuid])
        response = controller_client.get(url)
        assert response.status_code == 200
        assert response.context["can_control"] is True

    def test_viewer_post_is_denied(self, viewer_client, task):
        url = reverse("admin:django_celeryx_task_change", args=[task.uuid])
        response = viewer_client.post(url, {"action": "revoke"})
        assert response.status_code == 403

    def test_user_without_view_permission_is_denied(self, db, task):
        user = User.objects.create_user(
            username="nobody",
            email="nobody@example.com",
            password="password",  # noqa: S106
            is_staff=True,
        )
        client = Client()
        client.force_login(user)
        url = reverse("admin:django_celeryx_task_change", args=[task.uuid])
        assert client.get(url).status_code == 403


class TestWorkerDetailView:
    def test_viewer_can_read(self, viewer_client, worker):
        url = reverse("admin:django_celeryx_worker_change", args=[worker.hostname])
        response = viewer_client.get(url)
        assert response.status_code == 200
        assert response.context["can_control"] is False

    def test_viewer_does_not_see_control_forms(self, viewer_client, worker):
        url = reverse("admin:django_celeryx_worker_change", args=[worker.hostname])
        content = viewer_client.get(url).content.decode()
        assert "Pool Controls" not in content
        assert "Set Rate Limit" not in content

    def test_controller_sees_control_forms(self, controller_client, worker):
        url = reverse("admin:django_celeryx_worker_change", args=[worker.hostname])
        content = controller_client.get(url).content.decode()
        assert "Pool Controls" in content

    def test_viewer_post_is_denied(self, viewer_client, worker):
        url = reverse("admin:django_celeryx_worker_change", args=[worker.hostname])
        response = viewer_client.post(url, {"action": "pool_grow", "n": "1"})
        assert response.status_code == 403


class TestChangelistLinks:
    def test_viewer_does_not_see_send_task_link(self, viewer_client):
        content = viewer_client.get(reverse("admin:django_celeryx_task_changelist")).content.decode()
        assert "Send Task" not in content

    def test_controller_sees_send_task_link(self, controller_client):
        content = controller_client.get(reverse("admin:django_celeryx_task_changelist")).content.decode()
        assert "Send Task" in content


class TestActionPermissions:
    def test_revoke_action_hidden_from_viewer(self, viewer_client, task):
        content = viewer_client.get(reverse("admin:django_celeryx_task_changelist")).content.decode()
        assert "revoke_selected" not in content

    def test_revoke_action_offered_to_controller(self, controller_client, task):
        content = controller_client.get(reverse("admin:django_celeryx_task_changelist")).content.decode()
        assert "revoke_selected" in content
