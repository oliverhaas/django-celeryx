"""Package settings with defaults."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class CeleryXSettings:
    """Settings for django-celeryx with sensible defaults.

    All settings are configured via the CELERYX dict in Django settings::

        CELERYX = {
            "CELERY_APP": "myproject.celery.app",
            "DATABASE": "default",  # or a dedicated DB alias
            ...
        }
    """

    # Celery app
    CELERY_APP: str | None = None

    # Database for persisting event data.
    # None = in-memory only (no persistence across restarts).
    # Set to a Django DATABASES alias (e.g. "default", "celeryx") to persist.
    DATABASE: str | None = None

    # Maximum age of stored events in seconds (default 24h). Events older than
    # this are cleaned up periodically. Only applies when DATABASE is set.
    MAX_EVENT_AGE: int = 86400

    # Admin / event listener
    ADMIN_ENABLED: bool = True
    EVENT_LISTENER_AUTOSTART: bool = True
    ENABLE_EVENTS: bool = True

    # State limits (in-memory ring buffers)
    MAX_TASKS: int = 100_000
    MAX_WORKERS: int = 5_000

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
