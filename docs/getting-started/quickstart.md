# Quick Start

## Basic Setup

1. Install django-celeryx:

```console
pip install django-celeryx[celery]
```

2. Add to your Django settings:

```python
INSTALLED_APPS = [
    # ...
    "django_celeryx.admin",
]
```

3. Start your Django server and navigate to the admin. You'll see Tasks, Workers, Queues, and Registered Tasks sections.

## Configuration

Optional configuration via `CELERYX` dict in settings:

```python
CELERYX = {
    "MAX_TASK_COUNT": 100_000,
    "MAX_TASK_AGE": 86400,
    "AUTO_REFRESH_INTERVAL": 3,
}
```

See [Configuration](../user-guide/configuration.md) for all options.
