# django-celeryx Comprehensive Code Review

Thorough review of the entire package for production-readiness.

---

## Security Vulnerabilities

### 1. XSS via task/worker names in dashboard JSON

**Severity: HIGH** | `django_celeryx/admin/templates/admin/django_celeryx/dashboard/change_list.html:183-187`

The dashboard template embeds chart data using `{{ chartjs_throughput|safe }}` inside a `<script type="application/json">` tag. The data originates from `json.dumps()` in `dashboard.py`, which does **not** escape `</script>`. A malicious task name like `</script><script>alert(1)</script>` would break out of the JSON block and execute arbitrary JavaScript in every admin user's browser.

**Fix:** Pass chart data through the template context as a single escaped JSON blob, or use Django's `json_script` template tag, or call `json.dumps(...).replace("</", "<\\/")` before passing to the template.

### 2. No permission separation for destructive control actions

**Severity: MEDIUM** | `django_celeryx/admin/views/task_detail.py`, `worker_detail.py`

Any admin user with **view** permission on Task/Worker can:
- Revoke/terminate tasks
- Shutdown workers
- Restart worker pools
- Change rate limits and time limits

There is no separate permission check for write/control actions. The `change_view` only checks `has_view_or_change_permission` before delegating to views that accept destructive POSTs.

**Fix:** Add a custom permission (e.g., `control_task`, `control_worker`) and check it before processing POST actions.

### 3. CDN dependencies without fallback or vendored copies

**Severity: MEDIUM** | `change_list.html:6-9`, `dashboard/change_list.html:6`

HTMX, idiomorph, and Chart.js are loaded from external CDNs (unpkg.com, jsdelivr.net). The idiomorph tag also lacks SRI (Subresource Integrity). For a production monitoring tool:
- CDN outage = broken live updates and dashboard
- No SRI on idiomorph = supply chain risk

**Fix:** Vendor static assets into the package's `static/` directory, or at minimum add SRI hashes to all CDN script tags.

---

## Bugs

### 4. `order_by` sorts numeric fields as strings

`django_celeryx/admin/queryset.py:154`

```python
clone._data.sort(key=lambda t: str(getattr(t, bare, "") or ""), reverse=reverse)
```

Fields like `received`, `started`, and `runtime` are floats but sorted as strings. This means `"9.0" > "10.0"` in string comparison, producing wrong sort order.

**Fix:** Use numeric comparison for float fields:
```python
if bare in ("received", "started", "runtime"):
    clone._data.sort(key=lambda t: getattr(t, bare) or 0.0, reverse=reverse)
```

### 5. Dashboard throughput chart makes N individual DB queries per bin

`django_celeryx/admin/views/dashboard.py:28-35`

`_get_throughput` executes one aggregation query **per time bin** (24 for "today", 56 for "7d", 60 for "30d"). This is extremely inefficient -- 60 queries for the 30-day view.

**Fix:** Use a single query with Django's `TruncHour`/`TruncDay` or manual epoch-based binning with conditional aggregation.

### 6. `ENABLE_EVENTS` setting is defined but never used

`django_celeryx/settings.py:45` vs `django_celeryx/state/events.py:184`

The `ENABLE_EVENTS` setting exists in `CeleryXSettings` but `_consume_events` always broadcasts `enable_events()` unconditionally. Users who set `ENABLE_EVENTS = False` would expect events to not be broadcast.

**Fix:** Check `celeryx_settings.ENABLE_EVENTS` before calling `app.control.enable_events()`.

### 7. `persist_worker_event` allows empty strings to overwrite existing values

`django_celeryx/state/persistence.py:60`

```python
clean = {k: v for k, v in fields.items() if hasattr(WorkerState, k) and v is not None}
```

Unlike `persist_task_event` (line 34) which filters `v != ""`, the worker version does not filter empty strings. An event with `sw_ident=""` would overwrite a previously set value.

**Fix:** Add `and v != ""` for string fields, matching `persist_task_event`'s behavior.

### 8. Task detail template doesn't display retried/revoked timestamps

`django_celeryx/admin/views/task_detail.py:91-92` and `task/change_form.html`

The view computes `retried_fmt` and `revoked_fmt` and passes them in context, but the template **never renders them**. The Timing fieldset only shows received, started, succeeded, and failed.

**Fix:** Add `{% if retried_fmt %}` and `{% if revoked_fmt %}` blocks to the template.

### 9. Test expects SVG charts but dashboard uses Chart.js (canvas)

`tests/admin/test_views.py:334,342`

```python
def test_dashboard_has_svg_charts(self, admin_client):
    ...
    assert "<svg" in content  # Will fail: Chart.js uses <canvas>, not <svg>
```

