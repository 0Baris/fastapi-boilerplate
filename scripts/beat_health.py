"""Cloud Run beat sidecar — HTTP no-op + celery beat subprocess.

Cloud Run requires every service container to bind a port and answer HTTP
probes, but `celery beat` is a long-running scheduler with no built-in HTTP
surface. This module:

  1. Spawns `celery -A src.core.celery beat` as a child process.
  2. Serves a minimal HTTP responder on $PORT that returns 200 for /health/live
     and /health/ready (alive only — readiness reflects whether the child is
     still running).
  3. Propagates SIGTERM/SIGINT to the child so Cloud Run revision rollover is
     clean (graceful_timeout window).

The HTTP server intentionally has zero dependencies on FastAPI / SQLAlchemy /
Redis — beat must boot before any of those, and a heavy import would defeat
the cold-start health window.
"""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from types import FrameType

PORT = int(os.environ.get("PORT", "8000"))

_beat_proc: subprocess.Popen[bytes] | None = None


class _HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path in {"/health/live", "/health/ready", "/"}:
            alive = _beat_proc is not None and _beat_proc.poll() is None
            status = 200 if alive else 503
            self.send_response(status)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"ok" if alive else b"beat-down")
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
    if _beat_proc and _beat_proc.poll() is None:
        _beat_proc.send_signal(signum)


def main() -> int:
    global _beat_proc

    # --schedule under /tmp: the image runs as a non-root user and cannot write
    # the default celerybeat-schedule shelf in the working dir (/app). /tmp is
    # writable; the schedule is ephemeral state, safe to lose on restart since
    # beat_schedule is statically defined in src/core/celery.py.
    _beat_proc = subprocess.Popen(
        [
            "celery",
            "-A",
            "src.core.celery",
            "beat",
            "-l",
            "info",
            "--schedule",
            "/tmp/celerybeat-schedule",
            "--pidfile",
            "",
        ]
    )

    signal.signal(signal.SIGTERM, _forward_signal)
    signal.signal(signal.SIGINT, _forward_signal)

    health_thread = threading.Thread(target=_serve_health, daemon=True)
    health_thread.start()

    return _beat_proc.wait()


if __name__ == "__main__":
    sys.exit(main())
