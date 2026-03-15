"""
Example project app configuration.

This AppConfig sends sample Celery tasks on Django startup so the
admin has data to display immediately.
See startup.py for the task dispatching logic.
"""

# ruff: noqa: T201
# T201: print statements are intentional for visibility
# BLE001: broad exception catching is intentional for robustness

import os

from django.apps import AppConfig


class ExampleConfig(AppConfig):
    """App configuration that sends sample tasks on startup."""

    name = "example"
    verbose_name = "Example Project"

    def ready(self) -> None:
        """
        Called when Django starts up.

        We send sample Celery tasks here so the admin immediately has
        data to display. Only runs in the main process to avoid
        running twice during auto-reload.
        """
        # Only run in the reloader child process (the one that actually serves)
        if os.environ.get("RUN_MAIN") == "true":
            from example.startup import send_sample_tasks

            try:
                send_sample_tasks()
            except Exception as e:
                # Don't crash on startup if task dispatching fails
                print(f"Warning: Failed to send sample tasks: {e}")
