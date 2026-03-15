# Workers

The worker list shows all active Celery workers with their status.

## Worker Detail Tabs

- **Pool** — Pool type, concurrency, processes. Controls: grow/shrink, autoscale
- **Queues** — Active queues. Controls: add/cancel consumer
- **Tasks** — Processed counts, active/scheduled/reserved/revoked tasks
- **Limits** — Rate limits and timeouts. Controls: set rate limit, set timeout
- **Config** — Full worker Celery configuration
- **Stats** — System resource usage, broker connection info

## Control Actions

- Shutdown worker
- Restart worker pool
- Grow/shrink pool
- Set autoscale limits
- Add/cancel queue consumer
- Set rate limits and time limits
