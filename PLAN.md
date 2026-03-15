# django-celeryx Implementation Plan

## Overview

Celery Flower reimagined as a Django admin app. Same event-driven monitoring and worker control, but embedded in Django admin with htmx + Alpine.js for real-time updates. Follows django-cachex project structure and conventions.

## Architecture

```
celery workers → events → Redis Streams (via celery-redis-plus) → django-celeryx event listener thread
                                                                          ↓
                                                                   in-memory state
                                                                          ↓
                                                                   Django admin views (htmx polling / SSE)
                                                                          ↓
                                                               worker control via celery.control
```

**Two data sources** (same as Flower):
1. **Real-time events** via Celery's `EventReceiver` — continuous stream of task and worker events, consumed in a daemon thread
2. **On-demand inspection** via `celery.control.inspect()` — detailed worker stats, queues, config (used for worker detail views)

**In-memory state** — events build up an in-memory representation of tasks and workers. On restart, replay recent Redis Stream history to rebuild state. Bounded by configurable `max_tasks` / `max_workers` limits.

**Real-time UI** — htmx polling or SSE for auto-refreshing task/worker lists. Alpine.js for interactive UI elements (dropdowns, confirmations, tab switching). No React/Vue/npm build step.

---

## Project Structure

```
django-celeryx/
├── django_celeryx/
│   ├── __init__.py                     # Version, re-exports
│   ├── apps.py                         # AppConfig — starts event listener on ready()
│   ├── settings.py                     # Package settings with defaults
│   ├── types.py                        # Type aliases, enums (TaskState, WorkerState)
│   │
│   ├── state/                          # In-memory state management
│   │   ├── __init__.py
│   │   ├── events.py                   # Event listener (daemon thread, EventReceiver)
│   │   ├── tasks.py                    # TaskState — in-memory task store (ring buffer)
│   │   ├── workers.py                  # WorkerState — in-memory worker store
│   │   └── metrics.py                  # Computed metrics (throughput, latency percentiles, rates)
│   │
│   ├── control/                        # Celery control actions
│   │   ├── __init__.py
│   │   ├── tasks.py                    # Revoke, terminate, abort, apply, rate-limit, timeout
│   │   └── workers.py                  # Shutdown, restart pool, grow/shrink, autoscale, add/cancel consumer
│   │
│   ├── admin/                          # Django admin integration
│   │   ├── __init__.py
│   │   ├── apps.py                     # CeleryAdminConfig
│   │   ├── models.py                   # Unmanaged models: Task, Worker, Queue (proxy to in-memory state)
│   │   ├── admin.py                    # TaskAdmin, WorkerAdmin, QueueAdmin
│   │   ├── queryset.py                 # Custom querysets backed by in-memory state
│   │   ├── filters.py                  # Admin filters (state, task name, worker, queue)
│   │   ├── views/                      # Custom admin views
│   │   │   ├── __init__.py
│   │   │   ├── base.py                 # Base view with htmx/Alpine support
│   │   │   ├── dashboard.py            # Metrics dashboard (throughput, latency, rates)
│   │   │   ├── task_detail.py          # Task detail (args, result, traceback, timing)
│   │   │   ├── worker_detail.py        # Worker detail (pool, queues, limits, config, stats)
│   │   │   └── broker.py              # Broker/queue overview
│   │   ├── actions.py                  # Admin actions (revoke selected, terminate selected)
│   │   ├── templates/
│   │   │   └── admin/django_celeryx/
│   │   │       ├── base.html           # Base with htmx + Alpine.js includes
│   │   │       ├── dashboard.html      # Metrics dashboard
│   │   │       ├── task/
│   │   │       │   ├── change_list.html  # Task list (auto-refreshing)
│   │   │       │   └── change_form.html  # Task detail
│   │   │       ├── worker/
│   │   │       │   ├── change_list.html  # Worker list (auto-refreshing)
│   │   │       │   └── change_form.html  # Worker detail (tabbed: pool, queues, limits, config, stats)
│   │   │       ├── queue/
│   │   │       │   └── change_list.html  # Queue list with message counts
│   │   │       └── partials/            # htmx partial templates
│   │   │           ├── task_table.html
│   │   │           ├── worker_table.html
│   │   │           ├── queue_table.html
│   │   │           ├── metrics.html
│   │   │           └── worker_tabs/
│   │   │               ├── pool.html
│   │   │               ├── queues.html
│   │   │               ├── tasks.html
│   │   │               ├── limits.html
│   │   │               ├── config.html
│   │   │               └── stats.html
│   │   ├── urls.py                     # URL patterns for htmx endpoints + custom views
│   │   └── static/
│   │       └── django_celeryx/
│   │           └── css/
│   │               └── styles.css      # Custom admin styling
│   │
│   ├── unfold/                         # django-unfold themed variant
│   │   ├── admin.py
│   │   ├── apps.py
│   │   ├── models.py
│   │   └── templates/
│   │
│   └── py.typed                        # PEP 561 marker
│
├── tests/
│   ├── state/                          # State management tests
│   │   ├── test_events.py
│   │   ├── test_tasks.py
│   │   ├── test_workers.py
│   │   └── test_metrics.py
│   ├── control/                        # Control action tests
│   │   ├── test_task_control.py
│   │   └── test_worker_control.py
│   ├── admin/                          # Admin view tests
│   │   ├── test_task_views.py
│   │   ├── test_worker_views.py
│   │   ├── test_dashboard.py
│   │   ├── test_broker.py
│   │   └── test_actions.py
│   ├── fixtures/
│   │   ├── celery.py                   # Celery app fixtures
│   │   ├── events.py                   # Fake event fixtures
│   │   ├── containers.py              # Testcontainers (Redis)
│   │   └── settings.py
│   ├── settings/
│   │   ├── base.py
│   │   └── urls.py
│   └── conftest.py
│
├── examples/
│   └── simple/
│       ├── example/
│       │   ├── settings.py
│       │   ├── celery.py
│       │   ├── tasks.py               # Sample tasks for demo
│       │   ├── urls.py
│       │   └── wsgi.py
│       ├── manage.py
│       └── docker-compose.yml         # Redis + worker + beat + Django
│
├── docs/
│   ├── index.md
│   ├── getting-started/
│   │   ├── installation.md
│   │   └── quickstart.md
│   ├── user-guide/
│   │   ├── configuration.md
│   │   ├── dashboard.md
│   │   ├── tasks.md
│   │   ├── workers.md
│   │   └── broker.md
│   └── reference/
│       ├── api.md
│       └── changelog.md
│
├── .github/workflows/
│   ├── ci.yml
│   ├── publish.yml
│   ├── docs.yml
│   └── tag.yml
│
├── pyproject.toml
├── .pre-commit-config.yaml
├── mkdocs.yml
├── .gitignore
├── .python-version
├── CLAUDE.md
├── LICENSE
└── README.md
```

