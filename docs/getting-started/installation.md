# Installation

## Requirements

- Python 3.12+
- Django 5.2+
- Celery 5.4+

## Install

```console
pip install django-celeryx
```

For [django-unfold](https://github.com/unfoldadmin/django-unfold) themed admin:

```console
pip install django-celeryx[unfold]
```

## Setup

Add `django_celeryx.admin` to your `INSTALLED_APPS`:

```python
INSTALLED_APPS = [
    # ...
    "django_celeryx.admin",
]
```

For django-unfold, use `django_celeryx.unfold` instead.
