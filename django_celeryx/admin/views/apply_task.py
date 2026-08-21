"""View for sending/applying a Celery task by name."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseRedirect
from django.shortcuts import render

from django_celeryx.admin.models import Task

if TYPE_CHECKING:
    from django.http import HttpRequest, HttpResponse


def _parse_args(raw: str) -> tuple | None:
    """Parse a JSON array string into a tuple of args."""
    raw = raw.strip()
    if not raw:
        return None
    parsed = json.loads(raw)
    if not isinstance(parsed, list):
        msg = "args must be a JSON array"
        raise TypeError(msg)
    return tuple(parsed)


def _parse_kwargs(raw: str) -> dict | None:
    """Parse a JSON object string into kwargs dict."""
    raw = raw.strip()
    if not raw:
        return None
    parsed = json.loads(raw)
    if not isinstance(parsed, dict):
        msg = "kwargs must be a JSON object"
        raise TypeError(msg)
    return parsed


def apply_task_view(request: HttpRequest, task_name: str = "", *, can_control: bool = False) -> HttpResponse:
    """Form to send a Celery task by name with optional args/kwargs.

    Sending a task runs arbitrary registered code on a worker, so ``can_control``
    must reflect the caller's change permission.
    """
    if not can_control:
        raise PermissionDenied

    if request.method == "POST":
        name = request.POST.get("task_name", task_name).strip()
        if not name:
            messages.error(request, "Task name is required.")
            return HttpResponseRedirect(request.get_full_path())

        try:
            args = _parse_args(request.POST.get("args", ""))
            kwargs = _parse_kwargs(request.POST.get("kwargs", ""))

            from django_celeryx.control.tasks import apply_task

            task_id = apply_task(name, args=args, kwargs=kwargs)
            messages.success(request, f"Task {name} sent successfully. ID: {task_id[:8]}")

            from django.urls import reverse

            return HttpResponseRedirect(reverse("admin:django_celeryx_task_change", args=[task_id]))
        except json.JSONDecodeError as exc:
            messages.error(request, f"Invalid JSON: {exc}")
        except Exception as exc:
            messages.error(request, f"Failed to send task: {exc}")

        return HttpResponseRedirect(request.get_full_path())

    # GET: show the form
    registered_tasks = []
    try:
        from django_celeryx.helpers import get_celery_app
        from django_celeryx.settings import celeryx_settings

        app = get_celery_app()
        inspector = app.control.inspect(timeout=celeryx_settings.INSPECT_TIMEOUT)
        all_registered = inspector.registered() or {}
        names: set[str] = set()
        for worker_tasks in all_registered.values():
            names.update(worker_tasks)
        names.update(app.tasks)
        registered_tasks = sorted(n for n in names if not n.startswith("celery."))
    except Exception:  # noqa: S110
        pass  # Gracefully degrade: show empty dropdown or text input

    context = admin.site.each_context(request)
    context.update(
        {
            "title": "Send Task",
            "task_name": task_name,
            "registered_tasks": registered_tasks,
            "opts": Task._meta,
        },
    )
    return render(request, "admin/django_celeryx/task/apply.html", context)
