"""Reuse the migration history of django_celeryx.admin.

Both apps use the label "django_celeryx" and the same models, so only one can
be installed and they must share one migration history. Django looks up
migrations by app *name*, not label, so point this package at the admin app's
migration directory instead of duplicating the files.
"""

from django_celeryx.admin import migrations as _admin_migrations

__path__ = list(_admin_migrations.__path__)
