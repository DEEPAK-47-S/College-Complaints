from .base import *
from django.core.exceptions import ImproperlyConfigured

DEBUG = False

# Production security: fail startup if SECRET_KEY is missing or using default
raw_secret = os.getenv('DJANGO_SECRET_KEY')
if not raw_secret or raw_secret == 'augis-default-secret-key-aicte-2026':
    raise ImproperlyConfigured(
        "DJANGO_SECRET_KEY environment variable is mandatory and must not use default fallback in production."
    )
SECRET_KEY = raw_secret

ALLOWED_HOSTS = [h.strip() for h in os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1,.vercel.app').split(',') if h.strip()]
if '.vercel.app' not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append('.vercel.app')

CSRF_TRUSTED_ORIGINS = [
    'https://*.vercel.app',
    'http://localhost:8000',
    'http://127.0.0.1:8000'
]
custom_csrf = os.getenv('CSRF_TRUSTED_ORIGINS', '')
if custom_csrf:
    CSRF_TRUSTED_ORIGINS.extend([o.strip() for o in custom_csrf.split(',') if o.strip()])

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True

STORAGES = {
    'default': {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
    },
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedStaticFilesStorage',
    },
}

