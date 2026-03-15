"""
Example project startup task dispatching.

Sends a batch of sample Celery tasks on Django startup so the admin
has data to display immediately. This runs every time the dev server
starts (or reloads), which is fine — it just adds more tasks to the
in-memory state for demonstration.

The logic is intentionally verbose so developers can see what's happening.
"""

# ruff: noqa: T201
# T201: print statements are intentional for visibility
# BLE001: broad exception catching is intentional for robustness


def send_sample_tasks() -> None:
    """Send a batch of sample tasks to the Celery worker."""
    from example.celery import app

    print("\n" + "=" * 60)
    print("CELERYX STARTUP: Sending sample tasks")
    print("=" * 60)

    sent = 0

    # Arithmetic tasks
    for i in range(3):
        try:
            app.send_task("example.tasks.add", args=[i, i + 1])
            sent += 1
        except Exception as e:
            print(f"  Warning: Failed to send add task: {e}")
            return  # If broker is down, no point sending more

    for i in range(2):
        try:
            app.send_task("example.tasks.multiply", args=[i + 1, 10])
            sent += 1
        except Exception as e:
            print(f"  Warning: Failed to send multiply task: {e}")

    # Slow task
    try:
        app.send_task("example.tasks.slow_task", args=[2])
        sent += 1
    except Exception:
        pass

    # Failing task (to show FAILURE state in admin)
    try:
        app.send_task("example.tasks.failing_task")
        sent += 1
    except Exception:
        pass

    # Random tasks (mix of success and failure)
    for _ in range(3):
        try:
            app.send_task("example.tasks.random_task")
            sent += 1
        except Exception:
            pass

    print(f"  Sent {sent} sample tasks")
    print("=" * 60)
    print("CELERYX STARTUP: Complete")
    print("=" * 60 + "\n")
