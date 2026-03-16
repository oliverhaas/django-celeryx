"""Shared helpers for django-celeryx."""

from __future__ import annotations

from typing import Any


def get_celery_app() -> Any:
    """Get the Celery app instance from settings or auto-detect."""
    from django_celeryx.settings import celeryx_settings

    if celeryx_settings.CELERY_APP:
        from importlib import import_module

        module_path, attr = celeryx_settings.CELERY_APP.rsplit(".", 1)
        module = import_module(module_path)
        return getattr(module, attr)

    from celery import current_app

    return current_app
