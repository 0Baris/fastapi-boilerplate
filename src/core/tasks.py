"""
Example Celery tasks.

This module contains example background tasks that can be executed asynchronously using Celery.
"""

from src.core.celery import celery_app
from src.core.logging import get_logger

logger = get_logger(__name__)


@celery_app.task(name="tasks.send_welcome_email")
def send_welcome_email(user_email: str, user_name: str) -> dict[str, str]:
    """
    Send welcome email to new user.

    Args:
        user_email: User's email address
        user_name: User's name

    Returns:
        Dictionary with status and message
    """
    logger.info(f"Sending welcome email to {user_name} at {user_email}")

    # TODO: Implement actual email sending logic
    # Example:
    # email_service.send_template_email(
    #     to=user_email,
    #     template="welcome",
    #     context={"name": user_name}
    # )

    logger.info(f"Welcome email sent successfully to {user_email}")
    return {"status": "success", "message": f"Email sent to {user_email}"}


@celery_app.task(name="tasks.cleanup_expired_tokens")
def cleanup_expired_tokens() -> dict[str, int]:
    """
    Cleanup expired refresh tokens from database.

    This task should be run periodically (e.g., daily) to remove expired tokens.

    Returns:
        Dictionary with count of deleted tokens
    """
    logger.info("Starting cleanup of expired tokens")

    # TODO: Implement actual cleanup logic
    # Example:
    # from src.modules.auth.repository import RefreshTokenRepository
    # deleted_count = await RefreshTokenRepository.delete_expired()

    deleted_count = 0
    logger.info(f"Cleanup completed. Removed {deleted_count} expired tokens")
    return {"deleted_count": deleted_count}


@celery_app.task(name="tasks.generate_daily_report")
def generate_daily_report() -> dict[str, str]:
    """
    Generate daily usage report.

    This task runs daily and generates a report of system usage.

    Returns:
        Dictionary with report status
    """
    logger.info("Generating daily report")

    # TODO: Implement report generation logic
    # Example:
    # report_service.generate_report(
    #     start_date=yesterday,
    #     end_date=today,
    #     metrics=["active_users", "api_calls", "errors"]
    # )

    logger.info("Daily report generated successfully")
    return {"status": "success", "report_date": "2026-02-09"}


@celery_app.task(name="tasks.process_file_upload", bind=True, max_retries=3)
def process_file_upload(self, file_url: str, user_id: str) -> dict[str, str]:
    """
    Process uploaded file (resize image, extract metadata, etc).

    Args:
        self: Celery task instance (auto-injected when bind=True)
        file_url: URL of uploaded file
        user_id: ID of user who uploaded the file

    Returns:
        Dictionary with processing status
    """
    try:
        logger.info(f"Processing file upload: {file_url} for user {user_id}")

        # TODO: Implement file processing logic
        # Example:
        # storage_service.download_file(file_url)
        # image_service.resize_and_optimize(file_path)
        # metadata = extract_metadata(file_path)
        # storage_service.upload_processed_file(processed_file)

        logger.info(f"File processed successfully: {file_url}")
        return {"status": "success", "file_url": file_url}

    except Exception as exc:
        # Retry with exponential backoff
        logger.error(f"Error processing file {file_url}: {exc}")
        raise self.retry(exc=exc, countdown=60 * (2**self.request.retries))


@celery_app.task(name="tasks.send_notification")
def send_notification(user_id: str, title: str, message: str, notification_type: str = "info") -> dict[str, str]:
    """
    Send push notification to user.

    Args:
        user_id: User ID
        title: Notification title
        message: Notification message
        notification_type: Type of notification (info, warning, error, success)

    Returns:
        Dictionary with send status
    """
    logger.info(f"Sending {notification_type} notification to user {user_id}: {title} - {message}")

    # TODO: Implement push notification logic
    # Example:
    # fcm_service.send_notification(
    #     user_id=user_id,
    #     title=title,
    #     body=message,
    #     data={"type": notification_type}
    # )

    logger.info(f"Notification sent successfully to user {user_id}")
    return {"status": "success", "user_id": user_id}
