import base64
import json
import logging
import uuid
from datetime import timedelta
from typing import BinaryIO

from fastapi.concurrency import run_in_threadpool
from google.cloud import storage as gcs_storage
from google.oauth2 import service_account

from src.core.config import settings

logger: logging.Logger = logging.getLogger(__name__)


class StorageService:
    def __init__(self):
        self.public_bucket_name: str = settings.PUBLIC_BUCKET_NAME
        self.private_bucket_name: str = settings.PRIVATE_BUCKET_NAME
        self._client = None

    @property
    def client(self):
        """Lazily initialize the GCS client."""
        if self._client is None:
            base64_creds = settings.GOOGLE_APPLICATION_CREDENTIALS_BASE64

            if base64_creds:
                decoded_json = ""
                try:
                    decoded_bytes = base64.b64decode(base64_creds)
                    decoded_json = decoded_bytes.decode("utf-8")

                    creds_dict = json.loads(decoded_json)
                    credentials = service_account.Credentials.from_service_account_info(creds_dict)
                    self._client = gcs_storage.Client(
                        credentials=credentials,
                        project=creds_dict.get("project_id"),
                    )
                    logger.info("GCS: Authenticated using Base64 credentials")
                except Exception as e:
                    if isinstance(e, json.JSONDecodeError):
                        logger.error(f"Invalid JSON in GCS credentials: {e}")
                        logger.error(f"Decoded string preview (first 200 chars): {decoded_json[:200]}")
                        raise ValueError(f"GCS credentials contain invalid JSON: {e}")
                    else:
                        logger.error(f"Failed to initialize GCS client: {e}")
                        raise ValueError(f"GCS credentials error: {e}")
            else:
                logger.warning("GOOGLE_APPLICATION_CREDENTIALS_BASE64 not set, GCS client not initialized")
                raise ValueError("GCS credentials not configured")

        return self._client

    def _upload_sync(self, file_obj: BinaryIO, object_name: str, content_type: str, bucket_name: str) -> str:
        """Upload a file to GCS synchronously.

        Args:
            file_obj: File object to upload
            object_name: Path/name in bucket
            content_type: MIME type
            bucket_name: Target bucket name

        Returns:
            Full GCS URL of uploaded file
        """
        try:
            logger.info(f"Uploading: bucket={bucket_name}, key={object_name}")

            file_obj.seek(0)

            bucket = self.client.bucket(bucket_name)
            blob = bucket.blob(object_name)

            blob.upload_from_file(
                file_obj,
                content_type=content_type,
            )
            url = f"https://storage.googleapis.com/{bucket_name}/{object_name}"
            logger.info(f"Upload successful: {url}")
            return url

        except Exception as e:
            logger.error(f"Upload error: {type(e).__name__}: {e}", exc_info=True)
            raise Exception(f"Storage upload failed: {e}")

    async def upload_file(
        self,
        file_obj: BinaryIO,
        filename: str,
        content_type: str,
        folder: str = "avatars",
        use_private: bool = False,
    ) -> str:
        """Upload a file to GCS and return its URL.

        Args:
            file_obj: File to upload
            filename: Original filename
            content_type: MIME type
            folder: Folder path in bucket
            use_private: If True, upload to private bucket, else public bucket

        Returns:
            Full GCS URL of uploaded file
        """
        extension: str = filename.split(".")[-1] if "." in filename else "jpg"
        unique_name = f"{folder}/{uuid.uuid4()}.{extension}"

        bucket_name = self.private_bucket_name if use_private else self.public_bucket_name

        url: str = await run_in_threadpool(self._upload_sync, file_obj, unique_name, content_type, bucket_name)
        return url

    async def delete_file(self, file_url: str):
        """Delete a file from GCS given its URL.

        Automatically detects which bucket the file is in from the URL.
        """
        try:
            # Try to extract bucket name from URL
            if self.private_bucket_name in file_url:
                bucket_name = self.private_bucket_name
                object_name = file_url.split(f"{self.private_bucket_name}/")[-1]
            elif self.public_bucket_name in file_url:
                bucket_name = self.public_bucket_name
                object_name = file_url.split(f"{self.public_bucket_name}/")[-1]
            else:
                logger.error(f"Could not determine bucket from URL: {file_url}")
                return

            bucket = self.client.bucket(bucket_name)
            blob = bucket.blob(object_name)
            await run_in_threadpool(blob.delete)
            logger.info(f"Deleted file: {object_name} from {bucket_name}")
        except Exception as e:
            logger.error(f"Delete error: {e}")

    def _generate_signed_url_sync(self, object_name: str, bucket_name: str, expiration_minutes: int) -> str:
        """Generate a signed URL synchronously.

        Args:
            object_name: Path/name in bucket
            bucket_name: Bucket name
            expiration_minutes: URL validity duration

        Returns:
            Signed URL with temporary access token
        """
        try:
            bucket = self.client.bucket(bucket_name)
            blob = bucket.blob(object_name)

            url = blob.generate_signed_url(
                version="v4",
                expiration=timedelta(minutes=expiration_minutes),
                method="GET",
            )

            logger.debug(f"Generated signed URL for {object_name} in {bucket_name} (expires in {expiration_minutes}m)")
            return url

        except Exception as e:
            logger.error(f"Signed URL generation error: {type(e).__name__}: {e}", exc_info=True)
            raise Exception(f"Signed URL generation failed: {e}")

    async def generate_signed_url(self, file_url: str, expiration_minutes: int = 60) -> str:
        """Generate a signed URL for secure file access.

        Automatically detects which bucket the file is in from the URL.

        Args:
            file_url: Full GCS URL (e.g., https://storage.googleapis.com/bucket/path/file.jpg)
            expiration_minutes: URL validity duration in minutes (default: 60)

        Returns:
            Signed URL with temporary access token

        Example:
            url = await storage_service.generate_signed_url(
                "https://storage.googleapis.com/bucket-name/chat_uploads/user123/file.jpg",
                expiration_minutes=120
            )
        """
        # Detect bucket and extract object name from full URL
        if self.private_bucket_name in file_url:
            bucket_name = self.private_bucket_name
            object_name = file_url.split(f"{self.private_bucket_name}/")[-1]
        elif self.public_bucket_name in file_url:
            bucket_name = self.public_bucket_name
            object_name = file_url.split(f"{self.public_bucket_name}/")[-1]
        else:
            raise ValueError(f"Could not determine bucket from URL: {file_url}")

        url: str = await run_in_threadpool(self._generate_signed_url_sync, object_name, bucket_name, expiration_minutes)
        return url


storage_service = StorageService()
