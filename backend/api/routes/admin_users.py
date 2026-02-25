"""
Admin user management API routes.
"""

from datetime import datetime, timezone
from typing import Annotated, Optional
from math import ceil

from fastapi import APIRouter, Depends, HTTPException, status, Query, Request, Header
from sqlalchemy import select, func, or_, and_, desc, asc
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.database.connection import get_db
from infrastructure.database.models.user import User, UserRole, UserStatus
from infrastructure.database.models.admin import AdminAuditLog, AuditAction, AuditTargetType
from core.security.password import password_hasher
from core.security.tokens import TokenService
from infrastructure.config.settings import settings
from adapters.email.resend_adapter import email_service
from api.deps_admin import get_current_admin_user, get_current_super_admin_user
from api.utils import escape_like
from api.schemas.admin import (
    UserListResponse,
    UserListItemResponse,
    UserDetailResponse,
    UserUpdateRequest,
    SuspendUserRequest,
    UnsuspendUserRequest,
    PasswordResetRequest,
    UserActionResponse,
    DeleteUserResponse,
    AuditLogListResponse,
    AuditLogResponse,
    AdminUserInfo,
    UsageStatsResponse,
)

router = APIRouter(prefix="/admin", tags=["Admin - Users"])


# Initialize token service
token_service = TokenService(
    secret_key=settings.jwt_secret_key,
    algorithm=settings.jwt_algorithm,
    access_token_expire_minutes=settings.jwt_access_token_expire_minutes,
    refresh_token_expire_days=settings.jwt_refresh_token_expire_days,
)


# ============================================================================
# Helper Functions
# ============================================================================


async def create_audit_log(
    db: AsyncSession,
    admin_user: User,
    action: AuditAction,
    target_type: AuditTargetType,
    target_id: str,
    description: str,
    metadata: Optional[dict] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> AdminAuditLog:
    """
    Create an audit log entry for admin actions.
    """
    # Combine description, metadata, and user_agent into the details JSON field
    details = metadata.copy() if metadata else {}
    if description:
        details["description"] = description
    if user_agent:
        details["user_agent"] = user_agent

    audit_log = AdminAuditLog(
        admin_user_id=admin_user.id,
        action=action.value,
        target_type=target_type.value,
        target_id=target_id,
        details=details if details else None,
        ip_address=ip_address,
    )
    db.add(audit_log)
    await db.commit()
    await db.refresh(audit_log)
    return audit_log


def build_user_detail_response(user: User) -> UserDetailResponse:
    """Build detailed user response from user model."""
    return UserDetailResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        avatar_url=user.avatar_url,
        role=user.role,
        status=user.status,
        subscription_tier=user.subscription_tier,
        subscription_status=user.subscription_status,
        subscription_expires=user.subscription_expires,
        lemonsqueezy_customer_id=user.lemonsqueezy_customer_id,
        lemonsqueezy_subscription_id=user.lemonsqueezy_subscription_id,
        email_verified=user.email_verified,
        language=user.language,
        timezone=user.timezone,
        usage_stats=UsageStatsResponse(
            articles_generated=user.articles_generated_this_month,
            outlines_generated=user.outlines_generated_this_month,
            images_generated=user.images_generated_this_month,
            usage_reset_date=user.usage_reset_date,
        ),
        last_login=user.last_login,
        login_count=user.login_count,
        created_at=user.created_at,
        updated_at=user.updated_at,
        deleted_at=user.deleted_at,
    )


# ============================================================================
# User Management Endpoints
# ============================================================================


