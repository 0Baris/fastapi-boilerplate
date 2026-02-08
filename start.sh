#!/bin/sh

set -e

echo "Checking database connection..."
python wait_for_db.py

echo "Running database migrations..."
alembic upgrade head

echo "Starting the application with Gunicorn..."
exec gunicorn api:app \
    -w 4 \
    -k uvicorn.workers.UvicornWorker \
    -b 0.0.0.0:8000 \
    --access-logfile - \
    --error-logfile -
