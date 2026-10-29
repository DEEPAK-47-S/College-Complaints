import os
from pathlib import Path
from dotenv import load_dotenv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Load environment variables from .env file
load_dotenv(BASE_DIR / '.env')

# Quick-start development settings - unsuitable for production
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'augis-default-secret-key-aicte-2026')

DEBUG = os.getenv('DEBUG', 'True').lower() in ('true', '1')

ALLOWED_HOSTS = [host.strip() for host in os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1,[::1],testserver').split(',') if host.strip()]
if 'testserver' not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append('testserver')

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'whitenoise.runserver_nostatic',
    'django.contrib.staticfiles',

    # AUGIS Modular Monolith Apps
    'apps.accounts.apps.AccountsConfig',
    'apps.bureaus.apps.BureausConfig',
    'apps.institutions.apps.InstitutionsConfig',
    'apps.complaints.apps.ComplaintsConfig',
    'apps.workflows.apps.WorkflowsConfig',
    'apps.intelligence.apps.IntelligenceConfig',
    'apps.coordination.apps.CoordinationConfig',
    'apps.notifications.apps.NotificationsConfig',
    'apps.dashboard.apps.DashboardConfig',
    'apps.reports.apps.ReportsConfig',
    'apps.audit.apps.AuditConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'apps.audit.middleware.AuditCorrelationMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            str(BASE_DIR / 'templates'),
            BASE_DIR / 'templates',
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'apps.notifications.context_processors.unread_notifications_count',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'

# Database configuration
# PostgreSQL default if DATABASE_URL or POSTGRES_DB is provided, otherwise robust SQLite for local testing
DATABASE_URL = os.getenv('DATABASE_URL')
if DATABASE_URL:
    try:
        import dj_database_url
        db_config = dj_database_url.config(
            default=DATABASE_URL,
            conn_max_age=600,
            conn_health_checks=True,
            ssl_require=True
        )
        db_config['DISABLE_SERVER_SIDE_CURSORS'] = True
        DATABASES = {
            'default': db_config
        }
    except ImportError:
        import urllib.parse as urlparse
        url = urlparse.urlparse(DATABASE_URL)
        DATABASES = {
            'default': {
                'ENGINE': 'django.db.backends.postgresql',
                'NAME': urlparse.unquote(url.path[1:]),
                'USER': urlparse.unquote(url.username or ''),
                'PASSWORD': urlparse.unquote(url.password or ''),
                'HOST': url.hostname,
                'PORT': url.port or '5432',
                'OPTIONS': {
                    'sslmode': 'require',
                },
                'DISABLE_SERVER_SIDE_CURSORS': True,
            }
        }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# Custom User Model (Mandatory before initial migrations)
AUTH_USER_MODEL = 'accounts.User'

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {'min_length': 8},
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Authentication URLs
LOGIN_URL = 'accounts:login'
LOGIN_REDIRECT_URL = 'dashboard:index'
LOGOUT_REDIRECT_URL = 'accounts:login'

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kolkata'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'static_collected'

STORAGES = {
    'default': {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
    },
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
    },
}

# Private Media Storage (Document Scrutiny Vault)
MEDIA_URL = '/media_private/'
MEDIA_ROOT = BASE_DIR / 'media_private'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Security Settings
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
X_FRAME_OPTIONS = 'DENY'

# AUGIS Intelligence Engine Settings
SIMILARITY_THRESHOLD = float(os.getenv('SIMILARITY_THRESHOLD', '0.65'))
USE_SENTENCE_TRANSFORMERS = os.getenv('USE_SENTENCE_TRANSFORMERS', 'True').lower() in ('true', '1')
TRANSFORMER_MODEL_NAME = os.getenv('TRANSFORMER_MODEL_NAME', 'all-MiniLM-L6-v2')

# Google Gemini AI Integration (Google AI Studio)
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')
GEMINI_MODEL = os.getenv('GEMINI_MODEL', 'gemini-2.5-flash')

# Email & 2FA OTP Configuration (Gmail SMTP & Development Console)
EMAIL_BACKEND = os.getenv(
    'EMAIL_BACKEND',
    'django.core.mail.backends.smtp.EmailBackend' if os.getenv('EMAIL_HOST_USER') else 'django.core.mail.backends.console.EmailBackend'
)
EMAIL_HOST = os.getenv('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', '587'))
EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'True').lower() in ('true', '1')
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', 'AICTE AUGIS Portal <augis.aicte.portal@gmail.com>')
AUTH_2FA_ENABLED = os.getenv('AUTH_2FA_ENABLED', 'True').lower() in ('true', '1')