@router.get("/users", response_model=UserListResponse)
async def list_users(
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
    role: Optional[str] = Query(None, pattern="^(user|admin|super_admin)$"),
    subscription_tier: Optional[str] = Query(None, pattern="^(free|starter|professional|enterprise)$"),
    status: Optional[str] = Query(None, pattern="^(pending|active|suspended|deleted)$"),
    email_verified: Optional[bool] = Query(None),
    sort_by: str = Query("created_at", pattern="^(created_at|email|subscription_tier|last_login)$"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
) -> UserListResponse:
    """
    List all users with pagination and filtering.

    Admin access required.
    """
    # Build query
    query = select(User)

    # Apply filters
    filters = []

    if search:
        search_pattern = f"%{escape_like(search)}%"
        filters.append(
            or_(
                User.email.ilike(search_pattern),
                User.name.ilike(search_pattern),
            )
        )

    if role:
        filters.append(User.role == role)

    if subscription_tier:
        filters.append(User.subscription_tier == subscription_tier)

    if status:
        filters.append(User.status == status)

    if email_verified is not None:
        filters.append(User.email_verified == email_verified)

    if filters:
        query = query.where(and_(*filters))

    # Get total count
    count_query = select(func.count()).select_from(User)
    if filters:
        count_query = count_query.where(and_(*filters))
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Apply sorting
    sort_column = getattr(User, sort_by)
    if sort_order == "desc":
        query = query.order_by(desc(sort_column))
    else:
        query = query.order_by(asc(sort_column))

    # Apply pagination
    offset = (page - 1) * page_size
    query = query.limit(page_size).offset(offset)

    # Execute query
    result = await db.execute(query)
    users = result.scalars().all()

    # Calculate total pages
    total_pages = ceil(total / page_size) if total > 0 else 0

    # Build response
    return UserListResponse(
        users=[
            UserListItemResponse(
                id=user.id,
                email=user.email,
                name=user.name,
                role=user.role,
                status=user.status,
                subscription_tier=user.subscription_tier,
                email_verified=user.email_verified,
                last_login=user.last_login,
                created_at=user.created_at,
            )
            for user in users
        ],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/users/{user_id}", response_model=UserDetailResponse)
async def get_user_detail(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user),
) -> UserDetailResponse:
    """
    Get detailed information about a specific user.

    Admin access required.
    """
    # Get user
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return build_user_detail_response(user)


@router.put("/users/{user_id}", response_model=UserActionResponse)
async def update_user(
    user_id: str,
    request: UserUpdateRequest,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user),
    http_request: Request = None,
    user_agent: Optional[str] = Header(None),
) -> UserActionResponse:
    """
    Update user details (role, subscription, suspension status).

    Admin access required. Cannot demote yourself from super_admin.
    """
    # Get user
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Track changes for audit log
    changes = {}
    old_values = {}
    new_values = {}

    # Prevent self-demotion for super_admin
    if request.role and user.id == admin_user.id:
        if admin_user.role == UserRole.SUPER_ADMIN.value and request.role != UserRole.SUPER_ADMIN.value:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot demote yourself from super_admin role",
            )

    # Prevent privilege escalation: only super_admin can assign admin-level roles
    if request.role and request.role in [UserRole.SUPER_ADMIN.value, UserRole.ADMIN.value]:
        if admin_user.role != UserRole.SUPER_ADMIN.value:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only super admins can assign admin roles",
            )

    # Update role
    if request.role and request.role != user.role:
        old_values["role"] = user.role
        new_values["role"] = request.role
        user.role = request.role
        changes["role"] = f"{old_values['role']} -> {new_values['role']}"

    # Update subscription tier
    if request.subscription_tier and request.subscription_tier != user.subscription_tier:
        old_values["subscription_tier"] = user.subscription_tier
        new_values["subscription_tier"] = request.subscription_tier
        user.subscription_tier = request.subscription_tier
        changes["subscription_tier"] = f"{old_values['subscription_tier']} -> {new_values['subscription_tier']}"

    # Update suspension status
    if request.is_suspended is not None:
        old_status = user.status
        if request.is_suspended:
            user.status = UserStatus.SUSPENDED.value
            user.suspended_at = datetime.now(timezone.utc)
            if request.suspended_reason:
                # Store reason in metadata for now
                changes["suspended_reason"] = request.suspended_reason
        else:
            user.status = UserStatus.ACTIVE.value
            user.suspended_at = None

        if old_status != user.status:
            old_values["status"] = old_status
            new_values["status"] = user.status
            changes["status"] = f"{old_values['status']} -> {new_values['status']}"

    if not changes:
        return UserActionResponse(
            success=True,
            message="No changes were made",
            user=build_user_detail_response(user),
        )

    # Save changes
    await db.commit()
    await db.refresh(user)

    # Create audit log
    description = f"Updated user {user.email}: " + ", ".join(f"{k}={v}" for k, v in changes.items())
    await create_audit_log(
        db=db,
        admin_user=admin_user,
        action=AuditAction.USER_UPDATED,
        target_type=AuditTargetType.USER,
        target_id=user.id,
        description=description,
        metadata={
            "changes": changes,
            "old_values": old_values,
            "new_values": new_values,
        },
        ip_address=http_request.client.host if http_request else None,
        user_agent=user_agent,
    )

    return UserActionResponse(
        success=True,
        message=f"User updated successfully",
        user=build_user_detail_response(user),
    )


