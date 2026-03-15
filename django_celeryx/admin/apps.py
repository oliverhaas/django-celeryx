from django.apps import AppConfig


class CeleryAdminConfig(AppConfig):
    """Django app configuration for the Celery admin interface.

    On ready():
    - Ensures database tables exist (auto-migrates for in-memory SQLite)
    - Starts the event listener thread (if ADMIN_ENABLED)
    """

    name = "django_celeryx.admin"
    label = "django_celeryx"
    verbose_name = "django-celeryx"

    def ready(self):
        from django_celeryx.settings import celeryx_settings

        if not celeryx_settings.ADMIN_ENABLED:
            return

        from django_celeryx.state.persistence import ensure_tables

        ensure_tables()

        if celeryx_settings.EVENT_LISTENER_AUTOSTART:
            from django_celeryx.state.events import start_event_listener

            start_event_listener()
