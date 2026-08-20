# API Reference

Most of django-celeryx is used through the Django admin rather than imported.
These are the pieces you may want to call directly.

## Settings

::: django_celeryx.settings.CeleryXSettings

::: django_celeryx.settings.get_db_alias

## Task control

::: django_celeryx.control.tasks

## Worker control

::: django_celeryx.control.workers

## Event listener

::: django_celeryx.state.events.start_event_listener

::: django_celeryx.state.events.stop_event_listener

## Persistence

::: django_celeryx.state.persistence.cleanup_old_tasks

::: django_celeryx.state.persistence.ensure_tables

## Metrics

::: django_celeryx.metrics.metrics_view
