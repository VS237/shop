#!/usr/bin/env bash
# exit on error
set -o errexit

# 1. Install dependencies
pip install -r requirements.txt

# 2. Collect Static Files (This creates the 'staticfiles' folder)
python manage.py collectstatic --noinput

# 3. Apply any database migrations
python manage.py migrate