"""Worker detail view with tabbed sections matching Flower's worker detail."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from django.contrib import admin
from django.shortcuts import render

from django_celeryx.state.workers import worker_store

if TYPE_CHECKING:
    from django.http import HttpRequest, HttpResponse

logger = logging.getLogger(__name__)

# Tabs matching Flower's worker detail
WORKER_TABS = ("pool", "queues", "tasks", "limits", "config", "stats")


def _get_celery_app() -> Any:
    """Get the Celery app instance."""
    from django_celeryx.settings import celeryx_settings

    if celeryx_settings.CELERY_APP:
        from importlib import import_module

        module_path, attr = celeryx_settings.CELERY_APP.rsplit(".", 1)
        module = import_module(module_path)
        return getattr(module, attr)

    from celery import current_app

    return current_app


def _inspect_worker(hostname: str) -> dict[str, Any]:
    """Fetch detailed worker data via celery.control.inspect()."""
    from django_celeryx.settings import celeryx_settings

    result: dict[str, Any] = {}
    try:
        app = _get_celery_app()
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


def worker_detail_view(request: HttpRequest, hostname: str) -> HttpResponse:
    """Display worker details with tabbed navigation matching Flower."""
    worker = worker_store.get(hostname)
    tab = request.GET.get("tab", "pool")
    if tab not in WORKER_TABS:
        tab = "pool"

    # Fetch inspect data
    data = _inspect_worker(hostname)

    # Pool info
    pool_info = data.get("pool", {})
    pool_impl = pool_info.get("implementation", "")
    pool_type = pool_impl.rsplit(":", 1)[-1] if ":" in pool_impl else pool_impl

    # Format config as sorted list of tuples for the template
    conf = data.get("conf", {})
    conf_items = sorted(conf.items()) if isinstance(conf, dict) else []

    # Format rusage
    rusage = data.get("rusage", {})

    context = admin.site.each_context(request)
    context.update({
        "title": f"Worker: {hostname}",
        "hostname": hostname,
        "worker": worker,
        "current_tab": tab,
        "tabs": WORKER_TABS,
        "opts": {"app_label": "django_celeryx", "model_name": "worker", "verbose_name_plural": "Workers",
                 "app_config": type("", (), {"verbose_name": "django-celeryx"})()},
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
        "rusage": rusage,
        "broker_info": data.get("broker", {}),
        "pid": data.get("pid"),
        "uptime": data.get("uptime"),
        "clock": data.get("clock"),
    })
    return render(request, "admin/django_celeryx/worker/change_form.html", context)
