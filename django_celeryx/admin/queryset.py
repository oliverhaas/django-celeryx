"""QuerySet-like objects and admin mixins for task, worker, and queue list views.

All data reads come from the database (TaskEvent, WorkerEvent models).
The database is the single source of truth — there is no separate in-memory store.
"""

from __future__ import annotations

import datetime
import logging
from typing import TYPE_CHECKING, Any, ClassVar

from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from django_celeryx.admin.helpers import get_celery_app
from django_celeryx.admin.models import Queue, RegisteredTask, Task, Worker
from django_celeryx.types import TASK_STATE_COLORS, WORKER_STATUS_COLORS, TaskState, WorkerStatus

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from collections.abc import Iterator

    from django.http import HttpRequest


def _get_db() -> str:
    from django_celeryx.settings import get_db_alias

    return get_db_alias()


class _FakeQuery:
    """Minimal query-like object for ChangeList compatibility."""

    select_related = False
    order_by: tuple[str, ...] = ()


# ======================================================================
# Task QuerySet + Mixin
# ======================================================================


def _tasks_from_db() -> list[Task]:
    """Load tasks from the database."""
    try:
        from django_celeryx.db_models import TaskEvent

        db = _get_db()
        tasks = []
        for te in TaskEvent.objects.using(db).order_by("-updated_at")[:1000]:
            task = Task()
            task.uuid = te.uuid
            task.name = te.name
            task.state = te.state
            task.worker = te.worker
            task.args = te.args
            task.kwargs = te.kwargs
            task.result = te.result
            task.exception = te.exception
            task.traceback = te.traceback
            task.received = te.received
            task.started = te.started
            task.runtime = te.runtime
            task.eta = te.eta
            task.expires = te.expires
            task.exchange = te.exchange
            task.routing_key = te.routing_key
            task.retries = te.retries
            task.parent_id = te.parent_id
            task.root_id = te.root_id
            tasks.append(task)
        return tasks
    except Exception:
        logger.debug("Failed to load tasks from DB", exc_info=True)
        return []


class TaskQuerySet:
    """QuerySet-like object backed by TaskEvent database table."""

    model = Task
    ordered = True
    db = "default"

    def __init__(self, data: list[Task] | None = None) -> None:
        if data is None:
            self._data = _tasks_from_db()
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
    title = _("state")
    parameter_name = "state"

    def lookups(self, request: HttpRequest, model_admin: admin.ModelAdmin) -> list[tuple[str, str]]:
        return [(s.value, s.value) for s in TaskState]

    def queryset(self, request: HttpRequest, queryset: TaskQuerySet) -> TaskQuerySet:  # type: ignore[override]
        value = self.value()
        if value:
            return TaskQuerySet([t for t in queryset if t.state == value])
        return queryset


class TaskNameFilter(admin.SimpleListFilter):
    title = _("task name")
    parameter_name = "task_name"

    def lookups(self, request: HttpRequest, model_admin: admin.ModelAdmin) -> list[tuple[str, str]]:
        try:
            from django_celeryx.db_models import TaskEvent

            db = _get_db()
            names = sorted(TaskEvent.objects.using(db).exclude(name="").values_list("name", flat=True).distinct())
            return [(n, n) for n in names]
        except Exception:
            return []

    def queryset(self, request: HttpRequest, queryset: TaskQuerySet) -> TaskQuerySet:  # type: ignore[override]
        value = self.value()
        if value:
            return TaskQuerySet([t for t in queryset if t.name == value])
        return queryset


class TaskWorkerFilter(admin.SimpleListFilter):
    title = _("worker")
    parameter_name = "task_worker"

    def lookups(self, request: HttpRequest, model_admin: admin.ModelAdmin) -> list[tuple[str, str]]:
        try:
            from django_celeryx.db_models import WorkerEvent

            db = _get_db()
            hostnames = sorted(WorkerEvent.objects.using(db).values_list("hostname", flat=True))
            return [(h, h) for h in hostnames]
        except Exception:
            return []

    def queryset(self, request: HttpRequest, queryset: TaskQuerySet) -> TaskQuerySet:  # type: ignore[override]
        value = self.value()
        if value:
            return TaskQuerySet([t for t in queryset if t.worker == value])
        return queryset


