"""
Authentication API routes.
"""

import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Annotated, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, status, Header, Request, UploadFile, File
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select, delete, and_
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.database.connection import get_db
from infrastructure.database.models.user import User, UserStatus
from infrastructure.database.models.project import Project, ProjectMember
from infrastructure.database.models.content import Article, Outline, GeneratedImage
from infrastructure.database.models.knowledge import KnowledgeSource
from infrastructure.database.models.social import ScheduledPost, PostTarget
from infrastructure.database.models.analytics import GSCConnection
from infrastructure.config.settings import settings
from adapters.storage.image_storage import storage_adapter
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
    DeleteAccountRequest,
)

logger = logging.getLogger(__name__)


def _get_cookie_kwargs(settings_obj) -> dict:
    """Return cookie kwargs based on environment.

    Uses SameSite=None; Secure=True whenever the frontend is deployed to a
    non-localhost domain — this handles Railway deployments where ENVIRONMENT
    may not be explicitly set to 'production' but the frontend is on Vercel.
    SameSite=Lax is kept for local development (same-origin, HTTP-safe).
    """
    is_production = getattr(settings_obj, 'environment', 'development') == 'production'
    # Also treat as cross-site when FRONTEND_URL is not localhost
    frontend_url = getattr(settings_obj, 'frontend_url', 'http://localhost:3000')
    is_deployed = not any(h in frontend_url for h in ('localhost', '127.0.0.1', '0.0.0.0'))
    use_cross_site = is_production or is_deployed
    kwargs = dict(
        httponly=True,
        secure=use_cross_site,
        samesite="none" if use_cross_site else "lax",
        path="/",
    )
    cookie_domain = getattr(settings_obj, 'cookie_domain', None)
    if cookie_domain:
        kwargs['domain'] = cookie_domain
    return kwargs


def _set_auth_cookies(response: JSONResponse, access_token: str, refresh_token: str, settings_obj) -> None:
    """Set HttpOnly auth cookies on response."""
    kwargs = _get_cookie_kwargs(settings_obj)
    # Access token: same expiry as JWT (in seconds)
    access_max_age = getattr(settings_obj, 'jwt_access_token_expire_minutes', 60) * 60
    # Refresh token: 7 days default
    refresh_max_age = getattr(settings_obj, 'jwt_refresh_token_expire_days', 7) * 86400
    response.set_cookie("access_token", access_token, max_age=access_max_age, **kwargs)
    response.set_cookie("refresh_token", refresh_token, max_age=refresh_max_age, **kwargs)