---

## Feature Parity with Flower

### Pages / Views

| Flower Page | django-celeryx Equivalent |
|---|---|
| Workers list (`/`) | WorkerAdmin change_list — auto-refreshing table via htmx |
| Worker detail (`/worker/<name>`) | WorkerAdmin change_form — tabbed view (pool, queues, tasks, limits, config, stats) |
| Tasks list (`/tasks`) | TaskAdmin change_list — filterable, searchable, auto-refreshing |
| Task detail (`/task/<uuid>`) | TaskAdmin change_form — all fields, traceback, parent/child links |
| Broker (`/broker`) | QueueAdmin change_list or custom broker view — queue names, message counts |
| Dashboard (not in Flower) | Custom admin view — throughput, latency percentiles, success/failure rates |

### Worker Detail Tabs (matching Flower)

| Tab | Content |
|---|---|
| Pool | Pool type, concurrency, max-tasks-per-child, processes, prefetch count. Controls: grow/shrink pool, set autoscale min/max |
| Queues | Active queues table. Controls: add consumer, cancel consumer |
| Tasks | Processed counts by task name, active/scheduled/reserved/revoked task lists |
| Limits | Per-task rate limits and timeouts. Controls: set rate limit, set soft/hard timeout |
| Config | Full worker Celery configuration key/value table |
| Stats | System resource usage (rusage), broker connection info |

### Control Actions (matching Flower)

