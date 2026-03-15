"""QuerySet-like objects and admin mixins for task, worker, and queue list views.

Provides fake queryset objects that satisfy Django's ChangeList and Paginator
interfaces, backed by in-memory state. Same pattern as django-cachex.
"""

from __future__ import annotations

import datetime
from typing import TYPE_CHECKING, Any, ClassVar

from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from django_celeryx.admin.models import Queue, Task, Worker
from django_celeryx.state.tasks import task_store
from django_celeryx.state.workers import worker_store
from django_celeryx.types import TASK_STATE_COLORS, WORKER_STATUS_COLORS, TaskState, WorkerStatus

if TYPE_CHECKING:
    from collections.abc import Iterator

    from django.http import HttpRequest


class _FakeQuery:
    """Minimal query-like object for ChangeList compatibility."""

    select_related = False
    order_by: tuple[str, ...] = ()


# ======================================================================
# Task QuerySet + Mixin
# ======================================================================


class TaskQuerySet:
    """In-memory queryset-like object backed by TaskStore."""

    model = Task
    ordered = True
    db = "default"

    def __init__(self, data: list[Task] | None = None) -> None:
        if data is None:
            self._data = [Task.from_task_info(t) for t in reversed(task_store.all())]
        else:
            self._data = list(data)
        self.query = _FakeQuery()

    def _clone(self) -> TaskQuerySet:
        return TaskQuerySet(self._data)

    def count(self) -> int:
        return len(self._data)

    def __len__(self) -> int:
        return len(self._data)

    def __iter__(self) -> Iterator[Task]:
        return iter(self._data)

    def __bool__(self) -> bool:
        return bool(self._data)

    def __getitem__(self, key: int | slice) -> TaskQuerySet | Task:
        if isinstance(key, slice):
            return TaskQuerySet(self._data[key])
        return self._data[key]

    def filter(self, *args: Any, **kwargs: Any) -> TaskQuerySet:
        clone = self._clone()
        if "pk__in" in kwargs:
            uuids = set(kwargs["pk__in"])
            clone._data = [t for t in clone._data if t.pk in uuids]
        return clone

    def order_by(self, *fields: str) -> TaskQuerySet:
        clone = self._clone()
        for field in fields:
            bare = field.lstrip("-")
            reverse = field.startswith("-")
            if bare in ("uuid", "pk", "name", "state", "worker", "received", "started", "runtime"):
                clone._data.sort(key=lambda t: str(getattr(t, bare, "") or ""), reverse=reverse)
                break
        return clone

    def select_related(self, *args: Any) -> TaskQuerySet:
        return self._clone()

    def distinct(self) -> TaskQuerySet:
        return self._clone()

    def alias(self, **kwargs: Any) -> TaskQuerySet:
        return self._clone()


class TaskStateFilter(admin.SimpleListFilter):
    """Filter tasks by state."""

    title = _("state")
    parameter_name = "state"

    def lookups(self, request: HttpRequest, model_admin: admin.ModelAdmin) -> list[tuple[str, str]]:
        return [(s.value, s.value) for s in TaskState]

    def queryset(self, request: HttpRequest, queryset: TaskQuerySet) -> TaskQuerySet:  # type: ignore[override]
        value = self.value()
        if value:
            return TaskQuerySet([t for t in queryset if t.state == value])
        return queryset


