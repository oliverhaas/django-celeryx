"""Django admin classes for Celery monitoring and management."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from django.contrib import admin, messages
from django.contrib.admin.utils import unquote
from django.core.exceptions import PermissionDenied
from django.urls import path
from django.utils.translation import gettext_lazy as _

from .models import Dashboard, Queue, RegisteredTask, Task, Worker
from .queryset import (
    QueueAdminMixin,
    RegisteredTaskAdminMixin,
    TaskAdminMixin,
    WorkerAdminMixin,
)

if TYPE_CHECKING:
    from django.http import HttpRequest, HttpResponse

    _TaskBase = admin.ModelAdmin[Task]
    _WorkerBase = admin.ModelAdmin[Worker]
    _QueueBase = admin.ModelAdmin[Queue]
    _RegisteredTaskBase = admin.ModelAdmin[RegisteredTask]
else:
    _TaskBase = admin.ModelAdmin
    _WorkerBase = admin.ModelAdmin
    _QueueBase = admin.ModelAdmin
    _RegisteredTaskBase = admin.ModelAdmin


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
class TaskAdmin(LiveUpdateMixin, TaskAdminMixin, _TaskBase):  # type: ignore[misc]
    """Admin for Celery tasks."""

    change_list_template = "admin/django_celeryx/task/change_list.html"  # type: ignore[misc]
    actions = ["revoke_selected", "terminate_selected"]  # noqa: RUF012

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_delete_permission(self, request: HttpRequest, obj: Task | None = None) -> bool:
        return False

    def get_urls(self) -> list:
        urls = super().get_urls()
        custom_urls = [
            path(
                "apply/",
                self.admin_site.admin_view(self._apply_task_view),
                name="django_celeryx_task_apply",
            ),
            path(
                "<path:object_id>/change/",
                self.admin_site.admin_view(self.change_view),
                name="django_celeryx_task_change",
            ),
        ]
        return custom_urls + urls

    def _apply_task_view(self, request: HttpRequest) -> HttpResponse:
        from .views.apply_task import apply_task_view

        return apply_task_view(request)

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
class WorkerAdmin(LiveUpdateMixin, WorkerAdminMixin, _WorkerBase):  # type: ignore[misc]
    """Admin for Celery workers."""

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

        from .views.worker_detail import worker_detail_view

        return worker_detail_view(request, unquote(object_id))


@admin.register(Queue)
class QueueAdmin(LiveUpdateMixin, QueueAdminMixin, _QueueBase):  # type: ignore[misc]
    """Admin for Celery queues."""

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_delete_permission(self, request: HttpRequest, obj: Queue | None = None) -> bool:
        return False


@admin.register(RegisteredTask)
class RegisteredTaskAdmin(RegisteredTaskAdminMixin, _RegisteredTaskBase):  # type: ignore[misc]
    """Admin for registered Celery task types."""

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_delete_permission(self, request: HttpRequest, obj: RegisteredTask | None = None) -> bool:
        return False


class DashboardPeriodFilter(admin.SimpleListFilter):
    title = _("time period")
    parameter_name = "period"

    def lookups(self, request: HttpRequest, model_admin: admin.ModelAdmin) -> list[tuple[str, str]]:
        return [("today", _("Today")), ("7d", _("Last 7 days")), ("30d", _("Last 30 days"))]

    def queryset(self, request: HttpRequest, queryset: Any) -> Any:

        deltas = {"today": 1, "7d": 7, "30d": 30}
        if self.value() in deltas:
            import time

            cutoff = time.time() - deltas[self.value()] * 86400
            return queryset.filter(updated_at__gte=cutoff)
        return queryset


class DashboardQueueFilter(admin.SimpleListFilter):
    title = _("queue")
    parameter_name = "queue"

    def lookups(self, request: HttpRequest, model_admin: admin.ModelAdmin) -> list[tuple[str, str]]:
        from django_celeryx.db_models import TaskState
        from django_celeryx.settings import get_db_alias

        try:
            return [
                (q, q)
                for q in sorted(
                    TaskState.objects.using(get_db_alias())
                    .exclude(routing_key="")
                    .values_list("routing_key", flat=True)
                    .distinct()
                )
            ]
        except Exception:
            return []

    def queryset(self, request: HttpRequest, queryset: Any) -> Any:
        if self.value():
            return queryset.filter(routing_key=self.value())
        return queryset


class DashboardWorkerFilter(admin.SimpleListFilter):
    title = _("worker")
    parameter_name = "worker"

    def lookups(self, request: HttpRequest, model_admin: admin.ModelAdmin) -> list[tuple[str, str]]:
        from django_celeryx.db_models import TaskState
        from django_celeryx.settings import get_db_alias

        try:
            return [
                (w, w)
                for w in sorted(
                    TaskState.objects.using(get_db_alias())
                    .exclude(worker="")
                    .values_list("worker", flat=True)
                    .distinct()
                )
            ]
        except Exception:
            return []

    def queryset(self, request: HttpRequest, queryset: Any) -> Any:
        if self.value():
            return queryset.filter(worker=self.value())
        return queryset


if TYPE_CHECKING:
    _DashboardBase = admin.ModelAdmin[Dashboard]
else:
    _DashboardBase = admin.ModelAdmin


@admin.register(Dashboard)
class DashboardAdmin(_DashboardBase):  # type: ignore[misc]
    """Dashboard view using native Django admin filters."""

    change_list_template = "admin/django_celeryx/dashboard/change_list.html"  # type: ignore[misc]
    list_filter = [DashboardPeriodFilter, DashboardQueueFilter, DashboardWorkerFilter]  # noqa: RUF012
    show_facets = admin.ShowFacets.NEVER

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_delete_permission(self, request: HttpRequest, obj: Dashboard | None = None) -> bool:
        return False

    def has_change_permission(self, request: HttpRequest, obj: Dashboard | None = None) -> bool:
        return False

    def get_queryset(self, request: HttpRequest) -> Any:
        from django_celeryx.db_models import TaskState
        from django_celeryx.settings import get_db_alias

        return TaskState.objects.using(get_db_alias()).all()

    def changelist_view(
        self,
        request: HttpRequest,
        extra_context: dict[str, Any] | None = None,
    ) -> HttpResponse:
        extra_context = extra_context or {}

        # Build a filtered queryset by applying our filters to TaskState
        from django_celeryx.db_models import TaskState as _TaskState
        from django_celeryx.settings import get_db_alias

        from .views.dashboard import compute_dashboard_context

        qs = _TaskState.objects.using(get_db_alias()).all()
        for f_cls in self.list_filter:
            f = f_cls(request, request.GET.copy(), _TaskState, self)
            qs = f.queryset(request, qs) or qs

        extra_context.update(compute_dashboard_context(qs))

        return super().changelist_view(request, extra_context)
