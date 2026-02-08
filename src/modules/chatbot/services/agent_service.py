import time
from typing import Any

from fastapi import WebSocket
from google.genai.types import HarmBlockThreshold, HarmCategory
from pydantic_ai import Agent, AudioUrl, DocumentUrl, ImageUrl, VideoUrl
from pydantic_ai.models.google import GoogleModel, GoogleModelSettings
from pydantic_ai.providers.google import GoogleProvider

from src.core.config import settings
from src.core.logging import get_logger

logger = get_logger(__name__)

FileAttachment = ImageUrl | DocumentUrl | VideoUrl | AudioUrl


class ChatAgentService:
    """Pydantic AI wrapper for streaming chat responses.

    This service handles:
    - AI agent initialization with Gemini Flash model
    - Streaming responses to WebSocket
    - Token counting and performance metrics
    - Title generation for new threads
    """

    def __init__(self):
        model_settings = GoogleModelSettings(
            google_safety_settings=[  # type: ignore[typeddict-item]
                {
                    "category": HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                    "threshold": HarmBlockThreshold.BLOCK_ONLY_HIGH,
                },
                {
                    "category": HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                    "threshold": HarmBlockThreshold.BLOCK_ONLY_HIGH,
                },
                {
                    "category": HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                    "threshold": HarmBlockThreshold.BLOCK_ONLY_HIGH,
                },
                {
                    "category": HarmCategory.HARM_CATEGORY_HARASSMENT,
                    "threshold": HarmBlockThreshold.BLOCK_ONLY_HIGH,
                },
            ]
        )

        # Create Google provider with API key from settings
        google_provider = GoogleProvider(api_key=settings.GOOGLE_API_KEY)

        self.agent = Agent(
            model=GoogleModel(model_name=settings.GEMINI_CHAT_MODEL, provider=google_provider),
            output_type=str,
            model_settings=model_settings,
        )

        self.title_agent = Agent(
            model=GoogleModel(model_name=settings.GEMINI_MODEL_LOW, provider=google_provider), output_type=str
        )

        logger.debug("ChatAgentService initialized:")
        logger.debug(f"  - Chat model: {settings.GEMINI_CHAT_MODEL}")
        logger.debug(f"  - Title model: {settings.GEMINI_MODEL_LOW}")

    async def stream_response(
        self,
        user_prompt: str,
        system_instructions: str,
        websocket: WebSocket,
        files: list[FileAttachment] | None = None,
    ) -> tuple[str, int, int]:
        """Stream AI response to WebSocket in real-time.

        This is the CORE method that:
        1. Calls Pydantic AI with streaming enabled
        2. Sends each text chunk to WebSocket as it arrives (like Claude/ChatGPT)
        3. Returns final response + metrics after completion

        Args:
            user_prompt: User's message
            system_instructions: System prompt + health context (from ChatContextService)
            websocket: WebSocket connection to stream to
            files: Optional list of file attachments (images, documents, videos, audio)

        Returns:
            tuple: (full_response, tokens_used, response_time_ms)

        Example WebSocket messages sent:
            {"type": "assistant_chunk", "content": "Bug"}
            {"type": "assistant_chunk", "content": "ün"}
            {"type": "assistant_chunk", "content": " koş"}
        """
        start_time = time.time()
        full_response = ""

        try:
            file_count = len(files) if files else 0
            logger.debug(f"Starting AI stream for prompt: {user_prompt[:50]}... (files: {file_count})")

            message: str | list[Any] = [user_prompt, *files] if files else user_prompt

            async with self.agent.run_stream(message, instructions=system_instructions) as response:
                async for text_chunk in response.stream_text(delta=True):
                    if text_chunk:
                        await websocket.send_json({"type": "assistant_chunk", "content": text_chunk})
                        full_response += text_chunk

                usage = response.usage()
                tokens_used = usage.total_tokens if usage else 0

            response_time_ms = int((time.time() - start_time) * 1000)

            logger.info(f"AI stream completed: {len(full_response)} chars, {tokens_used} tokens, {response_time_ms}ms")

            return (full_response, tokens_used, response_time_ms)

        except Exception as e:
            logger.error(f"AI streaming error: {e}", exc_info=True)
            raise

    async def generate_thread_title(self, first_message: str) -> str:
        """Generate short title from first message using LOW model.

        Uses AI to create a concise title (max 50 chars).
        Falls back to truncated message if AI fails.

        Args:
            first_message: User's first message in thread

        Returns:
            Generated title (max 50 characters)

        """
        try:
            result = await self.title_agent.run(
                f"Create a very short title (max 5 words) for this chat: '{first_message[:200]}'. "
                "Use the SAME LANGUAGE as the message. Respond ONLY with the title, no quotes."
            )

            title = result.output.strip().strip('"').strip("'")

            title = title[:50]

            logger.debug(f"Generated title: {title}")
            return title

        except Exception as e:
            logger.warning(f"Title generation failed: {e}")
            return first_message[:50] + ("..." if len(first_message) > 50 else "")

    async def generate_thread_summary(self, messages: list[dict[str, Any]]) -> str:
        """Generate a concise summary of thread messages.

        Args:
            messages: List of message dicts with 'role' and 'content'

        Returns:
            Generated summary (max 500 characters)
        """
        try:
            # Build conversation context
            conversation_text = "\n".join(
                [f"{msg['role']}: {msg['content'][:200]}" for msg in messages[-20:]]  # Last 20 messages
            )

            prompt = (
                f"Summarize this conversation in 2-3 sentences (max 100 words). "
                f"Focus on key topics discussed and main outcomes.\n\n{conversation_text}"
            )

            result = await self.title_agent.run(prompt)
            summary = result.output.strip()[:500]

            logger.debug(f"Generated summary: {summary[:100]}...")
            return summary

        except Exception as e:
            logger.warning(f"Summary generation failed: {e}")
            return "Summary generation failed. Please try again later."
