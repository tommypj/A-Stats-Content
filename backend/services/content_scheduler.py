"""
Content Calendar Auto-Publish Scheduler.

Background service that checks for articles with a planned_date <= now(),
auto_publish=True, status='completed', and no published_at. For each,
it triggers the WordPress publish flow.
"""

import asyncio
import logging
from datetime import UTC, datetime

import redis.asyncio as aioredis
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.config.settings import settings
from infrastructure.database import async_session_maker
from infrastructure.database.models import Article, ContentStatus
from infrastructure.database.models.project import Project

logger = logging.getLogger(__name__)


class ContentSchedulerService:
    """Auto-publishes articles to WordPress when their planned_date arrives."""

    def __init__(self):
        self.is_running = False
        self.check_interval = 120  # Check every 2 minutes

    async def start(self):
        """Start the scheduler background loop."""
        if self.is_running:
            return
        self.is_running = True
        logger.info("Content scheduler started — checking every %ds", self.check_interval)

        while self.is_running:
            try:
                await self._process_due_articles()
            except Exception as e:
                logger.error("Content scheduler error: %s", e, exc_info=True)
            await asyncio.sleep(self.check_interval)

    async def stop(self):
        self.is_running = False
        logger.info("Content scheduler stopped")

    async def _process_due_articles(self):
        """Find articles due for auto-publish and push them to WordPress."""
        # Distributed lock via Redis to prevent duplicate publishes in multi-worker
        redis_client = None
        lock_acquired = False
        lock_key = "scheduler:content_publish:lock"
        try:
            if settings.redis_url:
                redis_client = aioredis.from_url(settings.redis_url, socket_timeout=2)
                lock_acquired = await redis_client.set(lock_key, "1", nx=True, ex=120)
                if not lock_acquired:
                    return
        except Exception:
            logger.debug("Redis lock unavailable, proceeding without lock")

        try:
            async with async_session_maker() as db:
                now = datetime.now(UTC)
                result = await db.execute(
                    select(Article).where(
                        and_(
                            Article.auto_publish == True,  # noqa: E712
                            Article.planned_date <= now,
                            Article.status == ContentStatus.COMPLETED.value,
                            Article.published_at.is_(None),
                            Article.deleted_at.is_(None),
                        )
                    )
                )
                articles = result.scalars().all()

                if not articles:
                    return

                logger.info("Content scheduler: %d article(s) due for auto-publish", len(articles))

                for article in articles:
                    await self._publish_article(db, article)
        finally:
            if redis_client and lock_acquired:
                try:
                    await redis_client.delete(lock_key)
                except Exception:
                    pass
                try:
                    await redis_client.aclose()
                except Exception:
                    pass

    async def _publish_article(self, db: AsyncSession, article: Article):
        """Publish a single article to WordPress."""
        try:
            # Need the project for WordPress credentials
            if not article.project_id:
                logger.warning("Article %s has no project_id, skipping auto-publish", article.id)
                article.auto_publish = False
                await db.commit()
                return

            proj_result = await db.execute(
                select(Project).where(Project.id == article.project_id)
            )
            project = proj_result.scalar_one_or_none()
            if not project:
                logger.warning("Project %s not found for article %s", article.project_id, article.id)
                return

            # Import WordPress helpers (avoid circular import at module level)
            from api.routes.wordpress import (
                _generate_image_seo_metadata,
                _upload_image_to_wp,
                _wp_client,
                create_wp_auth_header,
                get_wp_credentials,
            )
            from infrastructure.database.models import GeneratedImage

            wp_creds = get_wp_credentials(project)
            if not wp_creds:
                logger.warning(
                    "No WordPress credentials for project %s — skipping article %s",
                    article.project_id, article.id,
                )
                return

            auth_header = create_wp_auth_header(wp_creds["username"], wp_creds["app_password"])

            # Upload featured image if available
            featured_media_id = None
            if article.featured_image_id:
                try:
                    img_result = await db.execute(
                        select(GeneratedImage).where(GeneratedImage.id == article.featured_image_id)
                    )
                    featured_image = img_result.scalar_one_or_none()
                    if featured_image and featured_image.url:
                        seo_meta = _generate_image_seo_metadata(
                            article_title=article.title,
                            article_keyword=article.keyword,
                            article_meta_description=article.meta_description,
                        )
                        async with _wp_client(timeout=60.0) as media_client:
                            upload_result = await _upload_image_to_wp(
                                client=media_client,
                                image=featured_image,
                                wp_creds=wp_creds,
                                auth_header=auth_header,
                                title=seo_meta["title"],
                                alt_text=seo_meta["alt_text"],
                                caption=seo_meta["caption"],
                                description=seo_meta["description"],
                            )
                            featured_media_id = upload_result["wordpress_media_id"]
                except Exception as img_exc:
                    logger.warning("Auto-publish: image upload failed for %s: %s", article.id, img_exc)

            # Prepare WordPress post data
            post_data = {
                "title": article.title,
                "content": article.content_html or article.content,
                "status": "publish",
                "excerpt": article.meta_description or "",
            }
            if featured_media_id is not None:
                post_data["featured_media"] = featured_media_id

            # Create post on WordPress
            async with _wp_client(timeout=30.0) as client:
                create_url = f"{wp_creds['site_url']}/wp-json/wp/v2/posts"
                response = await client.post(
                    create_url,
                    headers={
                        "Authorization": auth_header,
                        "Content-Type": "application/json",
                    },
                    json=post_data,
                )

                if response.status_code not in (200, 201):
                    logger.error(
                        "Auto-publish failed for article %s: HTTP %s — %s",
                        article.id, response.status_code, response.text[:500],
                    )
                    # Mark as failed so we don't retry endlessly
                    article.status = ContentStatus.FAILED.value
                    article.generation_error = f"Auto-publish failed: WordPress returned HTTP {response.status_code}"
                    await db.commit()
                    return

                wp_post = response.json()
                article.wordpress_post_id = wp_post["id"]
                article.published_url = wp_post["link"]
                article.published_at = datetime.now(UTC)
                article.status = ContentStatus.PUBLISHED.value
                await db.commit()

                logger.info(
                    "Auto-published article %s to WordPress (post ID: %s, URL: %s)",
                    article.id, wp_post["id"], wp_post["link"],
                )

        except Exception as exc:
            logger.error("Auto-publish error for article %s: %s", article.id, exc, exc_info=True)
            try:
                article.status = ContentStatus.FAILED.value
                article.generation_error = f"Auto-publish error: {str(exc)[:500]}"
                await db.commit()
            except Exception:
                pass


content_scheduler = ContentSchedulerService()
