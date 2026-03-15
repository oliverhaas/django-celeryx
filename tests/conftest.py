"""Pytest configuration for django-celeryx tests."""

from tests.fixtures.containers import redis_container, redis_container_factory
from tests.fixtures.settings import settings

# Re-export fixtures so pytest can discover them
__all__ = [
    "redis_container",
    "redis_container_factory",
    "settings",
]
