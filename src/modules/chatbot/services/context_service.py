"""Context service for AI chat.

Build AI context from thread history and optional user data.
This service is designed to be generic and easily extensible.
"""

import uuid
from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.chatbot.constants import CONTEXT_TEMPLATES, build_system_prompt
from src.modules.chatbot.repositories import MessageRepository, SummaryRepository
from src.modules.users.models import User


class ContextProvider(Protocol):
    """Protocol for custom context providers.

    Implement this protocol to add custom context to the AI.
    Examples: health data, user preferences, subscription info, etc.

    Example:
        class HealthContextProvider:
            def __init__(self, db: AsyncSession):
                self.db = db

            async def get_context(self, user: User) -> str:
                # Fetch and format health data
                return "User's health summary..."

        # Register in ChatContextService
        service = ChatContextService(db)
        service.register_provider("health", HealthContextProvider(db))
    """

    async def get_context(self, user: User) -> str:
        """Get context string for the given user.

        Args:
            user: The user to get context for

        Returns:
            Formatted context string to include in system prompt
        """
        ...


class ChatContextService:
    """Build AI context from thread history and custom providers.

    This service prepares the context (message history + custom data)
    that will be sent to the AI model for generating responses.

    The service is designed to be:
    - Generic: No hardcoded domain-specific logic
    - Extensible: Register custom context providers
    - Configurable: Control what goes into the prompt

    Example:
        service = ChatContextService(db)

        # Add custom context provider
        service.register_provider("user_prefs", UserPreferencesProvider(db))

        # Build system instructions
        instructions = await service.build_system_instructions(thread_id, user)
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.summary_repo = SummaryRepository(db)
        self.message_repo = MessageRepository(db)
        self._context_providers: dict[str, ContextProvider] = {}

    def register_provider(self, name: str, provider: ContextProvider) -> None:
        """Register a custom context provider.

        Args:
            name: Unique name for the provider
            provider: Provider instance implementing ContextProvider protocol

        Example:
            service.register_provider("health", HealthDataProvider(db))
            service.register_provider("subscription", SubscriptionProvider(db))
        """
        self._context_providers[name] = provider

    def unregister_provider(self, name: str) -> None:
        """Remove a context provider.

        Args:
            name: Name of the provider to remove
        """
        self._context_providers.pop(name, None)

    async def build_system_instructions(
        self,
        thread_id: uuid.UUID,
        user: User,
        include_summary: bool = True,
        include_providers: bool = True,
        additional_context: str | None = None,
    ) -> str:
        """Build system instructions from thread history and context providers.

        Returns a single string combining:
        - Base system prompt (from constants.py)
        - Conversation summary (if exists)
        - Custom provider contexts (if registered)
        - Additional context (if provided)

        Args:
            thread_id: Thread UUID to load summary from
            user: Current user for context
            include_summary: Whether to include conversation summary
            include_providers: Whether to include registered provider contexts
            additional_context: Extra context to append

        Returns:
            Combined system instructions string
        """
        instructions_parts: list[str] = []

        # Base system prompt from constants
        instructions_parts.append(build_system_prompt())

        # Conversation summary
        if include_summary:
            summary = await self.summary_repo.get_latest(thread_id)
            if summary:
                formatted = CONTEXT_TEMPLATES["conversation_summary"].format(summary=summary.summary)
                instructions_parts.append(formatted)

        # Context from registered providers
        if include_providers and self._context_providers:
            for _name, provider in self._context_providers.items():
                try:
                    context = await provider.get_context(user)
                    if context and context.strip():
                        formatted = CONTEXT_TEMPLATES["user_context"].format(context=context)
                        instructions_parts.append(formatted)
                except Exception:
                    # Log error but continue - don't break the chat
                    pass

        # Additional context passed directly
        if additional_context:
            formatted = CONTEXT_TEMPLATES["custom_instructions"].format(instructions=additional_context)
            instructions_parts.append(formatted)

        return "\n".join(instructions_parts)

    async def build_minimal_instructions(self) -> str:
        """Build minimal system instructions without any context.

        Useful for simple queries that don't need user context.

        Returns:
            Base system prompt only
        """
        return build_system_prompt()

    async def get_user_context_summary(self, user: User) -> dict[str, str]:
        """Get all context provider outputs for debugging/display.

        Args:
            user: User to get context for

        Returns:
            Dict mapping provider name to context string
        """
        results: dict[str, str] = {}

        for name, provider in self._context_providers.items():
            try:
                context = await provider.get_context(user)
                results[name] = context if context else "(empty)"
            except Exception as e:
                results[name] = f"(error: {e})"

        return results
