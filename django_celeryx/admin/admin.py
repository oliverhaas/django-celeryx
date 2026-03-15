"""Django admin classes for Celery monitoring and management."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from django.contrib import admin
from django.contrib.admin.utils import unquote
from django.core.exceptions import PermissionDenied
from django.urls import path

from .models import Queue, Task, Worker
from .queryset import QueueAdminMixin, TaskAdminMixin, WorkerAdminMixin

if TYPE_CHECKING:
    from django.http import HttpRequest, HttpResponse

    _TaskBase = admin.ModelAdmin[Task]
    _WorkerBase = admin.ModelAdmin[Worker]
    _QueueBase = admin.ModelAdmin[Queue]
else:
    _TaskBase = admin.ModelAdmin
    _WorkerBase = admin.ModelAdmin
    _QueueBase = admin.ModelAdmin


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

        # Build toggle URL: add or remove ?live=on, preserving other params
        params = request.GET.copy()
        if live:
            params.pop("live", None)
        else:
            params["live"] = "on"
        toggle_qs = params.urlencode()
        extra_context["live_toggle_url"] = f"?{toggle_qs}" if toggle_qs else "?"

        # Build the URL htmx will poll (same page with all current params)
        extra_context["live_url"] = request.get_full_path()

        return super().changelist_view(request, extra_context)  # type: ignore[misc]


@admin.register(Task)
class TaskAdmin(LiveUpdateMixin, TaskAdminMixin, _TaskBase):  # type: ignore[misc]
    """Admin for Celery tasks."""

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_delete_permission(self, request: HttpRequest, obj: Task | None = None) -> bool:
        return False

    def get_urls(self) -> list:
        urls = super().get_urls()
        custom_urls = [
            path(
                "<path:object_id>/change/",
                self.admin_site.admin_view(self.change_view),
                name="django_celeryx_task_change",
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

        from .views.task_detail import task_detail_view

        return task_detail_view(request, unquote(object_id))


@admin.register(Worker)
class WorkerAdmin(LiveUpdateMixin, WorkerAdminMixin, _WorkerBase):  # type: ignore[misc]
    """Admin for Celery workers."""

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

        from .views.worker_detail import worker_detail_view

        return worker_detail_view(request, unquote(object_id))


@admin.register(Queue)
class QueueAdmin(LiveUpdateMixin, QueueAdminMixin, _QueueBase):  # type: ignore[misc]
    """Admin for Celery queues."""

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_delete_permission(self, request: HttpRequest, obj: Queue | None = None) -> bool:
        return False
