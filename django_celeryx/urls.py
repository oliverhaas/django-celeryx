"""URL patterns for django-celeryx.

Include in your project's urlconf::

    urlpatterns = [
        path("celeryx/", include("django_celeryx.urls")),
        ...
    ]

This exposes:

- ``/celeryx/metrics/`` — Prometheus metrics endpoint (requires ``prometheus-client``)
"""

from __future__ import annotations

from django.urls import path

from django_celeryx.metrics import metrics_view

app_name = "django_celeryx"

urlpatterns = [
    path("metrics/", metrics_view, name="metrics"),
]
