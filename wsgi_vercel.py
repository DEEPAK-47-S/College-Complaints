"""
Vercel Serverless WSGI Adapter for AUGIS
Exposes Django WSGI callable as `app` for Vercel's Python runtime.
"""
import os
import sys

# Add project root to sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.production')

from django.core.wsgi import get_wsgi_application

app = get_wsgi_application()
