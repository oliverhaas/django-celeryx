"""Unmanaged display models for the Django admin interface.

These models don't create database tables. Admin views populate them from
the managed TaskState/WorkerState models (or from Celery inspect() calls).
"""

from __future__ import annotations

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
    parent_id = models.CharField(max_length=255, blank=True, default="")
    root_id = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        managed = False
        app_label = "django_celeryx"
        default_permissions = ("view",)
        verbose_name = "Task"
        verbose_name_plural = "Tasks"

    def __str__(self) -> str:
        return f"{self.name or 'Task'} ({self.uuid[:8]})"

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
    processed = models.IntegerField(null=True, blank=True)
    succeeded = models.IntegerField(null=True, blank=True)
    failed = models.IntegerField(null=True, blank=True)
    retried = models.IntegerField(null=True, blank=True)
    pool = models.CharField(max_length=50, blank=True, default="")
    concurrency = models.IntegerField(null=True, blank=True)
    loadavg = models.CharField(max_length=100, blank=True, default="")
    sw_ident = models.CharField(max_length=255, blank=True, default="")
    sw_ver = models.CharField(max_length=255, blank=True, default="")
    sw_sys = models.CharField(max_length=255, blank=True, default="")
    uptime = models.IntegerField(null=True, blank=True)
    pid = models.IntegerField(null=True, blank=True)
    freq = models.FloatField(default=2.0)
    prefetch_count = models.IntegerField(null=True, blank=True)
    last_heartbeat = models.FloatField(null=True, blank=True)

    class Meta:
        managed = False
        app_label = "django_celeryx"
        default_permissions = ("view",)
        verbose_name = "Worker"
        verbose_name_plural = "Workers"

    def __str__(self) -> str:
        return self.hostname or "Worker"

    @property
    def pk(self) -> str:
        return self.hostname

    @pk.setter
    def pk(self, value: str) -> None:  # type: ignore[return]
        self.hostname = value


class Queue(models.Model):
    """Unmanaged model representing a Celery queue for admin display."""

    name = models.CharField(max_length=255, primary_key=True)
    exchange = models.CharField(max_length=255, blank=True, default="")
    routing_key = models.CharField(max_length=255, blank=True, default="")
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


class RegisteredTask(models.Model):
    """Unmanaged model representing a registered Celery task type."""

    name = models.CharField(max_length=500, primary_key=True)

    class Meta:
        managed = False
        app_label = "django_celeryx"
        default_permissions = ("view",)
        verbose_name = "Registered Task"
        verbose_name_plural = "Registered Tasks"

    def __str__(self) -> str:
        return self.name or "Task"

    @property
    def pk(self) -> str:
        return self.name

    @pk.setter
    def pk(self, value: str) -> None:  # type: ignore[return]
        self.name = value


class Dashboard(models.Model):
    """Unmanaged model used as a sidebar entry for the dashboard view."""

    name = models.CharField(max_length=1, primary_key=True)

    class Meta:
        managed = False
        app_label = "django_celeryx"
        default_permissions = ("view",)
        verbose_name = "Dashboard"
        verbose_name_plural = "Dashboard"

    def __str__(self) -> str:
        return "Dashboard"


# Import managed DB models so Django discovers them for migrations
from django_celeryx.db_models import TaskState, WorkerState  # noqa: E402, F401
