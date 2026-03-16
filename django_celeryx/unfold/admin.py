"""Unfold-themed admin classes for Celery monitoring."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from django.contrib import admin, messages
from django.contrib.admin.utils import unquote
from django.core.exceptions import PermissionDenied
from django.urls import path
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin

from django_celeryx.admin.queryset import (
    QueueAdminMixin,
    RegisteredTaskAdminMixin,
    TaskAdminMixin,
    WorkerAdminMixin,
)

from .models import Queue, RegisteredTask, Task, Worker

if TYPE_CHECKING:
    from django.http import HttpRequest, HttpResponse


class LiveUpdateMixin:
    """Mixin that adds htmx live update toggle to changelist views."""

    change_list_template = "admin/django_celeryx/change_list.html"

    def changelist_view(
        self,
        request: HttpRequest,
        extra_context: dict[str, Any] | None = None,
    ) -> HttpResponse:
        from django_celeryx.settings import celeryx_settings

        extra_context = extra_context or {}

        live = request.GET.get("live") == "on"
        extra_context["live"] = live
        extra_context["refresh_interval"] = celeryx_settings.AUTO_REFRESH_INTERVAL

        params = request.GET.copy()
        if live:
            params.pop("live", None)
        else:
            params["live"] = "on"
        toggle_qs = params.urlencode()
        extra_context["live_toggle_url"] = f"?{toggle_qs}" if toggle_qs else "?"
        extra_context["live_url"] = request.get_full_path()

        return super().changelist_view(request, extra_context)  # type: ignore[misc]


@admin.register(Task)
class TaskAdmin(LiveUpdateMixin, TaskAdminMixin, ModelAdmin):  # type: ignore[misc]
    """Unfold-themed admin for Celery tasks."""

    actions = ["revoke_selected", "terminate_selected"]  # noqa: RUF012

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_delete_permission(self, request: HttpRequest, obj: Task | None = None) -> bool:
        return False

    change_list_template = "admin/django_celeryx/task/change_list.html"  # type: ignore[misc]

    def get_urls(self) -> list:
        urls = super().get_urls()
        custom_urls = [
            path(
                "apply/",
                self.admin_site.admin_view(self._apply_task_view),
                name="django_celeryx_task_apply",
            ),
            path(
                "dashboard/",
                self.admin_site.admin_view(self._dashboard_view),
                name="django_celeryx_dashboard",
            ),
            path(
                "<path:object_id>/change/",
                self.admin_site.admin_view(self.change_view),
                name="django_celeryx_task_change",
            ),
        ]
        return custom_urls + urls

    def _apply_task_view(self, request: HttpRequest) -> HttpResponse:
        from django_celeryx.admin.views.apply_task import apply_task_view

        return apply_task_view(request)

    def _dashboard_view(self, request: HttpRequest) -> HttpResponse:
        from django_celeryx.admin.views.dashboard import dashboard_view

        return dashboard_view(request)

    def change_view(
        self,
        request: HttpRequest,
        object_id: str,
        form_url: str = "",
        extra_context: dict[str, Any] | None = None,
    ) -> HttpResponse:
        if not self.has_view_or_change_permission(request):
            raise PermissionDenied

        from django_celeryx.admin.views.task_detail import task_detail_view

        return task_detail_view(request, unquote(object_id))

    @admin.action(description=_("Revoke selected tasks"))
    def revoke_selected(self, request: HttpRequest, queryset: Any) -> None:
        from django_celeryx.control.tasks import revoke_task

        count = 0
        for task in queryset:
            try:
                revoke_task(task.uuid)
                count += 1
            except Exception as exc:
                messages.error(request, f"Failed to revoke {task.uuid[:8]}: {exc}")
        if count:
            messages.success(request, f"Revoked {count} task(s).")

    @admin.action(description=_("Terminate selected tasks"))
    def terminate_selected(self, request: HttpRequest, queryset: Any) -> None:
        from django_celeryx.control.tasks import revoke_task

        count = 0
        for task in queryset:
            try:
                revoke_task(task.uuid, terminate=True)
                count += 1
            except Exception as exc:
                messages.error(request, f"Failed to terminate {task.uuid[:8]}: {exc}")
        if count:
            messages.success(request, f"Terminated {count} task(s).")


@admin.register(Worker)
class WorkerAdmin(LiveUpdateMixin, WorkerAdminMixin, ModelAdmin):  # type: ignore[misc]
    """Unfold-themed admin for Celery workers."""

    change_list_template = "admin/django_celeryx/worker/change_list.html"  # type: ignore[misc]

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_delete_permission(self, request: HttpRequest, obj: Worker | None = None) -> bool:
        return False

    def get_urls(self) -> list:
        urls = super().get_urls()
        custom_urls = [
            path(
                "<path:object_id>/change/",
                self.admin_site.admin_view(self.change_view),
                name="django_celeryx_worker_change",
            ),
        ]
        return custom_urls + urls

    def change_view(
        self,
        request: HttpRequest,
        object_id: str,
        form_url: str = "",
        extra_context: dict[str, Any] | None = None,
    ) -> HttpResponse:
        if not self.has_view_or_change_permission(request):
            raise PermissionDenied

        from django_celeryx.admin.views.worker_detail import worker_detail_view

        return worker_detail_view(request, unquote(object_id))


@admin.register(Queue)
class QueueAdmin(LiveUpdateMixin, QueueAdminMixin, ModelAdmin):  # type: ignore[misc]
    """Unfold-themed admin for Celery queues."""

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_delete_permission(self, request: HttpRequest, obj: Queue | None = None) -> bool:
        return False


@admin.register(RegisteredTask)
class RegisteredTaskAdmin(RegisteredTaskAdminMixin, ModelAdmin):  # type: ignore[misc]
    """Unfold-themed admin for registered Celery task types."""

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_delete_permission(self, request: HttpRequest, obj: RegisteredTask | None = None) -> bool:
        return False
