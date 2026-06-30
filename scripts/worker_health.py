"""Cloud Run worker sidecar — HTTP no-op + celery worker subprocess.

Cloud Run requires every service container to bind a port and answer HTTP
probes, but `celery worker` is a long-running consumer with no built-in HTTP
surface. This module:

  1. Serves a minimal HTTP responder on $PORT *first* so Cloud Run's startup
     probe sees an open port immediately — before the (potentially slow) DB
     readiness wait. /health/live always returns 200 once the port is open;
     /health/ready reflects whether the worker child is running.
  2. Waits for the database to become reachable.
  3. Spawns `celery -A src.core.celery worker` as a child process.
  4. Propagates SIGTERM/SIGINT to the child so Cloud Run revision rollover is
     clean (graceful_timeout window).

The HTTP server intentionally has zero dependencies on FastAPI / SQLAlchemy /
Redis at import time — the listener must come up before any heavy import so the
cold-start health window is never missed.
"""

from __future__ import annotations

import asyncio
import os
import signal
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from types import FrameType

# Invoked as `python scripts/worker_health.py`, so sys.path[0] is scripts/, not
# the app root — add the parent dir so `wait_for_db` and `src.*` import cleanly.
_APP_ROOT = str(Path(__file__).resolve().parent.parent)
if _APP_ROOT not in sys.path:
    sys.path.insert(0, _APP_ROOT)

PORT = int(os.environ.get("PORT", "8000"))
CONCURRENCY = os.environ.get("CELERY_CONCURRENCY", "2")

_worker_proc: subprocess.Popen[bytes] | None = None


class _HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path in {"/health/live", "/"}:
            # Liveness only needs the listener up — return 200 even while the
            # worker is still waiting on the database during startup.
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"ok")
            return
        if self.path == "/health/ready":
            alive = _worker_proc is not None and _worker_proc.poll() is None
            status = 200 if alive else 503
            self.send_response(status)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"ok" if alive else b"worker-down")
            return
        self.send_response(404)
        self.end_headers()

    def log_message(self, format: str, *args: object) -> None:
        # Silence default access log spam — Cloud Run probes are noisy.
        return


def _serve_health() -> None:
    server = HTTPServer(("0.0.0.0", PORT), _HealthHandler)
    server.serve_forever()


def _forward_signal(signum: int, _frame: FrameType | None) -> None:
    if _worker_proc and _worker_proc.poll() is None:
        _worker_proc.send_signal(signum)


def main() -> int:
    global _worker_proc

    # 1. Open the health port FIRST so Cloud Run's startup probe succeeds even
    #    while the DB wait below is still in progress.
    health_thread = threading.Thread(target=_serve_health, daemon=True)
    health_thread.start()

    # 2. Wait for the database. Imported here (not at module top) to keep the
    #    cold-start health window free of SQLAlchemy/Connector import cost.
    from wait_for_db import wait_for_database

    if not asyncio.run(wait_for_database(max_retries=10, retry_interval=2)):
        print("worker_health: database never became ready; exiting", file=sys.stderr)
        return 1

    # 3. Spawn the worker. Threads pool: the Cloud SQL Python Connector is not
    #    fork-safe — keep one event loop per process.
    _worker_proc = subprocess.Popen(
        [
            "celery",
            "-A",
            "src.core.celery",
            "worker",
            "-l",
            "info",
            "-c",
            CONCURRENCY,
            "--without-gossip",
            "--without-mingle",
            "--max-tasks-per-child",
            "100",
            "--pool=threads",
        ]
    )

    signal.signal(signal.SIGTERM, _forward_signal)
    signal.signal(signal.SIGINT, _forward_signal)

    return _worker_proc.wait()


if __name__ == "__main__":
    sys.exit(main())
