"""Task detail view showing all task fields matching Flower's task detail."""

from __future__ import annotations

import datetime
from typing import TYPE_CHECKING

from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.utils.html import format_html

from django_celeryx.admin.models import Task
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


def _handle_post(request: HttpRequest, task_id: str, *, can_control: bool) -> HttpResponse | None:
    """Handle control action POST requests."""
    if request.method != "POST":
        return None

    action = request.POST.get("action")
    if not action:
        return None

    if not can_control:
        raise PermissionDenied

    from django_celeryx.control.tasks import revoke_task

    try:
        if action == "revoke":
            revoke_task(task_id)
            messages.success(request, f"Task {task_id[:8]} revoked.")
        elif action == "terminate":
            signal = request.POST.get("signal", "SIGTERM")
            revoke_task(task_id, terminate=True, signal=signal)
            messages.success(request, f"Task {task_id[:8]} terminated ({signal}).")
    except Exception as exc:
        messages.error(request, f"Action failed: {exc}")

    return HttpResponseRedirect(request.get_full_path())


def task_detail_view(request: HttpRequest, task_id: str, *, can_control: bool = False) -> HttpResponse:
    """Display task details matching Flower's task detail page.

    ``can_control`` must reflect the caller's change permission; it gates both
    the control buttons and the POST actions behind them.
    """
    response = _handle_post(request, task_id, can_control=can_control)
    if response is not None:
        return response

    from django_celeryx.db_models import TaskState
    from django_celeryx.settings import get_db_alias

    task = TaskState.objects.using(get_db_alias()).filter(uuid=task_id).first()

    can_revoke = can_control and task is not None and task.state in ("PENDING", "RECEIVED", "STARTED")

    context = admin.site.each_context(request)
    context.update(
        {
            "title": f"Task: {task.name or task_id[:8] if task else task_id[:8]}",
            "task_id": task_id,
            "task": task,
            "state_badge": _state_badge(task.state) if task else "",
            "can_revoke": can_revoke,
            "can_control": can_control,
            "opts": Task._meta,
            "received_fmt": _format_ts(task.received) if task else None,
            "started_fmt": _format_ts(task.started) if task else None,
            "succeeded_fmt": _format_ts(getattr(task, "succeeded", None)) if task else None,
            "failed_fmt": _format_ts(getattr(task, "failed", None)) if task else None,
            "retried_fmt": _format_ts(getattr(task, "retried_at", None)) if task else None,
            "revoked_fmt": _format_ts(getattr(task, "revoked", None)) if task else None,
        },
    )
    return render(request, "admin/django_celeryx/task/change_form.html", context)
