from django.apps import AppConfig


class CeleryAdminConfig(AppConfig):
    """Django app configuration for the Celery admin interface.

    On ready():
    - Enables WAL mode for SQLite databases (reduces locking)
    - Starts the event listener thread (if ADMIN_ENABLED)
    """

    name = "django_celeryx.admin"
    label = "django_celeryx"
    verbose_name = "django-celeryx"

    def ready(self):
        self._enable_sqlite_wal()

        from django_celeryx.settings import celeryx_settings

        if not celeryx_settings.ADMIN_ENABLED:
            return

        from django_celeryx.state.persistence import ensure_tables

        ensure_tables()

        if celeryx_settings.EVENT_LISTENER_AUTOSTART:
            from django_celeryx.state.events import start_event_listener

            start_event_listener()

    @staticmethod
    def _enable_sqlite_wal():
        """Enable WAL journal mode and busy_timeout for SQLite databases.

        WAL allows concurrent readers with one writer. busy_timeout makes
        writers wait instead of raising 'database is locked' immediately.
        """
        from django.db.backends.signals import connection_created

        def _set_sqlite_pragmas(sender, connection, **kwargs):
            if connection.vendor == "sqlite":
                cursor = connection.cursor()
                cursor.execute("PRAGMA journal_mode=WAL;")
                cursor.execute("PRAGMA busy_timeout=5000;")  # 5s wait on lock

        connection_created.connect(_set_sqlite_pragmas)
