#!/bin/bash
# Vercel Build Script for AUGIS Django
echo "--> Installing dependencies from requirements.txt..."
python3 -m pip install -r requirements.txt

echo "--> Collecting static files..."
python3 manage.py collectstatic --noinput --clear

echo "--> Build complete!"
