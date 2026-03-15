from django.apps import AppConfig


class CeleryAdminConfig(AppConfig):
    """Django app configuration for the Celery admin interface.

    On ready():
    - Replays persisted events from DB into in-memory state (if DATABASE configured)
    - Starts the event listener thread (if ADMIN_ENABLED and EVENT_LISTENER_AUTOSTART)
    """

    name = "django_celeryx.admin"
    label = "django_celeryx"
    verbose_name = "django-celeryx"

    def ready(self):
        from django_celeryx.settings import celeryx_settings

        if not celeryx_settings.ADMIN_ENABLED:
            return

        # Replay persisted events into in-memory stores
        from django_celeryx.state.persistence import replay_from_db

        replay_from_db()

        # Start event listener
        if celeryx_settings.EVENT_LISTENER_AUTOSTART:
            from django_celeryx.state.events import start_event_listener

            start_event_listener()
