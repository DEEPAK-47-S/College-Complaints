from .base import *

DEBUG = True

# In local development, avoid static manifest strictness if assets are actively edited
STORAGES = {
    'default': {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
    },
    'staticfiles': {
        'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage',
    },
}

# Allow local console email backend
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
