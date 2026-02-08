import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import and_, delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.repository import BaseRepository
from src.modules.auth.models.refresh_token import RefreshToken


class RefreshTokenRepository(BaseRepository[RefreshToken]):
    """Repository for refresh token database operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(db, RefreshToken)

    async def create_token(
        self,
        user_id: uuid.UUID,
        token_hash: str,
        device_id: str | None,
        device_name: str | None,
        user_agent: str | None,
        ip_address: str | None,
        expires_delta: timedelta,
        parent_token_id: uuid.UUID | None = None,
    ) -> RefreshToken:
        """Create new refresh token entry."""
        token = RefreshToken(
            user_id=user_id,
            token_hash=token_hash,
            device_id=device_id,
            device_name=device_name,
            user_agent=user_agent,
            ip_address=ip_address,
            expires_at=datetime.now(UTC) + expires_delta,
            parent_token_id=parent_token_id,
        )
        return await self.create(token)

    async def get_by_token_hash(self, token_hash: str) -> RefreshToken | None:
        """Get refresh token by hash."""
        stmt = select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_user_tokens(
        self,
        user_id: uuid.UUID,
        device_id: str | None = None,
        include_revoked: bool = False,
    ) -> list[RefreshToken]:
        """Get all tokens for user, optionally filtered by device."""
        conditions = [RefreshToken.user_id == user_id]

        if device_id:
            conditions.append(RefreshToken.device_id == device_id)

        if not include_revoked:
            conditions.append(RefreshToken.is_revoked == False)  # noqa: E712

        stmt = select(RefreshToken).where(and_(*conditions))
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def revoke_token(self, token_id: uuid.UUID, replaced_by_id: uuid.UUID | None = None) -> bool:
        """Revoke a token (for rotation or logout)."""
        stmt = (
            update(RefreshToken)
            .where(RefreshToken.id == token_id)
            .values(
                is_revoked=True,
                revoked_at=datetime.now(UTC),
                replaced_by_id=replaced_by_id,
            )
        )
        result = await self.db.execute(stmt)
        await self.db.commit()
        # CursorResult from update/delete has rowcount
        return getattr(result, "rowcount", 0) > 0

    async def revoke_token_chain(self, token_id: uuid.UUID) -> int:
        """Revoke entire token chain (for reuse detection)."""
        token = await self.get(token_id)
        if not token:
            return 0

        chain_tokens = []
        current = token

        while current.parent_token_id:
            parent = await self.get(current.parent_token_id)
            if parent:
                chain_tokens.append(parent.id)
                current = parent
            else:
                break

        if chain_tokens:
            stmt = (
                update(RefreshToken)
                .where(RefreshToken.id.in_(chain_tokens))
                .values(is_revoked=True, revoked_at=datetime.now(UTC))
            )
            result = await self.db.execute(stmt)
            await self.db.commit()
            return getattr(result, "rowcount", 0)

        return 0

    async def revoke_all_user_tokens(self, user_id: uuid.UUID, except_token_id: uuid.UUID | None = None) -> int:
        """Revoke all tokens for a user (logout all devices)."""
        conditions = [RefreshToken.user_id == user_id, RefreshToken.is_revoked == False]  # noqa: E712

        if except_token_id:
            conditions.append(RefreshToken.id != except_token_id)

        stmt = update(RefreshToken).where(and_(*conditions)).values(is_revoked=True, revoked_at=datetime.now(UTC))
        result = await self.db.execute(stmt)
        await self.db.commit()
        return getattr(result, "rowcount", 0)

    async def revoke_device_tokens(self, user_id: uuid.UUID, device_id: str) -> int:
        """Revoke all tokens for specific device."""
        stmt = (
            update(RefreshToken)
            .where(
                and_(
                    RefreshToken.user_id == user_id,
                    RefreshToken.device_id == device_id,
                    RefreshToken.is_revoked == False,  # noqa: E712
                )
            )
            .values(is_revoked=True, revoked_at=datetime.now(UTC))
        )
        result = await self.db.execute(stmt)
        await self.db.commit()
        return getattr(result, "rowcount", 0)

    async def cleanup_expired_tokens(self) -> int:
        """Delete expired tokens (for celery task)."""
        stmt = delete(RefreshToken).where(RefreshToken.expires_at < datetime.now(UTC))
        result = await self.db.execute(stmt)
        await self.db.commit()
        return getattr(result, "rowcount", 0)

    async def is_token_valid(self, token_hash: str) -> bool:
        """Quick validation: exists, not revoked, not expired."""
        token = await self.get_by_token_hash(token_hash)

        if not token:
            return False

        if token.is_revoked:
            return False

        return not token.expires_at < datetime.now(UTC)
