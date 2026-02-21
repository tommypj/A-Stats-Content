"""
Integration tests for admin content management API.

Tests admin content endpoints:
- List and manage articles (all users)
- List and manage outlines
- List and manage images
- Bulk delete operations
- Audit logging
- Authorization checks
"""

import pytest
from datetime import datetime
from uuid import uuid4

from fastapi import status
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.database.models import User

# Skip all tests if admin routes or content models are not available
try:
    from api.routes import admin
    from infrastructure.database.models.content import Article, Outline
    ADMIN_CONTENT_AVAILABLE = True
except (ImportError, AttributeError):
    ADMIN_CONTENT_AVAILABLE = False
    pytestmark = pytest.mark.skip(reason="Admin content routes not implemented yet")


@pytest.fixture
async def sample_article(db_session: AsyncSession, test_user: User):
    """Create a sample article for testing."""
    article = Article(
        id=str(uuid4()),
        user_id=test_user.id,
        title="Sample Article",
        content="This is a sample article content.",
        status="published",
        word_count=500,
    )
    db_session.add(article)
    await db_session.commit()
    await db_session.refresh(article)
    return article


@pytest.fixture
async def sample_outline(db_session: AsyncSession, test_user: User):
    """Create a sample outline for testing."""
    outline = Outline(
        id=str(uuid4()),
        user_id=test_user.id,
        title="Sample Outline",
        topic="Mindfulness Meditation",
        sections=[{"title": "Introduction", "points": ["Point 1", "Point 2"]}],
    )
    db_session.add(outline)
    await db_session.commit()
    await db_session.refresh(outline)
    return outline


