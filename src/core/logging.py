import logging
import sys

from pythonjsonlogger import jsonlogger

from src.core.config import settings

LOG_FORMAT = "[%(asctime)s] [%(levelname)s] [%(name)s] - %(message)s"


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """Custom JSON formatter that adds application context."""

    def add_fields(self, log_record, record, message_dict):
        super().add_fields(log_record, record, message_dict)
        log_record["environment"] = settings.ENVIRONMENT
        log_record["app"] = settings.PROJECT_NAME


def configure_logging():
    """Configure application-wide logging settings with JSON format for production."""

    log_level = logging.WARNING if settings.is_production else logging.INFO

    # Choose formatter based on environment
    if settings.is_production:
        # JSON format for production (easier to parse in log aggregation systems)
        formatter = CustomJsonFormatter(
            "%(timestamp)s %(level)s %(name)s %(message)s",
            rename_fields={"levelname": "level", "asctime": "timestamp"},
        )
    else:
        # Human-readable format for development
        formatter = logging.Formatter(
            fmt=LOG_FORMAT,
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    logging.basicConfig(
        level=log_level,
        handlers=[handler],
        force=True,  # Override any existing configuration
    )

    # Silence noisy loggers
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("google_genai").setLevel(logging.WARNING)
    logging.getLogger("google.genai").setLevel(logging.WARNING)

    # Remove duplicate uvicorn handlers
    logging.getLogger("uvicorn.access").handlers = []
    logging.getLogger("uvicorn.error").handlers = []

    api_logger = logging.getLogger("api_logger")
    api_logger.setLevel(log_level)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with proper level configuration.

    Args:
        name: Logger name (usually __name__)

    Returns:
        Logger instance
    """
    logger = logging.getLogger(name)

    # Set level for this logger (propagates to root handler)
    # Child loggers inherit handlers from root, so we only need to set level
    logger.setLevel(logging.DEBUG if not settings.is_production else logging.INFO)

    return logger