Also, `TestDashboardView` docstring (line 312) references "Pygal charts" which was the old charting library.

**Fix:** Change assertion to `assert "<canvas" in content` and update the docstring.

### 10. No stale worker cleanup mechanism

`django_celeryx/state/persistence.py`

`cleanup_old_tasks()` exists but there is no `cleanup_old_workers()`. Workers that go offline and never come back remain in the database forever, cluttering the worker list.

**Fix:** Add `cleanup_old_workers()` that removes workers whose `last_heartbeat` exceeds a configurable threshold.

### 11. `TaskState.state` field has no default value

`django_celeryx/db_models.py:18`

```python
state = models.CharField(max_length=50, db_index=True)  # no default!
```

If `persist_task_event` is ever called without a state (edge case), the `create()` call will fail with a database error.

**Fix:** Add `default=""` or `default="PENDING"`.

### 12. `_format_timestamp` treats `0.0` as no-timestamp

`django_celeryx/admin/queryset.py:37`

```python
if not ts:  # 0.0 is falsy!
    return "-"
```

While epoch 0 is unlikely, the correct check is `if ts is None`.

### 13. `TaskQuerySet.order_by` only applies first field, ignores rest

`django_celeryx/admin/queryset.py:155`

The `break` statement means `order_by("-received", "name")` only sorts by `received`, silently ignoring `name`. Django's ChangeList may pass multiple fields.

---

## Inconsistencies

### 14. Two copies of admin code (admin vs unfold)

`django_celeryx/admin/admin.py` vs `django_celeryx/unfold/admin.py`

The unfold admin is a near-complete copy of the regular admin. Bugfixes must be applied in both places. The dashboard filters (DashboardPeriodFilter, etc.) are likely duplicated too.

**Fix:** Extract shared logic into the existing mixins, and have both admin modules use them. The unfold admin should only differ in the base class.

### 15. `_tasks_from_db` copies fields one-by-one manually

`django_celeryx/admin/queryset.py:80-99`

Fields are copied from `TaskState` to `Task` line by line. Adding a new field requires updating this function, `db_models.py`, and `admin/models.py` separately. Same issue with `_workers_from_db`.

**Fix:** Use a loop over shared field names, or use `model_to_dict`, or have Task/Worker accept a TaskState/WorkerState in a class method.

### 16. `_tasks_from_db` hardcodes limit of 1000

`django_celeryx/admin/queryset.py:79`

The task list is hardcoded to fetch at most 1000 tasks. This limit is not configurable and not documented. With `list_per_page = 50`, you get max 20 pages of history.

**Fix:** Make this configurable via a setting (e.g., `MAX_TASKS_IN_ADMIN`), or at least document the limitation.

### 17. Dashboard "today" means "last 24 hours", not "since midnight"

`django_celeryx/admin/admin.py:211-215` and `dashboard.py:11`

`DashboardPeriodFilter` and `_PERIOD_CONFIG` both use `86400` seconds for "today", meaning "last 24 hours" rather than "since midnight today". The label "Today" is misleading.

**Fix:** Either rename to "Last 24h" or calculate from midnight: `datetime.combine(date.today(), time.min, tzinfo=UTC)`.

### 18. `_format_timestamp` non-natural mode only shows time, not date

`django_celeryx/admin/queryset.py:55`

```python
return format_html("<code>{}</code>", dt.strftime("%H:%M:%S"))
```

When viewing tasks from yesterday, the timestamp shows only `"14:32:01"` with no date. Users can't distinguish between today's and yesterday's tasks.

**Fix:** Show date when task is not from today: `"%Y-%m-%d %H:%M:%S"` or at least `"%m-%d %H:%M:%S"`.

### 19. Badge rendering duplicated in 3 places

- `django_celeryx/admin/queryset.py:298-304` (TaskAdminMixin.state_display)
- `django_celeryx/admin/views/task_detail.py:25-32` (_state_badge)
- `django_celeryx/admin/templatetags/celeryx_tags.py:18-27` (task_state_badge)

The same badge HTML is rendered in three separate functions with identical logic.

**Fix:** Consolidate into a single helper function, or always use the template tag.

### 20. Inconsistent `_get_db()` helper duplication

`_get_db()` is defined in both `persistence.py:15` and `queryset.py:29` with identical implementations.

**Fix:** Import from a single location.

---

## Missing Features / Production Readiness

### 21. No tests for control module

`tests/control/` directory contains only `__init__.py`. The `revoke_task`, `abort_task`, `apply_task`, `set_rate_limit`, `set_time_limit`, `shutdown_worker`, `pool_restart`, `pool_grow`, `pool_shrink`, `autoscale`, `add_consumer`, `cancel_consumer` functions have zero test coverage.

