from django.apps import AppConfig


class UnfoldCeleryAdminConfig(AppConfig):
    """Django app configuration for the unfold-themed Celery admin interface.

    Starts the event listener thread on ready() to begin capturing
    Celery events for the in-memory task/worker state.
    """

    name = "django_celeryx.unfold"
    label = "django_celeryx"
    verbose_name = "django-celeryx"

    def ready(self):
        from django_celeryx.settings import celeryx_settings

        if celeryx_settings.EVENT_LISTENER_AUTOSTART:
            from django_celeryx.state.events import start_event_listener

            start_event_listener()
