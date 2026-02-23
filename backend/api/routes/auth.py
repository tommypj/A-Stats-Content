"""
Authentication API routes.
"""

from datetime import datetime, timezone, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status, Header, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.database.connection import get_db
from infrastructure.database.models.user import User, UserStatus
from infrastructure.config.settings import settings
from core.security.password import password_hasher
from core.security.tokens import TokenService
from adapters.email.resend_adapter import email_service
from api.middleware.rate_limit import limiter
from api.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
    UserUpdateRequest,
    RefreshTokenRequest,
    PasswordResetRequest,
    PasswordResetConfirm,
    PasswordChangeRequest,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])

# Initialize token service
token_service = TokenService(
    secret_key=settings.jwt_secret_key,
    algorithm=settings.jwt_algorithm,
    access_token_expire_minutes=settings.jwt_access_token_expire_minutes,
    refresh_token_expire_days=settings.jwt_refresh_token_expire_days,
)


class VerifyEmailRequest(BaseModel):
    """Request body for email verification."""

    token: str


class ResendVerificationRequest(BaseModel):
    """Request body for resending email verification."""

    email: str


async def get_current_user(
    authorization: Annotated[str | None, Header()] = None,
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Dependency to get the current authenticated user.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = authorization.split(" ")[1]
    payload = token_service.verify_access_token(token)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Get user from database
    result = await db.execute(select(User).where(User.id == payload.sub))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is not active",
        )

    # Reject tokens issued before the user's last security event (password change/reset).
    # updated_at is bumped explicitly on password change and reset, so any token
    # issued before that moment is no longer valid.
    if payload.iat and user.updated_at:
        token_iat = payload.iat
        # Ensure both datetimes are timezone-aware for comparison
        user_updated = user.updated_at
        if user_updated.tzinfo is None:
            user_updated = user_updated.replace(tzinfo=timezone.utc)
        if user_updated > token_iat:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token invalidated due to security event",
                headers={"WWW-Authenticate": "Bearer"},
            )

    return user


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("3/minute")
async def register(
    request: Request,
    register_data: RegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Register a new user account.
    """
    # Check if email already exists
    result = await db.execute(select(User).where(User.email == register_data.email.lower()))
    existing_user = result.scalar_one_or_none()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email already exists",
        )

    # Create new user
    user = User(
        email=register_data.email.lower(),
        name=register_data.name,
        password_hash=password_hasher.hash(register_data.password),
        language=register_data.language,
        status=UserStatus.PENDING.value,
    )

    db.add(user)
    await db.commit()
    await db.refresh(user)

    # Send verification email
    verification_token = token_service.create_email_verification_token(
        user.id, user.email
    )
    user.email_verification_token = verification_token
    await db.commit()

    await email_service.send_verification_email(
        to_email=user.email,
        user_name=user.name,
        verification_token=verification_token,
    )

    return user


@router.post("/login", response_model=TokenResponse)
@limiter.limit("5/minute")
async def login(
    request: Request,
    login_data: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Authenticate user and return access tokens.
    """
    # Find user by email
    result = await db.execute(
        select(User).where(User.email == login_data.email.lower())
    )
    user = result.scalar_one_or_none()

    if not user or not password_hasher.verify(login_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if user.status == UserStatus.SUSPENDED.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account has been suspended",
        )

    if user.status == UserStatus.DELETED.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account has been deleted",
        )

    # Update login tracking
    user.last_login = datetime.now(timezone.utc)
    user.login_count += 1
    await db.commit()

    # Create tokens
    access_token, refresh_token = token_service.create_token_pair(
        user_id=user.id,
        email=user.email,
        role=user.role,
    )

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": settings.jwt_access_token_expire_minutes * 60,
    }


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Refresh access token using refresh token.
    """
    payload = token_service.verify_refresh_token(request.refresh_token)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    # Get user from database
    result = await db.execute(select(User).where(User.id == payload.sub))
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    # Create new tokens
    access_token, refresh_token = token_service.create_token_pair(
        user_id=user.id,
        email=user.email,
        role=user.role,
    )

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": settings.jwt_access_token_expire_minutes * 60,
    }


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """
    Get current authenticated user profile.
    """
    return current_user


@router.put("/me", response_model=UserResponse)
async def update_me(
    update_data: UserUpdateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Update current authenticated user profile.
    """
    if update_data.name is not None:
        current_user.name = update_data.name
    if update_data.language is not None:
        current_user.language = update_data.language
    if update_data.timezone is not None:
        current_user.timezone = update_data.timezone
    await db.commit()
    await db.refresh(current_user)
    return current_user


