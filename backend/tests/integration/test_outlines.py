"""Integration tests for outline endpoints."""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from infrastructure.database.models import User, Outline, ContentStatus

pytestmark = pytest.mark.asyncio


class TestCreateOutline:
    """Tests for POST /outlines endpoint."""

    async def test_create_outline_manual(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        test_user: User,
    ):
        """Test creating outline without auto-generation."""
        response = await async_client.post(
            "/api/v1/outlines",
            headers=auth_headers,
            json={
                "keyword": "content marketing",
                "target_audience": "small business owners",
                "tone": "professional",
                "word_count_target": 1500,
                "auto_generate": False,
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert data["keyword"] == "content marketing"
        assert data["target_audience"] == "small business owners"
        assert data["tone"] == "professional"
        assert data["word_count_target"] == 1500
        assert data["status"] == ContentStatus.DRAFT.value
        assert data["user_id"] == test_user.id
        assert "id" in data

    async def test_create_outline_with_auto_generate(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        test_user: User,
    ):
        """Test creating outline with AI auto-generation."""
        # Mock the AI service
        from adapters.ai.anthropic_adapter import GeneratedOutline, OutlineSection

        mock_outline = GeneratedOutline(
            title="Complete Guide to Content Marketing",
            sections=[
                OutlineSection(
                    heading="Introduction to Content Marketing",
                    subheadings=["What is Content Marketing", "Why It Matters"],
                    notes="Overview of content marketing basics",
                    word_count_target=300
                ),
                OutlineSection(
                    heading="Content Strategy",
                    subheadings=["Planning", "Execution", "Measurement"],
                    notes="How to develop a content strategy",
                    word_count_target=600
                ),
            ],
            meta_description="A complete guide to content marketing for small business owners.",
            estimated_word_count=1500,
            estimated_read_time=8
        )

        with patch(
            "api.routes.outlines.content_ai_service.generate_outline",
            new_callable=AsyncMock,
            return_value=mock_outline
        ):
            response = await async_client.post(
                "/api/v1/outlines",
                headers=auth_headers,
                json={
                    "keyword": "content marketing",
                    "target_audience": "small business owners",
                    "tone": "professional",
                    "word_count_target": 1500,
                    "auto_generate": True,
                }
            )

        assert response.status_code == 201
        data = response.json()
        assert data["status"] == ContentStatus.COMPLETED.value
        assert data["title"] == "Complete Guide to Content Marketing"
        assert len(data["sections"]) == 2
        assert data["estimated_read_time"] == 8

    async def test_create_outline_unauthorized(self, async_client: AsyncClient):
        """Test creating outline without authentication."""
        response = await async_client.post(
            "/api/v1/outlines",
            json={
                "keyword": "test",
                "auto_generate": False,
            }
        )
        assert response.status_code == 401

    async def test_create_outline_validation_error(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
    ):
        """Test creating outline with invalid data."""
        response = await async_client.post(
            "/api/v1/outlines",
            headers=auth_headers,
            json={
                # Missing required keyword field
                "auto_generate": False,
            }
        )
        assert response.status_code == 422


class TestListOutlines:
    """Tests for GET /outlines endpoint."""

    async def test_list_outlines_empty(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
    ):
        """Test listing outlines when none exist."""
        response = await async_client.get("/api/v1/outlines", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["items"] == []
        assert data["page"] == 1
        assert data["pages"] == 0

    async def test_list_outlines_with_data(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        test_user: User,
        db_session: AsyncSession,
    ):
        """Test listing outlines with existing data."""
        # Create test outlines
        outlines = [
            Outline(
                id=str(uuid4()),
                user_id=test_user.id,
                title=f"Test Outline {i}",
                keyword=f"keyword{i}",
                status=ContentStatus.COMPLETED.value,
            )
            for i in range(5)
        ]
        for outline in outlines:
            db_session.add(outline)
        await db_session.commit()

        response = await async_client.get("/api/v1/outlines", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 5
        assert len(data["items"]) == 5

    async def test_list_outlines_pagination(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        test_user: User,
        db_session: AsyncSession,
    ):
        """Test outline list pagination."""
        # Create 25 test outlines
        for i in range(25):
            outline = Outline(
                id=str(uuid4()),
                user_id=test_user.id,
                title=f"Test Outline {i}",
                keyword=f"keyword{i}",
                status=ContentStatus.COMPLETED.value,
            )
            db_session.add(outline)
        await db_session.commit()

        # Get first page
        response = await async_client.get(
            "/api/v1/outlines?page=1&page_size=10",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 25
        assert len(data["items"]) == 10
        assert data["page"] == 1
        assert data["pages"] == 3

        # Get second page
        response = await async_client.get(
            "/api/v1/outlines?page=2&page_size=10",
            headers=auth_headers,
        )

        data = response.json()
        assert len(data["items"]) == 10
        assert data["page"] == 2

    async def test_list_outlines_filter_by_status(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        test_user: User,
        db_session: AsyncSession,
    ):
        """Test filtering outlines by status."""
        # Create outlines with different statuses
        for i, status in enumerate([
            ContentStatus.DRAFT.value,
            ContentStatus.COMPLETED.value,
            ContentStatus.COMPLETED.value,
            ContentStatus.FAILED.value,
        ]):
            outline = Outline(
                id=str(uuid4()),
                user_id=test_user.id,
                title=f"Outline {i}",
                keyword=f"keyword{i}",
                status=status,
            )
            db_session.add(outline)
        await db_session.commit()

        # Filter by completed status
        response = await async_client.get(
            "/api/v1/outlines?status=completed",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert all(item["status"] == ContentStatus.COMPLETED.value for item in data["items"])

    async def test_list_outlines_filter_by_keyword(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        test_user: User,
        db_session: AsyncSession,
    ):
        """Test filtering outlines by keyword."""
        # Create outlines with different keywords
        keywords = ["seo optimization", "content marketing", "social media"]
        for i, kw in enumerate(keywords):
            outline = Outline(
                id=str(uuid4()),
                user_id=test_user.id,
                title=f"Outline {i}",
                keyword=kw,
                status=ContentStatus.COMPLETED.value,
            )
            db_session.add(outline)
        await db_session.commit()

        # Filter by keyword
        response = await async_client.get(
            "/api/v1/outlines?keyword=marketing",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["keyword"] == "content marketing"


class TestGetOutline:
    """Tests for GET /outlines/{outline_id} endpoint."""

    async def test_get_outline_success(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        test_user: User,
        db_session: AsyncSession,
    ):
        """Test retrieving a specific outline."""
        outline = Outline(
            id=str(uuid4()),
            user_id=test_user.id,
            title="Test Outline",
            keyword="test keyword",
            status=ContentStatus.COMPLETED.value,
        )
        db_session.add(outline)
        await db_session.commit()

        response = await async_client.get(
            f"/api/v1/outlines/{outline.id}",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == outline.id
        assert data["title"] == "Test Outline"
        assert data["keyword"] == "test keyword"

    async def test_get_outline_not_found(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
    ):
        """Test retrieving non-existent outline."""
        response = await async_client.get(
            f"/api/v1/outlines/{str(uuid4())}",
            headers=auth_headers,
        )
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    async def test_get_outline_unauthorized(
        self,
        async_client: AsyncClient,
        test_user: User,
        db_session: AsyncSession,
    ):
        """Test retrieving outline without authentication."""
        outline = Outline(
            id=str(uuid4()),
            user_id=test_user.id,
            title="Test Outline",
            keyword="test",
            status=ContentStatus.DRAFT.value,
        )
        db_session.add(outline)
        await db_session.commit()

        response = await async_client.get(f"/api/v1/outlines/{outline.id}")
        assert response.status_code == 401

    async def test_get_outline_wrong_user(
        self,
        async_client: AsyncClient,
        other_auth_headers: dict,
        test_user: User,
        db_session: AsyncSession,
    ):
        """Test retrieving outline owned by different user."""
        outline = Outline(
            id=str(uuid4()),
            user_id=test_user.id,
            title="Test Outline",
            keyword="test",
            status=ContentStatus.DRAFT.value,
        )
        db_session.add(outline)
        await db_session.commit()

        response = await async_client.get(
            f"/api/v1/outlines/{outline.id}",
            headers=other_auth_headers,
        )
        assert response.status_code == 404


class TestUpdateOutline:
    """Tests for PUT /outlines/{outline_id} endpoint."""

    async def test_update_outline_success(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        test_user: User,
        db_session: AsyncSession,
    ):
        """Test successful outline update."""
        outline = Outline(
            id=str(uuid4()),
            user_id=test_user.id,
            title="Original Title",
            keyword="original",
            status=ContentStatus.DRAFT.value,
        )
        db_session.add(outline)
        await db_session.commit()

        response = await async_client.put(
            f"/api/v1/outlines/{outline.id}",
            headers=auth_headers,
            json={
                "title": "Updated Title",
                "keyword": "updated keyword",
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated Title"
        assert data["keyword"] == "updated keyword"

    async def test_update_outline_sections(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        test_user: User,
        db_session: AsyncSession,
    ):
        """Test updating outline sections."""
        outline = Outline(
            id=str(uuid4()),
            user_id=test_user.id,
            title="Test Outline",
            keyword="test",
            status=ContentStatus.DRAFT.value,
        )
        db_session.add(outline)
        await db_session.commit()

        new_sections = [
            {
                "heading": "Introduction",
                "subheadings": ["Overview", "Background"],
                "notes": "Intro section",
                "word_count_target": 200
            }
        ]

        response = await async_client.put(
            f"/api/v1/outlines/{outline.id}",
            headers=auth_headers,
            json={"sections": new_sections}
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["sections"]) == 1
        assert data["sections"][0]["heading"] == "Introduction"

    async def test_update_outline_not_found(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
    ):
        """Test updating non-existent outline."""
        response = await async_client.put(
            f"/api/v1/outlines/{str(uuid4())}",
            headers=auth_headers,
            json={"title": "Updated"}
        )
        assert response.status_code == 404


class TestDeleteOutline:
    """Tests for DELETE /outlines/{outline_id} endpoint."""

    async def test_delete_outline_success(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        test_user: User,
        db_session: AsyncSession,
    ):
        """Test successful outline deletion."""
        outline = Outline(
            id=str(uuid4()),
            user_id=test_user.id,
            title="To Delete",
            keyword="delete",
            status=ContentStatus.DRAFT.value,
        )
        db_session.add(outline)
        await db_session.commit()

        response = await async_client.delete(
            f"/api/v1/outlines/{outline.id}",
            headers=auth_headers,
        )

        assert response.status_code == 204

        # Verify outline was deleted
        from sqlalchemy import select
        result = await db_session.execute(
            select(Outline).where(Outline.id == outline.id)
        )
        deleted_outline = result.scalar_one_or_none()
        assert deleted_outline is None

    async def test_delete_outline_not_found(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
    ):
        """Test deleting non-existent outline."""
        response = await async_client.delete(
            f"/api/v1/outlines/{str(uuid4())}",
            headers=auth_headers,
        )
        assert response.status_code == 404


class TestRegenerateOutline:
    """Tests for POST /outlines/{outline_id}/regenerate endpoint."""

    async def test_regenerate_outline_success(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        test_user: User,
        db_session: AsyncSession,
    ):
        """Test successful outline regeneration."""
        outline = Outline(
            id=str(uuid4()),
            user_id=test_user.id,
            title="Original Title",
            keyword="seo optimization",
            target_audience="marketers",
            tone="professional",
            word_count_target=1500,
            status=ContentStatus.COMPLETED.value,
        )
        db_session.add(outline)
        await db_session.commit()

        # Mock the AI service
        from adapters.ai.anthropic_adapter import GeneratedOutline, OutlineSection

        mock_outline = GeneratedOutline(
            title="Regenerated SEO Guide",
            sections=[
                OutlineSection(
                    heading="SEO Basics",
                    subheadings=["What is SEO"],
                    notes="Introduction to SEO",
                    word_count_target=300
                ),
            ],
            meta_description="A comprehensive guide to SEO optimization for marketers.",
            estimated_word_count=1000,
            estimated_read_time=5
        )

        with patch(
            "api.routes.outlines.content_ai_service.generate_outline",
            new_callable=AsyncMock,
            return_value=mock_outline
        ):
            response = await async_client.post(
                f"/api/v1/outlines/{outline.id}/regenerate",
                headers=auth_headers,
            )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == ContentStatus.COMPLETED.value
        assert data["title"] == "Regenerated SEO Guide"
        assert len(data["sections"]) == 1

    async def test_regenerate_outline_not_found(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
    ):
        """Test regenerating non-existent outline."""
        response = await async_client.post(
            f"/api/v1/outlines/{str(uuid4())}/regenerate",
            headers=auth_headers,
        )
        assert response.status_code == 404

    async def test_regenerate_outline_ai_failure(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        test_user: User,
        db_session: AsyncSession,
    ):
        """Test outline regeneration when AI service fails."""
        outline = Outline(
            id=str(uuid4()),
            user_id=test_user.id,
            title="Test Outline",
            keyword="test",
            status=ContentStatus.COMPLETED.value,
        )
        db_session.add(outline)
        await db_session.commit()

        with patch(
            "api.routes.outlines.content_ai_service.generate_outline",
            new_callable=AsyncMock,
            side_effect=Exception("AI service error")
        ):
            response = await async_client.post(
                f"/api/v1/outlines/{outline.id}/regenerate",
                headers=auth_headers,
            )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == ContentStatus.FAILED.value
        # generation_error is stored in the DB model but not exposed in
        # OutlineResponse schema; verify only that status is FAILED.
