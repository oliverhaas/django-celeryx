# Configuration

All settings are optional and configured via the `CELERYX` dict in your Django settings.

```python
CELERYX = {
    # State limits
    "MAX_TASKS": 100_000,
    "MAX_WORKERS": 5_000,

    # Event listener
    "ENABLE_EVENTS": True,
    "EVENT_LISTENER_AUTOSTART": True,

    # Stream replay on restart
    "STREAM_REPLAY_DEPTH": 10_000,

    # UI
    "AUTO_REFRESH_INTERVAL": 3,
    "TASK_COLUMNS": [
        "name", "uuid", "state", "worker", "received", "started", "runtime",
    ],
    "NATURAL_TIME": False,

    # Worker inspection
    "INSPECT_TIMEOUT": 1.0,

    # Celery app
    "CELERY_APP": None,
}
```
