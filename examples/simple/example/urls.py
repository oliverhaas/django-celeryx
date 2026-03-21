"""URL configuration for the simple example project."""

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("celeryx/", include("django_celeryx.urls")),
]
