"""
Social media scheduling API routes.
"""

import secrets
import time
from datetime import datetime, timezone, date
from typing import Optional, List
from urllib.parse import urlencode
import math

import httpx
from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from fastapi.responses import RedirectResponse
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

# In-memory OAuth state store (state -> {user_id, created_at})
# For production with multiple instances, use Redis instead.
_oauth_states: dict[str, dict] = {}
_OAUTH_STATE_TTL = 600  # 10 minutes


def _store_oauth_state(state: str, user_id: str) -> None:
    """Store OAuth state with TTL. Also cleans up expired entries."""
    now = time.time()
    # Clean expired
    expired = [k for k, v in _oauth_states.items() if now - v["created_at"] > _OAUTH_STATE_TTL]
    for k in expired:
        _oauth_states.pop(k, None)
    _oauth_states[state] = {"user_id": str(user_id), "created_at": now}


def _verify_oauth_state(state: str) -> Optional[str]:
    """Verify and consume an OAuth state. Returns user_id or None."""
    entry = _oauth_states.pop(state, None)
    if not entry:
        return None
    if time.time() - entry["created_at"] > _OAUTH_STATE_TTL:
        return None
    return entry["user_id"]


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
    Currently supports Facebook (which also covers Instagram Business accounts).
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
    _store_oauth_state(state, str(current_user.id))

    if platform == "facebook":
        if not settings.facebook_app_id or not settings.facebook_app_secret:
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail="Facebook integration is not configured. Please set FACEBOOK_APP_ID and FACEBOOK_APP_SECRET.",
            )

        params = urlencode({
            "client_id": settings.facebook_app_id,
            "redirect_uri": settings.facebook_redirect_uri,
            "state": state,
            "scope": "pages_show_list,pages_read_engagement,pages_manage_posts,pages_read_user_content",
            "response_type": "code",
        })
        authorization_url = f"https://www.facebook.com/v21.0/dialog/oauth?{params}"
    else:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=f"OAuth for {platform} is not yet implemented. Currently supported: facebook.",
        )

    return ConnectAccountResponse(
        authorization_url=authorization_url,
        state=state,
    )


