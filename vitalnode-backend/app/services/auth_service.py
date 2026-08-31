from app.api.v1.utils import ev
"""
Authentication service.
Handles login, token creation, current-user resolution.
Roles are enforced at the API layer via dependencies.
"""
from datetime import datetime, timezone
from typing import Optional
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import AuthenticationError
from app.core.security import verify_password, create_access_token, decode_access_token
from app.models.user import User, UserRole
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


async def authenticate_user(
    db: AsyncSession,
    staff_id: str,
    password: str,
) -> User:
    """
    Verify staff_id + password, return User on success.
    Raises AuthenticationError on any failure.
    """
    result = await db.execute(select(User).where(User.staff_id == staff_id))
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        # Same error for not-found and inactive to avoid enumeration
        raise AuthenticationError("Invalid staff ID or password")

    if not verify_password(password, user.hashed_password):
        raise AuthenticationError("Invalid staff ID or password")

    # Update last login
    user.last_login = datetime.now(timezone.utc)
    await db.flush()

    logger.info("user_login", staff_id=staff_id, role=user.role)
    return user


def issue_token(user: User) -> str:
    """Create a JWT access token for the authenticated user."""
    return create_access_token(
        subject=str(user.id),
        role=ev(user.role),
        extra={
            "staff_id": user.staff_id,
            "name": user.name,
            "department": user.department,
        },
    )


async def get_user_from_token(
    db: AsyncSession,
    token: str,
) -> Optional[User]:
    """Decode JWT and load the user from the database."""
    payload = decode_access_token(token)
    if not payload:
        return None

    user_id_str = payload.get("sub")
    if not user_id_str:
        return None

    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        return None

    result = await db.execute(select(User).where(User.id == user_id, User.is_active == True))
    return result.scalar_one_or_none()
