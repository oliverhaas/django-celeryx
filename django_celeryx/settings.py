"""Package settings with defaults."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# Default database alias used when no DATABASE is configured.
# An in-memory SQLite database is auto-configured under this alias.
CELERYX_DEFAULT_DB_ALIAS = "celeryx_default"


@dataclass
class CeleryXSettings:
    """Settings for django-celeryx.

    All settings are configured via the CELERYX dict in Django settings::

        CELERYX = {
            "CELERY_APP": "myproject.celery.app",
            "DATABASE": "default",  # or a dedicated DB alias
            ...
        }
    """

    # Celery app (dotted path to Celery instance). Auto-detected if None.
    CELERY_APP: str | None = None

    # Database alias for storing event data.
    # Default (None) = uses an auto-configured in-memory SQLite database.
    # Set to a Django DATABASES alias to use a persistent database.
    DATABASE: str | None = None

    # Maximum age of stored events in seconds (default 24h).
    # Events older than this are cleaned up periodically.
    MAX_EVENT_AGE: int = 86400

    # Maximum number of task events to keep in the database.
    MAX_TASKS: int = 100_000

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


def _get_settings() -> CeleryXSettings:
    """Load settings from Django's CELERYX dict, falling back to defaults."""
    from django.conf import settings as django_settings

    user_settings: dict[str, Any] = getattr(django_settings, "CELERYX", {})
    return CeleryXSettings(**{k: v for k, v in user_settings.items() if hasattr(CeleryXSettings, k)})


def get_db_alias() -> str:
    """Get the database alias for celeryx models.

    Returns the user-configured DATABASE, or the auto-configured
    in-memory SQLite alias.
    """
    settings = _get_settings()
    if settings.DATABASE is not None:
        return settings.DATABASE

    # Auto-configure in-memory SQLite if not already present
    from django.conf import settings as django_settings

    if CELERYX_DEFAULT_DB_ALIAS not in django_settings.DATABASES:
        django_settings.DATABASES[CELERYX_DEFAULT_DB_ALIAS] = {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": ":memory:",
        }
    return CELERYX_DEFAULT_DB_ALIAS


class _LazySettings:
    """Lazy proxy that defers settings loading until first access."""

    _settings: CeleryXSettings | None = None

    def _load(self) -> CeleryXSettings:
        if self._settings is None:
            self._settings = _get_settings()
        return self._settings

    def __getattr__(self, name: str) -> Any:
        return getattr(self._load(), name)

    def reload(self) -> None:
        """Force reload settings (useful for tests)."""
        self._settings = None


celeryx_settings = _LazySettings()
