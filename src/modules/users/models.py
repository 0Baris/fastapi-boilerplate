from src.core.models.user import BaseUser


class User(BaseUser):
    """Extended User model for application use.

    This class extends BaseUser and can be customized with additional fields.
    By default, it inherits all BaseUser fields without adding new ones.

    Example usage for adding custom fields:
        age: Mapped[int | None] = mapped_column(Integer, nullable=True)
        bio: Mapped[str | None] = mapped_column(String, nullable=True)
    """

    pass  # Extend with custom fields as needed
