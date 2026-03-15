"""Django admin classes for Celery monitoring and management."""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.contrib import admin

from .models import Queue, Task, Worker
from .queryset import QueueAdminMixin, TaskAdminMixin, WorkerAdminMixin

if TYPE_CHECKING:
    from django.http import HttpRequest

    _TaskBase = admin.ModelAdmin[Task]
    _WorkerBase = admin.ModelAdmin[Worker]
    _QueueBase = admin.ModelAdmin[Queue]
else:
    _TaskBase = admin.ModelAdmin
    _WorkerBase = admin.ModelAdmin
    _QueueBase = admin.ModelAdmin


@admin.register(Task)
class TaskAdmin(TaskAdminMixin, _TaskBase):  # type: ignore[misc]
    """Admin for Celery tasks.

    Uses TaskAdminMixin for list_display, filtering, search.
    Driven by TaskQuerySet (in-memory, backed by TaskStore).
    """

    # Tasks are events — add/delete don't apply
    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_delete_permission(self, request: HttpRequest, obj: Task | None = None) -> bool:
        return False


@admin.register(Worker)
class WorkerAdmin(WorkerAdminMixin, _WorkerBase):  # type: ignore[misc]
    """Admin for Celery workers.

    Uses WorkerAdminMixin for list_display, filtering, search.
    Driven by WorkerQuerySet (in-memory, backed by WorkerStore).
    """

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_delete_permission(self, request: HttpRequest, obj: Worker | None = None) -> bool:
        return False


@admin.register(Queue)
class QueueAdmin(QueueAdminMixin, _QueueBase):  # type: ignore[misc]
    """Admin for Celery queues.

    Uses QueueAdminMixin for list_display, filtering, search.
    Driven by QueueQuerySet (in-memory, backed by broker stats).
    """

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_delete_permission(self, request: HttpRequest, obj: Queue | None = None) -> bool:
        return False