def _clear_auth_cookies(response: JSONResponse, settings_obj) -> None:
    """Clear auth cookies on logout."""
    kwargs = _get_cookie_kwargs(settings_obj)
    response.delete_cookie("access_token", **kwargs)
    response.delete_cookie("refresh_token", **kwargs)


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
    request: Request,
    authorization: Annotated[str | None, Header()] = None,
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Dependency to get the current authenticated user.

    Checks the Authorization header first (Bearer token) for backward compatibility
    with existing API clients. Falls back to the HttpOnly access_token cookie for
    browser-based requests using the new cookie auth flow.
    """
    # Try Authorization header first (API clients, tests, backward compat)
    token = None
    if authorization and authorization.startswith("Bearer "):
        parts = authorization.split(" ", 1)
        token = parts[1] if len(parts) > 1 and parts[1] else None  # AUTH-20: guard empty/missing token

    # Fall back to HttpOnly cookie
    if not token:
        token = request.cookies.get("access_token")

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

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

    # Reject tokens issued before the user's last password change/reset.
    # password_changed_at is set *only* on explicit security events, unlike
    # updated_at which fires on any row modification (login tracking, usage
    # resets, etc.) via the onupdate trigger.
    if payload.iat and user.password_changed_at:
        token_iat = payload.iat
        # Ensure both datetimes are timezone-aware for comparison
        pwd_changed = user.password_changed_at
        if pwd_changed.tzinfo is None:
            pwd_changed = pwd_changed.replace(tzinfo=timezone.utc)
        if token_iat < pwd_changed:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token invalidated due to security event",
                headers={"WWW-Authenticate": "Bearer"},
            )

    # Validate project membership if user has a current_project_id set.
    # A user could have been removed from the project after switching to it;
    # reset to personal workspace if membership no longer exists.
    if user.current_project_id:
        membership = await db.execute(
            select(ProjectMember.id).where(
                and_(
                    ProjectMember.project_id == user.current_project_id,
                    ProjectMember.user_id == user.id,
                    ProjectMember.deleted_at.is_(None),
                )
            )
        )
        if not membership.scalar_one_or_none():
            # Reset to personal project instead of NULL
            personal = await db.execute(
                select(Project.id).where(
                    Project.owner_id == user.id,
                    Project.is_personal == True,
                    Project.deleted_at.is_(None),
                )
            )
            personal_project_id = personal.scalar_one_or_none()
            if personal_project_id is None:
                # AUTH-22: personal workspace missing — clear gracefully, log for operator
                logger.warning(
                    "AUTH-22: No personal workspace found for user %s while resetting "
                    "current_project_id. Clearing to None.",
                    user.id,
                )
            user.current_project_id = personal_project_id
            # AUTH-11: use flush() instead of commit() inside a dependency to avoid
            # interfering with the calling route's transaction boundary.
            await db.flush()

    return user


async def create_personal_project(db: AsyncSession, user: User) -> Project:
    """Create a personal workspace project for a user."""
    from infrastructure.database.models.project import ProjectMemberRole

    project = Project(
        name="Personal Workspace",
        slug=f"personal-{str(user.id)[:8]}",
        owner_id=user.id,
        is_personal=True,
        subscription_tier=user.subscription_tier or "free",
        subscription_status=user.subscription_status or "active",
        max_members=1,
    )
    db.add(project)
    await db.flush()

    member = ProjectMember(
        project_id=project.id,
        user_id=user.id,
        role=ProjectMemberRole.OWNER.value,
    )
    db.add(member)

    user.current_project_id = project.id
    await db.flush()

    return project


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

    # Create personal workspace project
    await create_personal_project(db, user)
    await db.commit()
    await db.refresh(user)

    # Send verification email
    verification_token = token_service.create_email_verification_token(
        user.id, user.email
    )
    user.email_verification_token = verification_token
    await db.commit()

    # AUTH-08: Catch email service errors so registration still succeeds.
    try:
        await email_service.send_verification_email(
            to_email=user.email,
            user_name=user.name,
            verification_token=verification_token,
        )
    except Exception as email_err:
        logger.error("Failed to send verification email to %s: %s", user.email, email_err)

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

    # AUTH-03: Always run bcrypt to prevent timing-based user-existence enumeration.
    # When user is not found, verify against a dummy hash (result is discarded).
    _DUMMY_HASH = "$2b$12$WmDNGEj9s7YLV5sV/N7aBOpWL0.T5.R5ZQOeKHNlLB.d7WN4HFXIC"
    password_ok = password_hasher.verify(
        login_data.password,
        user.password_hash if user else _DUMMY_HASH,
    )
    if not user or not password_ok:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    # AUTH-04: Reject inactive accounts (covers deleted_at soft-delete and any future statuses).
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive",
        )

    # INFRA-AUTH-05: Block unverified (PENDING) users even if is_active is True
    if user.status == UserStatus.PENDING.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Please verify your email address before logging in",
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

    # Return tokens in the JSON body (backward compat) AND set HttpOnly cookies
    # for browser-based clients (XSS protection).
    response_data = {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": settings.jwt_access_token_expire_minutes * 60,
    }
    response = JSONResponse(content=response_data)
    _set_auth_cookies(response, access_token, refresh_token, settings)
    return response


@router.post("/refresh", response_model=TokenResponse)
@limiter.limit("5/minute")  # AUTH-14: tightened from 10/min to match login limit
async def refresh_token(
    request: Request,
    body: Optional[RefreshTokenRequest] = Body(None),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Refresh access token using refresh token.

    Accepts the refresh token from the HttpOnly cookie first (browser clients),
    then falls back to the request body (API clients / backward compat).
    RefreshTokenRequest.refresh_token is now Optional so body-only requests
    that omit it are valid when the cookie is present.
    """
    # Try cookie first, then fall back to request body
    refresh_tok = request.cookies.get("refresh_token")
    if not refresh_tok:
        refresh_tok = body.refresh_token if body and body.refresh_token else None

    if not refresh_tok:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token required",
        )

    payload = token_service.verify_refresh_token(refresh_tok)

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

    # AUTH-01: Reject tokens issued before the last password change
    if user.password_changed_at:
        pwd_changed = user.password_changed_at
        if pwd_changed.tzinfo is None:
            pwd_changed = pwd_changed.replace(tzinfo=timezone.utc)
        # AUTH-21: guard against payload.iat being None (malformed token)
        if payload.iat and payload.iat < pwd_changed:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token invalidated due to password change. Please log in again.",
            )

    # Create new tokens
    access_token, refresh_token = token_service.create_token_pair(
        user_id=user.id,
        email=user.email,
        role=user.role,
    )

    # Return tokens in the JSON body (backward compat) AND rotate the HttpOnly
    # cookies so the next refresh cycle picks up the new refresh token.
    response_data = {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": settings.jwt_access_token_expire_minutes * 60,
    }
    response = JSONResponse(content=response_data)
    _set_auth_cookies(response, access_token, refresh_token, settings)
    return response


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

        # AUTH-08: Catch email service errors — still return success to caller.
        try:
            await email_service.send_password_reset_email(
                to_email=user.email,
                user_name=user.name,
                reset_token=reset_token,
            )
        except Exception as email_err:
            logger.error("Failed to send password reset email to %s: %s", user.email, email_err)

    return {"message": "If the email exists, a password reset link has been sent"}


