from pathlib import Path

from django.apps import AppConfig

import django_celeryx.admin


class UnfoldCeleryAdminConfig(AppConfig):
    """Django app configuration for the unfold-themed Celery admin interface."""

    name = "django_celeryx.unfold"
    label = "django_celeryx"
    verbose_name = "django-celeryx"
    # Templates live in the sibling admin package, which is never installed
    # alongside this one (same app label).
    path = str(Path(django_celeryx.admin.__file__).resolve().parent)

    def ready(self):
        from django_celeryx.admin.apps import CeleryAdminConfig

        # Share WAL setup
        CeleryAdminConfig._enable_sqlite_wal()

        from django_celeryx.settings import celeryx_settings

        if not celeryx_settings.ADMIN_ENABLED:
            return

        from django_celeryx.state.persistence import ensure_tables

        ensure_tables()

        if celeryx_settings.EVENT_LISTENER_AUTOSTART:
            from django_celeryx.state.events import start_event_listener

            start_event_listener()
