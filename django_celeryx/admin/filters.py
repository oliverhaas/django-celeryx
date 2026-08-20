"""Changelist filters shared by the standard and unfold dashboards.

They live outside admin.py because importing that module runs its
``@admin.register`` calls, which clash with the unfold registrations.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from django.contrib import admin
from django.utils.translation import gettext_lazy as _

if TYPE_CHECKING:
    from django.http import HttpRequest


class DashboardPeriodFilter(admin.SimpleListFilter):
    title = _("time period")
    parameter_name = "period"

    def lookups(self, request: HttpRequest, model_admin: admin.ModelAdmin) -> list[tuple[str, str]]:
        return [("today", str(_("Today"))), ("7d", str(_("Last 7 days"))), ("30d", str(_("Last 30 days")))]

    def queryset(self, request: HttpRequest, queryset: Any) -> Any:
        deltas = {"today": 1, "7d": 7, "30d": 30}
        value = self.value()
        if value is not None and value in deltas:
            import time

            cutoff = time.time() - deltas[value] * 86400
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
                    .distinct(),
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
                    .distinct(),
                )
            ]
        except Exception:
            return []

    def queryset(self, request: HttpRequest, queryset: Any) -> Any:
        if self.value():
            return queryset.filter(worker=self.value())
        return queryset
