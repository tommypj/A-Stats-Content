"""
Social media scheduling API routes.
"""

import secrets
from datetime import datetime, timezone, date
from typing import Optional, List
import math

from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from api.schemas.social import (
    ConnectAccountResponse,
    SocialAccountResponse,
    SocialAccountListResponse,
    DisconnectAccountResponse,
    VerifyAccountResponse,
    CreatePostRequest,
    UpdatePostRequest,
    ScheduledPostResponse,
    ScheduledPostListResponse,
    PostTargetResponse,
    CalendarResponse,
    CalendarDay,
    CalendarDayPost,
    PostAnalyticsResponse,
    PlatformAnalytics,
    PreviewRequest,
    PreviewResponse,
    PlatformLimits,
    BestTimesResponse,
    BestTimeSlot,
)
from api.routes.auth import get_current_user
from infrastructure.database.connection import get_db
from infrastructure.database.models import (
    User,
    SocialAccount,
    ScheduledPost,
    PostTarget,
    Platform,
    PostStatus,
)
from infrastructure.config.settings import settings
from core.security.encryption import encrypt_credential, decrypt_credential

router = APIRouter(prefix="/social", tags=["Social Media"])


# ============================================
# Platform Configuration
# ============================================

PLATFORM_LIMITS = {
    Platform.TWITTER.value: {"chars": 280, "images": 4, "video": 1},
    Platform.LINKEDIN.value: {"chars": 3000, "images": 20, "video": 1},
    Platform.FACEBOOK.value: {"chars": 63206, "images": 10, "video": 1},
    Platform.INSTAGRAM.value: {"chars": 2200, "images": 10, "video": 1},
}


def validate_content_length(content: str, platform: str) -> tuple[bool, Optional[str]]:
    """
    Validate content length for a platform.

    Returns:
        Tuple of (is_valid, error_message)
    """
    limits = PLATFORM_LIMITS.get(platform)
    if not limits:
        return False, f"Unsupported platform: {platform}"

    char_count = len(content)
    char_limit = limits["chars"]

    if char_count > char_limit:
        return (
            False,
            f"Content exceeds {platform} limit ({char_count}/{char_limit} characters)",
        )

    return True, None


# ============================================
# Account Connection Endpoints
# ============================================


@router.get("/accounts", response_model=SocialAccountListResponse)
async def list_connected_accounts(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List user's connected social media accounts."""
    result = await db.execute(
        select(SocialAccount)
        .where(SocialAccount.user_id == current_user.id)
        .order_by(SocialAccount.created_at.desc())
    )
    accounts = result.scalars().all()

    return SocialAccountListResponse(
        accounts=[SocialAccountResponse.model_validate(acc) for acc in accounts],
        total=len(accounts),
    )


@router.get("/{platform}/connect", response_model=ConnectAccountResponse)
async def initiate_connection(
    platform: str,
    current_user: User = Depends(get_current_user),
):
    """
    Get OAuth authorization URL for connecting a social account.

    NOTE: This is a placeholder implementation.
    In production, implement actual OAuth flows for each platform:
    - Twitter: Use Twitter API v2 OAuth 2.0
    - LinkedIn: Use LinkedIn OAuth 2.0
    - Facebook: Use Facebook Graph API OAuth
    - Instagram: Use Instagram Basic Display API or Graph API
    """
    # Validate platform
    try:
        Platform(platform)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported platform: {platform}. Supported: {', '.join([p.value for p in Platform])}",
        )

    # Generate CSRF state token
    state = secrets.token_urlsafe(32)

    # TODO: Store state in Redis/session for verification
    # await redis.setex(f"oauth_state:{state}", 600, current_user.id)

    # TODO: Get actual OAuth URLs from platform adapters
    # For now, return placeholder
    authorization_url = f"https://oauth.{platform}.com/authorize?client_id=XXX&state={state}"

    return ConnectAccountResponse(
        authorization_url=authorization_url,
        state=state,
    )


