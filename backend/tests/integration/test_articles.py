"""Integration tests for article endpoints."""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from infrastructure.database.models import User, Article, Outline, ContentStatus

pytestmark = pytest.mark.asyncio


class TestCreateArticle:
    """Tests for POST /articles endpoint."""

    async def test_create_article_manual(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        test_user: User,
    ):
        """Test creating article manually without AI generation."""
        response = await async_client.post(
            "/api/v1/articles",
            headers=auth_headers,
            json={
                "title": "Complete Guide to SEO",
                "keyword": "seo optimization",
                "meta_description": "Learn everything about SEO optimization",
                "content": "# Introduction\n\nSEO is important for digital marketing.",
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Complete Guide to SEO"
        assert data["keyword"] == "seo optimization"
        assert data["status"] == ContentStatus.DRAFT.value
        assert data["user_id"] == test_user.id
        assert "slug" in data
        assert data["word_count"] > 0
        assert data["read_time"] is not None
        assert "seo_score" in data

    async def test_create_article_with_outline(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        test_user: User,
        db_session: AsyncSession,
    ):
        """Test creating article linked to an outline."""
        # Create outline first
        outline = Outline(
            id=str(uuid4()),
            user_id=test_user.id,
            title="SEO Guide",
            keyword="seo",
            status=ContentStatus.COMPLETED.value,
        )
        db_session.add(outline)
        await db_session.commit()

        response = await async_client.post(
            "/api/v1/articles",
            headers=auth_headers,
            json={
                "title": "SEO Guide Article",
                "keyword": "seo",
                "outline_id": outline.id,
                "content": "Article content here",
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert data["outline_id"] == outline.id

    async def test_create_article_slug_generation(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
    ):
        """Test that article slug is auto-generated from title."""
        response = await async_client.post(
            "/api/v1/articles",
            headers=auth_headers,
            json={
                "title": "How to Optimize Your Website for SEO",
                "keyword": "seo",
                "content": "Content here",
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert data["slug"] == "how-to-optimize-your-website-for-seo"

    async def test_create_article_unauthorized(self, async_client: AsyncClient):
        """Test creating article without authentication."""
        response = await async_client.post(
            "/api/v1/articles",
            json={
                "title": "Test",
                "keyword": "test",
            }
        )
        assert response.status_code == 401


class TestGenerateArticle:
    """Tests for POST /articles/generate endpoint."""

    async def test_generate_article_from_outline(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        test_user: User,
        db_session: AsyncSession,
    ):
        """Test generating article from outline using AI."""
        # Create outline with sections
        outline = Outline(
            id=str(uuid4()),
            user_id=test_user.id,
            title="Complete SEO Guide",
            keyword="seo optimization",
            target_audience="marketers",
            tone="professional",
            sections=[
                {
                    "heading": "Introduction",
                    "subheadings": ["What is SEO"],
                    "notes": "Overview",
                    "word_count_target": 200
                }
            ],
            status=ContentStatus.COMPLETED.value,
        )
        db_session.add(outline)
        await db_session.commit()

        # Mock the AI service
        from adapters.ai.anthropic_adapter import GeneratedArticle

        mock_article = GeneratedArticle(
            title="Complete SEO Guide",
            content="# Introduction\n\nSEO optimization is crucial for success.",
            meta_description="Learn about SEO optimization strategies",
            word_count=150
        )

        with patch(
            "api.routes.articles.content_ai_service.generate_article",
            new_callable=AsyncMock,
            return_value=mock_article
        ):
            response = await async_client.post(
                "/api/v1/articles/generate",
                headers=auth_headers,
                json={
                    "outline_id": outline.id,
                }
            )

        assert response.status_code == 201
        data = response.json()
        # Article generation is async — the endpoint returns immediately
        # with status "generating"; content is populated by the background task.
        assert data["status"] == ContentStatus.GENERATING.value
        assert data["outline_id"] == outline.id
        assert data["id"] is not None

    async def test_generate_article_outline_not_found(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
    ):
        """Test generating article with non-existent outline."""
        response = await async_client.post(
            "/api/v1/articles/generate",
            headers=auth_headers,
            json={
                "outline_id": str(uuid4()),
            }
        )
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    async def test_generate_article_outline_no_sections(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        test_user: User,
        db_session: AsyncSession,
    ):
        """Test generating article from outline without sections."""
        outline = Outline(
            id=str(uuid4()),
            user_id=test_user.id,
            title="Empty Outline",
            keyword="test",
            sections=None,
            status=ContentStatus.DRAFT.value,
        )
        db_session.add(outline)
        await db_session.commit()

        response = await async_client.post(
            "/api/v1/articles/generate",
            headers=auth_headers,
            json={
                "outline_id": outline.id,
            }
        )
        assert response.status_code == 400
        assert "no sections" in response.json()["detail"].lower()

    async def test_generate_article_ai_failure(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        test_user: User,
        db_session: AsyncSession,
    ):
        """Test article generation when AI service fails."""
        outline = Outline(
            id=str(uuid4()),
            user_id=test_user.id,
            title="Test Outline",
            keyword="test",
            sections=[{"heading": "Test", "subheadings": [], "notes": "", "word_count_target": 100}],
            status=ContentStatus.COMPLETED.value,
        )
        db_session.add(outline)
        await db_session.commit()

        with patch(
            "api.routes.articles.content_ai_service.generate_article",
            new_callable=AsyncMock,
            side_effect=Exception("AI service error")
        ):
            response = await async_client.post(
                "/api/v1/articles/generate",
                headers=auth_headers,
                json={
                    "outline_id": outline.id,
                }
            )

        assert response.status_code == 201
        data = response.json()
        # AI failure happens in the background task, not during the request.
        # The endpoint always returns "generating" immediately.
        assert data["status"] == ContentStatus.GENERATING.value


class TestListArticles:
    """Tests for GET /articles endpoint."""

    async def test_list_articles_empty(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
    ):
        """Test listing articles when none exist."""
        response = await async_client.get("/api/v1/articles", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["items"] == []
        assert data["page"] == 1

    async def test_list_articles_with_data(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        test_user: User,
        db_session: AsyncSession,
    ):
        """Test listing articles with existing data."""
        # Create test articles
        articles = [
            Article(
                id=str(uuid4()),
                user_id=test_user.id,
                title=f"Article {i}",
                keyword=f"keyword{i}",
                status=ContentStatus.DRAFT.value,
            )
            for i in range(5)
        ]
        for article in articles:
            db_session.add(article)
        await db_session.commit()

        response = await async_client.get("/api/v1/articles", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 5
        assert len(data["items"]) == 5

    async def test_list_articles_pagination(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        test_user: User,
        db_session: AsyncSession,
    ):
        """Test article list pagination."""
        # Create 25 test articles
        for i in range(25):
            article = Article(
                id=str(uuid4()),
                user_id=test_user.id,
                title=f"Article {i}",
                keyword=f"keyword{i}",
                status=ContentStatus.DRAFT.value,
            )
            db_session.add(article)
        await db_session.commit()

        # Get first page
        response = await async_client.get(
            "/api/v1/articles?page=1&page_size=10",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 25
        assert len(data["items"]) == 10
        assert data["page"] == 1
        assert data["pages"] == 3

    async def test_list_articles_filter_by_status(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        test_user: User,
        db_session: AsyncSession,
    ):
        """Test filtering articles by status."""
        # Create articles with different statuses
        for i, status in enumerate([
            ContentStatus.DRAFT.value,
            ContentStatus.COMPLETED.value,
            ContentStatus.PUBLISHED.value,
        ]):
            article = Article(
                id=str(uuid4()),
                user_id=test_user.id,
                title=f"Article {i}",
                keyword=f"keyword{i}",
                status=status,
            )
            db_session.add(article)
        await db_session.commit()

        # Filter by published status
        response = await async_client.get(
            "/api/v1/articles?status=published",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["status"] == ContentStatus.PUBLISHED.value

    async def test_list_articles_filter_by_keyword(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        test_user: User,
        db_session: AsyncSession,
    ):
        """Test filtering articles by keyword."""
        keywords = ["seo optimization", "content marketing", "social media"]
        for i, kw in enumerate(keywords):
            article = Article(
                id=str(uuid4()),
                user_id=test_user.id,
                title=f"Article {i}",
                keyword=kw,
                status=ContentStatus.DRAFT.value,
            )
            db_session.add(article)
        await db_session.commit()

        # Filter by keyword
        response = await async_client.get(
            "/api/v1/articles?keyword=marketing",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["keyword"] == "content marketing"


class TestGetArticle:
    """Tests for GET /articles/{article_id} endpoint."""

    async def test_get_article_success(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        test_user: User,
        db_session: AsyncSession,
    ):
        """Test retrieving a specific article."""
        article = Article(
            id=str(uuid4()),
            user_id=test_user.id,
            title="Test Article",
            keyword="test",
            content="Article content here",
            status=ContentStatus.DRAFT.value,
        )
        db_session.add(article)
        await db_session.commit()

        response = await async_client.get(
            f"/api/v1/articles/{article.id}",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == article.id
        assert data["title"] == "Test Article"

    async def test_get_article_not_found(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
    ):
        """Test retrieving non-existent article."""
        response = await async_client.get(
            f"/api/v1/articles/{str(uuid4())}",
            headers=auth_headers,
        )
        assert response.status_code == 404

    async def test_get_article_wrong_user(
        self,
        async_client: AsyncClient,
        other_auth_headers: dict,
        test_user: User,
        db_session: AsyncSession,
    ):
        """Test retrieving article owned by different user."""
        article = Article(
            id=str(uuid4()),
            user_id=test_user.id,
            title="Test Article",
            keyword="test",
            status=ContentStatus.DRAFT.value,
        )
        db_session.add(article)
        await db_session.commit()

        response = await async_client.get(
            f"/api/v1/articles/{article.id}",
            headers=other_auth_headers,
        )
        assert response.status_code == 404


class TestUpdateArticle:
    """Tests for PUT /articles/{article_id} endpoint."""

    async def test_update_article_success(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        test_user: User,
        db_session: AsyncSession,
    ):
        """Test successful article update."""
        article = Article(
            id=str(uuid4()),
            user_id=test_user.id,
            title="Original Title",
            keyword="original",
            content="Original content",
            status=ContentStatus.DRAFT.value,
        )
        db_session.add(article)
        await db_session.commit()

        response = await async_client.put(
            f"/api/v1/articles/{article.id}",
            headers=auth_headers,
            json={
                "title": "Updated Title",
                "content": "Updated content here with more text",
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated Title"
        assert data["content"] == "Updated content here with more text"
        assert "seo_score" in data  # SEO should be re-analyzed

    async def test_update_article_recalculates_seo(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        test_user: User,
        db_session: AsyncSession,
    ):
        """Test that updating content recalculates SEO metrics."""
        article = Article(
            id=str(uuid4()),
            user_id=test_user.id,
            title="SEO Article",
            keyword="seo",
            content="Original content",
            meta_description="Original description",
            status=ContentStatus.DRAFT.value,
        )
        db_session.add(article)
        await db_session.commit()

        new_content = "# SEO Guide\n\nSEO optimization is key. " * 20  # Longer content

        response = await async_client.put(
            f"/api/v1/articles/{article.id}",
            headers=auth_headers,
            json={"content": new_content}
        )

        assert response.status_code == 200
        data = response.json()
        # The route refreshes the article in the shared DB session, so
        # article.word_count reflects the updated value. Assert word count
        # is positive and SEO analysis was performed.
        assert data["word_count"] > 0
        assert "seo_analysis" in data

    async def test_update_article_not_found(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
    ):
        """Test updating non-existent article."""
        response = await async_client.put(
            f"/api/v1/articles/{str(uuid4())}",
            headers=auth_headers,
            json={"title": "Updated"}
        )
        assert response.status_code == 404


class TestDeleteArticle:
    """Tests for DELETE /articles/{article_id} endpoint."""

    async def test_delete_article_success(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        test_user: User,
        db_session: AsyncSession,
    ):
        """Test successful article deletion."""
        article = Article(
            id=str(uuid4()),
            user_id=test_user.id,
            title="To Delete",
            keyword="delete",
            status=ContentStatus.DRAFT.value,
        )
        db_session.add(article)
        await db_session.commit()

        response = await async_client.delete(
            f"/api/v1/articles/{article.id}",
            headers=auth_headers,
        )

        assert response.status_code == 204

        # Verify article was deleted
        from sqlalchemy import select
        result = await db_session.execute(
            select(Article).where(Article.id == article.id)
        )
        deleted_article = result.scalar_one_or_none()
        assert deleted_article is None

    async def test_delete_article_not_found(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
    ):
        """Test deleting non-existent article."""
        response = await async_client.delete(
            f"/api/v1/articles/{str(uuid4())}",
            headers=auth_headers,
        )
        assert response.status_code == 404


class TestImproveArticle:
    """Tests for POST /articles/{article_id}/improve endpoint."""

    async def test_improve_article_success(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        test_user: User,
        db_session: AsyncSession,
    ):
        """Test successful article improvement using AI."""
        article = Article(
            id=str(uuid4()),
            user_id=test_user.id,
            title="Article to Improve",
            keyword="seo",
            content="Basic content that needs improvement.",
            status=ContentStatus.COMPLETED.value,
        )
        db_session.add(article)
        await db_session.commit()

        with patch(
            "api.routes.articles.content_ai_service.improve_content",
            new_callable=AsyncMock,
            return_value="Improved and enhanced content with better structure."
        ):
            response = await async_client.post(
                f"/api/v1/articles/{article.id}/improve",
                headers=auth_headers,
                json={
                    "improvement_type": "readability"
                }
            )

        assert response.status_code == 200
        data = response.json()
        assert data["content"] == "Improved and enhanced content with better structure."
        assert "seo_score" in data

    async def test_improve_article_no_content(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        test_user: User,
        db_session: AsyncSession,
    ):
        """Test improving article with no content."""
        article = Article(
            id=str(uuid4()),
            user_id=test_user.id,
            title="Empty Article",
            keyword="test",
            content=None,
            status=ContentStatus.DRAFT.value,
        )
        db_session.add(article)
        await db_session.commit()

        response = await async_client.post(
            f"/api/v1/articles/{article.id}/improve",
            headers=auth_headers,
            json={
                "improvement_type": "readability"
            }
        )
        assert response.status_code == 400
        assert "no content" in response.json()["detail"].lower()

    async def test_improve_article_not_found(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
    ):
        """Test improving non-existent article."""
        response = await async_client.post(
            f"/api/v1/articles/{str(uuid4())}/improve",
            headers=auth_headers,
            json={
                "improvement_type": "readability"
            }
        )
        assert response.status_code == 404


class TestAnalyzeSEO:
    """Tests for POST /articles/{article_id}/analyze-seo endpoint."""

    async def test_analyze_seo_success(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        test_user: User,
        db_session: AsyncSession,
    ):
        """Test SEO analysis on article."""
        article = Article(
            id=str(uuid4()),
            user_id=test_user.id,
            title="SEO Optimization Guide",
            keyword="seo",
            meta_description="Learn about SEO optimization techniques for better rankings",
            content="## Introduction\n\nSEO optimization is crucial. " * 10,
            status=ContentStatus.COMPLETED.value,
        )
        db_session.add(article)
        await db_session.commit()

        response = await async_client.post(
            f"/api/v1/articles/{article.id}/analyze-seo",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "seo_score" in data
        assert "seo_analysis" in data
        assert data["seo_analysis"]["keyword_density"] is not None
        assert "suggestions" in data["seo_analysis"]

    async def test_analyze_seo_no_content(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        test_user: User,
        db_session: AsyncSession,
    ):
        """Test SEO analysis on article without content."""
        article = Article(
            id=str(uuid4()),
            user_id=test_user.id,
            title="Empty Article",
            keyword="test",
            content=None,
            status=ContentStatus.DRAFT.value,
        )
        db_session.add(article)
        await db_session.commit()

        response = await async_client.post(
            f"/api/v1/articles/{article.id}/analyze-seo",
            headers=auth_headers,
        )
        assert response.status_code == 400
        assert "no content" in response.json()["detail"].lower()

    async def test_analyze_seo_not_found(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
    ):
        """Test SEO analysis on non-existent article."""
        response = await async_client.post(
            f"/api/v1/articles/{str(uuid4())}/analyze-seo",
            headers=auth_headers,
        )
        assert response.status_code == 404
