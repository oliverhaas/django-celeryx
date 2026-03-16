"""Database-backed models for persisting Celery event data.

These are managed models (unlike the admin display models in admin/models.py)
that create actual database tables for event persistence and replay.
Only used when CELERYX["DATABASE"] is configured.
"""

from __future__ import annotations

from django.db import models


class TaskState(models.Model):
    """Persisted task event data, written by the event listener."""

    uuid = models.CharField(max_length=255, unique=True)
    name = models.CharField(max_length=500, blank=True, default="", db_index=True)
    state = models.CharField(max_length=50, db_index=True)
    worker = models.CharField(max_length=255, blank=True, default="", db_index=True)
    args = models.TextField(blank=True, default="")
    kwargs = models.TextField(blank=True, default="")
    result = models.TextField(blank=True, default="")
    exception = models.TextField(blank=True, default="")
    traceback = models.TextField(blank=True, default="")
    runtime = models.FloatField(null=True, blank=True)
    eta = models.CharField(max_length=255, blank=True, default="")
    expires = models.CharField(max_length=255, blank=True, default="")
    exchange = models.CharField(max_length=255, blank=True, default="")
    routing_key = models.CharField(max_length=255, blank=True, default="")
    retries = models.IntegerField(default=0)
    parent_id = models.CharField(max_length=255, blank=True, default="")
    root_id = models.CharField(max_length=255, blank=True, default="")

    # Timestamps from events (epoch floats)
    received = models.FloatField(null=True, blank=True)
    started = models.FloatField(null=True, blank=True)
    succeeded = models.FloatField(null=True, blank=True)
    failed = models.FloatField(null=True, blank=True)
    retried_at = models.FloatField(null=True, blank=True)
    revoked = models.FloatField(null=True, blank=True)

    # When this record was last updated
    updated_at = models.FloatField(db_index=True)

    class Meta:
        app_label = "django_celeryx"
        indexes = [  # noqa: RUF012
            models.Index(fields=["-updated_at"], name="celeryx_task_updated_idx"),
            models.Index(fields=["worker", "state"], name="celeryx_task_worker_state_idx"),
            models.Index(fields=["name", "state"], name="celeryx_task_name_state_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.name or 'Task'} ({self.uuid[:8]})"


class WorkerState(models.Model):
    """Persisted worker state, written by the event listener."""

    hostname = models.CharField(max_length=255, unique=True)
    status = models.CharField(max_length=50, default="online")
    active = models.IntegerField(default=0)
    freq = models.FloatField(default=2.0)
    loadavg = models.JSONField(default=list, blank=True)
    sw_ident = models.CharField(max_length=255, blank=True, default="")
    sw_ver = models.CharField(max_length=255, blank=True, default="")
    sw_sys = models.CharField(max_length=255, blank=True, default="")
    last_heartbeat = models.FloatField(null=True, blank=True)

    # When this record was last updated
    updated_at = models.FloatField(db_index=True)

    class Meta:
        app_label = "django_celeryx"

    def __str__(self) -> str:
        return self.hostname
