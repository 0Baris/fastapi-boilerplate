#!/bin/sh

set -e

echo "Checking database connection..."
python wait_for_db.py

# Migrations are NOT run here — they run as a dedicated step (start-migrate.sh /
# the Cloud Run migrate Job, or a one-shot `migrate` compose service) so the api
# never races the worker/beat on schema changes.

echo "Starting the application with Gunicorn..."
exec gunicorn api:app \
    -w "${GUNICORN_WORKERS:-2}" \
    -k uvicorn.workers.UvicornWorker \
    -b "0.0.0.0:${PORT:-8000}" \
    --graceful-timeout 25 \
    --timeout 30 \
    --access-logfile - \
    --error-logfile -
