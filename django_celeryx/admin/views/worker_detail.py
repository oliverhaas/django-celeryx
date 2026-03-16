"""Worker detail view with tabbed sections matching Flower's worker detail."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from django.contrib import admin, messages
from django.http import HttpResponseRedirect
from django.shortcuts import render

from django_celeryx.admin.helpers import get_celery_app

if TYPE_CHECKING:
    from django.http import HttpRequest, HttpResponse

logger = logging.getLogger(__name__)

WORKER_TABS = ("pool", "queues", "tasks", "limits", "config", "stats")


def _inspect_worker(hostname: str) -> dict[str, Any]:
    """Fetch detailed worker data via celery.control.inspect()."""
    from django_celeryx.settings import celeryx_settings

    result: dict[str, Any] = {}
    try:
        app = get_celery_app()
        inspector = app.control.inspect(destination=[hostname], timeout=celeryx_settings.INSPECT_TIMEOUT)

        stats = (inspector.stats() or {}).get(hostname, {})
        result["stats"] = stats
        result["pool"] = stats.get("pool", {})
        result["broker"] = stats.get("broker", {})
        result["rusage"] = stats.get("rusage", {})
        result["total"] = stats.get("total", {})
        result["pid"] = stats.get("pid")
        result["uptime"] = stats.get("uptime")
        result["prefetch_count"] = stats.get("prefetch_count")
        result["clock"] = stats.get("clock")

        result["active"] = (inspector.active() or {}).get(hostname, [])
        result["scheduled"] = (inspector.scheduled() or {}).get(hostname, [])
        result["reserved"] = (inspector.reserved() or {}).get(hostname, [])
        result["revoked"] = (inspector.revoked() or {}).get(hostname, [])
        result["registered"] = (inspector.registered() or {}).get(hostname, [])
        result["queues"] = (inspector.active_queues() or {}).get(hostname, [])
        result["conf"] = (inspector.conf() or {}).get(hostname, {})
    except Exception:
        logger.debug("Failed to inspect worker %s", hostname, exc_info=True)

    return result


def _dispatch_pool_action(request: HttpRequest, hostname: str, action: str) -> str:
    """Handle pool and worker lifecycle actions."""
    from django_celeryx.control import workers as worker_ctl

    post = request.POST
    if action == "shutdown":
        worker_ctl.shutdown_worker(hostname)
        return f"Shutdown signal sent to {hostname}."
    if action == "pool_restart":
        worker_ctl.pool_restart(hostname)
        return f"Pool restart signal sent to {hostname}."
    if action == "pool_grow":
        n = int(post.get("n", 1))
        worker_ctl.pool_grow(hostname, n)
        return f"Pool grow by {n} sent to {hostname}."
    if action == "pool_shrink":
        n = int(post.get("n", 1))
        worker_ctl.pool_shrink(hostname, n)
        return f"Pool shrink by {n} sent to {hostname}."
    if action == "autoscale":
        worker_ctl.autoscale(hostname, int(post.get("max", 0)), int(post.get("min", 0)))
        return f"Autoscale sent to {hostname}."
    return ""


def _dispatch_queue_action(request: HttpRequest, hostname: str, action: str) -> str:
    """Handle queue consumer actions."""
    from django_celeryx.control import workers as worker_ctl

    queue = request.POST.get("queue", "").strip()
    if not queue:
        return ""
    if action == "add_consumer":
        worker_ctl.add_consumer(hostname, queue)
        return f"Added consumer for '{queue}' on {hostname}."
    if action == "cancel_consumer":
        worker_ctl.cancel_consumer(hostname, queue)
        return f"Cancelled consumer for '{queue}' on {hostname}."
    return ""


def _dispatch_limit_action(request: HttpRequest, hostname: str, action: str) -> str:
    """Handle rate limit and time limit actions."""
    from django_celeryx.control.tasks import set_rate_limit, set_time_limit

    post = request.POST
    task_name = post.get("task_name", "").strip()
    if not task_name:
        return ""
    if action == "rate_limit":
        rate = post.get("rate", "").strip()
        if rate:
            set_rate_limit(task_name, rate, destination=[hostname])
            return f"Rate limit {rate} set for {task_name}."
    if action == "time_limit":
        soft = post.get("soft", "").strip()
        hard = post.get("hard", "").strip()
        set_time_limit(
            task_name, soft=float(soft) if soft else None, hard=float(hard) if hard else None, destination=[hostname]
        )
        return f"Time limit set for {task_name}."
    return ""


_ACTION_DISPATCHERS = {
    "shutdown": _dispatch_pool_action,
    "pool_restart": _dispatch_pool_action,
    "pool_grow": _dispatch_pool_action,
    "pool_shrink": _dispatch_pool_action,
    "autoscale": _dispatch_pool_action,
    "add_consumer": _dispatch_queue_action,
    "cancel_consumer": _dispatch_queue_action,
    "rate_limit": _dispatch_limit_action,
    "time_limit": _dispatch_limit_action,
}


def _handle_post(request: HttpRequest, hostname: str) -> HttpResponse | None:
    """Handle worker control action POST requests."""
    if request.method != "POST":
        return None

    action = request.POST.get("action", "")
    dispatcher = _ACTION_DISPATCHERS.get(action)
    if not dispatcher:
        return None

    tab = request.GET.get("tab", "pool")

    try:
        msg = dispatcher(request, hostname, action)
        if msg:
            messages.success(request, msg)
    except Exception as exc:
        messages.error(request, f"Action failed: {exc}")

    return HttpResponseRedirect(f"{request.path}?tab={tab}")


def worker_detail_view(request: HttpRequest, hostname: str) -> HttpResponse:
    """Display worker details with tabbed navigation matching Flower."""
    response = _handle_post(request, hostname)
    if response is not None:
        return response

    from django_celeryx.db_models import WorkerState
    from django_celeryx.settings import get_db_alias

    worker = WorkerState.objects.using(get_db_alias()).filter(hostname=hostname).first()
    tab = request.GET.get("tab", "pool")
    if tab not in WORKER_TABS:
        tab = "pool"

    data = _inspect_worker(hostname)

    pool_info = data.get("pool", {})
    pool_impl = pool_info.get("implementation", "")
    pool_type = pool_impl.rsplit(":", 1)[-1] if ":" in pool_impl else pool_impl

    conf = data.get("conf", {})
    conf_items = sorted(conf.items()) if isinstance(conf, dict) else []

    context = admin.site.each_context(request)
    context.update(
        {
            "title": f"Worker: {hostname}",
            "hostname": hostname,
            "worker": worker,
            "current_tab": tab,
            "tabs": WORKER_TABS,
            "opts": {
                "app_label": "django_celeryx",
                "model_name": "worker",
                "verbose_name_plural": "Workers",
                "app_config": type("", (), {"verbose_name": "django-celeryx"})(),
            },
            # Pool tab
            "pool_type": pool_type,
            "pool_concurrency": pool_info.get("max-concurrency"),
            "pool_processes": pool_info.get("processes", []),
            "pool_max_tasks_per_child": pool_info.get("max-tasks-per-child"),
            "pool_timeouts": pool_info.get("timeouts"),
            "prefetch_count": data.get("prefetch_count"),
            # Queues tab
            "queues": data.get("queues", []),
            # Tasks tab
            "total_processed": data.get("total", {}),
            "active_tasks": data.get("active", []),
            "scheduled_tasks": data.get("scheduled", []),
            "reserved_tasks": data.get("reserved", []),
            "revoked_tasks": data.get("revoked", []),
            "registered_tasks": sorted(data.get("registered", [])),
            # Config tab
            "conf_items": conf_items,
            # Stats tab
            "rusage": data.get("rusage", {}),
            "broker_info": data.get("broker", {}),
            "pid": data.get("pid"),
            "uptime": data.get("uptime"),
            "clock": data.get("clock"),
        }
    )
    return render(request, "admin/django_celeryx/worker/change_form.html", context)
