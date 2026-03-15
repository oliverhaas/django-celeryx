#!/usr/bin/env bash
set -e

cd "$(dirname "$0")"
VENV="../../.venv/bin/activate"

case "${1:-}" in
    setup)
        echo "Starting Redis..."
        docker compose up -d 2>/dev/null || echo "Redis may already be running"
        sleep 2

        echo "Running migrations..."
        source "$VENV" && python manage.py migrate --verbosity=0

        echo "Creating admin user (admin/password)..."
        source "$VENV" && DJANGO_SUPERUSER_PASSWORD=password python manage.py createsuperuser \
            --username=admin --email=admin@example.com --noinput 2>/dev/null || true

        echo ""
        echo "Setup complete! Run './run.sh server' to start."
        ;;

    server|run)
        echo "Starting Django at http://127.0.0.1:8000/admin/django_celeryx/"
        echo "Login: admin / password"
        echo ""
        echo "Note: Start a worker in another terminal with './run.sh worker'"
        echo ""
        source "$VENV" && python manage.py runserver
        ;;

    worker)
        echo "Starting 2 Celery workers with events..."
        echo ""
        source "$VENV" && celery -A example worker -l info -E --concurrency=2 -n worker1@%h &
        source "$VENV" && celery -A example worker -l info -E --concurrency=1 -n worker2@%h &
        wait
        ;;

    send-tasks)
        source "$VENV" && python manage.py shell -c "
from example.celery import app

print('Sending tasks...')
print('')

# Arithmetic tasks
for i in range(5):
    r = app.send_task('example.tasks.add', args=[i, i+1])
    print(f'  add({i}, {i+1}) -> {r.id[:8]}')

for i in range(3):
    r = app.send_task('example.tasks.multiply', args=[i, 10])
    print(f'  multiply({i}, 10) -> {r.id[:8]}')

# Slow task
r = app.send_task('example.tasks.slow_task', args=[3])
print(f'  slow_task(3) -> {r.id[:8]}')

# Failing task
r = app.send_task('example.tasks.failing_task')
print(f'  failing_task() -> {r.id[:8]}')

# Random tasks
for i in range(5):
    r = app.send_task('example.tasks.random_task')
    print(f'  random_task() -> {r.id[:8]}')

print('')
print('Done! Check the admin to see tasks appear in real time.')
"
        ;;

    shell)
        source "$VENV" && python manage.py shell
        ;;

    stop)
        docker compose down
        ;;

    clean)
        docker compose down -v 2>/dev/null || true
        rm -f db.sqlite3
        echo "Cleaned up."
        ;;

    *)
        echo "Usage: ./run.sh <command>"
        echo ""
        echo "Commands:"
        echo "  setup      Start Redis, run migrations, create admin user"
        echo "  server     Start the Django development server"
        echo "  worker     Start the Celery worker (run in a separate terminal)"
        echo "  send-tasks Send sample Celery tasks"
        echo "  shell      Open Django shell"
        echo "  stop       Stop Redis container"
        echo "  clean      Stop Redis and remove database"
        ;;
esac
