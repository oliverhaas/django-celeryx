# Tasks

The task list provides a real-time view of all Celery tasks.

## Task List

Auto-refreshing table showing tasks with configurable columns:

- name, uuid, state, args, kwargs, result
- received, started, runtime
- worker, exchange, routing_key
- retries, revoked, exception, expires, eta

## Task States

Color-coded states: PENDING, RECEIVED, STARTED, SUCCESS, FAILURE, RETRY, REVOKED.

## Search

Structured search with prefix support:

- Free text across all fields
- `state:FAILURE` — Filter by state
- `result:value` — Search results
- `args:value` — Search arguments
- `kwargs:key=value` — Search keyword arguments

## Actions

- **Revoke** — Cancel a pending task
- **Terminate** — Kill a running task
- **Abort** — Abort an abortable task