| Action | Celery API |
|---|---|
| Revoke task | `celery.control.revoke(task_id)` |
| Terminate task | `celery.control.revoke(task_id, terminate=True, signal=signal)` |
| Abort task | `AbortableAsyncResult(task_id).abort()` |
| Shutdown worker | `celery.control.broadcast('shutdown', destination=[worker])` |
| Restart worker pool | `celery.control.pool_restart(destination=[worker])` |
| Grow pool | `celery.control.pool_grow(n, destination=[worker])` |
| Shrink pool | `celery.control.pool_shrink(n, destination=[worker])` |
| Autoscale | `celery.control.autoscale(max, min, destination=[worker])` |
| Add consumer | `celery.control.add_consumer(queue, destination=[worker])` |
| Cancel consumer | `celery.control.cancel_consumer(queue, destination=[worker])` |
| Set rate limit | `celery.control.rate_limit(task_name, rate, destination=[worker])` |
| Set time limit | `celery.control.time_limit(task_name, soft, hard, destination=[worker])` |
| Apply task | `app.send_task(name, args, kwargs)` |

### Task List Columns

All 17 columns from Flower, configurable which to show:
- name, uuid, state, args, kwargs, result, received, started, runtime, worker, exchange, routing_key, retries, revoked, exception, expires, eta

### Task States (color-coded)

- PENDING (grey), RECEIVED (yellow), STARTED (blue), SUCCESS (green), FAILURE (red), RETRY (orange), REVOKED (purple)

### Search

Structured search matching Flower:
- Free text across name, uuid, state, worker, args, kwargs, result
- Prefix search: `state:FAILURE`, `result:value`, `args:value`, `kwargs:key=value`

---

## Event Handling

### Event Listener Thread

```python
class EventListener(threading.Thread):
    """Daemon thread consuming Celery events via EventReceiver."""
    daemon = True

    def run(self):
        # Connect to broker, consume events
        # On each event: update in-memory state (TaskStore, WorkerStore)
        # Auto-reconnect with exponential backoff
        # Periodically broadcast enable_events to workers
```

### Events Consumed

| Event | Data Captured |
|---|---|
| task-sent | uuid, name, args, kwargs, eta, expires, exchange, routing_key |
| task-received | uuid, hostname (worker) |
| task-started | uuid, hostname, pid |
| task-succeeded | uuid, result, runtime |
| task-failed | uuid, exception, traceback |
| task-retried | uuid, exception, traceback |
| task-revoked | uuid, terminated, signum, expired |
| worker-online | hostname |
| worker-heartbeat | hostname, active, freq, loadavg, sw_ident, sw_ver, sw_sys |
| worker-offline | hostname |

### On Restart

1. Replay recent Redis Stream history (configurable depth)
2. Rebuild in-memory TaskStore and WorkerStore from replayed events
3. Run `celery.control.inspect()` to get current worker state
4. Resume real-time event consumption

---

## Real-Time UI (htmx + Alpine.js)

### htmx Patterns

- **Polling**: Task and worker list tables poll a partial endpoint every N seconds (`hx-trigger="every 3s"`)
- **Partial updates**: htmx endpoints return only the table body HTML, swapped via `hx-swap="innerHTML"`
- **Actions**: Control actions (revoke, terminate, pool grow/shrink) submitted via `hx-post` with confirmation
- **Search**: Task search input with `hx-trigger="keyup changed delay:300ms"` for live filtering

### Alpine.js Patterns

- **Tab switching**: Worker detail tabs managed with Alpine state (`x-show`, `@click`)
- **Confirmations**: Destructive actions (shutdown, terminate) show Alpine modal/dialog before proceeding
- **Dropdowns**: Action menus on worker detail page
- **Auto-refresh toggle**: Alpine toggle to enable/disable htmx polling
- **State badges**: Color-coded task state badges

### No npm/build step

htmx and Alpine.js are included as vendored static files or loaded from CDN (configurable). No JavaScript build pipeline.

---

## Configuration

```python
# settings.py
INSTALLED_APPS = [
    ...,
    "django_celeryx.admin",      # or "django_celeryx.unfold" for unfold theme
]

CELERYX = {
    # State limits
    "MAX_TASKS": 100_000,           # Max tasks in memory (ring buffer)
    "MAX_WORKERS": 5_000,           # Max workers in memory

    # Event listener
    "ENABLE_EVENTS": True,          # Periodically broadcast enable_events to workers
    "EVENT_LISTENER_AUTOSTART": True,  # Start listener on AppConfig.ready()

    # Stream replay on restart
    "STREAM_REPLAY_DEPTH": 10_000,  # How many stream entries to replay on startup

    # UI
    "AUTO_REFRESH_INTERVAL": 3,     # Seconds between htmx polls (0 to disable)
    "TASK_COLUMNS": [               # Visible columns on task list
        "name", "uuid", "state", "worker", "received", "started", "runtime",
    ],
    "NATURAL_TIME": False,          # Relative vs absolute timestamps

    # Worker inspection
    "INSPECT_TIMEOUT": 1.0,         # Seconds for celery.control.inspect() timeout

    # Celery app
    "CELERY_APP": None,             # Dotted path to Celery app (auto-detected if None)
}
```

