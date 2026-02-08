"""WebSocket utilities and base classes for real-time communication.

This module provides:
- WebSocket authentication
- Custom WebSocket exceptions with error codes
- Abstract base handler for WebSocket services
- Connection manager for tracking active connections
"""

import contextlib
import uuid
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any

import jwt
from fastapi import WebSocket, WebSocketDisconnect
from jwt import InvalidTokenError
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.core.database import get_db
from src.core.logging import get_logger
from src.modules.users.models import User
from src.modules.users.repository import UserRepository

logger = get_logger(__name__)


# =============================================================================
# WebSocket Error Codes
# =============================================================================


class WebSocketErrorCode(str, Enum):
    """Standard WebSocket error codes for consistent error handling."""

    # Authentication errors
    INVALID_TOKEN = "INVALID_TOKEN"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"
    UNAUTHORIZED = "UNAUTHORIZED"

    # Validation errors
    INVALID_MESSAGE_TYPE = "INVALID_MESSAGE_TYPE"
    INVALID_MESSAGE_FORMAT = "INVALID_MESSAGE_FORMAT"
    MESSAGE_TOO_LONG = "MESSAGE_TOO_LONG"
    MISSING_REQUIRED_FIELD = "MISSING_REQUIRED_FIELD"

    # Resource errors
    NOT_FOUND = "NOT_FOUND"
    THREAD_NOT_FOUND = "THREAD_NOT_FOUND"
    USER_NOT_FOUND = "USER_NOT_FOUND"

    # Rate limiting
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    DAILY_LIMIT_EXCEEDED = "DAILY_LIMIT_EXCEEDED"

    # Business logic errors
    MODERATION_BLOCKED = "MODERATION_BLOCKED"
    PERMISSION_DENIED = "PERMISSION_DENIED"

    # Server errors
    INTERNAL_ERROR = "INTERNAL_ERROR"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"


# =============================================================================
# WebSocket Exceptions
# =============================================================================


class WebSocketError(Exception):
    """Base exception for WebSocket errors.

    Provides structured error information that can be sent to clients
    as JSON error messages.
    """

    def __init__(
        self,
        code: WebSocketErrorCode,
        message: str,
        details: dict[str, Any] | None = None,
        close_connection: bool = False,
    ):
        self.code = code
        self.message = message
        self.details = details or {}
        self.close_connection = close_connection
        super().__init__(message)

    def to_dict(self) -> dict[str, Any]:
        """Convert exception to JSON-serializable dict for WebSocket response."""
        response: dict[str, Any] = {
            "type": "error",
            "code": self.code.value,
            "message": self.message,
        }
        if self.details:
            response["details"] = self.details
        return response


class WebSocketAuthError(WebSocketError):
    """Authentication-related WebSocket errors."""

    def __init__(
        self,
        message: str = "Authentication failed",
        code: WebSocketErrorCode = WebSocketErrorCode.UNAUTHORIZED,
    ):
        super().__init__(code=code, message=message, close_connection=True)


class WebSocketValidationError(WebSocketError):
    """Validation-related WebSocket errors."""

    def __init__(
        self,
        message: str,
        code: WebSocketErrorCode = WebSocketErrorCode.INVALID_MESSAGE_FORMAT,
        details: dict[str, Any] | None = None,
    ):
        super().__init__(code=code, message=message, details=details, close_connection=False)


class WebSocketRateLimitError(WebSocketError):
    """Rate limiting WebSocket errors."""

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after_seconds: int | None = None,
    ):
        details = {"retry_after_seconds": retry_after_seconds} if retry_after_seconds else None
        super().__init__(
            code=WebSocketErrorCode.RATE_LIMIT_EXCEEDED,
            message=message,
            details=details,
            close_connection=False,
        )


# =============================================================================
# Authentication
# =============================================================================


async def authenticate_websocket(token: str, db: AsyncSession) -> User:
    """Authenticate WebSocket connection via Bearer token.

    Extracts user from JWT token passed in query parameter.
    Similar to get_current_user but for WebSocket connections.

    Args:
        token: JWT token (with or without "Bearer " prefix)
        db: Database session

    Returns:
        Authenticated User object

    Raises:
        WebSocketAuthError: If token is invalid or user not found
    """
    try:
        logger.debug(f"Authenticating WebSocket with token: {token[:20]}...")

        if token.startswith("Bearer "):
            token = token[7:]

        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id_str = payload.get("sub")

        if not user_id_str:
            logger.error("Token payload missing 'sub' field")
            raise WebSocketAuthError("Invalid token: no user ID", WebSocketErrorCode.INVALID_TOKEN)

        user_repo = UserRepository(db)
        user = await user_repo.get(uuid.UUID(user_id_str))

        if not user:
            logger.error(f"User {user_id_str} not found")
            raise WebSocketAuthError("User not found", WebSocketErrorCode.USER_NOT_FOUND)

        if not user.is_active:
            logger.error(f"User {user_id_str} is inactive")
            raise WebSocketAuthError("User account is inactive", WebSocketErrorCode.UNAUTHORIZED)

        return user

    except InvalidTokenError as e:
        logger.error(f"JWT decode error: {e}")
        raise WebSocketAuthError("Invalid or expired token", WebSocketErrorCode.INVALID_TOKEN)


