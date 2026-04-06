# Changelog

## 0.1.0a2

- Production-ready audit: fix type errors, config alignment, documentation accuracy
- Fix `retried` timestamp silently dropped (field name mismatch with DB model)
- Fix `ENABLE_EVENTS` setting not being checked before broadcasting
- Fix `persist_worker_event` allowing empty strings to overwrite values
- Fix `_format_timestamp` treating `0.0` as no-data
- Fix `order_by` ignoring multi-field sort and sorting numeric fields as strings
- Fix Prometheus metrics dropping `runtime=0.0` events
- Fix signal handler accumulating duplicates (add `dispatch_uid`)
- Fix unfold `LiveUpdateMixin` not stripping `live` param from request
- Fix unfold `DashboardAdmin` loading full table, missing `LiveUpdateMixin` and `show_facets`
- Validate `CELERY_APP` dotted path, warn on unknown settings keys
- Thread-safe `_LazySettings` with double-checked locking
- Update dev dependencies (django-stubs 6.0.2, mypy 1.20, ruff 0.15.9, ty 0.0.29)
- Fix documentation: "in-memory SQLite" → "dedicated SQLite file", accurate dashboard/broker docs
- Document `PROMETHEUS_PREFIX` setting
- Remove stale planning docs

## 0.1.0a1

- Initial alpha release
- Event-driven task and worker monitoring
- Django admin integration with unmanaged models
- Real-time UI with htmx + idiomorph
- Worker control actions
- Metrics dashboard
- Prometheus metrics endpoint
- Configurable metric prefix (`PROMETHEUS_PREFIX`)
