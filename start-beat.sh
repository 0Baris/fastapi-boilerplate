#!/bin/sh

set -e

python wait_for_db.py

# Cloud Run service template requires an HTTP listener; beat is a background
# process. scripts/beat_health.py exposes a tiny no-op HTTP responder on $PORT
# and spawns the actual `celery beat` as a child process.
exec python scripts/beat_health.py