@router.get("/{platform}/callback")
async def oauth_callback(
    platform: str,
    code: str = Query(...),
    state: str = Query(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    OAuth callback handler for social account connection.

    NOTE: This is a placeholder implementation.
    In production:
    1. Verify state token against Redis/session
    2. Exchange code for access/refresh tokens
    3. Fetch user profile from platform
    4. Encrypt tokens and store in database
    """
    # Validate platform
    try:
        Platform(platform)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported platform: {platform}",
        )

    # TODO: Verify state token
    # stored_user_id = await redis.get(f"oauth_state:{state}")
    # if not stored_user_id or stored_user_id != current_user.id:
    #     raise HTTPException(status_code=400, detail="Invalid state token")

    # TODO: Exchange code for tokens using platform adapter
    # tokens = await platform_adapter.exchange_code(code)
    # profile = await platform_adapter.get_profile(tokens.access_token)

    # Placeholder: Mock token exchange
    mock_tokens = {
        "access_token": f"mock_access_token_{code}",
        "refresh_token": f"mock_refresh_token_{code}",
        "expires_in": 3600,
    }
    mock_profile = {
        "id": f"platform_user_{platform}",
        "username": f"user_{platform}",
        "display_name": "Mock User",
        "profile_image": None,
    }

    # Encrypt tokens
    access_token_encrypted = encrypt_credential(
        mock_tokens["access_token"], settings.secret_key
    )
    refresh_token_encrypted = (
        encrypt_credential(mock_tokens["refresh_token"], settings.secret_key)
        if mock_tokens.get("refresh_token")
        else None
    )

    # Check if account already exists
    result = await db.execute(
        select(SocialAccount).where(
            and_(
                SocialAccount.platform == platform,
                SocialAccount.platform_user_id == mock_profile["id"],
            )
        )
    )
    existing_account = result.scalar_one_or_none()

    if existing_account:
        # Update existing account
        existing_account.access_token_encrypted = access_token_encrypted
        existing_account.refresh_token_encrypted = refresh_token_encrypted
        existing_account.token_expires_at = datetime.now(timezone.utc)
        existing_account.platform_username = mock_profile.get("username")
        existing_account.platform_display_name = mock_profile.get("display_name")
        existing_account.profile_image_url = mock_profile.get("profile_image")
        existing_account.is_active = True
        existing_account.last_verified_at = datetime.now(timezone.utc)
        existing_account.verification_error = None
    else:
        # Create new account
        new_account = SocialAccount(
            user_id=current_user.id,
            platform=platform,
            platform_user_id=mock_profile["id"],
            platform_username=mock_profile.get("username"),
            platform_display_name=mock_profile.get("display_name"),
            profile_image_url=mock_profile.get("profile_image"),
            access_token_encrypted=access_token_encrypted,
            refresh_token_encrypted=refresh_token_encrypted,
            token_expires_at=datetime.now(timezone.utc),
            is_active=True,
            last_verified_at=datetime.now(timezone.utc),
        )
        db.add(new_account)

    await db.commit()

    # Redirect to frontend success page
    # In production, use proper redirect
    return {
        "message": "Account connected successfully",
        "platform": platform,
        "redirect_url": f"{settings.frontend_url}/settings/social?connected={platform}",
    }


@router.delete("/accounts/{account_id}", response_model=DisconnectAccountResponse)
async def disconnect_account(
    account_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Disconnect a social media account."""
    result = await db.execute(
        select(SocialAccount).where(
            and_(
                SocialAccount.id == account_id,
                SocialAccount.user_id == current_user.id,
            )
        )
    )
    account = result.scalar_one_or_none()

    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Social account not found",
        )

    await db.delete(account)
    await db.commit()

    return DisconnectAccountResponse(
        message=f"{account.platform} account disconnected successfully",
        disconnected_at=datetime.now(timezone.utc),
    )


@router.post("/accounts/{account_id}/verify", response_model=VerifyAccountResponse)
async def verify_account(
    account_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Verify account connection is still valid.

    NOTE: Placeholder implementation.
    In production, make API call to platform to verify token.
    """
    result = await db.execute(
        select(SocialAccount).where(
            and_(
                SocialAccount.id == account_id,
                SocialAccount.user_id == current_user.id,
            )
        )
    )
    account = result.scalar_one_or_none()

    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Social account not found",
        )

    # TODO: Verify token with platform API
    # is_valid = await platform_adapter.verify_token(access_token)

    # Placeholder: Always return valid
    is_valid = True
    account.last_verified_at = datetime.now(timezone.utc)
    account.verification_error = None if is_valid else "Token expired or invalid"
    account.is_active = is_valid

    await db.commit()

    return VerifyAccountResponse(
        is_valid=is_valid,
        last_verified_at=account.last_verified_at,
        error_message=account.verification_error,
    )


# ============================================
# Post Scheduling Endpoints
# ============================================


@router.post("/posts", response_model=ScheduledPostResponse, status_code=201)
async def create_scheduled_post(
    request: CreatePostRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new scheduled post."""
    # Validate account_ids belong to user
    result = await db.execute(
        select(SocialAccount).where(
            and_(
                SocialAccount.id.in_(request.account_ids),
                SocialAccount.user_id == current_user.id,
            )
        )
    )
    accounts = result.scalars().all()

    if len(accounts) != len(request.account_ids):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="One or more social accounts not found or not owned by user",
        )

    # Validate scheduled_at is in the future
    if request.scheduled_at and request.scheduled_at < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Scheduled time must be in the future",
        )

    # Validate content length for each platform
    for account in accounts:
        is_valid, error_msg = validate_content_length(request.content, account.platform)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg,
            )

    # Determine status
    post_status = (
        PostStatus.SCHEDULED.value if request.scheduled_at else PostStatus.DRAFT.value
    )

    # Create scheduled post
    scheduled_post = ScheduledPost(
        user_id=current_user.id,
        content=request.content,
        media_urls=request.media_urls,
        link_url=request.link_url,
        scheduled_at=request.scheduled_at,
        status=post_status,
        article_id=request.article_id,
    )
    db.add(scheduled_post)
    await db.flush()  # Get the ID

    # Create post targets
    for account in accounts:
        # Check if there's a custom target config
        target_config = None
        if request.targets:
            target_config = next(
                (t for t in request.targets if t.account_id == str(account.id)),
                None,
            )

        post_target = PostTarget(
            scheduled_post_id=scheduled_post.id,
            social_account_id=account.id,
            platform_content=target_config.platform_content if target_config else None,
            platform_metadata=target_config.platform_metadata if target_config else None,
        )
        db.add(post_target)

    await db.commit()
    await db.refresh(scheduled_post)

    # Load targets with account data
    result = await db.execute(
        select(PostTarget)
        .options(selectinload(PostTarget.social_account))
        .where(PostTarget.scheduled_post_id == scheduled_post.id)
    )
    targets = result.scalars().all()

    # Build response
    target_responses = [
        PostTargetResponse(
            id=str(t.id),
            social_account_id=str(t.social_account_id),
            platform=t.social_account.platform,
            platform_username=t.social_account.platform_username,
            platform_content=t.platform_content,
            is_published=t.is_published,
            published_at=t.published_at,
            platform_post_id=t.platform_post_id,
            platform_post_url=t.platform_post_url,
            publish_error=t.publish_error,
            analytics_data=t.analytics_data,
        )
        for t in targets
    ]

    return ScheduledPostResponse(
        id=str(scheduled_post.id),
        content=scheduled_post.content,
        media_urls=scheduled_post.media_urls,
        link_url=scheduled_post.link_url,
        scheduled_at=scheduled_post.scheduled_at,
        status=scheduled_post.status,
        published_at=scheduled_post.published_at,
        publish_error=scheduled_post.publish_error,
        article_id=str(scheduled_post.article_id) if scheduled_post.article_id else None,
        targets=target_responses,
        created_at=scheduled_post.created_at,
        updated_at=scheduled_post.updated_at,
    )


