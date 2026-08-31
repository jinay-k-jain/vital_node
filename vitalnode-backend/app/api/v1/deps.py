from app.api.v1.utils import ev
"""
FastAPI dependency injection: database session + current user + role guards.
All route protection flows through these dependencies.
The frontend NEVER determines authorization - the backend enforces it.
"""
from typing import Annotated, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.models.user import User, UserRole
from app.services.auth_service import get_user_from_token

bearer_scheme = HTTPBearer(auto_error=False)

DbDep = Annotated[AsyncSession, Depends(get_db)]


async def get_current_user(
    db: DbDep,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> User:
    """Resolve the current authenticated user from the Bearer token."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "MISSING_TOKEN", "message": "Authentication token required"},
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = await get_user_from_token(db, credentials.credentials)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_TOKEN", "message": "Invalid or expired token"},
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_roles(*allowed_roles: UserRole):
    """
    Factory: returns a dependency that enforces one of the allowed roles.
    Returns HTTP 403 if the user's role is not in allowed_roles.
    """
    async def _check_role(current_user: CurrentUser) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "FORBIDDEN",
                    "message": f"Role '{ev(current_user.role)}' is not permitted for this action",
                },
            )
        return current_user

    return _check_role


# Convenience role guards
NurseOrClinician = Annotated[
    User,
    Depends(require_roles(UserRole.TRIAGE_NURSE, UserRole.CLINICIAN, UserRole.ADMINISTRATOR)),
]
AdminOnly = Annotated[User, Depends(require_roles(UserRole.ADMINISTRATOR))]
ClinicalStaff = Annotated[
    User,
    Depends(require_roles(UserRole.TRIAGE_NURSE, UserRole.CLINICIAN)),
]
