import logging
import time
import uuid

from fastapi import Request, Response
from starlette.middleware.base import (
    BaseHTTPMiddleware,
    RequestResponseEndpoint,
)

logger = logging.getLogger("api_logger")


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        start_time: int | float = time.time()
        request_id: str = str(uuid.uuid4())

        try:
            response = await call_next(request)
            process_time = time.time() - start_time

            logger.info(
                f"RID={request_id} | {request.method} {request.url.path} |"
                f"Status={response.status_code} | Time={process_time:.3f}s"
            )

            response.headers["X-Process-Time"] = str(process_time)
            response.headers["X-Request-ID"] = request_id

            return response
        except Exception as e:
            process_time = time.time() - start_time
            logger.error(
                f"RID={request_id} | {request.method} {request.url.path} | "
                f"Failed | Time={process_time:.3f}s | Error={e!s}"
            )
            raise e
