#!/bin/sh

set -e

# Cloud Run service template requires an HTTP listener; the worker is a
# background consumer. scripts/worker_health.py opens a no-op HTTP responder on
# $PORT *first*, then waits for the DB and spawns `celery worker` as a child —
# this ordering keeps the Cloud Run startup probe satisfied while the DB wait
# is still in progress. Worker flags (threads pool, concurrency, gossip/mingle
# off, max-tasks-per-child) live inside the wrapper.
exec python scripts/worker_health.py
