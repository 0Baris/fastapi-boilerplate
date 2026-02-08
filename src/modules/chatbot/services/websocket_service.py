"""WebSocket service for AI chat functionality.

Handles WebSocket connection lifecycle and message routing for the chatbot.
"""

import uuid
from datetime import datetime
from typing import Any

from fastapi import WebSocket

from src.core.exception import NotFoundError
from src.core.logging import get_logger
from src.core.websocket import (
    BaseWebSocketHandler,
    WebSocketError,
    WebSocketErrorCode,
    WebSocketValidationError,
)
from src.modules.chatbot.services.chat_service import ChatService

logger = get_logger(__name__)


class ChatWebSocketHandler(BaseWebSocketHandler):
    """WebSocket handler for AI chat functionality.

    Handles:
    - send_message: Send user message and stream AI response
    - load_thread: Load conversation history
    - list_threads: List all user's threads
    - ping: Keep-alive ping/pong

    Connection URL: wss://api.example.com/api/v1/chat/ws?token=YOUR_JWT_TOKEN
    """

    def __init__(self, websocket: WebSocket, token: str):
        super().__init__(websocket, token)
        self._chat_service: ChatService | None = None

    @property
    def chat_service(self) -> ChatService:
        """Lazy initialization of ChatService."""
        if self._chat_service is None:
            if self.db is None:
                raise WebSocketError(
                    code=WebSocketErrorCode.INTERNAL_ERROR,
                    message="Database session not initialized",
                    close_connection=True,
                )
            self._chat_service = ChatService(self.db)
        return self._chat_service

    async def on_connect(self) -> None:
        """Send connected confirmation after authentication."""
        if self.user:
            await self.send(
                {
                    "type": "connected",
                    "user_id": str(self.user.id),
                }
            )
            logger.debug(f"[{self.conn_id}] Sent 'connected' message")

    async def handle_message(self, data: dict[str, Any]) -> None:
        """Route incoming messages to appropriate handlers.

        Supported message types:
        - send_message: Send user message to AI
        - load_thread: Load thread history
        - list_threads: List all threads
        - ping: Keep-alive

        Args:
            data: Parsed JSON message from client

        Raises:
            WebSocketValidationError: If message type is invalid
        """
        msg_type = data.get("type")

        if msg_type == "send_message":
            await self._handle_send_message(data)

        elif msg_type == "load_thread":
            await self._handle_load_thread(data)

        elif msg_type == "list_threads":
            await self._handle_list_threads(data)

        elif msg_type == "ping":
            await self._handle_ping()

        else:
            raise WebSocketValidationError(
                message=f"Unknown message type: {msg_type}",
                code=WebSocketErrorCode.INVALID_MESSAGE_TYPE,
                details={"received_type": msg_type},
            )

    async def _handle_send_message(self, data: dict[str, Any]) -> None:
        """Handle send_message: Send user message and stream AI response.

        Expected format:
        {
            "type": "send_message",
            "thread_id": "uuid-or-null",
            "content": "User message text",
            "upload_ids": ["uuid1", "uuid2"]  // optional
        }
        """
        if self.user is None:
            raise WebSocketError(
                code=WebSocketErrorCode.UNAUTHORIZED,
                message="User not authenticated",
                close_connection=True,
            )

        # Validate content
        content = self.require_field(data, "content")

        if not isinstance(content, str) or len(content.strip()) == 0:
            raise WebSocketValidationError(
                message="Message content cannot be empty",
                code=WebSocketErrorCode.INVALID_MESSAGE_FORMAT,
            )

        if len(content) > 2000:
            raise WebSocketValidationError(
                message="Message exceeds 2000 character limit",
                code=WebSocketErrorCode.MESSAGE_TOO_LONG,
                details={"max_length": 2000, "actual_length": len(content)},
            )

        # Parse optional fields
        thread_id_str = data.get("thread_id")
        thread_id: uuid.UUID | None = None
        if thread_id_str:
            try:
                thread_id = uuid.UUID(thread_id_str)
            except ValueError:
                raise WebSocketValidationError(
                    message="Invalid thread_id format",
                    code=WebSocketErrorCode.INVALID_MESSAGE_FORMAT,
                    details={"field": "thread_id"},
                )
        upload_ids = data.get("upload_ids", [])

        # Delegate to chat service
        try:
            await self.chat_service.handle_send_message(
                user=self.user,
                thread_id=thread_id,
                content=content,
                websocket=self.websocket,
                upload_ids=upload_ids,
            )
        except NotFoundError as e:
            raise WebSocketError(
                code=WebSocketErrorCode.THREAD_NOT_FOUND,
                message=str(e),
                close_connection=False,
            )

    async def _handle_load_thread(self, data: dict[str, Any]) -> None:
        """Handle load_thread: Load conversation history.

        Expected format:
        {
            "type": "load_thread",
            "thread_id": "uuid",
            "before_timestamp": "2026-02-04T10:00:00Z"  // optional
        }
        """
        if self.user is None:
            raise WebSocketError(
                code=WebSocketErrorCode.UNAUTHORIZED,
                message="User not authenticated",
                close_connection=True,
            )

        # Validate thread_id
        thread_id_str = self.require_field(data, "thread_id")

        try:
            thread_id = uuid.UUID(thread_id_str)
        except ValueError:
            raise WebSocketValidationError(
                message="Invalid thread_id format",
                code=WebSocketErrorCode.INVALID_MESSAGE_FORMAT,
                details={"field": "thread_id"},
            )

        # Parse optional before_timestamp
        before_ts_str = data.get("before_timestamp")
        before_ts = None
        if before_ts_str:
            try:
                before_ts = datetime.fromisoformat(before_ts_str)
            except ValueError:
                raise WebSocketValidationError(
                    message="Invalid timestamp format. Use ISO 8601.",
                    code=WebSocketErrorCode.INVALID_MESSAGE_FORMAT,
                    details={"field": "before_timestamp"},
                )

        # Get thread messages
        try:
            result = await self.chat_service.handle_load_thread(
                user=self.user,
                thread_id=thread_id,
                before_timestamp=before_ts,
            )
        except NotFoundError as e:
            raise WebSocketError(
                code=WebSocketErrorCode.THREAD_NOT_FOUND,
                message=str(e),
                close_connection=False,
            )

        await self.send({"type": "thread_messages", **result})

    async def _handle_list_threads(self, data: dict[str, Any]) -> None:
        """Handle list_threads: List all user's threads.

        Expected format:
        {
            "type": "list_threads",
            "skip": 0,  // optional, default 0
            "limit": 20  // optional, default 20
        }
        """
        if self.user is None:
            raise WebSocketError(
                code=WebSocketErrorCode.UNAUTHORIZED,
                message="User not authenticated",
                close_connection=True,
            )

        # Parse pagination params
        skip = data.get("skip", 0)
        limit = data.get("limit", 20)

        # Validate pagination
        if not isinstance(skip, int) or skip < 0:
            skip = 0
        if not isinstance(limit, int) or limit < 1:
            limit = 20
        if limit > 100:
            limit = 100  # Max limit

        # Get threads
        result = await self.chat_service.handle_list_threads(
            user=self.user,
            skip=skip,
            limit=limit,
        )

        await self.send({"type": "thread_list", **result})

    async def _handle_ping(self) -> None:
        """Handle ping: Keep-alive ping/pong."""
        await self.send({"type": "pong"})