@router.post("/users/{user_id}/suspend", response_model=UserActionResponse)
async def suspend_user(
    user_id: str,
    request: SuspendUserRequest,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user),
    http_request: Request = None,
    user_agent: Optional[str] = Header(None),
) -> UserActionResponse:
    """
    Suspend a user account.

    Admin access required.
    """
    # Get user
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if user.status == UserStatus.SUSPENDED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already suspended",
        )

    # Suspend user
    old_status = user.status
    user.status = UserStatus.SUSPENDED.value
    user.suspended_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(user)

    # Create audit log
    await create_audit_log(
        db=db,
        admin_user=admin_user,
        action=AuditAction.USER_SUSPENDED,
        target_type=AuditTargetType.USER,
        target_id=user.id,
        description=f"Suspended user {user.email}: {request.reason}",
        metadata={
            "reason": request.reason,
            "old_status": old_status,
            "new_status": user.status,
            "suspended_at": user.suspended_at.isoformat(),
        },
        ip_address=http_request.client.host if http_request else None,
        user_agent=user_agent,
    )

    return UserActionResponse(
        success=True,
        message=f"User suspended successfully",
        user=build_user_detail_response(user),
    )


@router.post("/users/{user_id}/unsuspend", response_model=UserActionResponse)
async def unsuspend_user(
    user_id: str,
    request: UnsuspendUserRequest,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user),
    http_request: Request = None,
    user_agent: Optional[str] = Header(None),
) -> UserActionResponse:
    """
    Unsuspend a user account.

    Admin access required.
    """
    # Get user
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if user.status != UserStatus.SUSPENDED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not suspended",
        )

    # Unsuspend user
    old_status = user.status
    old_suspended_at = user.suspended_at
    user.status = UserStatus.ACTIVE.value
    user.suspended_at = None

    await db.commit()
    await db.refresh(user)

    # Create audit log
    await create_audit_log(
        db=db,
        admin_user=admin_user,
        action=AuditAction.USER_UNSUSPENDED,
        target_type=AuditTargetType.USER,
        target_id=user.id,
        description=f"Unsuspended user {user.email}" + (f": {request.reason}" if request.reason else ""),
        metadata={
            "reason": request.reason,
            "old_status": old_status,
            "new_status": user.status,
            "was_suspended_at": old_suspended_at.isoformat() if old_suspended_at else None,
        },
        ip_address=http_request.client.host if http_request else None,
        user_agent=user_agent,
    )

    return UserActionResponse(
        success=True,
        message=f"User unsuspended successfully",
        user=build_user_detail_response(user),
    )


@router.delete("/users/{user_id}", response_model=DeleteUserResponse)
async def delete_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(get_current_super_admin_user),
    soft_delete: bool = Query(True, description="Soft delete (true) or hard delete (false)"),
    http_request: Request = None,
    user_agent: Optional[str] = Header(None),
) -> DeleteUserResponse:
    """
    Delete a user account (soft or hard delete).

    Super admin access required.
    """
    # Get user
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Prevent self-deletion
    if user.id == admin_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot delete your own account",
        )

    deleted_at = datetime.now(timezone.utc)

    if soft_delete:
        # Soft delete: mark as deleted
        user.status = UserStatus.DELETED.value
        user.deleted_at = deleted_at
        await db.commit()

        message = "User soft deleted successfully"
    else:
        # Hard delete: actually remove from database
        # Note: This will cascade delete related records based on foreign key constraints
        await db.delete(user)
        await db.commit()

        message = "User hard deleted successfully (all data removed)"

    # Create audit log
    await create_audit_log(
        db=db,
        admin_user=admin_user,
        action=AuditAction.USER_DELETED,
        target_type=AuditTargetType.USER,
        target_id=user.id,
        description=f"{'Soft' if soft_delete else 'Hard'} deleted user {user.email}",
        metadata={
            "user_email": user.email,
            "user_name": user.name,
            "soft_delete": soft_delete,
            "deleted_at": deleted_at.isoformat(),
        },
        ip_address=http_request.client.host if http_request else None,
        user_agent=user_agent,
    )

    return DeleteUserResponse(
        success=True,
        message=message,
        user_id=user_id,
        deleted_at=deleted_at,
    )


