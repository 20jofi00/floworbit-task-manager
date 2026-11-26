import os

from django.core.exceptions import ImproperlyConfigured

from .base import *

if DEBUG:
    raise ImproperlyConfigured("DJANGO_DEBUG must be false in production")
if not ALLOWED_HOSTS:
    raise ImproperlyConfigured("Set DJANGO_ALLOWED_HOSTS before starting production")
if (
    len(SECRET_KEY) < 50
    or len(set(SECRET_KEY)) < 5
    or SECRET_KEY.startswith("django-insecure-")
):
    raise ImproperlyConfigured("Production requires a strong random DJANGO_SECRET_KEY")

SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = int(os.getenv("DJANGO_HSTS_SECONDS", "3600"))
SECURE_HSTS_INCLUDE_SUBDOMAINS = (
    os.getenv("DJANGO_HSTS_INCLUDE_SUBDOMAINS", "false").lower() == "true"
)
SECURE_HSTS_PRELOAD = os.getenv("DJANGO_HSTS_PRELOAD", "false").lower() == "true"

# Enable only when the trusted proxy removes incoming X-Forwarded-Proto headers.
if os.getenv("DJANGO_TRUST_PROXY_HEADERS", "false").lower() == "true":
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

MAILERS = {
    "default": {
        "BACKEND": "django.core.mail.backends.smtp.EmailBackend",
        "OPTIONS": {
            "host": os.getenv("DJANGO_EMAIL_HOST", "localhost"),
            "port": int(os.getenv("DJANGO_EMAIL_PORT", "587")),
            "username": os.getenv("DJANGO_EMAIL_HOST_USER", ""),
            "password": os.getenv("DJANGO_EMAIL_HOST_PASSWORD", ""),
            "use_tls": os.getenv("DJANGO_EMAIL_USE_TLS", "true").lower() == "true",
            "use_ssl": os.getenv("DJANGO_EMAIL_USE_SSL", "false").lower() == "true",
            "timeout": 10,
        },
    },
}
DEFAULT_FROM_EMAIL = os.getenv("DJANGO_DEFAULT_FROM_EMAIL", "webmaster@localhost")


MIDDLEWARE = MIDDLEWARE.copy()
MIDDLEWARE.insert(1, "whitenoise.middleware.WhiteNoiseMiddleware")

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}
