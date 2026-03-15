"""Task detail view showing all task fields matching Flower's task detail."""

from __future__ import annotations

import datetime
from typing import TYPE_CHECKING

from django.contrib import admin
from django.shortcuts import render
from django.utils.html import format_html

from django_celeryx.state.tasks import task_store
from django_celeryx.types import TASK_STATE_COLORS

if TYPE_CHECKING:
    from django.http import HttpRequest, HttpResponse


def _format_ts(ts: float | None) -> str | None:
    if ts is None:
        return None
    return datetime.datetime.fromtimestamp(ts, tz=datetime.UTC).strftime("%Y-%m-%d %H:%M:%S UTC")


def _state_badge(state: str) -> str:
    style = TASK_STATE_COLORS.get(state, "background:#f3f4f6;color:#374151;")
    return format_html(
        '<span style="{}padding:2px 8px;border-radius:4px;'
        'font-size:11px;font-weight:600;text-transform:uppercase">{}</span>',
        style,
        state or "-",
    )


def task_detail_view(request: HttpRequest, task_id: str) -> HttpResponse:
    """Display task details matching Flower's task detail page."""
    task = task_store.get(task_id)

    context = admin.site.each_context(request)
    context.update({
        "title": f"Task: {task.name or task_id[:8] if task else task_id[:8]}",
        "task_id": task_id,
        "task": task,
        "state_badge": _state_badge(task.state) if task else "",
        "opts": {"app_label": "django_celeryx", "model_name": "task", "verbose_name_plural": "Tasks",
                 "app_config": type("", (), {"verbose_name": "django-celeryx"})()},
        "received_fmt": _format_ts(task.received) if task else None,
        "started_fmt": _format_ts(task.started) if task else None,
        "succeeded_fmt": _format_ts(getattr(task, "succeeded", None)) if task else None,
        "failed_fmt": _format_ts(getattr(task, "failed", None)) if task else None,
        "retried_fmt": _format_ts(getattr(task, "retried", None)) if task else None,
        "revoked_fmt": _format_ts(getattr(task, "revoked", None)) if task else None,
    })
    return render(request, "admin/django_celeryx/task/change_form.html", context)