@router.post("/password/reset", status_code=status.HTTP_200_OK)
@limiter.limit("3/hour")
async def reset_password(
    request: Request,
    body: PasswordResetConfirm,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Reset password using reset token.
    """
    # Verify token
    user_id = token_service.verify_password_reset_token(body.token)

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

    if not user.password_reset_token or user.password_reset_token != body.token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or already used reset token",
        )

    if user.password_reset_expires and user.password_reset_expires < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password reset token has expired",
        )

    # Update password and bump password_changed_at so existing tokens are invalidated
    user.password_hash = password_hasher.hash(body.new_password)
    user.password_reset_token = None
    user.password_reset_expires = None
    user.password_changed_at = datetime.now(timezone.utc)
    await db.commit()

    return {"message": "Password has been reset successfully"}


@router.post("/password/change", status_code=status.HTTP_200_OK)
@limiter.limit("5/minute")  # AUTH-15: tightened from 10/min (password changes should be rare)
async def change_password(
    request: Request,
    body: PasswordChangeRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Change password for authenticated user.
    """
    # Verify current password
    if not password_hasher.verify(body.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    # Update password and bump password_changed_at so existing tokens are invalidated
    current_user.password_hash = password_hasher.hash(body.new_password)
    current_user.password_changed_at = datetime.now(timezone.utc)
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

    # Send welcome email (fire-and-forget — failure does not block verification)
    try:
        await email_service.send_welcome_email(
            to_email=user.email,
            user_name=user.name or user.email,
        )
    except Exception as e:
        logger.error("Failed to send welcome email to %s: %s", user.email, e)

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
        try:
            verification_token = token_service.create_email_verification_token(
                user.id, user.email
            )
            user.email_verification_token = verification_token
            await db.commit()
        except Exception as db_err:
            # AUTH-19: DB failure is non-fatal — still return success to prevent enumeration
            logger.error("Failed to save verification token for user %s: %s", user.id, db_err)
            return {"message": "If the email exists and is not verified, a verification link has been sent"}

        try:
            await email_service.send_verification_email(
                to_email=user.email,
                user_name=user.name,
                verification_token=verification_token,
            )
        except Exception as email_err:
            logger.error("Failed to send verification email to %s: %s", user.email, email_err)

    return {"message": "If the email exists and is not verified, a verification link has been sent"}


@router.post("/logout", status_code=status.HTTP_200_OK)
@limiter.limit("20/minute")  # INFRA-11: prevent logout endpoint abuse
async def logout(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
) -> JSONResponse:
    """
    Logout current user.

    Note: JWT tokens are stateless, so individual token blacklisting requires
    Redis or a similar store (not implemented here). The client must discard
    the token on logout. Password change and password reset do invalidate all
    previously issued tokens via the password_changed_at timestamp check in
    get_current_user().

    Clears the HttpOnly auth cookies so browser-based clients are fully signed
    out without relying on the client-side token deletion.
    """
    response = JSONResponse(content={"message": "Logged out successfully"})
    _clear_auth_cookies(response, settings)
    return response


@router.delete("/account", status_code=status.HTTP_200_OK)
async def delete_account(
    body: DeleteAccountRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Permanently delete the current user's account and all associated data.

    The request body must contain {"confirmation": "DELETE MY ACCOUNT"} to
    prevent accidental deletion.  Deletion is hard (no soft-delete) and
    cascades in the following order:

    1. Projects where the user is the *sole* owner are fully deleted
       (cascade removes their content — articles, outlines, images — via
       the database-level ON DELETE CASCADE constraints on project_id).
    2. The user's membership rows in projects they do *not* solely own are
       deleted so other members retain their data.
    3. GSC connections owned by the user are deleted.
    4. Content (articles, outlines, images) that is tied to the user but
       belongs to no project is removed via the ON DELETE CASCADE on user_id,
       triggered when the user row itself is deleted.
    5. The user row is deleted.
    """
    _CONFIRMATION_PHRASE = "DELETE MY ACCOUNT"

    if body.confirmation != _CONFIRMATION_PHRASE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Confirmation text must be exactly '{_CONFIRMATION_PHRASE}'",
        )

    user_id = current_user.id

    logger.info("Account deletion initiated for user_id=%s email=%s", user_id, current_user.email)

    # AUTH-25: All deletion steps wrapped in a single try/except — any partial failure
    # triggers a full rollback so the DB is never left in an inconsistent state.
    try:
        # ------------------------------------------------------------------
        # Step 1: Find all projects where this user is the owner.
        # ------------------------------------------------------------------
        owned_projects_result = await db.execute(
            select(Project).where(Project.owner_id == user_id, Project.deleted_at.is_(None))
        )
        owned_projects = owned_projects_result.scalars().all()

        for project in owned_projects:
            # Count *other* owners (members with role == "owner" who are not this user)
            other_owners_result = await db.execute(
                select(ProjectMember).where(
                    ProjectMember.project_id == project.id,
                    ProjectMember.user_id != user_id,
                    ProjectMember.role == "owner",
                    ProjectMember.deleted_at.is_(None),
                )
            )
            other_owners = other_owners_result.scalars().all()

            if not other_owners:
                # Sole owner — delete the project entirely.
                # ON DELETE CASCADE on project_id will remove all content,
                # memberships and invitations for this project.
                await db.delete(project)
                logger.info("Deleted project project_id=%s (sole owner)", project.id)
            else:
                # Other owners exist — just remove this user's membership row so
                # the project survives.
                await db.execute(
                    delete(ProjectMember).where(
                        ProjectMember.project_id == project.id,
                        ProjectMember.user_id == user_id,
                    )
                )
                logger.info(
                    "Removed ownership membership from project_id=%s (other owners remain)",
                    project.id,
                )

        # ------------------------------------------------------------------
        # Step 2: Remove this user from projects they do NOT own (member rows).
        # ------------------------------------------------------------------
        await db.execute(
            delete(ProjectMember).where(ProjectMember.user_id == user_id)
        )

        # ------------------------------------------------------------------
        # Step 3: Delete GSC connections.
        # ------------------------------------------------------------------
        await db.execute(
            delete(GSCConnection).where(GSCConnection.user_id == user_id)
        )

        # ------------------------------------------------------------------
        # Step 4: Delete the user record itself.
        #
        # ON DELETE CASCADE on user_id in articles, outlines, generated_images,
        # article_revisions etc. handles any remaining user-level content.
        # ------------------------------------------------------------------
        await db.delete(current_user)
        await db.commit()

    except Exception:
        await db.rollback()
        logger.error("Account deletion failed for user_id=%s", user_id, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Account deletion failed. Please contact support.",
        )

    logger.info("Account deleted successfully for user_id=%s", user_id)

    return {"message": "Account deleted successfully"}


# Maximum avatar file size: 2 MB
_AVATAR_MAX_SIZE = 2 * 1024 * 1024
_AVATAR_ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}

# Magic bytes for supported image formats (server-side validation independent of Content-Type header)
_AVATAR_MAGIC_BYTES = {
    b'\xff\xd8\xff': 'image/jpeg',
    b'\x89PNG': 'image/png',
    b'GIF8': 'image/gif',
    b'RIFF': 'image/webp',  # RIFF....WEBP
}


@router.post("/me/avatar", response_model=UserResponse)
@limiter.limit("10/minute")
async def upload_avatar(
    request: Request,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Upload or replace the current user's profile avatar.

    Accepts JPEG, PNG, or WebP images up to 2 MB.
    """
    # Validate content type
    if file.content_type not in _AVATAR_ALLOWED_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type '{file.content_type}'. Allowed: JPEG, PNG, WebP.",
        )

    # Read and validate size
    image_data = await file.read()
    if len(image_data) > _AVATAR_MAX_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File too large. Maximum size is 2 MB.",
        )

    if len(image_data) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    # Validate actual file content via magic bytes (mitigates spoofed Content-Type headers)
    if not any(image_data.startswith(magic) for magic in _AVATAR_MAGIC_BYTES):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid image file format",
        )

    # Determine extension from content type
    ext_map = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}
    ext = ext_map.get(file.content_type, "jpg")
    filename = f"avatar_{current_user.id}.{ext}"

    # Delete old avatar if it exists
    if current_user.avatar_url:
        try:
            await storage_adapter.delete_image(current_user.avatar_url)
        except OSError:
            logger.warning("Failed to delete old avatar for user %s", current_user.id)

    # Save new avatar
    saved_path = await storage_adapter.save_image(image_data, filename)
    current_user.avatar_url = saved_path
    await db.commit()
    await db.refresh(current_user)

    logger.info("Avatar uploaded for user_id=%s path=%s", current_user.id, saved_path)
    return current_user