@router.get("/{platform}/callback")
async def oauth_callback(
    platform: str,
    code: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    error: Optional[str] = Query(None),
    error_description: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """
    OAuth callback handler for social account connection.
    This is hit by the browser redirect from the OAuth provider (no auth header).
    The user is identified from the stored OAuth state token.
    """
    frontend_callback = f"{settings.frontend_url}/social/callback"

    # Handle OAuth error from provider
    if error:
        return RedirectResponse(
            url=f"{frontend_callback}?error={error}&platform={platform}"
        )

    if not code or not state:
        return RedirectResponse(
            url=f"{frontend_callback}?error=missing_params&platform={platform}"
        )

    # Validate platform
    try:
        Platform(platform)
    except ValueError:
        return RedirectResponse(
            url=f"{frontend_callback}?error=invalid_platform&platform={platform}"
        )

    # Verify state and get user_id
    user_id = _verify_oauth_state(state)
    if not user_id:
        return RedirectResponse(
            url=f"{frontend_callback}?error=invalid_state&platform={platform}"
        )

    # Look up the user
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        return RedirectResponse(
            url=f"{frontend_callback}?error=user_not_found&platform={platform}"
        )

    if platform == "facebook":
        try:
            tokens, profile = await _facebook_exchange_and_profile(code)
        except Exception as e:
            return RedirectResponse(
                url=f"{frontend_callback}?error=token_exchange_failed&platform={platform}"
            )
    else:
        return RedirectResponse(
            url=f"{frontend_callback}?error=unsupported_platform&platform={platform}"
        )

    # Encrypt tokens
    access_token_encrypted = encrypt_credential(tokens["access_token"], settings.secret_key)

    # Check if account already exists for this user + platform + platform_user_id
    result = await db.execute(
        select(SocialAccount).where(
            and_(
                SocialAccount.user_id == user.id,
                SocialAccount.platform == platform,
                SocialAccount.platform_user_id == profile["id"],
            )
        )
    )
    existing_account = result.scalar_one_or_none()

    if existing_account:
        existing_account.access_token_encrypted = access_token_encrypted
        existing_account.token_expires_at = tokens.get("expires_at")
        existing_account.platform_username = profile.get("username")
        existing_account.platform_display_name = profile.get("display_name")
        existing_account.profile_image_url = profile.get("profile_image")
        existing_account.is_active = True
        existing_account.last_verified_at = datetime.now(timezone.utc)
        existing_account.verification_error = None
    else:
        new_account = SocialAccount(
            user_id=user.id,
            platform=platform,
            platform_user_id=profile["id"],
            platform_username=profile.get("username"),
            platform_display_name=profile.get("display_name"),
            profile_image_url=profile.get("profile_image"),
            access_token_encrypted=access_token_encrypted,
            token_expires_at=tokens.get("expires_at"),
            is_active=True,
            last_verified_at=datetime.now(timezone.utc),
        )
        db.add(new_account)

    await db.commit()

    # Redirect to frontend success page
    return RedirectResponse(
        url=f"{frontend_callback}?success=true&platform={platform}"
    )


async def _facebook_exchange_and_profile(code: str) -> tuple[dict, dict]:
    """
    Exchange Facebook OAuth code for a long-lived page access token
    and fetch the user's Facebook Page profile.
    """
    async with httpx.AsyncClient(timeout=15.0) as client:
        # Step 1: Exchange code for short-lived user access token
        token_resp = await client.get(
            "https://graph.facebook.com/v21.0/oauth/access_token",
            params={
                "client_id": settings.facebook_app_id,
                "client_secret": settings.facebook_app_secret,
                "redirect_uri": settings.facebook_redirect_uri,
                "code": code,
            },
        )
        if token_resp.status_code != 200:
            raise Exception(f"Token exchange failed: {token_resp.text}")

        token_data = token_resp.json()
        short_token = token_data["access_token"]

        # Step 2: Exchange for long-lived token (60 days)
        long_token_resp = await client.get(
            "https://graph.facebook.com/v21.0/oauth/access_token",
            params={
                "grant_type": "fb_exchange_token",
                "client_id": settings.facebook_app_id,
                "client_secret": settings.facebook_app_secret,
                "fb_exchange_token": short_token,
            },
        )
        if long_token_resp.status_code == 200:
            long_data = long_token_resp.json()
            access_token = long_data["access_token"]
            expires_in = long_data.get("expires_in", 5184000)  # Default 60 days
        else:
            # Fall back to short-lived token
            access_token = short_token
            expires_in = token_data.get("expires_in", 3600)

        # Step 3: Get user's Pages (we store Page access tokens for posting)
        pages_resp = await client.get(
            "https://graph.facebook.com/v21.0/me/accounts",
            params={"access_token": access_token},
        )

        if pages_resp.status_code == 200:
            pages_data = pages_resp.json()
            pages = pages_data.get("data", [])

            if pages:
                # Use the first page — its token never expires as long as
                # the user remains an admin and the app has permissions
                page = pages[0]
                page_token = page["access_token"]
                profile = {
                    "id": page["id"],
                    "username": page.get("name", ""),
                    "display_name": page.get("name", ""),
                    "profile_image": f"https://graph.facebook.com/v21.0/{page['id']}/picture?type=small",
                }
                tokens = {
                    "access_token": page_token,
                    "expires_at": None,  # Page tokens don't expire
                }
                return tokens, profile

        # Fallback: Use user profile if no pages
        me_resp = await client.get(
            "https://graph.facebook.com/v21.0/me",
            params={
                "fields": "id,name,picture.type(small)",
                "access_token": access_token,
            },
        )
        if me_resp.status_code != 200:
            raise Exception(f"Profile fetch failed: {me_resp.text}")

        me_data = me_resp.json()
        picture_url = me_data.get("picture", {}).get("data", {}).get("url")

        expires_at = datetime.now(timezone.utc).timestamp() + expires_in
        tokens = {
            "access_token": access_token,
            "expires_at": datetime.fromtimestamp(expires_at, tz=timezone.utc),
        }
        profile = {
            "id": me_data["id"],
            "username": me_data.get("name", ""),
            "display_name": me_data.get("name", ""),
            "profile_image": picture_url,
        }
        return tokens, profile


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