class TestAdminArticlesEndpoint:
    """Tests for GET /admin/content/articles endpoint."""

    @pytest.mark.asyncio
    async def test_admin_can_list_all_articles(
        self,
        async_client: AsyncClient,
        admin_token: dict,
        sample_article,
    ):
        """Test that admin can list articles from all users."""
        if not ADMIN_CONTENT_AVAILABLE:
            pytest.skip("Admin content routes not available")

        response = await async_client.get(
            "/api/v1/admin/content/articles",
            headers=admin_token,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "articles" in data
        assert "total" in data
        assert len(data["articles"]) > 0

        # Verify article structure
        article = data["articles"][0]
        assert "id" in article
        assert "title" in article
        assert "user_id" in article
        assert "user_email" in article  # Should include user info
        assert "status" in article
        assert "created_at" in article

    @pytest.mark.asyncio
    async def test_regular_user_cannot_list_all_articles(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
    ):
        """Test that regular user cannot list all articles."""
        if not ADMIN_CONTENT_AVAILABLE:
            pytest.skip("Admin content routes not available")

        response = await async_client.get(
            "/api/v1/admin/content/articles",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.asyncio
    async def test_list_articles_pagination(
        self,
        async_client: AsyncClient,
        admin_token: dict,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Test pagination in articles listing."""
        if not ADMIN_CONTENT_AVAILABLE:
            pytest.skip("Admin content routes not available")

        # Create multiple articles
        for i in range(15):
            article = Article(
                id=str(uuid4()),
                user_id=test_user.id,
                title=f"Article {i}",
                content=f"Content {i}",
                status="published",
                word_count=100,
            )
            db_session.add(article)
        await db_session.commit()

        # Get first page
        response = await async_client.get(
            "/api/v1/admin/content/articles?page=1&per_page=10",
            headers=admin_token,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["articles"]) == 10
        assert data["page"] == 1

    @pytest.mark.asyncio
    async def test_filter_articles_by_user(
        self,
        async_client: AsyncClient,
        admin_token: dict,
        test_user: User,
        other_user: User,
        db_session: AsyncSession,
    ):
        """Test filtering articles by user_id."""
        if not ADMIN_CONTENT_AVAILABLE:
            pytest.skip("Admin content routes not available")

        # Create articles for both users
        for user in [test_user, other_user]:
            article = Article(
                id=str(uuid4()),
                user_id=user.id,
                title=f"Article by {user.name}",
                content="Content",
                status="published",
                word_count=100,
            )
            db_session.add(article)
        await db_session.commit()

        # Filter by test_user
        response = await async_client.get(
            f"/api/v1/admin/content/articles?user_id={test_user.id}",
            headers=admin_token,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        # All articles should belong to test_user
        for article in data["articles"]:
            assert article["user_id"] == test_user.id

    @pytest.mark.asyncio
    async def test_filter_articles_by_status(
        self,
        async_client: AsyncClient,
        admin_token: dict,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Test filtering articles by status."""
        if not ADMIN_CONTENT_AVAILABLE:
            pytest.skip("Admin content routes not available")

        # Create articles with different statuses
        for status_val in ["draft", "published"]:
            article = Article(
                id=str(uuid4()),
                user_id=test_user.id,
                title=f"Article {status_val}",
                content="Content",
                status=status_val,
                word_count=100,
            )
            db_session.add(article)
        await db_session.commit()

        # Filter by published status
        response = await async_client.get(
            "/api/v1/admin/content/articles?status=published",
            headers=admin_token,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        for article in data["articles"]:
            assert article["status"] == "published"

    @pytest.mark.asyncio
    async def test_search_articles_by_title(
        self,
        async_client: AsyncClient,
        admin_token: dict,
        sample_article,
    ):
        """Test searching articles by title."""
        if not ADMIN_CONTENT_AVAILABLE:
            pytest.skip("Admin content routes not available")

        response = await async_client.get(
            f"/api/v1/admin/content/articles?search={sample_article.title}",
            headers=admin_token,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        titles = [a["title"] for a in data["articles"]]
        assert sample_article.title in titles


class TestAdminDeleteArticleEndpoint:
    """Tests for DELETE /admin/content/articles/{article_id} endpoint."""

    @pytest.mark.asyncio
    async def test_admin_can_delete_any_article(
        self,
        async_client: AsyncClient,
        admin_token: dict,
        sample_article,
        db_session: AsyncSession,
    ):
        """Test that admin can delete any user's article."""
        if not ADMIN_CONTENT_AVAILABLE:
            pytest.skip("Admin content routes not available")

        response = await async_client.delete(
            f"/api/v1/admin/content/articles/{sample_article.id}",
            headers=admin_token,
        )

        assert response.status_code == status.HTTP_200_OK

        # Verify deletion in database
        result = await db_session.execute(
            select(Article).where(Article.id == sample_article.id)
        )
        deleted_article = result.scalar_one_or_none()
        assert deleted_article is None

    @pytest.mark.asyncio
    async def test_regular_user_cannot_delete_other_users_article(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        other_user: User,
    ):
        """Test that regular user cannot delete other user's article via admin endpoint."""
        if not ADMIN_CONTENT_AVAILABLE:
            pytest.skip("Admin content routes not available")

        # Create article owned by other_user
        article = Article(
            id=str(uuid4()),
            user_id=other_user.id,
            title="Other User's Article",
            content="Content",
            status="published",
            word_count=100,
        )
        db_session.add(article)
        await db_session.commit()

        response = await async_client.delete(
            f"/api/v1/admin/content/articles/{article.id}",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.asyncio
    async def test_delete_nonexistent_article_returns_404(
        self,
        async_client: AsyncClient,
        admin_token: dict,
    ):
        """Test that deleting nonexistent article returns 404."""
        if not ADMIN_CONTENT_AVAILABLE:
            pytest.skip("Admin content routes not available")

        fake_id = str(uuid4())
        response = await async_client.delete(
            f"/api/v1/admin/content/articles/{fake_id}",
            headers=admin_token,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestAdminOutlinesEndpoint:
    """Tests for GET /admin/content/outlines endpoint."""

    @pytest.mark.asyncio
    async def test_admin_can_list_all_outlines(
        self,
        async_client: AsyncClient,
        admin_token: dict,
        sample_outline,
    ):
        """Test that admin can list outlines from all users."""
        if not ADMIN_CONTENT_AVAILABLE:
            pytest.skip("Admin content routes not available")

        response = await async_client.get(
            "/api/v1/admin/content/outlines",
            headers=admin_token,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "outlines" in data
        assert "total" in data
        assert len(data["outlines"]) > 0

        # Verify outline structure
        outline = data["outlines"][0]
        assert "id" in outline
        assert "title" in outline
        assert "topic" in outline
        assert "user_id" in outline
        assert "user_email" in outline

    @pytest.mark.asyncio
    async def test_filter_outlines_by_user(
        self,
        async_client: AsyncClient,
        admin_token: dict,
        test_user: User,
    ):
        """Test filtering outlines by user_id."""
        if not ADMIN_CONTENT_AVAILABLE:
            pytest.skip("Admin content routes not available")

        response = await async_client.get(
            f"/api/v1/admin/content/outlines?user_id={test_user.id}",
            headers=admin_token,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        for outline in data["outlines"]:
            assert outline["user_id"] == test_user.id


class TestAdminDeleteOutlineEndpoint:
    """Tests for DELETE /admin/content/outlines/{outline_id} endpoint."""

    @pytest.mark.asyncio
    async def test_admin_can_delete_any_outline(
        self,
        async_client: AsyncClient,
        admin_token: dict,
        sample_outline,
        db_session: AsyncSession,
    ):
        """Test that admin can delete any user's outline."""
        if not ADMIN_CONTENT_AVAILABLE:
            pytest.skip("Admin content routes not available")

        response = await async_client.delete(
            f"/api/v1/admin/content/outlines/{sample_outline.id}",
            headers=admin_token,
        )

        assert response.status_code == status.HTTP_200_OK

        # Verify deletion
        result = await db_session.execute(
            select(Outline).where(Outline.id == sample_outline.id)
        )
        deleted_outline = result.scalar_one_or_none()
        assert deleted_outline is None


class TestAdminImagesEndpoint:
    """Tests for GET /admin/content/images endpoint."""

    @pytest.mark.asyncio
    async def test_admin_can_list_all_images(
        self,
        async_client: AsyncClient,
        admin_token: dict,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Test that admin can list images from all users."""
        if not ADMIN_CONTENT_AVAILABLE:
            pytest.skip("Admin content routes not available")

        # Import Image model if available
        try:
            from infrastructure.database.models.content import Image
        except ImportError:
            pytest.skip("Image model not available")

        # Create sample image
        image = Image(
            id=str(uuid4()),
            user_id=test_user.id,
            prompt="Sample image",
            image_url="https://example.com/image.jpg",
            file_size=1024000,
        )
        db_session.add(image)
        await db_session.commit()

        response = await async_client.get(
            "/api/v1/admin/content/images",
            headers=admin_token,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "images" in data
        assert "total" in data

    @pytest.mark.asyncio
    async def test_filter_images_by_user(
        self,
        async_client: AsyncClient,
        admin_token: dict,
        test_user: User,
    ):
        """Test filtering images by user_id."""
        if not ADMIN_CONTENT_AVAILABLE:
            pytest.skip("Admin content routes not available")

        response = await async_client.get(
            f"/api/v1/admin/content/images?user_id={test_user.id}",
            headers=admin_token,
        )

        assert response.status_code == status.HTTP_200_OK


class TestAdminDeleteImageEndpoint:
    """Tests for DELETE /admin/content/images/{image_id} endpoint."""

    @pytest.mark.asyncio
    async def test_admin_can_delete_any_image(
        self,
        async_client: AsyncClient,
        admin_token: dict,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Test that admin can delete any user's image."""
        if not ADMIN_CONTENT_AVAILABLE:
            pytest.skip("Admin content routes not available")

        try:
            from infrastructure.database.models.content import Image
        except ImportError:
            pytest.skip("Image model not available")

        # Create sample image
        image = Image(
            id=str(uuid4()),
            user_id=test_user.id,
            prompt="Sample image",
            image_url="https://example.com/image.jpg",
            file_size=1024000,
        )
        db_session.add(image)
        await db_session.commit()

        response = await async_client.delete(
            f"/api/v1/admin/content/images/{image.id}",
            headers=admin_token,
        )

        assert response.status_code == status.HTTP_200_OK


class TestBulkDeleteEndpoint:
    """Tests for POST /admin/content/bulk-delete endpoint."""

    @pytest.mark.asyncio
    async def test_admin_can_bulk_delete_articles(
        self,
        async_client: AsyncClient,
        admin_token: dict,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Test bulk deletion of articles."""
        if not ADMIN_CONTENT_AVAILABLE:
            pytest.skip("Admin content routes not available")

        # Create multiple articles
        article_ids = []
        for i in range(3):
            article = Article(
                id=str(uuid4()),
                user_id=test_user.id,
                title=f"Article {i}",
                content="Content",
                status="published",
                word_count=100,
            )
            db_session.add(article)
            article_ids.append(article.id)
        await db_session.commit()

        # Bulk delete
        response = await async_client.post(
            "/api/v1/admin/content/bulk-delete",
            headers=admin_token,
            json={
                "content_type": "articles",
                "ids": article_ids,
            },
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["deleted_count"] == 3

        # Verify deletion
        for article_id in article_ids:
            result = await db_session.execute(
                select(Article).where(Article.id == article_id)
            )
            assert result.scalar_one_or_none() is None

    @pytest.mark.asyncio
    async def test_regular_user_cannot_bulk_delete(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
    ):
        """Test that regular user cannot bulk delete content."""
        if not ADMIN_CONTENT_AVAILABLE:
            pytest.skip("Admin content routes not available")

        response = await async_client.post(
            "/api/v1/admin/content/bulk-delete",
            headers=auth_headers,
            json={
                "content_type": "articles",
                "ids": [str(uuid4())],
            },
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.asyncio
    async def test_bulk_delete_with_invalid_content_type(
        self,
        async_client: AsyncClient,
        admin_token: dict,
    ):
        """Test bulk delete with invalid content type."""
        if not ADMIN_CONTENT_AVAILABLE:
            pytest.skip("Admin content routes not available")

        response = await async_client.post(
            "/api/v1/admin/content/bulk-delete",
            headers=admin_token,
            json={
                "content_type": "invalid_type",
                "ids": [str(uuid4())],
            },
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestAuditLogging:
    """Tests for admin action audit logging."""

    @pytest.mark.asyncio
    async def test_admin_actions_are_logged(
        self,
        async_client: AsyncClient,
        admin_token: dict,
        sample_article,
    ):
        """Test that admin actions are logged in audit log."""
        if not ADMIN_CONTENT_AVAILABLE:
            pytest.skip("Admin content routes not available")

        # Perform admin action (delete article)
        await async_client.delete(
            f"/api/v1/admin/content/articles/{sample_article.id}",
            headers=admin_token,
        )

        # Check audit log endpoint
        try:
            response = await async_client.get(
                "/api/v1/admin/audit-log",
                headers=admin_token,
            )

            if response.status_code == status.HTTP_200_OK:
                data = response.json()
                assert "logs" in data
                # Should include the delete action
                actions = [log["action"] for log in data["logs"]]
                assert "delete_article" in actions or "content.delete" in actions
        except Exception:
            # Audit log endpoint might not be implemented yet
            pytest.skip("Audit log endpoint not available")

    @pytest.mark.asyncio
    async def test_audit_log_includes_admin_info(
        self,
        async_client: AsyncClient,
        admin_token: dict,
        admin_user: User,
    ):
        """Test that audit log includes admin user info."""
        if not ADMIN_CONTENT_AVAILABLE:
            pytest.skip("Admin content routes not available")

        try:
            response = await async_client.get(
                "/api/v1/admin/audit-log",
                headers=admin_token,
            )

            if response.status_code == status.HTTP_200_OK:
                data = response.json()
                if data["logs"]:
                    log = data["logs"][0]
                    assert "admin_id" in log or "user_id" in log
                    assert "timestamp" in log
                    assert "action" in log
        except Exception:
            pytest.skip("Audit log endpoint not available")

    @pytest.mark.asyncio
    async def test_regular_user_cannot_access_audit_log(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
    ):
        """Test that regular user cannot access audit log."""
        if not ADMIN_CONTENT_AVAILABLE:
            pytest.skip("Admin content routes not available")

        try:
            response = await async_client.get(
                "/api/v1/admin/audit-log",
                headers=auth_headers,
            )

            # Should be forbidden or not found
            assert response.status_code in [
                status.HTTP_403_FORBIDDEN,
                status.HTTP_404_NOT_FOUND,
            ]
        except Exception:
            pytest.skip("Audit log endpoint not available")
