from typing import Any

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import InvalidTokenError
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.core.database import get_db
from src.modules.users.models import User
from src.modules.users.repository import UserRepository

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(dependency=security),
    db: AsyncSession = Depends(dependency=get_db),
) -> User:
    """
    Retrieve the current authenticated user based on the provided token.
    """
    token: str = credentials.credentials

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials (token may be invalid or expired)",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload: Any = jwt.decode(
            jwt=token,
            key=settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception

    except InvalidTokenError:
        raise credentials_exception
    user_repo = UserRepository(db=db)
    user: User | None = await user_repo.get(id=user_id)
    if user is None:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user",
        )

    return user
