"""In-memory worker store."""

from __future__ import annotations

import threading
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any

from django_celeryx.settings import celeryx_settings
from django_celeryx.types import WorkerStatus


@dataclass
class WorkerInfo:
    """In-memory representation of a Celery worker."""

    hostname: str
    status: str = WorkerStatus.ONLINE
    active: int = 0
    freq: float = 2.0
    loadavg: list[float] = field(default_factory=list)
    sw_ident: str | None = None
    sw_ver: str | None = None
    sw_sys: str | None = None
    last_heartbeat: float | None = None

    # Fields populated via inspect() on demand
    processed: int | None = None
    pool: str | None = None
    concurrency: int | None = None
    pid: int | None = None
    uptime: int | None = None
    prefetch_count: int | None = None


class WorkerStore:
    """Thread-safe in-memory worker store."""

    def __init__(self, max_workers: int | None = None) -> None:
        self._max_workers = max_workers or celeryx_settings.MAX_WORKERS
        self._workers: OrderedDict[str, WorkerInfo] = OrderedDict()
        self._lock = threading.Lock()

    def update(self, hostname: str, **fields: Any) -> WorkerInfo:
        """Update or create a worker entry."""
        with self._lock:
            if hostname in self._workers:
                worker = self._workers[hostname]
                for k, v in fields.items():
                    if hasattr(worker, k):
                        setattr(worker, k, v)
                self._workers.move_to_end(hostname)
            else:
                worker = WorkerInfo(hostname=hostname, **{k: v for k, v in fields.items() if hasattr(WorkerInfo, k)})
                self._workers[hostname] = worker
                while len(self._workers) > self._max_workers:
                    self._workers.popitem(last=False)
            return worker

    def get(self, hostname: str) -> WorkerInfo | None:
        """Get a worker by hostname."""
        with self._lock:
            return self._workers.get(hostname)

    def all(self) -> list[WorkerInfo]:
        """Get all workers."""
        with self._lock:
            return list(self._workers.values())

    def online(self) -> list[WorkerInfo]:
        """Get all online workers."""
        with self._lock:
            return [w for w in self._workers.values() if w.status == WorkerStatus.ONLINE]

    def count(self) -> int:
        """Get the number of workers."""
        with self._lock:
            return len(self._workers)

    def clear(self) -> None:
        """Clear all workers."""
        with self._lock:
            self._workers.clear()


# Global worker store instance
worker_store = WorkerStore()
