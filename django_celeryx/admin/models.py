"""Unmanaged models for Celery tasks, workers, and queues.

These models don't create database tables — they're backed by in-memory state.
This follows the same pattern as django-cachex's unmanaged models.
"""

from __future__ import annotations

from typing import Any

from django.db import models


class Task(models.Model):
    """Unmanaged model representing a Celery task for admin display."""

    uuid = models.CharField(max_length=255, primary_key=True)
    name = models.CharField(max_length=255, blank=True, default="")
    state = models.CharField(max_length=50, blank=True, default="PENDING")
    worker = models.CharField(max_length=255, blank=True, default="")
    args = models.TextField(blank=True, default="")
    kwargs = models.TextField(blank=True, default="")
    result = models.TextField(blank=True, default="")
    exception = models.TextField(blank=True, default="")
    traceback = models.TextField(blank=True, default="")
    received = models.FloatField(null=True, blank=True)
    started = models.FloatField(null=True, blank=True)
    runtime = models.FloatField(null=True, blank=True)
    eta = models.CharField(max_length=255, blank=True, default="")
    expires = models.CharField(max_length=255, blank=True, default="")
    exchange = models.CharField(max_length=255, blank=True, default="")
    routing_key = models.CharField(max_length=255, blank=True, default="")
    retries = models.IntegerField(default=0)

    class Meta:
        managed = False
        app_label = "django_celeryx"
        default_permissions = ("view",)
        verbose_name = "Task"
        verbose_name_plural = "Tasks"

    def __str__(self) -> str:
        return f"{self.name or 'Task'} ({self.uuid[:8]})"

    @classmethod
    def from_task_info(cls, task_info: Any) -> Task:
        """Create a Task instance from a TaskInfo dataclass."""
        task = cls()
        task.uuid = task_info.uuid
        task.name = task_info.name or ""
        task.state = task_info.state
        task.worker = task_info.worker or ""
        task.args = task_info.args or ""
        task.kwargs = task_info.kwargs or ""
        task.result = task_info.result or ""
        task.exception = task_info.exception or ""
        task.traceback = task_info.traceback or ""
        task.received = task_info.received
        task.started = task_info.started
        task.runtime = task_info.runtime
        task.eta = task_info.eta or ""
        task.expires = task_info.expires or ""
        task.exchange = task_info.exchange or ""
        task.routing_key = task_info.routing_key or ""
        task.retries = task_info.retries
        return task

    @property
    def pk(self) -> str:
        return self.uuid

    @pk.setter
    def pk(self, value: str) -> None:  # type: ignore[return]
        self.uuid = value


class Worker(models.Model):
    """Unmanaged model representing a Celery worker for admin display."""

    hostname = models.CharField(max_length=255, primary_key=True)
    status = models.CharField(max_length=50, blank=True, default="online")
    active = models.IntegerField(default=0)
    freq = models.FloatField(default=2.0)
    sw_ident = models.CharField(max_length=255, blank=True, default="")
    sw_ver = models.CharField(max_length=255, blank=True, default="")
    sw_sys = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        managed = False
        app_label = "django_celeryx"
        default_permissions = ("view",)
        verbose_name = "Worker"
        verbose_name_plural = "Workers"

    def __str__(self) -> str:
        return self.hostname or "Worker"

    @classmethod
    def from_worker_info(cls, worker_info: Any) -> Worker:
        """Create a Worker instance from a WorkerInfo dataclass."""
        worker = cls()
        worker.hostname = worker_info.hostname
        worker.status = worker_info.status
        worker.active = worker_info.active
        worker.freq = worker_info.freq
        worker.sw_ident = worker_info.sw_ident or ""
        worker.sw_ver = worker_info.sw_ver or ""
        worker.sw_sys = worker_info.sw_sys or ""
        return worker

    @property
    def pk(self) -> str:
        return self.hostname

    @pk.setter
    def pk(self, value: str) -> None:  # type: ignore[return]
        self.hostname = value


class Queue(models.Model):
    """Unmanaged model representing a Celery queue for admin display."""

    name = models.CharField(max_length=255, primary_key=True)
    messages = models.IntegerField(default=0)
    consumers = models.IntegerField(default=0)

    class Meta:
        managed = False
        app_label = "django_celeryx"
        default_permissions = ("view",)
        verbose_name = "Queue"
        verbose_name_plural = "Queues"

    def __str__(self) -> str:
        return self.name or "Queue"

    @property
    def pk(self) -> str:
        return self.name

    @pk.setter
    def pk(self, value: str) -> None:  # type: ignore[return]
        self.name = value
