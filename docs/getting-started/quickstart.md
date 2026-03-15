# Quick Start

## Basic Setup

1. Install django-celeryx:

```console
pip install django-celeryx
```

2. Add to your Django settings:

```python
INSTALLED_APPS = [
    # ...
    "django_celeryx.admin",
]
```

3. Start your Django server and navigate to the admin. You'll see Tasks, Workers, and Queues sections.

## Configuration

Optional configuration via `CELERYX` dict in settings:

```python
CELERYX = {
    "MAX_TASKS": 100_000,
    "MAX_WORKERS": 5_000,
    "AUTO_REFRESH_INTERVAL": 3,
}
```

See [Configuration](../user-guide/configuration.md) for all options.
