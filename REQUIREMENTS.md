# django-celeryx — Requirements & Feature Goals

## What is this?

Celery Flower reimagined as a Django admin app. Same monitoring and management capabilities, but embedded in your existing Django admin — no separate process, no separate auth, no separate port.

## Core Principles

1. **Flower feature parity** — match Flower's exact layout, columns, and capabilities, just restyled for Django admin
2. **Database as single source of truth** — all event data persisted to a configurable database (in-memory SQLite by default, or any Django database)
3. **Zero extra infrastructure** — runs inside your Django process, uses your existing admin auth
4. **Celery + celery-asyncio compatibility** — works with both via optional dependencies

## Must-Have Features (Flower Parity)

### List Views

- **Workers list**: hostname, status (online/offline badge), active tasks, processed, succeeded, failed, retried, load average
- **Tasks list**: name, UUID, state (color badge), worker, received, started, runtime — configurable via `CELERYX.TASK_COLUMNS`
- **Queues list**: name, exchange, routing key, consumer count
- **Registered Tasks list**: task name, link to filtered task list

### Detail Views

- **Task detail**: UUID, name, state badge, worker (linked), args, kwargs, result, exception, traceback, timing (received/started/succeeded/failed/runtime/ETA/expires), routing (exchange, routing key, retries), related tasks (parent/root links)
- **Worker detail** (tabbed, matching Flower):
  - **Pool**: type, concurrency, max-tasks-per-child, prefetch count, processes, timeouts. Controls: grow, shrink, autoscale, restart pool, shutdown worker
  - **Queues**: active queues table. Controls: add consumer, cancel consumer
  - **Tasks**: processed counts by task name, active/scheduled/reserved/revoked task lists
  - **Limits**: rate limit and time limit controls per task type
  - **Config**: full worker configuration key/value table
  - **Stats**: PID, uptime, clock, resource usage (rusage), broker connection info

### Control Actions

- **Task**: revoke, terminate (with signal), abort (AbortableAsyncResult)
- **Worker**: shutdown, pool restart, pool grow/shrink, autoscale, add/cancel consumer
- **Bulk**: revoke selected, terminate selected (via admin actions)
- **Task execution**: send task by name with args/kwargs

### Real-Time Updates

- htmx-based auto-refresh on list views (configurable interval via `CELERYX.AUTO_REFRESH_INTERVAL`)
- Live toggle button (off by default, state via query param `?live=on`)
- Morphing swap (idiomorph) to preserve scroll position and form state

### Filters & Search

- Task list filters: state, task name (from DB distinct values), worker
- Worker list filter: status (online/offline)
- Free text search across all visible fields (standard Django admin search box)

## Architecture

### Event Listener

- Daemon thread consuming Celery events via `EventReceiver`
- Handles: task-sent, task-received, task-started, task-succeeded, task-failed, task-retried, task-revoked, task-rejected, worker-online, worker-heartbeat, worker-offline
- Exponential backoff reconnection (1s → 60s)
- Periodic `enable_events` broadcast (every 60s)
- Periodic cleanup of old events (every hour, configurable via `MAX_EVENT_AGE`)

### Database Persistence

- Managed models: `TaskEvent`, `WorkerEvent` — actual DB tables
- Unmanaged models: `Task`, `Worker`, `Queue`, `RegisteredTask` — display-only, populated from DB/inspect()
- Database router (`CeleryXRouter`) for isolating to a dedicated database
- Auto-configured in-memory SQLite when no `DATABASE` setting provided
- User must explicitly set `DATABASE` to use a named database (no silent default to `"default"`)

### Configuration

All settings under `CELERYX = {...}` in Django settings:

| Setting | Default | Description |
|---|---|---|
| `CELERY_APP` | auto-detect | Dotted path to Celery app instance |
| `DATABASE` | `None` (in-memory SQLite) | Django DATABASES alias |
| `MAX_EVENT_AGE` | `86400` (24h) | Seconds before old events are cleaned up |
| `MAX_TASKS` | `100_000` | Max task events in database |
| `ADMIN_ENABLED` | `True` | Enable/disable admin and event listener |
| `EVENT_LISTENER_AUTOSTART` | `True` | Auto-start event listener on app ready |
| `ENABLE_EVENTS` | `True` | Broadcast enable_events to workers |
| `INSPECT_TIMEOUT` | `1.0` | Timeout for celery.control.inspect() calls |
| `AUTO_REFRESH_INTERVAL` | `3` | Seconds between htmx auto-refresh polls |
| `TASK_COLUMNS` | `[name, uuid, state, worker, received, started, runtime]` | Columns shown in task list |
| `NATURAL_TIME` | `False` | Use relative timestamps ("2m ago") |

### Indexing (million-task scale)

- `TaskEvent`: composite indexes on (worker, state), (name, state), (-updated_at); unique on uuid
- `WorkerEvent`: unique on hostname, indexed on updated_at

## Nice-to-Have (Post-MVP)

- **Dashboard/metrics view**: throughput, latency percentiles, success/failure rates, per-worker/per-task breakdowns
- **Prometheus metrics endpoint**: `/metrics` compatible with Prometheus scraping
- **REST API**: GET endpoints for tasks, workers, queues (for external integrations)
- **Unfold theme**: full unfold-themed variant (basic implementation exists)
- **Batch write optimization**: configurable debounce/batching for high-throughput event writes
- **WebSocket/SSE**: replace htmx polling with push-based updates

## Compatibility

- Python 3.12+
- Django 5.2+ (including 6.0)
- Celery 5.4+ (via `django-celeryx[celery]`)
- celery-asyncio 6.0+ (via `django-celeryx[celery-asyncio]`)
- Unfold 0.70+ (via `django-celeryx[unfold]`)