class TaskAdminMixin:
    """Shared task list admin behaviour for default and unfold themes."""

    list_display: ClassVar[Any] = [
        "name",
        "uuid_short",
        "state_display",
        "worker",
        "received_display",
        "runtime_display",
    ]
    list_display_links: ClassVar[Any] = ["name"]
    list_filter: ClassVar[Any] = [TaskStateFilter]
    search_fields: ClassVar[Any] = ["name", "uuid"]
    ordering: ClassVar[Any] = ["-received"]
    list_per_page: ClassVar[int] = 50

    def get_queryset(self, request: HttpRequest) -> TaskQuerySet:
        return TaskQuerySet()

    def get_search_results(
        self,
        request: HttpRequest,
        queryset: TaskQuerySet,
        search_term: str,
    ) -> tuple[TaskQuerySet, bool]:
        if not search_term:
            return queryset, False
        term = search_term.lower()

        # Support structured search: state:FAILURE, name:task_name, etc.
        if ":" in term:
            prefix, value = term.split(":", 1)
            if prefix in ("state", "name", "worker", "uuid", "args", "kwargs", "result"):
                filtered = [t for t in queryset if value in str(getattr(t, prefix, "")).lower()]
                return TaskQuerySet(filtered), False

        # Free text search across key fields
        filtered = [
            t
            for t in queryset
            if term in (t.name or "").lower()
            or term in t.uuid.lower()
            or term in t.state.lower()
            or term in (t.worker or "").lower()
        ]
        return TaskQuerySet(filtered), False

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_delete_permission(self, request: HttpRequest, obj: Task | None = None) -> bool:
        return False

    # Display columns

    @admin.display(description=_("UUID"))
    def uuid_short(self, obj: Task) -> str:
        return format_html('<code title="{}">{}</code>', obj.uuid, obj.uuid[:8])

    @admin.display(description=_("State"))
    def state_display(self, obj: Task) -> str:
        style = TASK_STATE_COLORS.get(obj.state, "background:#f3f4f6;color:#374151;")
        return format_html(
            '<span style="{}padding:2px 8px;border-radius:4px;'
            'font-size:11px;font-weight:600;text-transform:uppercase">{}</span>',
            style,
            obj.state,
        )

    @admin.display(description=_("Received"))
    def received_display(self, obj: Task) -> str:
        if obj.received:
            try:
                dt = datetime.datetime.fromtimestamp(float(obj.received), tz=datetime.UTC)
                return format_html("<code>{}</code>", dt.strftime("%H:%M:%S"))
            except (ValueError, TypeError, OSError):
                return format_html("<code>{}</code>", obj.received)
        return "-"

    @admin.display(description=_("Runtime"))
    def runtime_display(self, obj: Task) -> str:
        if obj.runtime is not None:
            try:
                return format_html("<code>{}s</code>", f"{float(obj.runtime):.3f}")
            except (ValueError, TypeError):
                return format_html("<code>{}</code>", obj.runtime)
        return "-"


# ======================================================================
# Worker QuerySet + Mixin
# ======================================================================


class WorkerQuerySet:
    """In-memory queryset-like object backed by WorkerStore."""

    model = Worker
    ordered = True
    db = "default"

    def __init__(self, data: list[Worker] | None = None) -> None:
        if data is None:
            self._data = [Worker.from_worker_info(w) for w in worker_store.all()]
        else:
            self._data = list(data)
        self.query = _FakeQuery()

    def _clone(self) -> WorkerQuerySet:
        return WorkerQuerySet(self._data)

    def count(self) -> int:
        return len(self._data)

    def __len__(self) -> int:
        return len(self._data)

    def __iter__(self) -> Iterator[Worker]:
        return iter(self._data)

    def __bool__(self) -> bool:
        return bool(self._data)

    def __getitem__(self, key: int | slice) -> WorkerQuerySet | Worker:
        if isinstance(key, slice):
            return WorkerQuerySet(self._data[key])
        return self._data[key]

    def filter(self, *args: Any, **kwargs: Any) -> WorkerQuerySet:
        clone = self._clone()
        if "pk__in" in kwargs:
            hostnames = set(kwargs["pk__in"])
            clone._data = [w for w in clone._data if w.pk in hostnames]
        return clone

    def order_by(self, *fields: str) -> WorkerQuerySet:
        clone = self._clone()
        for field in fields:
            bare = field.lstrip("-")
            if bare in ("hostname", "pk", "status"):
                clone._data.sort(key=lambda w: getattr(w, bare, ""), reverse=field.startswith("-"))
                break
        return clone

    def select_related(self, *args: Any) -> WorkerQuerySet:
        return self._clone()

    def distinct(self) -> WorkerQuerySet:
        return self._clone()

    def alias(self, **kwargs: Any) -> WorkerQuerySet:
        return self._clone()


class WorkerStatusFilter(admin.SimpleListFilter):
    """Filter workers by status."""

    title = _("status")
    parameter_name = "status"

    def lookups(self, request: HttpRequest, model_admin: admin.ModelAdmin) -> list[tuple[str, str]]:
        return [(s.value, s.value) for s in WorkerStatus]

    def queryset(self, request: HttpRequest, queryset: WorkerQuerySet) -> WorkerQuerySet:  # type: ignore[override]
        value = self.value()
        if value:
            return WorkerQuerySet([w for w in queryset if w.status == value])
        return queryset