@router.get("/posts", response_model=ScheduledPostListResponse)
async def list_scheduled_posts(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    platform: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List scheduled posts with filtering."""
    # Build query
    query = select(ScheduledPost).where(ScheduledPost.user_id == current_user.id)

    # Apply filters
    if status:
        query = query.where(ScheduledPost.status == status)

    if start_date:
        query = query.where(ScheduledPost.scheduled_at >= start_date)

    if end_date:
        query = query.where(ScheduledPost.scheduled_at <= end_date)

    # Platform filter requires join
    if platform:
        query = (
            query.join(PostTarget)
            .join(SocialAccount)
            .where(SocialAccount.platform == platform)
        )

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Apply pagination
    offset = (page - 1) * page_size
    query = query.order_by(ScheduledPost.scheduled_at.desc()).offset(offset).limit(page_size)

    # Execute query
    result = await db.execute(query)
    posts = result.scalars().all()

    # Load targets for each post
    post_responses = []
    for post in posts:
        targets_result = await db.execute(
            select(PostTarget)
            .options(selectinload(PostTarget.social_account))
            .where(PostTarget.scheduled_post_id == post.id)
        )
        targets = targets_result.scalars().all()

        target_responses = [
            PostTargetResponse(
                id=str(t.id),
                social_account_id=str(t.social_account_id),
                platform=t.social_account.platform,
                platform_username=t.social_account.platform_username,
                platform_content=t.platform_content,
                is_published=t.is_published,
                published_at=t.published_at,
                platform_post_id=t.platform_post_id,
                platform_post_url=t.platform_post_url,
                publish_error=t.publish_error,
                analytics_data=t.analytics_data,
            )
            for t in targets
        ]

        post_responses.append(
            ScheduledPostResponse(
                id=str(post.id),
                content=post.content,
                media_urls=post.media_urls,
                link_url=post.link_url,
                scheduled_at=post.scheduled_at,
                status=post.status,
                published_at=post.published_at,
                publish_error=post.publish_error,
                article_id=str(post.article_id) if post.article_id else None,
                targets=target_responses,
                created_at=post.created_at,
                updated_at=post.updated_at,
            )
        )

    total_pages = math.ceil(total / page_size) if total > 0 else 0

    return ScheduledPostListResponse(
        posts=post_responses,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/posts/{post_id}", response_model=ScheduledPostResponse)
async def get_scheduled_post(
    post_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get details of a scheduled post."""
    result = await db.execute(
        select(ScheduledPost).where(
            and_(
                ScheduledPost.id == post_id,
                ScheduledPost.user_id == current_user.id,
            )
        )
    )
    post = result.scalar_one_or_none()

    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scheduled post not found",
        )

    # Load targets
    targets_result = await db.execute(
        select(PostTarget)
        .options(selectinload(PostTarget.social_account))
        .where(PostTarget.scheduled_post_id == post.id)
    )
    targets = targets_result.scalars().all()

    target_responses = [
        PostTargetResponse(
            id=str(t.id),
            social_account_id=str(t.social_account_id),
            platform=t.social_account.platform,
            platform_username=t.social_account.platform_username,
            platform_content=t.platform_content,
            is_published=t.is_published,
            published_at=t.published_at,
            platform_post_id=t.platform_post_id,
            platform_post_url=t.platform_post_url,
            publish_error=t.publish_error,
            analytics_data=t.analytics_data,
        )
        for t in targets
    ]

    return ScheduledPostResponse(
        id=str(post.id),
        content=post.content,
        media_urls=post.media_urls,
        link_url=post.link_url,
        scheduled_at=post.scheduled_at,
        status=post.status,
        published_at=post.published_at,
        publish_error=post.publish_error,
        article_id=str(post.article_id) if post.article_id else None,
        targets=target_responses,
        created_at=post.created_at,
        updated_at=post.updated_at,
    )


