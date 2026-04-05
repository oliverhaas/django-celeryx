# Broker

The broker view shows queue information from connected workers.

## Queue List

- Queue name
- Exchange name
- Routing key
- Consumer count (number of workers consuming from this queue)

Queue data is fetched via `celery.control.inspect().active_queues()`.
