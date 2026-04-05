"""Package settings with defaults."""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

# Default database alias auto-configured when DATABASE is not set.
CELERYX_DB_ALIAS = "celeryx"


@dataclass
class CeleryXSettings:
    """Settings for django-celeryx.

    All settings are configured via the CELERYX dict in Django settings::

        CELERYX = {
            "CELERY_APP": "myproject.celery.app",
            "DATABASE": "celeryx",  # or any Django DATABASES alias
            ...
        }
    """

    # Celery app (dotted path to Celery instance). Auto-detected if None.
    CELERY_APP: str | None = None

    # Database alias for storing event data.
    # Default (None) = auto-configures a dedicated 'celeryx' SQLite file database.
    # Set to a Django DATABASES alias to use your own database (e.g. PostgreSQL).
    DATABASE: str | None = None

    # Maximum age of stored task records in seconds (default 24h).
    # Tasks older than this are cleaned up periodically.
    MAX_TASK_AGE: int = 86400

    # Maximum number of task records to keep in the database.
    # Oldest records are pruned when this limit is exceeded.
    MAX_TASK_COUNT: int = 100_000

    # Admin / event listener
    ADMIN_ENABLED: bool = True
    EVENT_LISTENER_AUTOSTART: bool = True
    ENABLE_EVENTS: bool = True

    # Worker inspection
    INSPECT_TIMEOUT: float = 1.0

    # UI
    AUTO_REFRESH_INTERVAL: int = 3
    TASK_COLUMNS: list[str] = field(
        default_factory=lambda: [
            "name",
            "uuid",
            "state",
            "worker",
            "received",
            "started",
            "runtime",
        ],
    )
    NATURAL_TIME: bool = False

    # Prometheus metric name prefix. Set to "flower" for Flower drop-in compat.
    PROMETHEUS_PREFIX: str = "django_celeryx"


def _get_settings() -> CeleryXSettings:
    """Load settings from Django's CELERYX dict, falling back to defaults."""
    from django.conf import settings as django_settings

    user_settings: dict[str, Any] = getattr(django_settings, "CELERYX", {})
    known = {k: v for k, v in user_settings.items() if hasattr(CeleryXSettings, k)}
    unknown = set(user_settings) - set(known)
    if unknown:
        logger.warning("Unknown CELERYX settings (ignored): %s", ", ".join(sorted(unknown)))
    return CeleryXSettings(**known)


def get_db_alias() -> str:
    """Get the database alias for celeryx models.

    If DATABASE is not configured, auto-creates a dedicated 'celeryx' SQLite
    file database alongside the default database.
    """
    settings = _get_settings()
    if settings.DATABASE is not None:
        return settings.DATABASE

    from django.conf import settings as django_settings

    if CELERYX_DB_ALIAS not in django_settings.DATABASES:
        # Place celeryx.sqlite3 next to the default database file
        from pathlib import Path

        default_db = django_settings.DATABASES.get("default", {})
        default_name = default_db.get("NAME", "")
        if default_name and default_name != ":memory:":
            db_dir = Path(str(default_name)).resolve().parent
        else:
            base_dir = getattr(django_settings, "BASE_DIR", None)
            db_dir = Path(str(base_dir)) if base_dir is not None else Path.cwd()

        db_config: dict[str, Any] = {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": str(db_dir / "celeryx.sqlite3"),
            "ATOMIC_REQUESTS": False,
            "AUTOCOMMIT": True,
            "CONN_MAX_AGE": 0,
            "CONN_HEALTH_CHECKS": False,
            "OPTIONS": {},
            "TIME_ZONE": None,
            "USER": "",
            "PASSWORD": "",
            "HOST": "",
            "PORT": "",
            "TEST": {},
        }
        django_settings.DATABASES[CELERYX_DB_ALIAS] = db_config

    return CELERYX_DB_ALIAS


class _LazySettings:
    """Lazy proxy that defers settings loading until first access."""

    _settings: CeleryXSettings | None = None
    _lock: threading.Lock = threading.Lock()

    def _load(self) -> CeleryXSettings:
        if self._settings is None:
            with self._lock:
                if self._settings is None:
                    self._settings = _get_settings()
        return self._settings

    def __getattr__(self, name: str) -> Any:
        return getattr(self._load(), name)

    def reload(self) -> None:
        """Force reload settings (useful for tests)."""
        self._settings = None


celeryx_settings = _LazySettings()
