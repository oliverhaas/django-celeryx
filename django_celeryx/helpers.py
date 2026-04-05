"""Shared helpers for django-celeryx."""

from __future__ import annotations

from typing import Any


def get_celery_app() -> Any:
    """Get the Celery app instance from settings or auto-detect."""
    from django_celeryx.settings import celeryx_settings

    if celeryx_settings.CELERY_APP:
        from importlib import import_module

        dotted = celeryx_settings.CELERY_APP
        if "." not in dotted:
            msg = f"CELERYX['CELERY_APP'] must be a dotted path (e.g. 'myproject.celery.app'), got: {dotted!r}"
            raise ValueError(msg)
        module_path, attr = dotted.rsplit(".", 1)
        module = import_module(module_path)
        return getattr(module, attr)

    from celery import current_app

    return current_app