@router.put("/posts/{post_id}", response_model=ScheduledPostResponse)
async def update_scheduled_post(
    post_id: str,
    request: UpdatePostRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a scheduled post (only if not yet posted)."""
    result = await db.execute(
        select(ScheduledPost).where(
            and_(
                ScheduledPost.id == post_id,
                ScheduledPost.user_id == current_user.id,
            )
        )
    )
    post = result.scalar_one_or_none()

    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scheduled post not found",
        )

    # Prevent editing published posts
    if post.status == PostStatus.PUBLISHED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot edit published posts",
        )

    # Update fields
    if request.content is not None:
        post.content = request.content

    if request.scheduled_at is not None:
        post.scheduled_at = request.scheduled_at
        # Update status if scheduling
        if post.status == PostStatus.DRAFT.value:
            post.status = PostStatus.SCHEDULED.value

    if request.media_urls is not None:
        post.media_urls = request.media_urls

    if request.link_url is not None:
        post.link_url = request.link_url

    if request.status is not None:
        post.status = request.status

    await db.commit()
    await db.refresh(post)

    # Load targets
    targets_result = await db.execute(
        select(PostTarget)
        .options(selectinload(PostTarget.social_account))
        .where(PostTarget.scheduled_post_id == post.id)
    )
    targets = targets_result.scalars().all()

    target_responses = [
        PostTargetResponse(
            id=str(t.id),
            social_account_id=str(t.social_account_id),
            platform=t.social_account.platform,
            platform_username=t.social_account.platform_username,
            platform_content=t.platform_content,
            is_published=t.is_published,
            published_at=t.published_at,
            platform_post_id=t.platform_post_id,
            platform_post_url=t.platform_post_url,
            publish_error=t.publish_error,
            analytics_data=t.analytics_data,
        )
        for t in targets
    ]

    return ScheduledPostResponse(
        id=str(post.id),
        content=post.content,
        media_urls=post.media_urls,
        link_url=post.link_url,
        scheduled_at=post.scheduled_at,
        status=post.status,
        published_at=post.published_at,
        publish_error=post.publish_error,
        article_id=str(post.article_id) if post.article_id else None,
        targets=target_responses,
        created_at=post.created_at,
        updated_at=post.updated_at,
    )


@router.delete("/posts/{post_id}")
async def delete_scheduled_post(
    post_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Cancel/delete a scheduled post."""
    result = await db.execute(
        select(ScheduledPost).where(
            and_(
                ScheduledPost.id == post_id,
                ScheduledPost.user_id == current_user.id,
            )
        )
    )
    post = result.scalar_one_or_none()

    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scheduled post not found",
        )

    await db.delete(post)
    await db.commit()

    return {"message": "Scheduled post deleted successfully"}


