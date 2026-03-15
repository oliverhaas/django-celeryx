"""Base Django settings for tests."""

SECRET_KEY = "django_tests_secret_key"

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.messages",
    "django.contrib.sessions",
    "django_celeryx.admin",
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    },
}

ROOT_URLCONF = "tests.settings.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

MIDDLEWARE = [
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
]

USE_TZ = False

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# Celery configuration for tests
CELERY_BROKER_URL = "redis://127.0.0.1:6379/0"

# Disable event listener autostart in tests
CELERYX = {
    "EVENT_LISTENER_AUTOSTART": False,
}