### 22. No tests for event listener (`state/events.py`)

The `EventListener` thread, `_handle_task_event`, `_handle_worker_event` functions, backoff logic, and cleanup scheduling have no tests.

### 23. No tests for dashboard chart computation

`dashboard.py` functions `_get_throughput`, `_chart_slowest`, `_chart_failure_rate`, `_chart_worker_load`, `compute_dashboard_context` have no dedicated unit tests. The view test only checks HTTP 200 and one stat value.

### 24. No tests for template tags

`celeryx_tags.py` template tags (`task_state_badge`, `worker_status_badge`, `format_uptime`) have no tests.

### 25. No test for worker detail POST actions

Worker detail POST actions (pool_grow, pool_shrink, shutdown, autoscale, add_consumer, cancel_consumer, rate_limit, time_limit) have no tests.

### 26. Missing input validation on worker control forms

`django_celeryx/admin/views/worker_detail.py:67-75`

```python
n = int(post.get("n", 1))  # No upper bound validation
```

Pool grow/shrink, autoscale min/max have no validation beyond `int()` conversion. A user could enter negative numbers or extremely large values.

**Fix:** Validate ranges (e.g., 1-100 for grow/shrink, sensible bounds for autoscale).

### 27. `_enrich_workers` calls `inspect()` on every page load

`django_celeryx/admin/queryset.py:384-405`

Every time the worker list is loaded, `inspect().stats()` is called for ALL workers. This is a blocking network call with `INSPECT_TIMEOUT` (default 1s). With many workers or slow broker, this blocks the admin view.

**Fix:** Cache inspect results briefly (e.g., 5-10 seconds), or make enrichment optional/lazy.

### 28. `ensure_tables()` runs full migrations on every startup

`django_celeryx/state/persistence.py:104-112`

`call_command("migrate", ...)` runs on every Django startup via `ready()`. For production deployments, this is unnecessary overhead and could cause issues with migration locks on shared databases.

**Fix:** Check if tables exist first (e.g., `connection.introspection.table_names()`), only migrate if needed.

### 29. Event listener errors logged at DEBUG level only

`django_celeryx/state/persistence.py:44,70,100,112`

All persistence and migration errors are logged at `debug` level. In production, these errors would be invisible unless DEBUG logging is enabled. Database connection failures would be silently swallowed.

**Fix:** Use `logger.warning` or `logger.error` for persistence failures, keep `debug` only for expected/benign cases.

### 30. No graceful degradation when Celery broker is unavailable

Multiple views call `inspect()` and will hang for `INSPECT_TIMEOUT` seconds if the broker is down. The Queue and RegisteredTask views are entirely dependent on `inspect()`.

**Fix:** Add a cached "broker available" check, or show a clear error message when the broker is unreachable instead of silently returning empty lists.

### 31. `apply_task` doesn't support common Celery send options

`django_celeryx/control/tasks.py:29-34` and `apply_task.py`

The "Send Task" form only supports `args` and `kwargs`. Common options like `countdown`, `eta`, `queue`, `routing_key`, `priority`, `expires` are not available.

### 32. No export/download functionality for task data

There's no way to export task history as CSV/JSON from the admin interface.

### 33. No way to manually clear/purge task history from the UI

No admin action to clear old task records or purge all data.

---

## Code Quality / Simplifications

### 34. `_FakeQuery` is repeated conceptually but could be shared better

`django_celeryx/admin/queryset.py:60-64`

The fake query object is shared via a class, but each QuerySet creates a new instance. Since it's stateless, a single module-level instance would suffice.

### 35. Four nearly identical QuerySet classes

`TaskQuerySet`, `WorkerQuerySet`, `QueueQuerySet`, `RegisteredTaskQuerySet` all implement the same interface with minor differences. A generic base class would reduce ~200 lines of duplication.

### 36. `type("", (), {"verbose_name": "django-celeryx"})()` hack for opts

`task_detail.py:85`, `worker_detail.py:189`, `apply_task.py:94`

Creating anonymous classes for template context is fragile. If Django admin templates change their expectations for `opts`, these break silently.

**Fix:** Use the actual model's `_meta` object or create a proper named class.

### 37. `_workers_from_db` loads ALL workers with no limit

Unlike `_tasks_from_db` which limits to 1000, workers have no limit. Deployments with thousands of historical workers would load them all into memory.

### 38. Dashboard context computed twice on filter views

`DashboardAdmin.changelist_view` builds a filtered queryset and computes context. But the parent `LiveUpdateMixin.changelist_view` also runs, and ChangeList also processes filters. The filter logic runs twice with different querysets.