@router.get("/me/export")
@limiter.limit("1/hour")
async def export_my_data(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Export all data associated with the current user (GDPR data portability).

    Returns a JSON file containing the user's profile, articles, outlines,
    images (metadata), knowledge sources, social posts, GSC connections,
    and project memberships.
    """
    user_id = current_user.id

    # Profile
    profile_data = {
        "id": str(current_user.id),
        "email": current_user.email,
        "name": current_user.name,
        "language": current_user.language,
        "timezone": current_user.timezone,
        "avatar_url": current_user.avatar_url,
        "subscription_tier": current_user.subscription_tier,
        "subscription_status": current_user.subscription_status,
        "email_verified": current_user.email_verified,
        "created_at": current_user.created_at.isoformat() if current_user.created_at else None,
        "last_login": current_user.last_login.isoformat() if current_user.last_login else None,
    }

    # Articles — AUTH-24: exclude soft-deleted rows
    result = await db.execute(
        select(Article).where(Article.user_id == user_id, Article.deleted_at.is_(None))
    )
    articles = [
        {
            "id": str(a.id),
            "title": a.title,
            "keyword": a.keyword,
            "status": a.status,
            "content": a.content,
            "meta_description": a.meta_description,
            "word_count": a.word_count,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        }
        for a in result.scalars().all()
    ]

    # Outlines — AUTH-24: exclude soft-deleted rows
    result = await db.execute(
        select(Outline).where(Outline.user_id == user_id, Outline.deleted_at.is_(None))
    )
    outlines = [
        {
            "id": str(o.id),
            "title": o.title,
            "keyword": o.keyword,
            "status": o.status,
            "sections": o.sections,
            "created_at": o.created_at.isoformat() if o.created_at else None,
        }
        for o in result.scalars().all()
    ]

    # Images (metadata only)
    result = await db.execute(select(GeneratedImage).where(GeneratedImage.user_id == user_id))
    images = [
        {
            "id": str(img.id),
            "prompt": img.prompt,
            "alt_text": img.alt_text,
            "style": img.style,
            "width": img.width,
            "height": img.height,
            "status": img.status,
            "created_at": img.created_at.isoformat() if img.created_at else None,
        }
        for img in result.scalars().all()
    ]

    # Knowledge sources
    result = await db.execute(select(KnowledgeSource).where(KnowledgeSource.user_id == user_id))
    knowledge = [
        {
            "id": str(k.id),
            "title": k.title,
            "filename": k.filename,
            "file_type": k.file_type,
            "file_size": k.file_size,
            "status": k.status,
            "tags": k.tags,
            "created_at": k.created_at.isoformat() if k.created_at else None,
        }
        for k in result.scalars().all()
    ]

    # Social posts
    result = await db.execute(select(ScheduledPost).where(ScheduledPost.user_id == user_id))
    social_posts = [
        {
            "id": str(p.id),
            "content": p.content,
            "status": p.status,
            "scheduled_at": p.scheduled_at.isoformat() if p.scheduled_at else None,
            "published_at": p.published_at.isoformat() if p.published_at else None,
            "created_at": p.created_at.isoformat() if p.created_at else None,
        }
        for p in result.scalars().all()
    ]

    # GSC connections
    result = await db.execute(select(GSCConnection).where(GSCConnection.user_id == user_id))
    gsc_connections = [
        {
            "id": str(g.id),
            "site_url": g.site_url,
            "created_at": g.created_at.isoformat() if g.created_at else None,
        }
        for g in result.scalars().all()
    ]

    # Project memberships
    result = await db.execute(select(ProjectMember).where(ProjectMember.user_id == user_id, ProjectMember.deleted_at.is_(None)))
    memberships = [
        {
            "project_id": str(m.project_id),
            "role": m.role,
            "created_at": m.created_at.isoformat() if m.created_at else None,
        }
        for m in result.scalars().all()
    ]

    export = {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "profile": profile_data,
        "articles": articles,
        "outlines": outlines,
        "images": images,
        "knowledge_sources": knowledge,
        "social_posts": social_posts,
        "gsc_connections": gsc_connections,
        "project_memberships": memberships,
    }

    export_json = json.dumps(export, indent=2, default=str)

    return StreamingResponse(
        iter([export_json]),
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="user_data_export_{user_id}.json"',
        },
    )
