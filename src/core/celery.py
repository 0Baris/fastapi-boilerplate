from celery import Celery
from celery.schedules import crontab

from src.core.config import settings

celery_app: Celery = Celery("celery_worker", broker=settings.REDIS_URL, backend=settings.REDIS_URL)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_default_retry_delay=60,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
)

# Celery Beat Schedule
celery_app.conf.beat_schedule = {
    "cleanup-expired-tokens-daily": {
        "task": "tasks.cleanup_expired_tokens",
        "schedule": crontab(hour=2, minute=0),  # Run daily at 2 AM
        "options": {
            "expires": 3600,
        },
    },
    "generate-daily-report": {
        "task": "tasks.generate_daily_report",
        "schedule": crontab(hour=0, minute=30),  # Run daily at 12:30 AM
        "options": {
            "expires": 3600,
        },
    },
}

# Auto-discover tasks from modules
celery_app.autodiscover_tasks(["src.core", "src.modules.auth"])
