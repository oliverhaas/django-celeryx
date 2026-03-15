# django-celeryx

[![PyPI version](https://img.shields.io/pypi/v/django-celeryx.svg?style=flat)](https://pypi.org/project/django-celeryx/)
[![Python versions](https://img.shields.io/pypi/pyversions/django-celeryx.svg)](https://pypi.org/project/django-celeryx/)
[![CI](https://github.com/oliverhaas/django-celeryx/actions/workflows/ci.yml/badge.svg)](https://github.com/oliverhaas/django-celeryx/actions/workflows/ci.yml)

Celery monitoring and management for Django admin. Like Flower, but embedded in your Django admin with htmx + Alpine.js for real-time updates.

## Installation

```console
pip install django-celeryx
```

## Quick Start

```python
INSTALLED_APPS = [
    # ...
    "django_celeryx.admin",
]
```

That's it. Start your Django server and navigate to the admin to see your Celery tasks and workers.

## Features

- **Real-time task monitoring** — Live task list with state, args, result, timing, auto-refreshing via htmx
- **Worker management** — View worker status, pool info, active queues, configuration
- **Control actions** — Revoke/terminate tasks, shutdown/restart workers, manage pools and queues
- **Metrics dashboard** — Throughput, latency percentiles, success/failure rates
- **Broker overview** — Queue names, message counts, consumer counts
- **Django admin native** — Looks and feels like standard Django admin, no separate service to run
- **No npm/build step** — htmx + Alpine.js included as static files, no JavaScript build pipeline
- **Structured search** — Filter tasks by state, name, args, kwargs, result with prefix search
- **Event-driven** — In-memory state built from Celery events, same approach as Flower

## Task Monitoring

The task list shows all Celery tasks with color-coded states:

- **PENDING** (grey), **RECEIVED** (yellow), **STARTED** (blue), **SUCCESS** (green), **FAILURE** (red), **RETRY** (orange), **REVOKED** (purple)

All 17 columns from Flower are available, configurable which to show.

## Worker Management

Worker detail view with tabbed interface (matching Flower):

- **Pool** — Pool type, concurrency, processes. Controls: grow/shrink, autoscale
- **Queues** — Active queues. Controls: add/cancel consumer
- **Tasks** — Processed counts, active/scheduled/reserved/revoked tasks
- **Limits** — Rate limits and timeouts
- **Config** — Full worker Celery configuration
- **Stats** — System resource usage, broker connection info

## Control Actions

Full control parity with Flower:

- Revoke / terminate / abort tasks
- Shutdown / restart worker pool
- Grow / shrink pool, set autoscale
- Add / cancel queue consumer
- Set rate limits and time limits
- Apply (execute) tasks from admin

## Configuration

```python
CELERYX = {
    "MAX_TASKS": 100_000,
    "MAX_WORKERS": 5_000,
    "AUTO_REFRESH_INTERVAL": 3,
    "TASK_COLUMNS": ["name", "uuid", "state", "worker", "received", "started", "runtime"],
}
```

## Unfold Theme

For [django-unfold](https://github.com/unfoldadmin/django-unfold) users:

```python
INSTALLED_APPS = [
    "unfold",
    # ...
    "django_celeryx.unfold",  # instead of django_celeryx.admin
]
```

## Documentation

Full documentation at [oliverhaas.github.io/django-celeryx](https://oliverhaas.github.io/django-celeryx/)

## Requirements

- Python 3.12+
- Django 5.2+
- Celery 5.4+

## License

MIT
