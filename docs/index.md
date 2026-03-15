# Django CeleryX

Celery monitoring and management for Django admin. Like Flower, but embedded in your Django admin with htmx + Alpine.js for real-time updates.

## Features

- **Real-time task monitoring** — Live task list with state, args, result, timing
- **Worker management** — View worker status, pool info, queues, config
- **Control actions** — Revoke/terminate tasks, shutdown/restart workers, manage pools and queues
- **Metrics dashboard** — Throughput, latency percentiles, success/failure rates
- **Broker overview** — Queue names and message counts
- **Django admin native** — Looks and feels like Django admin, no separate service
- **No npm/build step** — htmx + Alpine.js included as static files

## Quick Start

```python
INSTALLED_APPS = [
    # ...
    "django_celeryx.admin",
]
```

That's it. Start your Django server and navigate to the admin to see your Celery tasks and workers.
