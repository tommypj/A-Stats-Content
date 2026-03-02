"""
Integration tests for images API routes.
"""

from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from fastapi import status
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from adapters.ai.replicate_adapter import GeneratedImage as ReplicateGeneratedImage
from infrastructure.database.models import Article, GeneratedImage, User


class TestImageGenerateEndpoint:
    """Tests for POST /images/generate endpoint."""

    @pytest.mark.asyncio
    async def test_generate_image_success(
        self,
        async_client: AsyncClient,
        test_user: User,
        auth_headers: dict,
        db_session: AsyncSession,
    ):
        """Test successful image generation."""
        # Mock the image generation service
        mock_generated = ReplicateGeneratedImage(
            url="https://replicate.delivery/test-image.png",
            prompt="A beautiful sunset",
            width=1024,
            height=1024,
            model="flux-1.1-pro",
            style="photographic",
        )

        # Mock download_image
        mock_image_data = b"fake image bytes"

        with (
            patch(
                "api.routes.images.image_ai_service.generate_image",
                new_callable=AsyncMock,
                return_value=mock_generated,
            ),
            patch(
                "api.routes.images.download_image",
                new_callable=AsyncMock,
                return_value=mock_image_data,
            ),
            patch(
                "api.routes.images.storage_adapter.save_image",
                new_callable=AsyncMock,
                return_value="images/2026/02/test_image.jpg",
            ),
        ):
            response = await async_client.post(
                "/api/v1/images/generate",
                json={
                    "prompt": "A beautiful sunset",
                    "style": "photographic",
                    "width": 1024,
                    "height": 1024,
                },
                headers=auth_headers,
            )

        # Image generation is async — endpoint returns 202 with "generating" status.
        # The actual AI call and storage happen in a background task.
        assert response.status_code == status.HTTP_202_ACCEPTED
        data = response.json()

        assert data["prompt"] == "A beautiful sunset"
        assert data["style"] == "photographic"
        assert data["width"] == 1024
        assert data["height"] == 1024
        assert data["status"] == "generating"
        assert data["id"] is not None

    @pytest.mark.asyncio
    async def test_generate_image_with_article_id(
        self,
        async_client: AsyncClient,
        test_user: User,
        auth_headers: dict,
        db_session: AsyncSession,
    ):
        """Test image generation linked to an article."""
        # Create a test article
        article = Article(
            id=str(uuid4()),
            user_id=test_user.id,
            title="Test Article",
            keyword="test",
            status="draft",
        )
        db_session.add(article)
        await db_session.commit()

        mock_generated = ReplicateGeneratedImage(
            url="https://replicate.delivery/test-image.png",
            prompt="Article image",
            width=1024,
            height=1024,
            model="flux-1.1-pro",
        )

        with (
            patch(
                "api.routes.images.image_ai_service.generate_image",
                new_callable=AsyncMock,
                return_value=mock_generated,
            ),
            patch(
                "api.routes.images.download_image",
                new_callable=AsyncMock,
                return_value=b"fake bytes",
            ),
            patch(
                "api.routes.images.storage_adapter.save_image",
                new_callable=AsyncMock,
                return_value="images/2026/02/test.jpg",
            ),
        ):
            response = await async_client.post(
                "/api/v1/images/generate",
                json={
                    "prompt": "Article image",
                    "article_id": article.id,
                    "width": 1024,
                    "height": 1024,
                },
                headers=auth_headers,
            )

        assert response.status_code == status.HTTP_202_ACCEPTED
        data = response.json()
        assert data["article_id"] == article.id
        assert data["status"] == "generating"

    @pytest.mark.asyncio
    async def test_generate_image_invalid_article_id(
        self,
        async_client: AsyncClient,
        test_user: User,
        auth_headers: dict,
    ):
        """Test image generation with non-existent article."""
        response = await async_client.post(
            "/api/v1/images/generate",
            json={
                "prompt": "Test image",
                "article_id": str(uuid4()),  # Non-existent
                "width": 1024,
                "height": 1024,
            },
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "Article not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_generate_image_unauthorized(self, async_client: AsyncClient):
        """Test image generation without authentication."""
        response = await async_client.post(
            "/api/v1/images/generate",
            json={
                "prompt": "Test image",
                "width": 1024,
                "height": 1024,
            },
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_generate_image_validation_error(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
    ):
        """Test image generation with invalid request data."""
        response = await async_client.post(
            "/api/v1/images/generate",
            json={
                "prompt": "Too short",  # Less than 10 characters
                "width": 1024,
                "height": 1024,
            },
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_generate_image_service_failure(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
    ):
        """Test handling of image generation service failure."""
        with patch(
            "api.routes.images.image_ai_service.generate_image",
            new_callable=AsyncMock,
            side_effect=Exception("Service error"),
        ):
            response = await async_client.post(
                "/api/v1/images/generate",
                json={
                    "prompt": "Test image that will fail",
                    "width": 1024,
                    "height": 1024,
                },
                headers=auth_headers,
            )

        # Service failure happens in the background task, not during the request.
        # The endpoint always returns 202 with "generating" status.
        assert response.status_code == status.HTTP_202_ACCEPTED
        data = response.json()
        assert data["status"] == "generating"


class TestListImagesEndpoint:
    """Tests for GET /images endpoint."""

    @pytest.mark.asyncio
    async def test_list_images_empty(
        self,
        async_client: AsyncClient,
        test_user: User,
        auth_headers: dict,
    ):
        """Test listing images when none exist."""
        response = await async_client.get(
            "/api/v1/images",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 0
        assert data["items"] == []
        assert data["page"] == 1
        assert data["pages"] == 0

    @pytest.mark.asyncio
    async def test_list_images_with_data(
        self,
        async_client: AsyncClient,
        test_user: User,
        auth_headers: dict,
        db_session: AsyncSession,
    ):
        """Test listing images with existing data."""
        # Create test images
        images = [
            GeneratedImage(
                id=str(uuid4()),
                user_id=test_user.id,
                prompt=f"Test prompt {i}",
                url=f"https://example.com/image{i}.png",
                status="completed",
            )
            for i in range(5)
        ]
        for img in images:
            db_session.add(img)
        await db_session.commit()

        response = await async_client.get(
            "/api/v1/images",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 5
        assert len(data["items"]) == 5

    @pytest.mark.asyncio
    async def test_list_images_pagination(
        self,
        async_client: AsyncClient,
        test_user: User,
        auth_headers: dict,
        db_session: AsyncSession,
    ):
        """Test image list pagination."""
        # Create 25 test images
        for i in range(25):
            image = GeneratedImage(
                id=str(uuid4()),
                user_id=test_user.id,
                prompt=f"Test prompt {i}",
                url=f"https://example.com/image{i}.png",
                status="completed",
            )
            db_session.add(image)
        await db_session.commit()

        # Get first page
        response = await async_client.get(
            "/api/v1/images?page=1&page_size=10",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 25
        assert len(data["items"]) == 10
        assert data["page"] == 1
        assert data["pages"] == 3

        # Get second page
        response = await async_client.get(
            "/api/v1/images?page=2&page_size=10",
            headers=auth_headers,
        )

        data = response.json()
        assert len(data["items"]) == 10
        assert data["page"] == 2

    @pytest.mark.asyncio
    async def test_list_images_filter_by_article(
        self,
        async_client: AsyncClient,
        test_user: User,
        auth_headers: dict,
        db_session: AsyncSession,
    ):
        """Test filtering images by article_id."""
        # Create article
        article = Article(
            id=str(uuid4()),
            user_id=test_user.id,
            title="Test Article",
            keyword="test",
            status="draft",
        )
        db_session.add(article)

        # Create images - some linked to article, some not
        for i in range(3):
            image = GeneratedImage(
                id=str(uuid4()),
                user_id=test_user.id,
                article_id=article.id,
                prompt=f"Article image {i}",
                url=f"https://example.com/image{i}.png",
                status="completed",
            )
            db_session.add(image)

        for i in range(2):
            image = GeneratedImage(
                id=str(uuid4()),
                user_id=test_user.id,
                prompt=f"Other image {i}",
                url=f"https://example.com/other{i}.png",
                status="completed",
            )
            db_session.add(image)

        await db_session.commit()

        # Filter by article_id
        response = await async_client.get(
            f"/api/v1/images?article_id={article.id}",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 3
        assert all(img["article_id"] == article.id for img in data["items"])


class TestGetImageEndpoint:
    """Tests for GET /images/{image_id} endpoint."""

    @pytest.mark.asyncio
    async def test_get_image_success(
        self,
        async_client: AsyncClient,
        test_user: User,
        auth_headers: dict,
        db_session: AsyncSession,
    ):
        """Test retrieving a specific image."""
        image = GeneratedImage(
            id=str(uuid4()),
            user_id=test_user.id,
            prompt="Test image",
            url="https://example.com/image.png",
            status="completed",
        )
        db_session.add(image)
        await db_session.commit()

        response = await async_client.get(
            f"/api/v1/images/{image.id}",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == image.id
        assert data["prompt"] == "Test image"

    @pytest.mark.asyncio
    async def test_get_image_not_found(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
    ):
        """Test retrieving non-existent image."""
        response = await async_client.get(
            f"/api/v1/images/{str(uuid4())}",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_get_image_unauthorized(
        self,
        async_client: AsyncClient,
        test_user: User,
        db_session: AsyncSession,
    ):
        """Test retrieving image without authentication."""
        image = GeneratedImage(
            id=str(uuid4()),
            user_id=test_user.id,
            prompt="Test image",
            url="https://example.com/image.png",
            status="completed",
        )
        db_session.add(image)
        await db_session.commit()

        response = await async_client.get(f"/api/v1/images/{image.id}")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestDeleteImageEndpoint:
    """Tests for DELETE /images/{image_id} endpoint."""

    @pytest.mark.asyncio
    async def test_delete_image_success(
        self,
        async_client: AsyncClient,
        test_user: User,
        auth_headers: dict,
        db_session: AsyncSession,
    ):
        """Test successful image deletion."""
        image = GeneratedImage(
            id=str(uuid4()),
            user_id=test_user.id,
            prompt="Test image",
            url="https://example.com/image.png",
            local_path="images/2026/02/test.jpg",
            status="completed",
        )
        db_session.add(image)
        await db_session.commit()

        with patch(
            "api.routes.images.storage_adapter.delete_image",
            new_callable=AsyncMock,
            return_value=True,
        ):
            response = await async_client.delete(
                f"/api/v1/images/{image.id}",
                headers=auth_headers,
            )

        assert response.status_code == status.HTTP_204_NO_CONTENT

        # Verify image was deleted from database
        from sqlalchemy import select

        result = await db_session.execute(
            select(GeneratedImage).where(GeneratedImage.id == image.id)
        )
        deleted_image = result.scalar_one_or_none()
        assert deleted_image is None

    @pytest.mark.asyncio
    async def test_delete_image_not_found(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
    ):
        """Test deleting non-existent image."""
        response = await async_client.delete(
            f"/api/v1/images/{str(uuid4())}",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestSetFeaturedImageEndpoint:
    """Tests for POST /images/{image_id}/set-featured endpoint."""

    @pytest.mark.asyncio
    async def test_set_featured_image_success(
        self,
        async_client: AsyncClient,
        test_user: User,
        auth_headers: dict,
        db_session: AsyncSession,
    ):
        """Test setting an image as featured for an article."""
        # Create article and image
        article = Article(
            id=str(uuid4()),
            user_id=test_user.id,
            title="Test Article",
            keyword="test",
            status="draft",
        )
        image = GeneratedImage(
            id=str(uuid4()),
            user_id=test_user.id,
            prompt="Test image",
            url="https://example.com/image.png",
            status="completed",
        )
        db_session.add(article)
        db_session.add(image)
        await db_session.commit()

        response = await async_client.post(
            f"/api/v1/images/{image.id}/set-featured",
            json={"article_id": article.id},
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["article_id"] == article.id

        # Verify article was updated
        await db_session.refresh(article)
        assert article.featured_image_id == image.id

    @pytest.mark.asyncio
    async def test_set_featured_image_not_found(
        self,
        async_client: AsyncClient,
        test_user: User,
        auth_headers: dict,
        db_session: AsyncSession,
    ):
        """Test setting featured image with non-existent image."""
        article = Article(
            id=str(uuid4()),
            user_id=test_user.id,
            title="Test Article",
            keyword="test",
            status="draft",
        )
        db_session.add(article)
        await db_session.commit()

        response = await async_client.post(
            f"/api/v1/images/{str(uuid4())}/set-featured",
            json={"article_id": article.id},
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "Image not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_set_featured_article_not_found(
        self,
        async_client: AsyncClient,
        test_user: User,
        auth_headers: dict,
        db_session: AsyncSession,
    ):
        """Test setting featured image with non-existent article."""
        image = GeneratedImage(
            id=str(uuid4()),
            user_id=test_user.id,
            prompt="Test image",
            url="https://example.com/image.png",
            status="completed",
        )
        db_session.add(image)
        await db_session.commit()

        response = await async_client.post(
            f"/api/v1/images/{image.id}/set-featured",
            json={"article_id": str(uuid4())},
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "Article not found" in response.json()["detail"]
