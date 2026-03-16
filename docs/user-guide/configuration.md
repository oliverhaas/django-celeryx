# Configuration

All settings are optional and configured via the `CELERYX` dict in your Django settings.

```python
CELERYX = {
    # Celery app (dotted path). Auto-detected if None.
    "CELERY_APP": None,

    # Database alias for storing task/worker state.
    # None = auto-configured in-memory SQLite (lost on restart).
    # Set to a DATABASES alias to persist (e.g. "default", "celeryx").
    "DATABASE": None,

    # Maximum age of stored task records in seconds (default 24h).
    "MAX_TASK_AGE": 86400,

    # Maximum number of task records in the database.
    # Oldest records are pruned when this limit is exceeded.
    "MAX_TASK_COUNT": 100_000,

    # Set to False to disable monitoring on this instance.
    # Useful in multi-pod deployments where only one pod should monitor.
    "ADMIN_ENABLED": True,

    # Start the event listener automatically on Django startup.
    "EVENT_LISTENER_AUTOSTART": True,

    # Periodically broadcast enable_events to workers.
    "ENABLE_EVENTS": True,

    # Timeout for celery.control.inspect() calls.
    "INSPECT_TIMEOUT": 1.0,

    # Seconds between htmx live update polls (0 to disable).
    "AUTO_REFRESH_INTERVAL": 3,

    # Visible columns on the task list page.
    "TASK_COLUMNS": [
        "name", "uuid", "state", "worker", "received", "started", "runtime",
    ],

    # Use relative timestamps (e.g. "5 minutes ago") instead of absolute.
    "NATURAL_TIME": False,
}
```

## Database Persistence

By default, django-celeryx stores all state in an auto-configured in-memory SQLite database. This means data is lost on restart. To persist across restarts, configure a database:

```python
# Option 1: Use an explicit database
DATABASES = {
    "default": { ... },
    "celeryx": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "celeryx.sqlite3",
    },
}

CELERYX = {
    "DATABASE": "celeryx",
}

# Required: add the database router
DATABASE_ROUTERS = ["django_celeryx.db_router.CeleryXRouter"]
```

Then run migrations:

```console
python manage.py migrate --database=celeryx
```

## Multi-Pod Deployments

In production, you typically run multiple Django instances. Only one should run the event listener:

```python
# On the monitoring pod:
CELERYX = {
    "ADMIN_ENABLED": True,
    "DATABASE": "celeryx",
}

# On all other pods:
CELERYX = {
    "ADMIN_ENABLED": False,
}
```
