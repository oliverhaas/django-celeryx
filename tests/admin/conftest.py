import pytest
from django.contrib.auth.models import User
from django.test import Client


@pytest.fixture
def admin_user(db):
    return User.objects.create_superuser(username="admin", email="admin@example.com", password="password")  # noqa: S106


@pytest.fixture
def admin_client(admin_user):
    client = Client()
    client.force_login(admin_user)
    return client
