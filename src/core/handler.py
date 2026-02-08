from logging import Logger
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import HTTPException, RequestValidationError
from fastapi.responses import JSONResponse
from jwt import ExpiredSignatureError, InvalidTokenError

from src.core.exception import AppValueError, BaseAppError
from src.core.logging import get_logger

logger: Logger = get_logger(__name__)


def init(app: FastAPI):
    def _result(status_code: int, detail: Any, _type: str = "Error", headers: dict | None = None):
        logger.debug({status_code, detail, _type})
        content = {
            "type": _type,
            "error": detail,
        }
        return JSONResponse(
            status_code=status_code,
            content=content,
            headers=headers or {"X-Error": _type},
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(_request: Request, exc: HTTPException):
        logger.debug(f"HTTPException handler caught: {type(exc).__name__} - {exc.detail}")
        return _result(exc.status_code, str(exc.detail), headers=exc.headers)  # ty:ignore[invalid-argument-type]

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(_request: Request, exc: RequestValidationError):
        errors = exc.errors()
        messages = []
        for error in errors:
            field = ".".join(str(loc) for loc in error.get("loc", [])[1:])
            msg = error.get("msg", "Validation error")
            if field:
                messages.append(f"{msg}")
            else:
                messages.append(msg)
        return _result(status.HTTP_422_UNPROCESSABLE_CONTENT, "; ".join(messages), "ValidationError")

    @app.exception_handler(ExpiredSignatureError)
    async def jwt_expired_handler(_request: Request, _exc: ExpiredSignatureError):
        return _result(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Your session has expired. Please log in again.",
            _type="AuthenticationError",
            headers={"WWW-Authenticate": "Bearer"},
        )

    @app.exception_handler(InvalidTokenError)
    async def jwt_invalid_handler(_request: Request, _exc: InvalidTokenError):
        return _result(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token. Please log in again.",
            _type="AuthenticationError",
            headers={"WWW-Authenticate": "Bearer"},
        )

    @app.exception_handler(ValueError)
    async def builtin_value_error_handler(_request: Request, exc: ValueError):
        return _result(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc), _type="ValueError")

    @app.exception_handler(AppValueError)
    async def app_value_error_handler(_request: Request, exc: AppValueError):
        return _result(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.message, _type="ValueError")

    @app.exception_handler(BaseAppError)
    async def app_exception_handler(_request: Request, exc: BaseAppError):
        logger.debug(f"BaseAppError handler caught: {type(exc).__name__} - {exc.message}")
        return _result(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.message, _type=exc.__class__.__name__)

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: HTTPException):
        logger.error(
            f"Unhandled exception: {type(exc).__name__}: {exc!s}",
            exc_info=True,
            extra={
                "request_path": str(request.url.path),
                "request_method": request.method,
                "exception_type": type(exc).__name__,
            },
        )

        return _result(status.HTTP_500_INTERNAL_SERVER_ERROR, "Internal server error", "InternalServerError")