---

## Unmanaged Models

Like django-cachex, the admin models are **unmanaged** (`managed = False`) — they don't create database tables. Instead, the custom querysets read from the in-memory state.

```python
class Task(models.Model):
    """Proxy model backed by in-memory TaskStore."""
    uuid = models.CharField(max_length=255, primary_key=True)
    name = models.CharField(max_length=255)
    state = models.CharField(max_length=50)
    worker = models.CharField(max_length=255)
    # ... all Flower task fields

    class Meta:
        managed = False

class Worker(models.Model):
    """Proxy model backed by in-memory WorkerStore."""
    hostname = models.CharField(max_length=255, primary_key=True)
    status = models.CharField(max_length=50)
    # ...

    class Meta:
        managed = False

class Queue(models.Model):
    """Proxy model backed by broker queue stats."""
    name = models.CharField(max_length=255, primary_key=True)
    messages = models.IntegerField()
    # ...

    class Meta:
        managed = False
```

---

## Build & Tooling (matching django-cachex)

| Tool | Purpose |
|---|---|
| hatchling | Build backend |
| uv | Package manager, lockfile |
| ruff | Linter + formatter (line length 120, strict mode) |
| mypy + ty | Type checking (django-stubs) |
| pytest | Testing (pytest-django, pytest-cov) |
| testcontainers | Docker Redis for integration tests |
| pre-commit | Hooks (ruff, mypy, taplo, trailing comma) |
| mkdocs-material | Documentation |
| GitHub Actions | CI (Python × Django matrix), publish, docs |

### Python / Django Support

- Python: 3.12+
- Django: 5.2+
- Celery: 5.4+

### Dependencies

- **Required**: Django, celery
- **Optional**: django-unfold (themed admin)

---

## Implementation Phases

### Phase 1: Skeleton + Event Listener + Basic Admin

1. Project skeleton (pyproject.toml, pre-commit, CI, CLAUDE.md)
2. Event listener thread (EventReceiver, auto-reconnect, enable_events broadcast)
3. In-memory TaskStore and WorkerStore (ring buffer, bounded)
4. Unmanaged models + custom querysets
5. Basic TaskAdmin change_list (no htmx yet — just static list with filters)
6. Basic WorkerAdmin change_list
7. AppConfig.ready() to start event listener
8. Settings / configuration

### Phase 2: Full Task & Worker Views

1. Task detail view (all fields, traceback display, parent/child links)
2. Worker detail view with tabs (pool, queues, tasks, limits, config, stats)
3. Task search (structured search: state:, name:, args:, kwargs:, result:)
4. Task list columns configuration
5. Admin filters (state, task name, worker, queue)

### Phase 3: Control Actions

1. Task revoke / terminate / abort (from task detail and bulk admin action)
2. Worker shutdown / pool restart
3. Pool grow / shrink / autoscale
4. Add / cancel consumer
5. Rate limits and time limits
6. Apply task (execute from admin)

### Phase 4: htmx + Alpine.js Real-Time

1. htmx partial endpoints for task and worker tables
2. Polling-based auto-refresh
3. Alpine.js tab switching on worker detail
4. Alpine.js confirmation modals for destructive actions
5. Live search with htmx debounce
6. Auto-refresh toggle

### Phase 5: Metrics Dashboard

1. Computed metrics (throughput, latency percentiles, success/failure rates)
2. Custom admin dashboard view
3. Per-worker and per-task-name breakdowns
4. Time-windowed metrics (last 1m, 5m, 15m, 1h)

### Phase 6: Broker View + Queue Stats

1. Queue list with message counts
2. Broker connection info display
3. Redis-specific queue stats (LLEN)

### Phase 7: Stream Replay + Resilience

1. Redis Stream replay on startup (rebuild state from stream history)
2. Auto-reconnect with exponential backoff
3. Graceful shutdown of event listener thread
4. Health check endpoint

### Phase 8: Polish

1. django-unfold themed variant
2. Example project (docker-compose with Redis + worker + beat + Django)
3. Documentation (mkdocs-material)
4. PyPI publishing workflow
5. Prometheus metrics export (optional, matching Flower's metrics)