@router.post("/users/{user_id}/reset-password", response_model=UserActionResponse)
async def force_password_reset(
    user_id: str,
    request: PasswordResetRequest,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user),
    http_request: Request = None,
    user_agent: Optional[str] = Header(None),
) -> UserActionResponse:
    """
    Force a password reset for a user.

    Generates a password reset token and optionally sends reset email.
    Admin access required.
    """
    # Get user
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Generate reset token
    reset_token = token_service.create_password_reset_token(user.id)
    user.password_reset_token = reset_token
    user.password_reset_expires = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(user)

    # Send email if requested
    if request.send_email:
        try:
            await email_service.send_password_reset_email(
                to_email=user.email,
                user_name=user.name,
                reset_token=reset_token,
            )
            email_sent = True
        except Exception as e:
            # Log error but don't fail the request
            email_sent = False
    else:
        email_sent = False

    # Create audit log
    await create_audit_log(
        db=db,
        admin_user=admin_user,
        action=AuditAction.USER_PASSWORD_RESET,
        target_type=AuditTargetType.USER,
        target_id=user.id,
        description=f"Forced password reset for user {user.email}",
        metadata={
            "email_sent": email_sent,
            "send_email_requested": request.send_email,
        },
        ip_address=http_request.client.host if http_request else None,
        user_agent=user_agent,
    )

    return UserActionResponse(
        success=True,
        message=f"Password reset token generated" + (" and email sent" if email_sent else ""),
        user=build_user_detail_response(user),
    )


# ============================================================================
# Audit Log Endpoints
# ============================================================================


@router.get("/audit-logs", response_model=AuditLogListResponse)
async def list_audit_logs(
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    admin_user_id: Optional[str] = Query(None),
    target_type: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    target_id: Optional[str] = Query(None),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
) -> AuditLogListResponse:
    """
    List admin audit logs with filtering and pagination.

    Admin access required.
    """
    # Build query with eager loading of admin_user relationship
    from sqlalchemy.orm import selectinload
    query = select(AdminAuditLog).options(selectinload(AdminAuditLog.admin_user))

    # Apply filters
    filters = []

    if admin_user_id:
        filters.append(AdminAuditLog.admin_user_id == admin_user_id)

    if target_type:
        filters.append(AdminAuditLog.target_type == target_type)

    if action:
        filters.append(AdminAuditLog.action == action)

    if target_id:
        filters.append(AdminAuditLog.target_id == target_id)

    if date_from:
        filters.append(AdminAuditLog.created_at >= date_from)

    if date_to:
        filters.append(AdminAuditLog.created_at <= date_to)

    if filters:
        query = query.where(and_(*filters))

    # Get total count
    count_query = select(func.count()).select_from(AdminAuditLog)
    if filters:
        count_query = count_query.where(and_(*filters))
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Apply sorting
    if sort_order == "desc":
        query = query.order_by(desc(AdminAuditLog.created_at))
    else:
        query = query.order_by(asc(AdminAuditLog.created_at))

    # Apply pagination
    offset = (page - 1) * page_size
    query = query.limit(page_size).offset(offset)

    # Execute query
    result = await db.execute(query)
    logs = result.scalars().all()

    # Calculate total pages
    total_pages = ceil(total / page_size) if total > 0 else 0

    # Build response
    return AuditLogListResponse(
        logs=[
            AuditLogResponse(
                id=log.id,
                admin_user_id=log.admin_user_id,
                admin_user=AdminUserInfo(
                    id=log.admin_user.id,
                    email=log.admin_user.email,
                    name=log.admin_user.name,
                ) if log.admin_user else None,
                action=log.action,
                target_type=log.target_type,
                target_id=log.target_id,
                description=log.description,
                metadata=log.metadata,
                ip_address=log.ip_address,
                user_agent=log.user_agent,
                created_at=log.created_at,
            )
            for log in logs
        ],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.post("/users/{user_id}/reset-usage", response_model=UserActionResponse)
async def reset_user_usage(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user),
    http_request: Request = None,
    user_agent: Optional[str] = Header(None),
) -> UserActionResponse:
    """
    Reset a user's monthly generation usage counters to zero.

    Admin access required.
    """
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    old_articles = user.articles_generated_this_month
    old_outlines = user.outlines_generated_this_month
    old_images = user.images_generated_this_month

    user.articles_generated_this_month = 0
    user.outlines_generated_this_month = 0
    user.images_generated_this_month = 0

    await db.commit()
    await db.refresh(user)

    # Create audit log
    await create_audit_log(
        db=db,
        admin_user=admin_user,
        action=AuditAction.USER_UPDATED,
        target_type=AuditTargetType.USER,
        target_id=user.id,
        description=f"Reset usage counters for {user.email}",
        metadata={
            "old_articles": old_articles,
            "old_outlines": old_outlines,
            "old_images": old_images,
        },
        ip_address=http_request.client.host if http_request else None,
        user_agent=user_agent,
    )

    return UserActionResponse(
        success=True,
        message=f"Usage counters reset for {user.email}",
        user=build_user_detail_response(user),
    )
