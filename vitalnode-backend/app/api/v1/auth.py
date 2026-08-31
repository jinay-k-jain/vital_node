from app.api.v1.utils import ev
"""
Authentication API - /api/v1/auth/*

POST /api/v1/auth/login   - login, receive JWT
GET  /api/v1/auth/me      - get current user info
POST /api/v1/auth/logout  - record logout in audit log (token invalidation is client-side for JWT)
"""
from datetime import timezone
from fastapi import APIRouter, HTTPException, status

from app.api.v1.deps import DbDep, CurrentUser
from app.core.config import get_settings
from app.core.exceptions import AuthenticationError
from app.schemas.auth import LoginRequest, LoginResponse, UserResponse
from app.services.auth_service import authenticate_user, issue_token
from app.services.audit_service import record_audit_event

router = APIRouter(prefix="/auth", tags=["Authentication"])
settings = get_settings()


@router.post(
    "/login",
    response_model=LoginResponse,
    summary="Staff login",
    description="Authenticate with staff ID and password. Returns a JWT access token.",
)
async def login(payload: LoginRequest, db: DbDep):
    try:
        user = await authenticate_user(db, payload.staff_id, payload.password)
    except AuthenticationError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "AUTHENTICATION_FAILED", "message": exc.message},
        )

    token = issue_token(user)

    # Audit login
    await record_audit_event(
        db=db,
        event_type="LOGIN",
        user_id=user.id,
        user_staff_id=user.staff_id,
        user_name=user.name,
        user_role=ev(user.role),
    )

    user_response = UserResponse(
        id=str(user.id),
        name=user.name,
        role=ev(user.role),
        staffId=user.staff_id,
        department=user.department,
    )

    return LoginResponse(
        access_token=token,
        token_type="bearer",
        expires_in=settings.jwt_access_token_expire_minutes * 60,
        user=user_response,
    )


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user",
    description="Returns the authenticated user's profile.",
)
async def me(current_user: CurrentUser):
    return UserResponse(
        id=str(current_user.id),
        name=current_user.name,
        role=current_ev(user.role),
        staffId=current_user.staff_id,
        department=current_user.department,
    )


@router.post(
    "/logout",
    summary="Logout",
    description="Records the logout event in the audit log. The client must discard its token.",
)
async def logout(current_user: CurrentUser, db: DbDep):
    await record_audit_event(
        db=db,
        event_type="LOGOUT",
        user_id=current_user.id,
        user_staff_id=current_user.staff_id,
        user_name=current_user.name,
        user_role=current_ev(user.role),
    )
    return {"message": "Logged out successfully"}
