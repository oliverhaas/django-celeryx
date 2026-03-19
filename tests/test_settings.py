"""Tests for django_celeryx.settings module."""

from __future__ import annotations

from django.test import override_settings

from django_celeryx.settings import (
    CeleryXSettings,
    _get_settings,
    celeryx_settings,
    get_db_alias,
)


class TestDefaultSettings:
    """Tests for default CeleryXSettings values."""

    def test_default_celery_app(self):
        assert CeleryXSettings().CELERY_APP is None

    def test_default_database(self):
        assert CeleryXSettings().DATABASE is None

    def test_default_max_task_age(self):
        assert CeleryXSettings().MAX_TASK_AGE == 86400

    def test_default_max_task_count(self):
        assert CeleryXSettings().MAX_TASK_COUNT == 100_000

    def test_default_admin_enabled(self):
        assert CeleryXSettings().ADMIN_ENABLED is True

    def test_default_event_listener_autostart(self):
        assert CeleryXSettings().EVENT_LISTENER_AUTOSTART is True

    def test_default_enable_events(self):
        assert CeleryXSettings().ENABLE_EVENTS is True

    def test_default_inspect_timeout(self):
        assert CeleryXSettings().INSPECT_TIMEOUT == 1.0

    def test_default_auto_refresh_interval(self):
        assert CeleryXSettings().AUTO_REFRESH_INTERVAL == 3

    def test_default_task_columns(self):
        expected = ["name", "uuid", "state", "worker", "received", "started", "runtime"]
        assert expected == CeleryXSettings().TASK_COLUMNS

    def test_default_natural_time(self):
        assert CeleryXSettings().NATURAL_TIME is False


class TestGetSettings:
    """Tests for _get_settings reading from Django config."""

    @override_settings(
        CELERYX={
            "EVENT_LISTENER_AUTOSTART": False,
            "DATABASE": "default",
        }
    )
    def test_custom_settings_via_override(self):
        """Custom CELERYX dict overrides defaults."""
        settings = _get_settings()
        assert settings.EVENT_LISTENER_AUTOSTART is False
        assert settings.DATABASE == "default"

    @override_settings(
        CELERYX={
            "MAX_TASK_AGE": 3600,
            "MAX_TASK_COUNT": 500,
            "INSPECT_TIMEOUT": 5.0,
        }
    )
    def test_partial_override(self):
        """Unspecified fields retain defaults."""
        settings = _get_settings()
        assert settings.MAX_TASK_AGE == 3600
        assert settings.MAX_TASK_COUNT == 500
        assert settings.INSPECT_TIMEOUT == 5.0
        # Defaults preserved
        assert settings.CELERY_APP is None
        assert settings.ADMIN_ENABLED is True

    @override_settings(
        CELERYX={
            "UNKNOWN_KEY": "ignored",
            "DATABASE": "mydb",
        }
    )
    def test_unknown_keys_ignored(self):
        """Unknown keys in CELERYX dict are silently ignored."""
        settings = _get_settings()
        assert settings.DATABASE == "mydb"
        assert not hasattr(settings, "UNKNOWN_KEY")


class TestGetDbAlias:
    """Tests for get_db_alias database resolution."""

    @override_settings(CELERYX={"DATABASE": "default", "EVENT_LISTENER_AUTOSTART": False})
    def test_returns_configured_database(self, db):
        """Returns the DATABASE value when explicitly configured."""
        assert get_db_alias() == "default"

    @override_settings(CELERYX={"DATABASE": "custom_db", "EVENT_LISTENER_AUTOSTART": False})
    def test_returns_custom_database(self, db):
        """Returns a custom database alias when configured."""
        assert get_db_alias() == "custom_db"

    @override_settings(CELERYX={"EVENT_LISTENER_AUTOSTART": False})
    def test_auto_creates_celeryx_sqlite(self):
        """When DATABASE is not set, auto-creates a dedicated 'celeryx' SQLite alias."""
        from django_celeryx.settings import CELERYX_DB_ALIAS

        alias = get_db_alias()
        assert alias == CELERYX_DB_ALIAS


class TestLazySettings:
    """Tests for _LazySettings proxy and reload."""

    @override_settings(
        CELERYX={
            "DATABASE": "default",
            "EVENT_LISTENER_AUTOSTART": False,
        }
    )
    def test_lazy_attribute_access(self):
        """Lazy proxy forwards attribute access to underlying settings."""
        celeryx_settings.reload()
        assert celeryx_settings.DATABASE == "default"
        assert celeryx_settings.EVENT_LISTENER_AUTOSTART is False

    def test_reload_clears_cache(self):
        """After reload, settings are re-read from Django config."""
        celeryx_settings.reload()
        initial_db = celeryx_settings.DATABASE
        celeryx_settings.reload()
        assert celeryx_settings._settings is None

        # Access triggers reload
        _ = celeryx_settings.DATABASE
        assert celeryx_settings._settings is not None

    @override_settings(
        CELERYX={
            "DATABASE": "first_db",
            "EVENT_LISTENER_AUTOSTART": False,
        }
    )
    def test_reload_picks_up_new_settings(self):
        """Reload picks up changed Django settings."""
        celeryx_settings.reload()
        assert celeryx_settings.DATABASE == "first_db"

        with override_settings(
            CELERYX={
                "DATABASE": "second_db",
                "EVENT_LISTENER_AUTOSTART": False,
            }
        ):
            celeryx_settings.reload()
            assert celeryx_settings.DATABASE == "second_db"


class TestCeleryXRouter:
    """Tests for CeleryXRouter routing logic."""

    def test_routes_managed_model_for_read(self, db):
        """Router returns the configured db alias for managed celeryx models (read)."""
        from django_celeryx.db_models import TaskState
        from django_celeryx.db_router import CeleryXRouter

        router = CeleryXRouter()
        result = router.db_for_read(TaskState)
        assert result == "default"

    def test_routes_managed_model_for_write(self, db):
        """Router returns the configured db alias for managed celeryx models (write)."""
        from django_celeryx.db_models import WorkerState
        from django_celeryx.db_router import CeleryXRouter

        router = CeleryXRouter()
        result = router.db_for_write(WorkerState)
        assert result == "default"

    def test_does_not_route_unmanaged_model(self, db):
        """Router returns None for unmanaged celeryx models."""
        from django_celeryx.admin.models import Task
        from django_celeryx.db_router import CeleryXRouter

        router = CeleryXRouter()
        assert router.db_for_read(Task) is None
        assert router.db_for_write(Task) is None

    def test_does_not_route_non_celeryx_model(self, db):
        """Router returns None for models outside the celeryx app."""
        from django.contrib.auth.models import User

        from django_celeryx.db_router import CeleryXRouter

        router = CeleryXRouter()
        assert router.db_for_read(User) is None
        assert router.db_for_write(User) is None

    def test_allow_migrate_managed(self, db):
        """allow_migrate returns True for celeryx app on the configured db."""
        from django_celeryx.db_router import CeleryXRouter

        router = CeleryXRouter()
        assert router.allow_migrate("default", "django_celeryx") is True

    def test_allow_migrate_wrong_db(self, db):
        """allow_migrate returns False for celeryx app on a different db."""
        from django_celeryx.db_router import CeleryXRouter

        router = CeleryXRouter()
        assert router.allow_migrate("other_db", "django_celeryx") is False
