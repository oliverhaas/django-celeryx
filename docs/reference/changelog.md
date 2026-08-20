# Changelog

## 0.1.0a3

### Security

- Control actions now require the `change` permission. Custom admin views only
  ran through `AdminSite.admin_view()`, which checks `is_staff` and nothing else,
  so any staff user could revoke tasks, shut down workers, and send new tasks.
  Task and Worker gained a `change` permission; `view` is monitoring-only.
- Fix stored XSS on the dashboard. Chart data was rendered with `|safe`, so a
  task name or worker hostname containing `</script>` could inject markup. The
  data now goes through the `json_script` filter.

### Fixed

- The event listener stopped reconnecting after the first broker failure. The
  flush timer shared the listener's stop event, so shutting it down also
  cancelled the reconnect loop.
- The unfold app shipped no migrations and could not find its templates, so
  `migrate django_celeryx` failed and every page raised `TemplateDoesNotExist`.
- The unfold dashboard raised `AlreadyRegistered` by importing the standard
  admin module for its filters. The filters moved to `admin/filters.py`.
- Detail views passed a hand-built dict as `opts`, which broke unfold template
  tags that read `opts.app_label` in Python. They pass the model `_meta` now.
- `override_settings(CELERYX=...)` left the cached settings dataclass in place.
  A `setting_changed` receiver now invalidates it.
- `get_db_alias()` no longer rebuilds the settings dataclass on every database
  access.
- The stand-in querysets silently ignored unsupported `filter()` lookups and
  returned unfiltered rows. They raise `NotImplementedError` instead.
- Task and worker list queries are capped at 1000 rows with a warning, instead
  of loading the whole table into memory.

### Added

- `AUTO_MIGRATE` setting to control the startup migration.
- CI runs mypy and ty on publish, and the unfold test job is enabled again.
- Tests for the event listener, worker and task control, permission
  enforcement, and dashboard escaping. Coverage 67% to 78%.
- API reference documents the public symbols instead of a bare module dump.

### Changed

- Update dev dependencies (mypy 2.3.1, ruff 0.16.4, ty 0.0.73, pytest 9.1.1,
  django-stubs 6.1.0, and others). prometheus-client is now a dev dependency, so
  the metrics tests actually run.
- Document the permission model, the security caveats around task arguments,
  and the unauthenticated metrics endpoint.

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