@router.post("/posts/{post_id}/publish-now")
async def publish_post_now(
    post_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Publish a scheduled post immediately.

    NOTE: Placeholder implementation.
    In production, this would trigger the actual publishing to platforms
    via background jobs/workers (Celery, etc.)
    """
    result = await db.execute(
        select(ScheduledPost).where(
            and_(
                ScheduledPost.id == post_id,
                ScheduledPost.user_id == current_user.id,
            )
        )
    )
    post = result.scalar_one_or_none()

    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scheduled post not found",
        )

    if post.status == PostStatus.PUBLISHED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Post already published",
        )

    # TODO: Trigger background job to publish
    # await publish_post_task.delay(post_id)

    # Update status
    post.status = PostStatus.PUBLISHING.value
    post.publish_attempted_at = datetime.now(timezone.utc)

    await db.commit()

    return {
        "message": "Post publishing initiated",
        "status": post.status,
    }


# ============================================
# Calendar Endpoints
# ============================================


@router.get("/calendar", response_model=CalendarResponse)
async def get_calendar(
    start_date: date = Query(...),
    end_date: date = Query(...),
    platform: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get posts for calendar view."""
    # Build query
    query = (
        select(ScheduledPost)
        .where(
            and_(
                ScheduledPost.user_id == current_user.id,
                ScheduledPost.scheduled_at.isnot(None),
                ScheduledPost.scheduled_at >= datetime.combine(start_date, datetime.min.time()),
                ScheduledPost.scheduled_at <= datetime.combine(end_date, datetime.max.time()),
            )
        )
        .order_by(ScheduledPost.scheduled_at)
    )

    # Platform filter
    if platform:
        query = (
            query.join(PostTarget)
            .join(SocialAccount)
            .where(SocialAccount.platform == platform)
        )

    # Execute query
    result = await db.execute(query)
    posts = result.scalars().all()

    # Group posts by date
    days_dict = {}
    for post in posts:
        # Load targets for this post
        targets_result = await db.execute(
            select(PostTarget)
            .options(selectinload(PostTarget.social_account))
            .where(PostTarget.scheduled_post_id == post.id)
        )
        targets = targets_result.scalars().all()

        # Get date key
        post_date = post.scheduled_at.date().isoformat()

        if post_date not in days_dict:
            days_dict[post_date] = []

        # Add post to day
        days_dict[post_date].append(
            CalendarDayPost(
                id=str(post.id),
                content_preview=post.content[:100],
                scheduled_at=post.scheduled_at,
                status=post.status,
                platforms=[t.social_account.platform for t in targets],
            )
        )

    # Convert to list
    days = [
        CalendarDay(
            date=day_date,
            posts=day_posts,
            post_count=len(day_posts),
        )
        for day_date, day_posts in sorted(days_dict.items())
    ]

    return CalendarResponse(
        days=days,
        start_date=start_date.isoformat(),
        end_date=end_date.isoformat(),
    )


# ============================================
# Stats Endpoint
# ============================================


@router.get("/stats")
async def get_post_stats(
    breakdown: Optional[str] = Query(None, description="Breakdown type: 'platform'"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get post statistics for the current user."""
    # Count posts by status
    result = await db.execute(
        select(ScheduledPost.status, func.count(ScheduledPost.id).label("count"))
        .where(ScheduledPost.user_id == current_user.id)
        .group_by(ScheduledPost.status)
    )
    rows = result.all()

    counts: dict = {}
    total = 0
    for row in rows:
        counts[row.status] = row.count
        total += row.count

    stats: dict = {
        "scheduled": counts.get(PostStatus.SCHEDULED.value, 0),
        "pending": counts.get(PostStatus.SCHEDULED.value, 0),
        "published": counts.get(PostStatus.PUBLISHED.value, 0),
        "failed": counts.get(PostStatus.FAILED.value, 0),
        "draft": counts.get(PostStatus.DRAFT.value, 0),
        "total": total,
    }

    if breakdown == "platform":
        # Count by platform via PostTarget -> SocialAccount join
        platform_result = await db.execute(
            select(SocialAccount.platform, func.count(PostTarget.id).label("count"))
            .join(PostTarget, PostTarget.social_account_id == SocialAccount.id)
            .join(ScheduledPost, ScheduledPost.id == PostTarget.scheduled_post_id)
            .where(ScheduledPost.user_id == current_user.id)
            .group_by(SocialAccount.platform)
        )
        platform_rows = platform_result.all()
        stats["by_platform"] = {row.platform: row.count for row in platform_rows}

    return stats


# ============================================
# Analytics Endpoints
# ============================================


@router.get("/posts/{post_id}/analytics", response_model=PostAnalyticsResponse)
async def get_post_analytics(
    post_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get analytics for a posted content.

    NOTE: Placeholder implementation.
    In production, fetch real analytics from each platform's API.
    """
    result = await db.execute(
        select(ScheduledPost).where(
            and_(
                ScheduledPost.id == post_id,
                ScheduledPost.user_id == current_user.id,
            )
        )
    )
    post = result.scalar_one_or_none()

    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scheduled post not found",
        )

    # Load targets
    targets_result = await db.execute(
        select(PostTarget)
        .options(selectinload(PostTarget.social_account))
        .where(PostTarget.scheduled_post_id == post.id)
    )
    targets = targets_result.scalars().all()

    # Build analytics response
    platform_analytics = []
    total_likes = 0
    total_shares = 0
    total_comments = 0
    total_impressions = 0
    total_clicks = 0

    for target in targets:
        # Use stored analytics or fetch fresh
        analytics = target.analytics_data or {}

        likes = analytics.get("likes", 0)
        shares = analytics.get("shares", 0)
        comments = analytics.get("comments", 0)
        impressions = analytics.get("impressions", 0)
        clicks = analytics.get("clicks", 0)

        total_likes += likes
        total_shares += shares
        total_comments += comments
        total_impressions += impressions
        total_clicks += clicks

        engagement_rate = None
        if impressions > 0:
            engagement_rate = ((likes + shares + comments) / impressions) * 100

        platform_analytics.append(
            PlatformAnalytics(
                platform=target.social_account.platform,
                post_id=target.platform_post_id,
                post_url=target.platform_post_url,
                likes=likes,
                shares=shares,
                comments=comments,
                impressions=impressions,
                clicks=clicks,
                engagement_rate=engagement_rate,
                fetched_at=target.last_analytics_fetch,
            )
        )

    # Calculate average engagement rate
    avg_engagement = None
    if total_impressions > 0:
        avg_engagement = (
            (total_likes + total_shares + total_comments) / total_impressions
        ) * 100

    return PostAnalyticsResponse(
        post_id=str(post.id),
        published_at=post.published_at,
        platforms=platform_analytics,
        total_likes=total_likes,
        total_shares=total_shares,
        total_comments=total_comments,
        total_impressions=total_impressions,
        total_clicks=total_clicks,
        average_engagement_rate=avg_engagement,
    )


# ============================================
# Utility Endpoints
# ============================================


@router.post("/preview", response_model=PreviewResponse)
async def preview_post(
    content: str = Body(..., embed=True),
    platform: str = Body(..., embed=True),
):
    """Get platform-specific preview info (char count, validation)."""
    # Validate platform
    if platform not in PLATFORM_LIMITS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported platform: {platform}",
        )

    limits = PLATFORM_LIMITS[platform]
    char_count = len(content)
    char_limit = limits["chars"]
    is_valid = char_count <= char_limit

    warnings = []
    if char_count > char_limit:
        warnings.append(f"Content exceeds character limit by {char_count - char_limit} characters")

    if char_count > char_limit * 0.9:
        warnings.append("Content is near character limit")

    return PreviewResponse(
        platform=platform,
        content=content,
        char_count=char_count,
        char_limit=char_limit,
        is_valid=is_valid,
        warnings=warnings,
        limits=PlatformLimits(
            chars=limits["chars"],
            images=limits["images"],
            video=limits["video"],
        ),
    )


@router.get("/best-times", response_model=BestTimesResponse)
async def get_best_posting_times(
    platform: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get recommended posting times based on past performance.

    NOTE: Placeholder implementation.
    In production, analyze historical post performance to recommend times.
    """
    # Validate platform
    if platform not in PLATFORM_LIMITS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported platform: {platform}",
        )

    # TODO: Analyze user's historical post performance
    # Query published posts with analytics data
    # Group by hour and day of week
    # Calculate average engagement for each time slot
    # Return top 5 time slots

    # Placeholder: Return generic best times
    time_slots = [
        BestTimeSlot(hour=9, day_of_week=1, engagement_score=0.85, post_count=10),
        BestTimeSlot(hour=12, day_of_week=2, engagement_score=0.82, post_count=15),
        BestTimeSlot(hour=15, day_of_week=3, engagement_score=0.78, post_count=12),
        BestTimeSlot(hour=18, day_of_week=4, engagement_score=0.75, post_count=8),
        BestTimeSlot(hour=20, day_of_week=0, engagement_score=0.72, post_count=20),
    ]

    return BestTimesResponse(
        platform=platform,
        time_slots=time_slots,
        timezone="UTC",
    )
