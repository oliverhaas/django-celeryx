"""In-memory task store (ring buffer)."""

from __future__ import annotations

import threading
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any

from django_celeryx.settings import celeryx_settings
from django_celeryx.types import TaskState


@dataclass
class TaskInfo:
    """In-memory representation of a Celery task."""

    uuid: str
    name: str | None = None
    state: str = TaskState.PENDING
    worker: str | None = None
    args: str | None = None
    kwargs: str | None = None
    result: str | None = None
    exception: str | None = None
    traceback: str | None = None
    received: float | None = None
    started: float | None = None
    succeeded: float | None = None
    failed: float | None = None
    retried: float | None = None
    revoked: float | None = None
    runtime: float | None = None
    eta: str | None = None
    expires: str | None = None
    exchange: str | None = None
    routing_key: str | None = None
    retries: int = 0
    parent_id: str | None = None
    root_id: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)


class TaskStore:
    """Thread-safe in-memory task store with bounded size (ring buffer)."""

    def __init__(self, max_tasks: int | None = None) -> None:
        self._max_tasks = max_tasks or celeryx_settings.MAX_TASKS
        self._tasks: OrderedDict[str, TaskInfo] = OrderedDict()
        self._lock = threading.Lock()

    def update(self, uuid: str, **fields: Any) -> TaskInfo:
        """Update or create a task entry."""
        with self._lock:
            if uuid in self._tasks:
                task = self._tasks[uuid]
                for k, v in fields.items():
                    if hasattr(task, k):
                        setattr(task, k, v)
                # Move to end (most recently updated)
                self._tasks.move_to_end(uuid)
            else:
                task = TaskInfo(uuid=uuid, **{k: v for k, v in fields.items() if hasattr(TaskInfo, k)})
                self._tasks[uuid] = task
                # Evict oldest if at capacity
                while len(self._tasks) > self._max_tasks:
                    self._tasks.popitem(last=False)
            return task

    def get(self, uuid: str) -> TaskInfo | None:
        """Get a task by UUID."""
        with self._lock:
            return self._tasks.get(uuid)

    def all(self) -> list[TaskInfo]:
        """Get all tasks (most recent last)."""
        with self._lock:
            return list(self._tasks.values())

    def filter(self, **criteria: Any) -> list[TaskInfo]:
        """Filter tasks by field values."""
        with self._lock:
            result = list(self._tasks.values())
        for k, v in criteria.items():
            result = [t for t in result if getattr(t, k, None) == v]
        return result

    def count(self) -> int:
        """Get the number of tasks."""
        with self._lock:
            return len(self._tasks)

    def clear(self) -> None:
        """Clear all tasks."""
        with self._lock:
            self._tasks.clear()


# Global task store instance
task_store = TaskStore()
