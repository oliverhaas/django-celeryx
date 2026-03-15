"""Container fixtures for Redis using testcontainers."""

from __future__ import annotations

from contextlib import suppress
from typing import TYPE_CHECKING, NamedTuple

if TYPE_CHECKING:
    from collections.abc import Generator

import pytest
from testcontainers.core.container import DockerContainer
from testcontainers.core.waiting_utils import wait_for_logs


class ContainerInfo(NamedTuple):
    """Container connection info."""

    host: str
    port: int
    container: DockerContainer


def _start_redis_container() -> ContainerInfo:
    """Start a Redis container."""
    container = DockerContainer("redis:latest")
    container.with_exposed_ports(6379)
    container.with_command("redis-server --protected-mode no")
    container.start()
    wait_for_logs(container, "Ready to accept connections")
    return ContainerInfo(
        host=container.get_container_host_ip(),
        port=int(container.get_exposed_port(6379)),
        container=container,
    )


@pytest.fixture(scope="session")
def redis_container_factory() -> Generator[tuple[str, int]]:
    """Session-scoped Redis container for Celery broker."""
    info = _start_redis_container()
    yield info.host, info.port
    with suppress(Exception):
        info.container.stop()


@pytest.fixture
def redis_container(redis_container_factory: tuple[str, int]) -> tuple[str, int]:
    """Get the Redis container host and port."""
    return redis_container_factory