@router.post("/password/reset-request", status_code=status.HTTP_202_ACCEPTED)
@limiter.limit("3/hour")
async def request_password_reset(
    request: Request,
    reset_data: PasswordResetRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Request a password reset email.
    """
    # Find user by email
    result = await db.execute(
        select(User).where(User.email == reset_data.email.lower())
    )
    user = result.scalar_one_or_none()

    # Always return success to prevent email enumeration
    if user and user.is_active:
        # Create reset token
        reset_token = token_service.create_password_reset_token(user.id)
        user.password_reset_token = reset_token
        user.password_reset_expires = datetime.now(timezone.utc) + timedelta(hours=1)
        await db.commit()

        # Send password reset email
        await email_service.send_password_reset_email(
            to_email=user.email,
            user_name=user.name,
            reset_token=reset_token,
        )

    return {"message": "If the email exists, a password reset link has been sent"}


@router.post("/password/reset", status_code=status.HTTP_200_OK)
async def reset_password(
    request: PasswordResetConfirm,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Reset password using reset token.
    """
    # Verify token
    user_id = token_service.verify_password_reset_token(request.token)

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )

    # Find user
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )

    if not user.password_reset_token or user.password_reset_token != request.token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or already used reset token",
        )

    if user.password_reset_expires and user.password_reset_expires < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password reset token has expired",
        )

    # Update password and bump updated_at so existing tokens are invalidated
    user.password_hash = password_hasher.hash(request.new_password)
    user.password_reset_token = None
    user.password_reset_expires = None
    user.updated_at = datetime.now(timezone.utc)
    await db.commit()

    return {"message": "Password has been reset successfully"}


@router.post("/password/change", status_code=status.HTTP_200_OK)
async def change_password(
    request: PasswordChangeRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Change password for authenticated user.
    """
    # Verify current password
    if not password_hasher.verify(request.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    # Update password and bump updated_at so existing tokens are invalidated
    current_user.password_hash = password_hasher.hash(request.new_password)
    current_user.updated_at = datetime.now(timezone.utc)
    await db.commit()

    return {"message": "Password has been changed successfully"}


@router.post("/verify-email", status_code=status.HTTP_200_OK)
@limiter.limit("5/hour")
async def verify_email(
    request: Request,
    body: VerifyEmailRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Verify email address using verification token.
    """
    # Verify token
    result = token_service.verify_email_verification_token(body.token)

    if not result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification token",
        )

    user_id, email = result

    # Find user
    db_result = await db.execute(
        select(User).where(User.id == user_id, User.email == email)
    )
    user = db_result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification token",
        )

    if user.email_verified:
        return {"message": "Email is already verified"}

    # Update user
    user.email_verified = True
    user.status = UserStatus.ACTIVE.value
    user.email_verification_token = None
    user.email_verification_expires = None
    await db.commit()

    return {"message": "Email has been verified successfully"}


@router.post("/resend-verification", status_code=status.HTTP_202_ACCEPTED)
@limiter.limit("5/hour")
async def resend_verification(
    request: Request,
    body: ResendVerificationRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Resend email verification.
    """
    # Find user by email
    result = await db.execute(
        select(User).where(User.email == body.email.lower())
    )
    user = result.scalar_one_or_none()

    # Always return success to prevent email enumeration
    if user and not user.email_verified:
        # Create verification token
        verification_token = token_service.create_email_verification_token(
            user.id, user.email
        )
        user.email_verification_token = verification_token
        await db.commit()

        await email_service.send_verification_email(
            to_email=user.email,
            user_name=user.name,
            verification_token=verification_token,
        )

    return {"message": "If the email exists and is not verified, a verification link has been sent"}


@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """
    Logout current user.

    Note: JWT tokens are stateless, so individual token blacklisting requires
    Redis or a similar store (not implemented here). The client must discard
    the token on logout. Password change and password reset do invalidate all
    previously issued tokens via the updated_at timestamp check in get_current_user().
    """
    return {"message": "Logged out successfully"}
