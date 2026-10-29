#!/bin/bash
# Vercel Build Script for AUGIS Django
echo "--> Ensuring output directory exists..."
mkdir -p staticfiles_build/static

echo "--> Installing dependencies from requirements.txt..."
python3 -m pip install -r requirements.txt --break-system-packages

echo "--> Collecting static files..."
python3 manage.py collectstatic --noinput --clear

if [ -n "$DATABASE_URL" ]; then
    echo "--> Running cloud database migrations..."
    python3 manage.py migrate --noinput || true
    echo "--> Seeding institutions, bureaus, and accounts..."
    python3 manage.py seed_augis_demo || true
fi

echo "--> Build complete!"