class WorkerAdminMixin:
    """Shared worker list admin behaviour for default and unfold themes."""

    list_display: ClassVar[Any] = [
        "hostname",
        "status_display",
        "active_display",
        "sw_display",
    ]
    list_display_links: ClassVar[Any] = ["hostname"]
    list_filter: ClassVar[Any] = [WorkerStatusFilter]
    search_fields: ClassVar[Any] = ["hostname"]
    ordering: ClassVar[Any] = ["hostname"]
    list_per_page: ClassVar[int] = 100

    def get_queryset(self, request: HttpRequest) -> WorkerQuerySet:
        return WorkerQuerySet()

    def get_search_results(
        self,
        request: HttpRequest,
        queryset: WorkerQuerySet,
        search_term: str,
    ) -> tuple[WorkerQuerySet, bool]:
        if not search_term:
            return queryset, False
        term = search_term.lower()
        filtered = [w for w in queryset if term in w.hostname.lower()]
        return WorkerQuerySet(filtered), False

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_delete_permission(self, request: HttpRequest, obj: Worker | None = None) -> bool:
        return False

    # Display columns

    @admin.display(description=_("Status"))
    def status_display(self, obj: Worker) -> str:
        style = WORKER_STATUS_COLORS.get(obj.status, "background:#f3f4f6;color:#374151;")
        return format_html(
            '<span style="{}padding:2px 8px;border-radius:4px;'
            'font-size:11px;font-weight:600;text-transform:uppercase">{}</span>',
            style,
            obj.status,
        )

    @admin.display(description=_("Active Tasks"))
    def active_display(self, obj: Worker) -> str:
        return format_html("<code>{}</code>", obj.active)

    @admin.display(description=_("Software"))
    def sw_display(self, obj: Worker) -> str:
        if obj.sw_ident and obj.sw_ver:
            return format_html("<code>{} {}</code>", obj.sw_ident, obj.sw_ver)
        return "-"


# ======================================================================
# Queue QuerySet + Mixin
# ======================================================================


class QueueQuerySet:
    """In-memory queryset-like object for queues."""

    model = Queue
    ordered = True
    db = "default"

    def __init__(self, data: list[Queue] | None = None) -> None:
        self._data = list(data) if data is not None else []
        self.query = _FakeQuery()

    def _clone(self) -> QueueQuerySet:
        return QueueQuerySet(self._data)

    def count(self) -> int:
        return len(self._data)

    def __len__(self) -> int:
        return len(self._data)

    def __iter__(self) -> Iterator[Queue]:
        return iter(self._data)

    def __bool__(self) -> bool:
        return bool(self._data)

    def __getitem__(self, key: int | slice) -> QueueQuerySet | Queue:
        if isinstance(key, slice):
            return QueueQuerySet(self._data[key])
        return self._data[key]

    def filter(self, *args: Any, **kwargs: Any) -> QueueQuerySet:
        clone = self._clone()
        if "pk__in" in kwargs:
            names = set(kwargs["pk__in"])
            clone._data = [q for q in clone._data if q.pk in names]
        return clone

    def order_by(self, *fields: str) -> QueueQuerySet:
        clone = self._clone()
        for field in fields:
            bare = field.lstrip("-")
            if bare in ("name", "pk", "messages"):
                clone._data.sort(key=lambda q: getattr(q, bare, ""), reverse=field.startswith("-"))
                break
        return clone

    def select_related(self, *args: Any) -> QueueQuerySet:
        return self._clone()

    def distinct(self) -> QueueQuerySet:
        return self._clone()

    def alias(self, **kwargs: Any) -> QueueQuerySet:
        return self._clone()


class QueueAdminMixin:
    """Shared queue list admin behaviour for default and unfold themes."""

    list_display: ClassVar[Any] = [
        "name",
        "messages_display",
        "consumers_display",
    ]
    list_display_links: ClassVar[Any] = ["name"]
    search_fields: ClassVar[Any] = ["name"]
    ordering: ClassVar[Any] = ["name"]
    list_per_page: ClassVar[int] = 100

    def get_queryset(self, request: HttpRequest) -> QueueQuerySet:
        # TODO: Populate from broker stats
        return QueueQuerySet()

    def get_search_results(
        self,
        request: HttpRequest,
        queryset: QueueQuerySet,
        search_term: str,
    ) -> tuple[QueueQuerySet, bool]:
        if not search_term:
            return queryset, False
        term = search_term.lower()
        filtered = [q for q in queryset if term in q.name.lower()]
        return QueueQuerySet(filtered), False

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_delete_permission(self, request: HttpRequest, obj: Queue | None = None) -> bool:
        return False

    # Display columns

    @admin.display(description=_("Messages"))
    def messages_display(self, obj: Queue) -> str:
        return format_html("<code>{}</code>", obj.messages)

    @admin.display(description=_("Consumers"))
    def consumers_display(self, obj: Queue) -> str:
        return format_html("<code>{}</code>", obj.consumers)