### 39. `_LazySettings._load` is not thread-safe

`django_celeryx/settings.py:100-103`

Multiple threads could race on `_settings is None`, both calling `_get_settings()`. While benign (same result), it's technically incorrect for a component used in a multi-threaded event listener.

---

## Documentation Issues

### 40. Test docstring references "Pygal" (removed library)

`tests/admin/test_views.py:312`: `"""Tests for the dashboard view with Pygal charts."""` -- should reference Chart.js.

### 41. `apps.py` root module docstring says "not used directly" but gives no error

`django_celeryx/apps.py`

If a user adds `'django_celeryx'` to `INSTALLED_APPS` instead of `'django_celeryx.admin'`, they get no error -- just no admin interface and no event listener. This is a silent misconfiguration.

**Fix:** Add a warning in the root AppConfig's `ready()` if it detects it was loaded directly.

### 42. Default in-memory SQLite not prominently documented as ephemeral

The default database configuration uses `:memory:` SQLite, meaning all monitoring data is lost on every restart. This should be clearly called out in getting-started docs and settings.

---

## Summary TODO List

- [ ] **SECURITY: Fix XSS in dashboard JSON template** - escape `</script>` in chart data
- [ ] **SECURITY: Add permission checks for control actions** - separate view vs control permissions
- [ ] **SECURITY: Vendor or add SRI to all CDN scripts** - htmx, idiomorph, Chart.js
- [ ] **BUG: Fix numeric field sorting** - sort floats as floats, not strings
- [ ] **BUG: Fix throughput chart N+1 query** - single aggregation query instead of per-bin
- [ ] **BUG: Honor `ENABLE_EVENTS` setting** - check before broadcasting
- [ ] **BUG: Fix `persist_worker_event` empty string handling** - match task event filtering
- [ ] **BUG: Add retried/revoked timestamps to task detail template**
- [ ] **BUG: Fix SVG test assertion** - change to canvas, update docstring from Pygal to Chart.js
- [ ] **BUG: Add stale worker cleanup** - configurable heartbeat timeout
- [ ] **BUG: Add default for `TaskState.state` field**
- [ ] **BUG: Fix `_format_timestamp` falsy check** - use `is None` instead of `not ts`
- [ ] **BUG: Support multi-field `order_by`** - remove `break` statement
- [ ] **CONSISTENCY: DRY unfold admin** - extract shared logic, unfold only overrides base class
- [ ] **CONSISTENCY: DRY field copying** - eliminate manual field-by-field Task/Worker construction
- [ ] **CONSISTENCY: Make task list limit configurable** - setting instead of hardcoded 1000
- [ ] **CONSISTENCY: Fix "today" to mean today** - or rename to "Last 24h"
- [ ] **CONSISTENCY: Show date in timestamps** - not just time
- [ ] **CONSISTENCY: DRY badge rendering** - consolidate 3 identical implementations
- [ ] **CONSISTENCY: DRY `_get_db()` helper** - single definition
- [ ] **TESTS: Add control module tests** - revoke, apply, rate_limit, etc.
- [ ] **TESTS: Add event listener tests** - handlers, backoff, cleanup scheduling
- [ ] **TESTS: Add dashboard computation tests** - throughput, slowest, failure rate
- [ ] **TESTS: Add template tag tests** - badge rendering, uptime formatting
- [ ] **TESTS: Add worker detail POST action tests** - all control actions
- [ ] **QUALITY: Validate worker control form inputs** - bounds checking on pool_grow/shrink
- [ ] **QUALITY: Cache `inspect()` results** - avoid blocking on every page load
- [ ] **QUALITY: Only run migrations when needed** - check tables exist first
- [ ] **QUALITY: Raise log level for persistence errors** - warning/error, not debug
- [ ] **QUALITY: Graceful broker-unavailable handling** - clear UI feedback
- [ ] **FEATURE: Support more Celery send options** - countdown, eta, queue, priority
- [ ] **FEATURE: Task data export** - CSV/JSON download
- [ ] **FEATURE: UI purge action** - clear task history from admin
- [ ] **QUALITY: Extract generic QuerySet base class** - reduce 200+ lines of duplication
- [ ] **QUALITY: Use model `_meta` for opts context** - replace anonymous class hack
- [ ] **QUALITY: Limit workers loaded from DB** - add cap like tasks
- [ ] **QUALITY: Thread-safe `_LazySettings._load`** - add lock
- [ ] **DOCS: Fix Pygal reference in test docstring**
- [ ] **DOCS: Warn on root AppConfig direct usage** - add startup check
- [ ] **DOCS: Prominently document ephemeral default storage**
