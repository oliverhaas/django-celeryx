"""Send sample tasks to Celery workers for testing the celeryx admin."""

import random

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Send sample tasks to Celery for testing django-celeryx"

    def add_arguments(self, parser):
        parser.add_argument(
            "-n",
            "--count",
            type=int,
            default=100,
            help="Number of tasks to send (default: 100)",
        )
        parser.add_argument(
            "--slow",
            action="store_true",
            help="Include slow tasks (1-5s each)",
        )

    def handle(self, *args, **options):
        from example.celery import app

        count = options["count"]
        include_slow = options["slow"]

        # Distribution: 60% add, 15% multiply, 10% failing, 10% random, 5% slow
        with app.pool.acquire(block=True) as conn:
            sent = 0
            for i in range(int(count * 0.6)):
                app.send_task("example.tasks.add", args=[i, i + 1], connection=conn)
                sent += 1
            for i in range(int(count * 0.15)):
                app.send_task("example.tasks.multiply", args=[i + 1, 10], connection=conn)
                sent += 1
            for _ in range(int(count * 0.1)):
                app.send_task("example.tasks.failing_task", connection=conn)
                sent += 1
            for _ in range(int(count * 0.1)):
                app.send_task("example.tasks.random_task", connection=conn)
                sent += 1
            if include_slow:
                for _ in range(int(count * 0.05)):
                    app.send_task(
                        "example.tasks.slow_task",
                        args=[random.randint(1, 5)],
                        connection=conn,
                    )
                    sent += 1

        self.stdout.write(self.style.SUCCESS(f"Sent {sent} tasks"))
