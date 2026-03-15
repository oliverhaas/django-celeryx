from django.apps import AppConfig


class UnfoldCeleryAdminConfig(AppConfig):
    """Django app configuration for the unfold-themed Celery admin interface."""

    name = "django_celeryx.unfold"
    label = "django_celeryx"
    verbose_name = "django-celeryx"
