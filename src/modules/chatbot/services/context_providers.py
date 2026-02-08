"""Context providers for the chatbot.

Implement custom providers by following the ContextProvider protocol.

Example:
    class MyCustomProvider:
        async def get_context(self, user: User) -> str:
            return "Custom context here"

    # Register with service
    service = ChatContextService(db)
    service.register_provider("custom", MyCustomProvider())
"""

from src.modules.users.models import User


class UserProfileProvider:
    """Provides basic user profile context."""

    async def get_context(self, user: User) -> str:
        """Get basic profile context for the user."""
        parts = [
            f"User: {user.full_name or 'Anonymous'}",
        ]

        if hasattr(user, "age") and user.age:
            parts.append(f"Age: {user.age}")

        if hasattr(user, "timezone") and user.timezone:
            parts.append(f"Timezone: {user.timezone}")

        return "\n".join(parts)
