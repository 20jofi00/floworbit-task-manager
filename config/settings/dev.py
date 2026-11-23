import os

from .base import *

DEBUG = os.getenv("DJANGO_DEBUG", "true").lower() in {"true", "1", "yes"}
ALLOWED_HOSTS = ALLOWED_HOSTS or ["localhost", "127.0.0.1", "[::1]"]
MAILERS = {
    "default": {"BACKEND": "django.core.mail.backends.console.EmailBackend"},
}
