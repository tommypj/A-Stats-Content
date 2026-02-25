"""
Social Media Scheduler Service.

Handles background scheduling and publishing of social media posts
at their scheduled times. Processes due posts, publishes to multiple
platforms, and tracks results.
"""

import asyncio
from datetime import datetime, timezone
from typing import List, Optional
import logging

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from adapters.social import get_social_adapter, SocialPlatform
from adapters.social.base import SocialCredentials, PostResult, SocialRateLimitError
from infrastructure.database import async_session_maker
from infrastructure.database.models.social import (
    ScheduledPost,
    PostTarget,
    SocialAccount,
    PostStatus,
)
from core.security.encryption import decrypt_credential
from infrastructure.config.settings import settings

logger = logging.getLogger(__name__)


class SocialSchedulerService:
    """Service for scheduling and publishing social media posts."""

    def __init__(self):
        self.is_running = False
        self.check_interval = 60  # Check every minute
        self._task: Optional[asyncio.Task] = None

    async def start(self):
        """Start the scheduler background loop."""
        if self.is_running:
            logger.warning("Scheduler is already running")
            return

        self.is_running = True
        logger.info("Social scheduler started - checking for posts every %d seconds", self.check_interval)

        while self.is_running:
            try:
                await self.process_due_posts()
            except Exception as e:
                logger.error(f"Scheduler error: {e}", exc_info=True)

            # Sleep until next check
            await asyncio.sleep(self.check_interval)

    async def stop(self):
        """Stop the scheduler."""
        if not self.is_running:
            return

        self.is_running = False
        logger.info("Social scheduler stopped")

    async def process_due_posts(self):
        """Find and publish posts that are due."""
        async with async_session_maker() as db:
            try:
                # Find posts that are due for publishing
                now = datetime.now(timezone.utc)

                stmt = (
                    select(ScheduledPost)
                    .options(
                        selectinload(ScheduledPost.targets).selectinload(PostTarget.social_account)
                    )
                    .where(
                        and_(
                            ScheduledPost.scheduled_at <= now,
                            ScheduledPost.status == PostStatus.SCHEDULED.value,
                        )
                    )
                    .order_by(ScheduledPost.scheduled_at)
                )

                result = await db.execute(stmt)
                due_posts = result.scalars().all()

                if not due_posts:
                    logger.debug("No posts due for publishing")
                    return

                logger.info(f"Found {len(due_posts)} posts due for publishing")

                # Process each post
                for post in due_posts:
                    await self._process_post(post, db)

                # Commit all changes
                await db.commit()

            except Exception as e:
                logger.error(f"Error processing due posts: {e}", exc_info=True)
                await db.rollback()

    async def _process_post(self, post: ScheduledPost, db: AsyncSession):
        """
        Process a single scheduled post.

        Args:
            post: The scheduled post to process
            db: Database session
        """
        try:
            logger.info(f"Processing post {post.id} scheduled for {post.scheduled_at}")

            # Update post status to PUBLISHING
            post.status = PostStatus.PUBLISHING.value
            post.publish_attempted_at = datetime.now(timezone.utc)
            await db.flush()

            # Track results
            success_count = 0
            failed_count = 0

            # Publish to each target account
            for target in post.targets:
                if target.is_published:
                    continue  # Skip already published targets

                try:
                    result = await self.publish_to_platform(post, target, target.social_account, db)

                    if result.success:
                        success_count += 1
                    else:
                        failed_count += 1

                except Exception as e:
                    logger.error(
                        f"Failed to publish to {target.social_account.platform} "
                        f"({target.social_account.platform_username}): {e}",
                        exc_info=True,
                    )
                    target.publish_error = str(e)
                    failed_count += 1

            # Update overall post status based on results
            if success_count > 0 and failed_count == 0:
                post.status = PostStatus.PUBLISHED.value
                post.published_at = datetime.now(timezone.utc)
                logger.info(f"Post {post.id} published successfully to all platforms")
            elif success_count > 0 and failed_count > 0:
                post.status = PostStatus.PUBLISHED.value  # Partially successful
                post.published_at = datetime.now(timezone.utc)
                logger.warning(
                    f"Post {post.id} partially published: "
                    f"{success_count} succeeded, {failed_count} failed"
                )
            else:
                post.status = PostStatus.FAILED.value
                post.publish_error = f"All {failed_count} targets failed"
                logger.error(f"Post {post.id} failed to publish to all platforms")

        except Exception as e:
            logger.error(f"Error processing post {post.id}: {e}", exc_info=True)
            post.status = PostStatus.FAILED.value

    async def publish_to_platform(
        self,
        post: ScheduledPost,
        target: PostTarget,
        account: SocialAccount,
        db: AsyncSession,
    ) -> PostResult:
        """
        Publish a post to a specific platform.

        Args:
            post: The scheduled post
            target: The post target (links post to account)
            account: The social media account
            db: Database session

        Returns:
            PostResult with success status and details
        """
        try:
            logger.info(
                f"Publishing post {post.id} to {account.platform} "
                f"({account.platform_username})"
            )

            # Decrypt credentials — map DB column names to SocialCredentials fields
            credentials = SocialCredentials(
                platform=SocialPlatform(account.platform),
                access_token=decrypt_credential(
                    account.access_token_encrypted, settings.secret_key
                ),
                refresh_token=(
                    decrypt_credential(account.refresh_token_encrypted, settings.secret_key)
                    if account.refresh_token_encrypted
                    else None
                ),
                token_expiry=account.token_expires_at,
                account_id=account.platform_user_id,
                account_name=account.platform_username,
                account_username=account.platform_display_name,
                profile_image_url=account.profile_image_url,
            )

            # Get platform adapter
            adapter = get_social_adapter(SocialPlatform(account.platform))

            # Check if token needs refresh
            if credentials.token_expiry and credentials.token_expiry < datetime.now(timezone.utc):
                logger.info(f"Refreshing expired token for {account.platform}")
                credentials = await adapter.refresh_token(credentials)
                # Update stored credentials
                await self._update_account_tokens(account, credentials, db)

            # Publish the post
            result: PostResult
            if post.media_urls:
                # Post with media
                media_list = post.media_urls if isinstance(post.media_urls, list) else []
                result = await adapter.post_with_media(credentials, post.content, media_list)
            else:
                # Text-only post
                result = await adapter.post_text(credentials, post.content)

            # Update target
            if result.success:
                target.is_published = True
                target.platform_post_id = result.post_id
                target.platform_post_url = result.post_url
                target.publish_error = None
                target.published_at = datetime.now(timezone.utc)

                logger.info(
                    f"Successfully published to {account.platform}: {result.post_url}"
                )
            else:
                target.publish_error = result.error_message
                logger.warning(
                    f"Failed to publish to {account.platform}: {result.error_message}"
                )

            return result

        except SocialRateLimitError as e:
            logger.warning(f"Rate limit hit for {account.platform}: {e}")
            target.publish_error = f"Rate limit exceeded: {str(e)}"
            return PostResult(success=False, error_message=str(e))

        except Exception as e:
            logger.error(f"Failed to publish to {account.platform}: {e}", exc_info=True)
            target.publish_error = str(e)
            return PostResult(success=False, error_message=str(e))

    async def publish_post_immediately(self, post_id: str, db: AsyncSession) -> dict:
        """
        Publish a specific post immediately (bypassing schedule).

        Args:
            post_id: UUID of the scheduled post
            db: Database session

        Returns:
            Dictionary with publication results
        """
        try:
            # Load post with targets and accounts
            stmt = (
                select(ScheduledPost)
                .options(
                    selectinload(ScheduledPost.targets).selectinload(PostTarget.social_account)
                )
                .where(ScheduledPost.id == post_id)
            )

            result = await db.execute(stmt)
            post = result.scalar_one_or_none()

            if not post:
                return {"success": False, "error": "Post not found"}

            if post.status == PostStatus.PUBLISHED.value:
                return {"success": False, "error": "Post already published"}

            if post.status == PostStatus.CANCELLED.value:
                return {"success": False, "error": "Post is cancelled"}

            # Process the post
            await self._process_post(post, db)
            await db.commit()

            # Count results
            success_count = sum(1 for t in post.targets if t.is_published)
            failed_count = sum(
                1 for t in post.targets if not t.is_published and t.publish_error
            )

            return {
                "success": True,
                "post_status": post.status,
                "published_count": success_count,
                "failed_count": failed_count,
                "targets": [
                    {
                        "account": t.social_account.platform_username,
                        "platform": t.social_account.platform,
                        "status": "published" if t.is_published else "failed" if t.publish_error else "pending",
                        "post_url": t.platform_post_url,
                        "error": t.publish_error,
                    }
                    for t in post.targets
                ],
            }

        except Exception as e:
            logger.error(f"Error publishing post immediately: {e}", exc_info=True)
            await db.rollback()
            return {"success": False, "error": str(e)}

    async def retry_failed_target(self, target_id: str, db: AsyncSession) -> PostResult:
        """
        Retry a failed post target.

        Args:
            target_id: UUID of the post target
            db: Database session

        Returns:
            PostResult with retry attempt status
        """
        try:
            # Load target with post and account
            stmt = (
                select(PostTarget)
                .options(
                    selectinload(PostTarget.scheduled_post),
                    selectinload(PostTarget.social_account),
                )
                .where(PostTarget.id == target_id)
            )

            result = await db.execute(stmt)
            target = result.scalar_one_or_none()

            if not target:
                return PostResult(success=False, error_message="Target not found")

            if target.is_published:
                return PostResult(success=False, error_message="Target already posted")

            # Clear previous error for retry
            target.publish_error = None

            # Attempt to publish
            result = await self.publish_to_platform(
                target.scheduled_post, target, target.social_account, db
            )

            await db.commit()
            return result

        except Exception as e:
            logger.error(f"Error retrying target: {e}", exc_info=True)
            await db.rollback()
            return PostResult(success=False, error_message=str(e))

    async def _update_account_tokens(
        self,
        account: SocialAccount,
        credentials: SocialCredentials,
        db: AsyncSession,
    ):
        """
        Update stored tokens after refresh.

        Args:
            account: The social account to update
            credentials: New credentials with refreshed tokens
            db: Database session
        """
        from core.security.encryption import encrypt_credential

        account.access_token_encrypted = encrypt_credential(
            credentials.access_token, settings.secret_key
        )

        if credentials.refresh_token:
            account.refresh_token_encrypted = encrypt_credential(
                credentials.refresh_token, settings.secret_key
            )

        account.token_expires_at = credentials.token_expiry

        await db.flush()
        logger.info(f"Updated tokens for {account.platform} account")


# Singleton instance
scheduler_service = SocialSchedulerService()
