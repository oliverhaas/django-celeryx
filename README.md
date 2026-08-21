# django-celeryx

[![PyPI version](https://img.shields.io/pypi/v/django-celeryx.svg?style=flat)](https://pypi.org/project/django-celeryx/)
[![Python versions](https://img.shields.io/pypi/pyversions/django-celeryx.svg)](https://pypi.org/project/django-celeryx/)
[![CI](https://github.com/oliverhaas/django-celeryx/actions/workflows/ci.yml/badge.svg)](https://github.com/oliverhaas/django-celeryx/actions/workflows/ci.yml)

Celery monitoring and management for Django admin. Like Flower, but embedded in your Django admin with htmx for real-time updates.

## Installation

```console
pip install django-celeryx[celery]
```

Or with celery-asyncio:

```console
pip install django-celeryx[celery-asyncio]
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

- **Real-time task monitoring** - Live task list with state, args, result, timing, auto-refreshing via htmx
- **Worker management** - View worker status, pool info, active queues, configuration
- **Control actions** - Revoke/terminate tasks, shutdown/restart workers, manage pools and queues
- **Broker overview** - Queue names, routing keys, consumer counts
- **Django admin native** - Looks and feels like standard Django admin, no separate service to run
- **Database persistence** - All state persisted to database (dedicated SQLite file by default, or any Django database)
- **Registered tasks** - Browse all registered task types, link to filtered task list

## Task Monitoring

The task list shows all Celery tasks with color-coded states:

- **PENDING** (grey), **RECEIVED** (yellow), **STARTED** (blue), **SUCCESS** (green), **FAILURE** (red), **RETRY** (orange), **REVOKED** (purple)

Configurable columns via `TASK_COLUMNS` setting.

## Worker Management

Worker detail view with tabbed interface (matching Flower):

- **Pool**: pool type, concurrency, processes. Controls: grow/shrink, autoscale
- **Queues**: active queues. Controls: add/cancel consumer
- **Tasks**: processed counts, active/scheduled/reserved/revoked tasks
- **Limits**: rate limits and timeouts
- **Config**: full worker Celery configuration
- **Stats**: system resource usage, broker connection info

## Control Actions

Full control parity with Flower:

- Revoke / terminate / abort tasks
- Shutdown / restart worker pool
- Grow / shrink pool, set autoscale
- Add / cancel queue consumer
- Set rate limits and time limits

## Configuration

```python
CELERYX = {
    "MAX_TASK_COUNT": 100_000,
    "MAX_TASK_AGE": 86400,  # 24 hours
    "AUTO_MIGRATE": True,  # migrate the auto-configured SQLite file on startup
    "AUTO_REFRESH_INTERVAL": 3,
    "TASK_COLUMNS": ["name", "uuid", "state", "worker", "received", "started", "runtime"],
}
```

See the [configuration guide](https://oliverhaas.github.io/django-celeryx/user-guide/configuration/)
for every setting, the permission model, and the security notes.

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
- Celery 5.4+ or celery-asyncio 6.0+

## License

MIT
