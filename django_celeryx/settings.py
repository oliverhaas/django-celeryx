"""Package settings with defaults."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class CeleryXSettings:
    """Settings for django-celeryx with sensible defaults."""

    # State limits
    MAX_TASKS: int = 100_000
    MAX_WORKERS: int = 5_000

    # Event listener
    ENABLE_EVENTS: bool = True
    EVENT_LISTENER_AUTOSTART: bool = True

    # Stream replay on restart
    STREAM_REPLAY_DEPTH: int = 10_000

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

    # Worker inspection
    INSPECT_TIMEOUT: float = 1.0

    # Celery app
    CELERY_APP: str | None = None


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
