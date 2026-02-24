"""
Authentication API routes.
"""

import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status, Header, Request, UploadFile, File
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select, delete
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
        if pwd_changed > token_iat:
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
@limiter.limit("10/minute")
async def refresh_token(
    request: Request,
    body: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Refresh access token using refresh token.
    """
    payload = token_service.verify_refresh_token(body.refresh_token)

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

    # Update password and bump password_changed_at so existing tokens are invalidated
    user.password_hash = password_hasher.hash(request.new_password)
    user.password_reset_token = None
    user.password_reset_expires = None
    user.password_changed_at = datetime.now(timezone.utc)
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

    # Update password and bump password_changed_at so existing tokens are invalidated
    current_user.password_hash = password_hasher.hash(request.new_password)
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

    logger.info("Account deleted successfully for user_id=%s", user_id)

    return {"message": "Account deleted successfully"}


# Maximum avatar file size: 2 MB
_AVATAR_MAX_SIZE = 2 * 1024 * 1024
_AVATAR_ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}


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

    # Determine extension from content type
    ext_map = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}
    ext = ext_map.get(file.content_type, "jpg")
    filename = f"avatar_{current_user.id}.{ext}"

    # Delete old avatar if it exists
    if current_user.avatar_url:
        try:
            await storage_adapter.delete_image(current_user.avatar_url)
        except Exception:
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

    # Articles
    result = await db.execute(select(Article).where(Article.user_id == user_id))
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

    # Outlines
    result = await db.execute(select(Outline).where(Outline.user_id == user_id))
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
    result = await db.execute(select(ProjectMember).where(ProjectMember.user_id == user_id))
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
