from django.apps import AppConfig


class CeleryXConfig(AppConfig):
    """Root app configuration for django-celeryx.

    This app starts the event listener thread on ready() when
    EVENT_LISTENER_AUTOSTART is enabled.
    """

    name = "django_celeryx"
    verbose_name = "django-celeryx"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self):
        from django_celeryx.settings import celeryx_settings

        if celeryx_settings.EVENT_LISTENER_AUTOSTART:
            from django_celeryx.state.events import start_event_listener

            start_event_listener()
