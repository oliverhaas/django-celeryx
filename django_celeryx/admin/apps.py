from django.apps import AppConfig


class CeleryAdminConfig(AppConfig):
    """Django app configuration for the Celery admin interface."""

    name = "django_celeryx.admin"
    label = "django_celeryx"
    verbose_name = "django-celeryx"