# =============================================================================
# Base WebSocket Handler
# =============================================================================


class BaseWebSocketHandler(ABC):
    """Abstract base class for WebSocket handlers.

    Provides common functionality for WebSocket connection management:
    - Connection lifecycle (accept, authenticate, close)
    - Error handling with structured error responses
    - Database session management
    - Logging with connection IDs

    Subclasses must implement:
    - handle_message(): Process incoming WebSocket messages
    - on_connect(): Called after successful authentication (optional)
    - on_disconnect(): Called when connection closes (optional)

    Example usage:
        class ChatWebSocketHandler(BaseWebSocketHandler):
            async def handle_message(self, data: dict) -> None:
                msg_type = data.get("type")
                if msg_type == "send_message":
                    await self._process_chat_message(data)

            async def on_connect(self) -> None:
                await self.send({"type": "connected", "user_id": str(self.user.id)})
    """

    def __init__(self, websocket: WebSocket, token: str):
        self.websocket = websocket
        self.token = token
        self.user: User | None = None
        self.db: AsyncSession | None = None
        self._db_generator = None
        self._conn_id = uuid.uuid4().hex[:8]
        self._is_connected = False

    @property
    def conn_id(self) -> str:
        """Unique connection identifier for logging."""
        return self._conn_id

    # -------------------------------------------------------------------------
    # Abstract methods - must be implemented by subclasses
    # -------------------------------------------------------------------------

    @abstractmethod
    async def handle_message(self, data: dict[str, Any]) -> None:
        """Process incoming WebSocket message.

        Args:
            data: Parsed JSON message from client

        Raises:
            WebSocketError: For any error that should be sent to client
        """
        pass

    # -------------------------------------------------------------------------
    # Optional hooks - can be overridden by subclasses
    # -------------------------------------------------------------------------

    async def on_connect(self) -> None:  # noqa: B027
        """Called after successful authentication.

        Override to send initial messages or setup resources.
        Default implementation does nothing.
        """
        pass

    async def on_disconnect(self) -> None:  # noqa: B027
        """Called when connection closes (normally or due to error).

        Override to cleanup resources.
        Default implementation does nothing.
        """
        pass

    # -------------------------------------------------------------------------
    # Core connection lifecycle
    # -------------------------------------------------------------------------

    async def run(self) -> None:
        """Main entry point - handles full WebSocket lifecycle.

        1. Accept connection
        2. Setup database session
        3. Authenticate user
        4. Call on_connect hook
        5. Message loop
        6. Call on_disconnect hook
        7. Cleanup
        """
        logger.info(f"[{self._conn_id}] New WebSocket connection")

        await self.websocket.accept()
        self._is_connected = True

        try:
            # Setup database session
            self._db_generator = get_db()
            self.db = await anext(self._db_generator)

            # Authenticate
            self.user = await authenticate_websocket(self.token, self.db)
            logger.info(f"[{self._conn_id}] User {self.user.id} authenticated")

            # Connection established hook
            await self.on_connect()

            # Message loop
            await self._message_loop()

        except WebSocketDisconnect:
            logger.info(f"[{self._conn_id}] Client disconnected")

        except WebSocketAuthError as e:
            logger.warning(f"[{self._conn_id}] Auth error: {e.message}")
            await self._send_error_and_close(e)

        except WebSocketError as e:
            logger.error(f"[{self._conn_id}] WebSocket error: {e.message}")
            if e.close_connection:
                await self._send_error_and_close(e)
            else:
                await self.send(e.to_dict())

        except Exception as e:
            logger.error(f"[{self._conn_id}] Unexpected error: {e}", exc_info=True)
            await self._send_error_and_close(
                WebSocketError(
                    code=WebSocketErrorCode.INTERNAL_ERROR,
                    message="An unexpected error occurred",
                    close_connection=True,
                )
            )

        finally:
            await self._cleanup()

    async def _message_loop(self) -> None:
        """Receive and process messages until disconnect."""
        while True:
            try:
                data = await self.websocket.receive_json()
                logger.debug(f"[{self._conn_id}] Received: {data.get('type', 'unknown')}")

                await self.handle_message(data)

            except WebSocketDisconnect:
                raise  # Re-raise to exit loop

            except WebSocketError as e:
                logger.warning(f"[{self._conn_id}] Message error: {e.code} - {e.message}")
                await self.send(e.to_dict())
                if e.close_connection:
                    raise

            except Exception as e:
                logger.error(f"[{self._conn_id}] Error processing message: {e}", exc_info=True)
                await self.send(
                    WebSocketError(
                        code=WebSocketErrorCode.INTERNAL_ERROR,
                        message="Error processing message",
                    ).to_dict()
                )

    async def _cleanup(self) -> None:
        """Cleanup resources after connection closes."""
        logger.info(f"[{self._conn_id}] Cleaning up connection")

        try:
            await self.on_disconnect()
        except Exception as e:
            logger.error(f"[{self._conn_id}] Error in on_disconnect: {e}")

        # Close database session
        if self._db_generator:
            with contextlib.suppress(StopAsyncIteration):
                await anext(self._db_generator, None)

        self._is_connected = False

    async def _send_error_and_close(self, error: WebSocketError) -> None:
        """Send error message and close connection."""
        try:
            await self.send(error.to_dict())
            await self.websocket.close(code=1008, reason=error.message[:120])
        except Exception:
            pass  # Connection might already be closed

    # -------------------------------------------------------------------------
    # Helper methods for subclasses
    # -------------------------------------------------------------------------

    async def send(self, data: dict[str, Any]) -> None:
        """Send JSON message to client.

        Args:
            data: Dictionary to send as JSON
        """
        if self._is_connected:
            await self.websocket.send_json(data)

    async def send_error(
        self,
        code: WebSocketErrorCode,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Send error message to client.

        Args:
            code: Error code from WebSocketErrorCode enum
            message: Human-readable error message
            details: Optional additional error details
        """
        error = WebSocketError(code=code, message=message, details=details)
        await self.send(error.to_dict())

    def require_field(self, data: dict[str, Any], field: str) -> Any:
        """Validate that required field exists in message.

        Args:
            data: Message data dict
            field: Required field name

        Returns:
            Field value

        Raises:
            WebSocketValidationError: If field is missing
        """
        if field not in data:
            raise WebSocketValidationError(
                message=f"Missing required field: {field}",
                code=WebSocketErrorCode.MISSING_REQUIRED_FIELD,
                details={"field": field},
            )
        return data[field]


# =============================================================================
# Connection Manager
# =============================================================================


class ConnectionManager:
    """Manages active WebSocket connections by user ID.

    Useful for:
    - Tracking which users are connected
    - Sending messages to specific users
    - Preventing duplicate connections
    """

    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}

    async def connect(self, user_id: str, websocket: WebSocket) -> None:
        """Register a new connection.

        Args:
            user_id: User identifier
            websocket: WebSocket connection (should already be accepted)
        """
        # Close existing connection if any
        if user_id in self.active_connections:
            with contextlib.suppress(Exception):
                await self.active_connections[user_id].close(code=1000, reason="New connection opened")

        self.active_connections[user_id] = websocket

    def disconnect(self, user_id: str) -> None:
        """Remove a connection.

        Args:
            user_id: User identifier
        """
        if user_id in self.active_connections:
            del self.active_connections[user_id]

    def is_connected(self, user_id: str) -> bool:
        """Check if user is connected.

        Args:
            user_id: User identifier

        Returns:
            True if user has active connection
        """
        return user_id in self.active_connections

    async def send_to_user(self, user_id: str, message: dict[str, Any]) -> bool:
        """Send message to specific user.

        Args:
            user_id: User identifier
            message: JSON-serializable message

        Returns:
            True if message was sent, False if user not connected
        """
        if user_id in self.active_connections:
            try:
                await self.active_connections[user_id].send_json(message)
                return True
            except Exception:
                self.disconnect(user_id)
        return False

    async def broadcast(self, message: dict[str, Any], exclude: list[str] | None = None) -> int:
        """Broadcast message to all connected users.

        Args:
            message: JSON-serializable message
            exclude: User IDs to exclude from broadcast

        Returns:
            Number of users message was sent to
        """
        exclude = exclude or []
        sent_count = 0

        for user_id in list(self.active_connections.keys()):
            if user_id not in exclude and await self.send_to_user(user_id, message):
                sent_count += 1

        return sent_count


# Singleton instance
connection_manager = ConnectionManager()