_TASK_COLUMN_MAP: dict[str, str] = {
    "name": "name",
    "uuid": "uuid_short",
    "state": "state_display",
    "worker": "worker",
    "received": "received_display",
    "started": "started_display",
    "runtime": "runtime_display",
    "args": "args",
    "kwargs": "kwargs",
    "result": "result",
    "exchange": "exchange",
    "routing_key": "routing_key",
    "retries": "retries",
    "exception": "exception",
    "eta": "eta",
    "expires": "expires",
}


class TaskAdminMixin:
    list_display: ClassVar[Any] = [
        "name",
        "uuid_short",
        "state_display",
        "worker",
        "received_display",
        "runtime_display",
    ]
    list_display_links: ClassVar[Any] = ["name"]
    list_filter: ClassVar[Any] = [TaskStateFilter, TaskNameFilter, TaskWorkerFilter]
    search_fields: ClassVar[Any] = ["name", "uuid"]
    ordering: ClassVar[Any] = ["-received"]
    list_per_page: ClassVar[int] = 50

    def get_list_display(self, request: HttpRequest) -> list[str]:
        from django_celeryx.settings import celeryx_settings

        columns = [_TASK_COLUMN_MAP[c] for c in celeryx_settings.TASK_COLUMNS if c in _TASK_COLUMN_MAP]
        return columns or list(self.list_display)

    def get_queryset(self, request: HttpRequest) -> TaskQuerySet:
        return TaskQuerySet()

    def get_search_results(
        self, request: HttpRequest, queryset: TaskQuerySet, search_term: str
    ) -> tuple[TaskQuerySet, bool]:
        if not search_term:
            return queryset, False
        term = search_term.lower()
        filtered = [
            t
            for t in queryset
            if term in (t.name or "").lower()
            or term in t.uuid.lower()
            or term in t.state.lower()
            or term in (t.worker or "").lower()
            or term in (t.args or "").lower()
            or term in (t.kwargs or "").lower()
            or term in (t.result or "").lower()
        ]
        return TaskQuerySet(filtered), False

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_delete_permission(self, request: HttpRequest, obj: Task | None = None) -> bool:
        return False

    @admin.display(description=_("UUID"))
    def uuid_short(self, obj: Task) -> str:
        return format_html('<code title="{}">{}</code>', obj.uuid, obj.uuid[:8])

    @admin.display(description=_("State"))
    def state_display(self, obj: Task) -> str:
        style = TASK_STATE_COLORS.get(obj.state, "background:#f3f4f6;color:#374151;")
        return format_html(
            '<span style="{}padding:2px 8px;border-radius:4px;font-size:11px;font-weight:600;text-transform:uppercase">{}</span>',
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

    @admin.display(description=_("Started"))
    def started_display(self, obj: Task) -> str:
        if obj.started:
            try:
                dt = datetime.datetime.fromtimestamp(float(obj.started), tz=datetime.UTC)
                return format_html("<code>{}</code>", dt.strftime("%H:%M:%S"))
            except (ValueError, TypeError, OSError):
                return format_html("<code>{}</code>", obj.started)
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


def _workers_from_db() -> list[Worker]:
    try:
        from django_celeryx.db_models import WorkerEvent

        db = _get_db()
        workers = []
        for we in WorkerEvent.objects.using(db).all():
            worker = Worker()
            worker.hostname = we.hostname
            worker.status = we.status
            worker.active = we.active
            worker.freq = we.freq
            worker.sw_ident = we.sw_ident
            worker.sw_ver = we.sw_ver
            worker.sw_sys = we.sw_sys
            worker.last_heartbeat = we.last_heartbeat
            if we.loadavg:
                worker.loadavg = ", ".join(f"{x:.2f}" for x in we.loadavg)
            workers.append(worker)
        return workers
    except Exception:
        logger.debug("Failed to load workers from DB", exc_info=True)
        return []


def _enrich_workers(workers: list[Worker]) -> None:
    if not workers:
        return

    # Count task states per worker from DB
    try:
        from django.db.models import Count, Q

        from django_celeryx.db_models import TaskEvent

        db = _get_db()
        by_hostname = {w.hostname: w for w in workers}
        for row in (
            TaskEvent.objects.using(db)
            .values("worker")
            .annotate(
                succeeded=Count("id", filter=Q(state="SUCCESS")),
                failed=Count("id", filter=Q(state="FAILURE")),
                retried=Count("id", filter=Q(state="RETRY")),
            )
        ):
            worker = by_hostname.get(row["worker"])
            if worker:
                worker.succeeded = row["succeeded"]
                worker.failed = row["failed"]
                worker.retried = row["retried"]
    except Exception:
        logger.debug("Failed to count task states", exc_info=True)

    # Enrich with inspect() data
    try:
        from django_celeryx.settings import celeryx_settings

        by_hostname = {w.hostname: w for w in workers}
        stats = get_celery_app().control.inspect(timeout=celeryx_settings.INSPECT_TIMEOUT).stats() or {}
        for hostname, data in stats.items():
            worker = by_hostname.get(hostname)
            if not worker:
                continue
            pool_info = data.get("pool", {})
            impl = pool_info.get("implementation", "")
            if impl:
                worker.pool = impl.rsplit(":", 1)[-1] if ":" in impl else impl
            worker.concurrency = pool_info.get("max-concurrency")
            total = data.get("total", {})
            if total:
                worker.processed = sum(total.values())
            worker.pid = data.get("pid")
            worker.uptime = data.get("uptime")
            worker.prefetch_count = data.get("prefetch_count")
    except Exception:
        logger.debug("Failed to enrich workers from inspect", exc_info=True)


class WorkerQuerySet:
    model = Worker
    ordered = True
    db = "default"

    def __init__(self, data: list[Worker] | None = None, *, enriched: bool = False) -> None:
        if data is None:
            self._data = _workers_from_db()
            if not enriched:
                _enrich_workers(self._data)
        else:
            self._data = list(data)
        self.query = _FakeQuery()

    def _clone(self) -> WorkerQuerySet:
        return WorkerQuerySet(self._data, enriched=True)

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
            return WorkerQuerySet(self._data[key], enriched=True)
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
            if bare in ("hostname", "pk", "status", "active", "processed", "concurrency"):
                clone._data.sort(key=lambda w: str(getattr(w, bare, "") or ""), reverse=field.startswith("-"))
                break
        return clone

    def select_related(self, *args: Any) -> WorkerQuerySet:
        return self._clone()

    def distinct(self) -> WorkerQuerySet:
        return self._clone()

    def alias(self, **kwargs: Any) -> WorkerQuerySet:
        return self._clone()


class WorkerStatusFilter(admin.SimpleListFilter):
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
    list_display: ClassVar[Any] = [
        "hostname",
        "status_display",
        "active_display",
        "processed_display",
        "succeeded_display",
        "failed_display",
        "retried_display",
        "loadavg_display",
    ]
    list_display_links: ClassVar[Any] = ["hostname"]
    list_filter: ClassVar[Any] = [WorkerStatusFilter]
    search_fields: ClassVar[Any] = ["hostname"]
    ordering: ClassVar[Any] = ["hostname"]
    list_per_page: ClassVar[int] = 100

    def changelist_view(self, request: HttpRequest, extra_context: dict[str, Any] | None = None) -> Any:
        extra_context = extra_context or {}
        try:
            from django.db.models import Count, Q

            from django_celeryx.db_models import TaskEvent

            db = _get_db()
            extra_context.update(
                TaskEvent.objects.using(db).aggregate(
                    total_active=Count("id", filter=Q(state="STARTED")),
                    total_processed=Count("id"),
                    total_succeeded=Count("id", filter=Q(state="SUCCESS")),
                    total_failed=Count("id", filter=Q(state="FAILURE")),
                    total_retried=Count("id", filter=Q(state="RETRY")),
                )
            )
        except Exception:
            extra_context.update(
                {"total_active": 0, "total_processed": 0, "total_succeeded": 0, "total_failed": 0, "total_retried": 0}
            )
        return super().changelist_view(request, extra_context)  # type: ignore[misc]

    def get_queryset(self, request: HttpRequest) -> WorkerQuerySet:
        return WorkerQuerySet()

    def get_search_results(
        self, request: HttpRequest, queryset: WorkerQuerySet, search_term: str
    ) -> tuple[WorkerQuerySet, bool]:
        if not search_term:
            return queryset, False
        term = search_term.lower()
        return WorkerQuerySet([w for w in queryset if term in w.hostname.lower()], enriched=True), False

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_delete_permission(self, request: HttpRequest, obj: Worker | None = None) -> bool:
        return False

    @admin.display(description=_("Status"))
    def status_display(self, obj: Worker) -> str:
        style = WORKER_STATUS_COLORS.get(obj.status, "background:#f3f4f6;color:#374151;")
        return format_html(
            '<span style="{}padding:2px 8px;border-radius:4px;font-size:11px;font-weight:600;text-transform:uppercase">{}</span>',
            style,
            obj.status,
        )

    @admin.display(description=_("Active"))
    def active_display(self, obj: Worker) -> str:
        return format_html("<code>{}</code>", obj.active)

    @admin.display(description=_("Processed"))
    def processed_display(self, obj: Worker) -> str:
        return format_html("<code>{}</code>", obj.processed) if obj.processed is not None else "-"

    @admin.display(description=_("Succeeded"))
    def succeeded_display(self, obj: Worker) -> str:
        return format_html("<code>{}</code>", obj.succeeded or 0)

    @admin.display(description=_("Failed"))
    def failed_display(self, obj: Worker) -> str:
        return format_html("<code>{}</code>", obj.failed or 0)

    @admin.display(description=_("Retried"))
    def retried_display(self, obj: Worker) -> str:
        return format_html("<code>{}</code>", obj.retried or 0)

    @admin.display(description=_("Load Average"))
    def loadavg_display(self, obj: Worker) -> str:
        return format_html("<code>{}</code>", obj.loadavg) if obj.loadavg else "-"


# ======================================================================
# Queue QuerySet + Mixin
# ======================================================================


def _fetch_queues() -> list[Queue]:
    try:
        from django_celeryx.settings import celeryx_settings

        all_queues = get_celery_app().control.inspect(timeout=celeryx_settings.INSPECT_TIMEOUT).active_queues() or {}
        queue_map: dict[str, Queue] = {}
        for queues in all_queues.values():
            for q_data in queues:
                name = q_data.get("name", "")
                if name not in queue_map:
                    queue = Queue()
                    queue.name = name
                    exchange = q_data.get("exchange", {})
                    queue.exchange = exchange.get("name", "") if isinstance(exchange, dict) else str(exchange)
                    queue.routing_key = q_data.get("routing_key", "")
                    queue.consumers = 0
                    queue_map[name] = queue
                queue_map[name].consumers += 1
        return sorted(queue_map.values(), key=lambda q: q.name)
    except Exception:
        logger.debug("Failed to fetch queues", exc_info=True)
        return []


class QueueQuerySet:
    model = Queue
    ordered = True
    db = "default"

    def __init__(self, data: list[Queue] | None = None) -> None:
        self._data = list(data) if data is not None else _fetch_queues()
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
            if bare in ("name", "pk", "consumers"):
                clone._data.sort(key=lambda q: str(getattr(q, bare, "") or ""), reverse=field.startswith("-"))
                break
        return clone

    def select_related(self, *args: Any) -> QueueQuerySet:
        return self._clone()

    def distinct(self) -> QueueQuerySet:
        return self._clone()

    def alias(self, **kwargs: Any) -> QueueQuerySet:
        return self._clone()


class QueueAdminMixin:
    list_display: ClassVar[Any] = ["name", "exchange_display", "routing_key_display", "consumers_display"]
    list_display_links: ClassVar[Any] = None
    search_fields: ClassVar[Any] = ["name"]
    ordering: ClassVar[Any] = ["name"]
    list_per_page: ClassVar[int] = 100

    def get_queryset(self, request: HttpRequest) -> QueueQuerySet:
        return QueueQuerySet()

    def get_search_results(
        self, request: HttpRequest, queryset: QueueQuerySet, search_term: str
    ) -> tuple[QueueQuerySet, bool]:
        if not search_term:
            return queryset, False
        return QueueQuerySet([q for q in queryset if search_term.lower() in q.name.lower()]), False

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_delete_permission(self, request: HttpRequest, obj: Queue | None = None) -> bool:
        return False

    @admin.display(description=_("Exchange"))
    def exchange_display(self, obj: Queue) -> str:
        return format_html("<code>{}</code>", obj.exchange) if obj.exchange else "-"

    @admin.display(description=_("Routing Key"))
    def routing_key_display(self, obj: Queue) -> str:
        return format_html("<code>{}</code>", obj.routing_key) if obj.routing_key else "-"

    @admin.display(description=_("Consumers"))
    def consumers_display(self, obj: Queue) -> str:
        return format_html("<code>{}</code>", obj.consumers)


# ======================================================================
# RegisteredTask QuerySet + Mixin
# ======================================================================


def _fetch_registered_tasks() -> list[RegisteredTask]:
    try:
        from django_celeryx.settings import celeryx_settings

        app = get_celery_app()
        all_registered = app.control.inspect(timeout=celeryx_settings.INSPECT_TIMEOUT).registered() or {}
        names: set[str] = set()
        for worker_tasks in all_registered.values():
            names.update(worker_tasks)
        names.update(app.tasks)
        tasks = []
        for name in sorted(names):
            if name.startswith("celery."):
                continue
            task = RegisteredTask()
            task.name = name
            tasks.append(task)
        return tasks
    except Exception:
        logger.debug("Failed to fetch registered tasks", exc_info=True)
        return []


class RegisteredTaskQuerySet:
    model = RegisteredTask
    ordered = True
    db = "default"

    def __init__(self, data: list[RegisteredTask] | None = None) -> None:
        self._data = list(data) if data is not None else _fetch_registered_tasks()
        self.query = _FakeQuery()

    def _clone(self) -> RegisteredTaskQuerySet:
        return RegisteredTaskQuerySet(self._data)

    def count(self) -> int:
        return len(self._data)

    def __len__(self) -> int:
        return len(self._data)

    def __iter__(self) -> Iterator[RegisteredTask]:
        return iter(self._data)

    def __bool__(self) -> bool:
        return bool(self._data)

    def __getitem__(self, key: int | slice) -> RegisteredTaskQuerySet | RegisteredTask:
        if isinstance(key, slice):
            return RegisteredTaskQuerySet(self._data[key])
        return self._data[key]

    def filter(self, *args: Any, **kwargs: Any) -> RegisteredTaskQuerySet:
        clone = self._clone()
        if "pk__in" in kwargs:
            names = set(kwargs["pk__in"])
            clone._data = [t for t in clone._data if t.pk in names]
        return clone

    def order_by(self, *fields: str) -> RegisteredTaskQuerySet:
        return self._clone()

    def select_related(self, *args: Any) -> RegisteredTaskQuerySet:
        return self._clone()

    def distinct(self) -> RegisteredTaskQuerySet:
        return self._clone()

    def alias(self, **kwargs: Any) -> RegisteredTaskQuerySet:
        return self._clone()


class RegisteredTaskAdminMixin:
    list_display: ClassVar[Any] = ["name", "tasks_link"]
    list_display_links: ClassVar[Any] = ["name"]
    search_fields: ClassVar[Any] = ["name"]
    ordering: ClassVar[Any] = ["name"]
    list_per_page: ClassVar[int] = 200

    def get_queryset(self, request: HttpRequest) -> RegisteredTaskQuerySet:
        return RegisteredTaskQuerySet()

    def get_search_results(
        self, request: HttpRequest, queryset: RegisteredTaskQuerySet, search_term: str
    ) -> tuple[RegisteredTaskQuerySet, bool]:
        if not search_term:
            return queryset, False
        return RegisteredTaskQuerySet([t for t in queryset if search_term.lower() in t.name.lower()]), False

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_delete_permission(self, request: HttpRequest, obj: RegisteredTask | None = None) -> bool:
        return False

    def has_change_permission(self, request: HttpRequest, obj: RegisteredTask | None = None) -> bool:
        return False

    @admin.display(description=_("Tasks"))
    def tasks_link(self, obj: RegisteredTask) -> str:
        from django.urls import reverse

        url = reverse("admin:django_celeryx_task_changelist") + f"?q={obj.name}"
        return format_html('<a href="{}">View Tasks &rarr;</a>', url)
