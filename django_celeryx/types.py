"""Type aliases and enums for django-celeryx."""

from __future__ import annotations

from enum import StrEnum


class TaskState(StrEnum):
    """Celery task states."""

    PENDING = "PENDING"
    RECEIVED = "RECEIVED"
    STARTED = "STARTED"
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    RETRY = "RETRY"
    REVOKED = "REVOKED"
    REJECTED = "REJECTED"


class WorkerStatus(StrEnum):
    """Worker online/offline status."""

    ONLINE = "online"
    OFFLINE = "offline"


# Color mapping for task states (used in admin display)
TASK_STATE_COLORS: dict[str, str] = {
    TaskState.PENDING: "background:#f3f4f6;color:#374151;",
    TaskState.RECEIVED: "background:#fef9c3;color:#854d0e;",
    TaskState.STARTED: "background:#dbeafe;color:#1d4ed8;",
    TaskState.SUCCESS: "background:#dcfce7;color:#15803d;",
    TaskState.FAILURE: "background:#fee2e2;color:#dc2626;",
    TaskState.RETRY: "background:#ffedd5;color:#c2410c;",
    TaskState.REVOKED: "background:#ede9fe;color:#7c3aed;",
    TaskState.REJECTED: "background:#f3f4f6;color:#374151;",
}

WORKER_STATUS_COLORS: dict[str, str] = {
    WorkerStatus.ONLINE: "background:#dcfce7;color:#15803d;",
    WorkerStatus.OFFLINE: "background:#fee2e2;color:#dc2626;",
}
