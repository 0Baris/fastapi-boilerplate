"""WebSocket routes for AI chatbot functionality.

Provides real-time bidirectional communication for:
- Chat message sending/receiving with AI streaming
- Thread management (load, list)
- Keep-alive ping/pong
"""

from fastapi import APIRouter, WebSocket

from src.core.logging import get_logger
from src.modules.chatbot.services.websocket_service import ChatWebSocketHandler

logger = get_logger(__name__)

router = APIRouter(prefix="/chat", tags=["Chatbot"])

# Standalone router for global docs endpoint (not prefixed)
docs_router = APIRouter(tags=["Documentation"])


@docs_router.get("/docs", summary="Get chatbot usage documentation")
async def get_chatbot_docs():
    """Real-time AI chat with streaming responses.

    **Connection:** wss://api.example.com/api/v1/chat/ws?token=YOUR_JWT_TOKEN

    **Authentication:**
    - Pass JWT token as query parameter
    - Token validates on connection (invalid token closes connection)
    - One connection per user (new connection replaces old)

    **Client to Server Messages:**

    1. Send Message
       ```json
       {
         "type": "send_message",
         "thread_id": "uuid-or-null",
         "content": "What can you help me with?",
         "upload_ids": ["uuid1", "uuid2"]
       }
       ```
       - thread_id: Existing thread UUID or null for new thread
       - content: User message text (1-2000 characters)
       - upload_ids: Optional array of file UUIDs from upload endpoint

    2. Load Thread History
       ```json
       {
         "type": "load_thread",
         "thread_id": "uuid",
         "before_timestamp": "2026-02-04T10:00:00Z"
       }
       ```
       - Loads messages before given timestamp (pagination)

    3. List All Threads
       ```json
       {
         "type": "list_threads",
         "skip": 0,
         "limit": 20
       }
       ```
       - Returns user's conversation threads with metadata

    4. Ping (Keep-alive)
       ```json
       {
         "type": "ping"
       }
       ```
       - Send every 30 seconds to maintain connection

    **Server to Client Messages:**

    1. Connected
       ```json
       {"type": "connected", "user_id": "uuid"}
       ```

    2. Thread Created
       ```json
       {"type": "thread_created", "thread_id": "uuid"}
       ```

    3. AI Response Chunk (streaming, multiple messages)
       ```json
       {"type": "assistant_chunk", "content": "Here's what I can help you with..."}
       ```

    4. Message Complete
       ```json
       {
         "type": "message_complete",
         "message_id": "uuid",
         "thread_id": "uuid",
         "tokens_used": 150,
         "response_time_ms": 1250
       }
       ```

    5. Thread Messages (history response)
       ```json
       {
         "type": "thread_messages",
         "thread_id": "uuid",
         "messages": [
           {
             "id": "uuid",
             "role": "user",
             "content": "What can you help me with?",
             "created_at": "2026-02-04T10:00:00Z",
             "media_urls": []
           },
           {
             "id": "uuid2",
             "role": "assistant",
             "content": "I can assist you with various tasks...",
             "created_at": "2026-02-04T10:00:05Z"
           }
         ],
         "has_more": true
       }
       ```

    6. Thread List
       ```json
       {
         "type": "thread_list",
         "threads": [
           {
             "id": "uuid",
             "title": "General conversation",
             "last_message_at": "2026-02-04T10:00:00Z",
             "message_count": 12,
             "preview": "What can you help me with..."
           }
         ],
         "total": 42
       }
       ```

    7. Error
       ```json
       {
         "type": "error",
         "code": "RATE_LIMIT_EXCEEDED",
         "message": "Too many messages. Wait 60 seconds."
       }
       ```
       Error codes: RATE_LIMIT_EXCEEDED, NOT_FOUND, UNAUTHORIZED, INTERNAL_ERROR, MESSAGE_TOO_LONG, MODERATION_BLOCKED

    8. Attachment Warning
       ```json
       {
         "type": "attachment_warning",
         "message": "2 file(s) could not be attached",
         "failed_files": ["Upload abc123 not found", "File has unsupported type"]
       }
       ```

    9. Pong
       ```json
       {"type": "pong"}
       ```

    **Rate Limits:**
    - 10 messages per minute
    - 100 messages per day
    - Max 2000 characters per message
    - Max 10 file attachments per message

    **AI Context:**
    - User profile and preferences
    - Last 10 messages (sliding window)
    - Thread summaries for older messages
    - Attached files and media content

    """
    return {"status": "ok"}


@router.websocket("/ws")
async def chat_websocket(websocket: WebSocket, token: str):
    """Real-time AI chat with streaming responses.

    All connection lifecycle, authentication, and message handling
    is delegated to ChatWebSocketHandler service.
    """
    handler = ChatWebSocketHandler(websocket=websocket, token=token)
    await handler.run()
