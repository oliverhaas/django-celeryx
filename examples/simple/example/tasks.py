"""Sample tasks for demo."""

import random
import time

from celery import shared_task


@shared_task
def add(x, y):
    """Add two numbers."""
    return x + y


@shared_task
def multiply(x, y):
    """Multiply two numbers."""
    return x * y


@shared_task
def slow_task(duration=5):
    """A task that takes a while."""
    time.sleep(duration)
    return f"Completed after {duration}s"


@shared_task
def failing_task():
    """A task that always fails."""
    msg = "This task always fails"
    raise ValueError(msg)


@shared_task
def random_task():
    """A task with random behavior."""
    duration = random.uniform(0.1, 3.0)
    time.sleep(duration)
    if random.random() < 0.2:
        msg = "Random failure"
        raise RuntimeError(msg)
    return f"Done in {duration:.2f}s"
