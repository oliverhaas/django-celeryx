"""Database router for django-celeryx models.

Routes all managed celeryx models (TaskState, WorkerState) to the database
specified by CELERYX["DATABASE"]. Unmanaged models (Task, Worker, Queue,
RegisteredTask) are not affected since they don't hit the database.

Usage in Django settings (only needed when using a non-default database)::

    DATABASE_ROUTERS = ["django_celeryx.db_router.CeleryXRouter"]
"""

from __future__ import annotations

from typing import Any

_CELERYX_APP_LABEL = "django_celeryx"


class CeleryXRouter:
    """Route celeryx managed models to the configured database."""

    def _get_db(self) -> str:
        from django_celeryx.settings import get_db_alias

        return get_db_alias()

    def db_for_read(self, model: type, **hints: Any) -> str | None:
        if model._meta.app_label == _CELERYX_APP_LABEL and model._meta.managed:  # type: ignore[attr-defined]
            return self._get_db()
        return None

    def db_for_write(self, model: type, **hints: Any) -> str | None:
        if model._meta.app_label == _CELERYX_APP_LABEL and model._meta.managed:  # type: ignore[attr-defined]
            return self._get_db()
        return None

    def allow_relation(self, obj1: Any, obj2: Any, **hints: Any) -> bool | None:
        if _CELERYX_APP_LABEL in {obj1._meta.app_label, obj2._meta.app_label}:
            return obj1._meta.app_label == obj2._meta.app_label
        return None

    def allow_migrate(self, db: str, app_label: str, **hints: Any) -> bool | None:
        if app_label == _CELERYX_APP_LABEL:
            return db == self._get_db()
        # Don't let other apps migrate to our DB (if it's a dedicated one)
        target_db = self._get_db()
        if db == target_db and target_db not in ("default", "celeryx_default"):
            return False
        return None
