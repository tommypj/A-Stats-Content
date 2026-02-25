"""
Integration tests for WordPress API routes.

Tests the /wordpress/* endpoints with mocked external HTTP calls.
All calls to the WordPress REST API are intercepted via unittest.mock.patch
so no real network traffic is made.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from infrastructure.database.models import User, Article, GeneratedImage, ContentStatus
from infrastructure.database.models.project import Project, ProjectMember, ProjectMemberRole
from core.security.encryption import encrypt_credential
from infrastructure.config import get_settings

settings = get_settings()

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_wp_credentials(site_url: str = "https://mysite.example.com") -> dict:
    """Return a credentials dict suitable for storing on a Project model."""
    encrypted = encrypt_credential("my-app-password", settings.secret_key)
    return {
        "site_url": site_url,
        "username": "admin",
        "app_password_encrypted": encrypted,
        "connected_at": "2026-01-01T00:00:00+00:00",
        "last_tested_at": "2026-01-01T00:00:00+00:00",
    }


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
async def project_with_wp(db_session: AsyncSession, test_user: User) -> Project:
    """
    Create a Project owned by test_user that already has WordPress credentials
    stored, and set it as the user's current project.
    """
    project = Project(
        id=str(uuid4()),
        name="Test Project",
        slug=f"test-project-{uuid4().hex[:8]}",
        owner_id=test_user.id,
        wordpress_credentials=_make_wp_credentials(),
    )
    db_session.add(project)

    member = ProjectMember(
        id=str(uuid4()),
        project_id=project.id,
        user_id=test_user.id,
        role=ProjectMemberRole.OWNER.value,
    )
    db_session.add(member)

    # Point the user at this project
    test_user.current_project_id = project.id
    await db_session.commit()
    await db_session.refresh(project)
    await db_session.refresh(test_user)
    return project


@pytest.fixture
async def project_without_wp(db_session: AsyncSession, test_user: User) -> Project:
    """
    Create a Project owned by test_user that has NO WordPress credentials,
    and set it as the user's current project.
    """
    project = Project(
        id=str(uuid4()),
        name="No-WP Project",
        slug=f"no-wp-project-{uuid4().hex[:8]}",
        owner_id=test_user.id,
        wordpress_credentials=None,
    )
    db_session.add(project)

    member = ProjectMember(
        id=str(uuid4()),
        project_id=project.id,
        user_id=test_user.id,
        role=ProjectMemberRole.OWNER.value,
    )
    db_session.add(member)

    test_user.current_project_id = project.id
    await db_session.commit()
    await db_session.refresh(project)
    await db_session.refresh(test_user)
    return project


@pytest.fixture
async def article_with_content(
    db_session: AsyncSession,
    test_user: User,
    project_with_wp: Project,
) -> Article:
    """Article owned by test_user that belongs to the WP-connected project."""
    article = Article(
        id=str(uuid4()),
        user_id=test_user.id,
        project_id=project_with_wp.id,
        title="My SEO Article",
        keyword="seo",
        content="# Introduction\n\nThis is the article body.",
        status=ContentStatus.COMPLETED.value,
    )
    db_session.add(article)
    await db_session.commit()
    await db_session.refresh(article)
    return article


@pytest.fixture
async def article_no_project(
    db_session: AsyncSession,
    test_user: User,
) -> Article:
    """Article with no project_id and user has no current_project_id set."""
    article = Article(
        id=str(uuid4()),
        user_id=test_user.id,
        project_id=None,
        title="Orphan Article",
        keyword="orphan",
        content="Some content",
        status=ContentStatus.COMPLETED.value,
    )
    db_session.add(article)
    await db_session.commit()
    await db_session.refresh(article)
    return article


@pytest.fixture
async def generated_image(
    db_session: AsyncSession,
    test_user: User,
    project_with_wp: Project,
) -> GeneratedImage:
    """A GeneratedImage owned by test_user inside the WP-connected project."""
    image = GeneratedImage(
        id=str(uuid4()),
        user_id=test_user.id,
        project_id=project_with_wp.id,
        prompt="A mountain landscape at sunset",
        url="https://cdn.example.com/ai-image.png",
        alt_text="Mountain at sunset",
    )
    db_session.add(image)
    await db_session.commit()
    await db_session.refresh(image)
    return image


# ---------------------------------------------------------------------------
# Tests: POST /wordpress/connect
# ---------------------------------------------------------------------------

class TestConnectWordPress:
    """Tests for POST /api/v1/wordpress/connect."""

    async def test_connect_wordpress_success(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        project_without_wp: Project,
    ):
        """Connect valid credentials — should store them on the project."""
        mock_wp_response = MagicMock()
        mock_wp_response.status_code = 200

        with patch(
            "api.routes.wordpress.test_wp_connection",
            new_callable=AsyncMock,
            return_value={"success": True, "error": None},
        ):
            response = await async_client.post(
                "/api/v1/wordpress/connect",
                headers=auth_headers,
                json={
                    "site_url": "https://mysite.example.com",
                    "username": "admin",
                    "app_password": "abcd efgh ijkl mnop qrst",
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert data["is_connected"] is True
        assert data["site_url"] == "https://mysite.example.com"
        assert data["username"] == "admin"
        assert data["connection_valid"] is True

    async def test_connect_wordpress_invalid_url_localhost(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        project_without_wp: Project,
    ):
        """SSRF protection — localhost should be rejected with 400."""
        response = await async_client.post(
            "/api/v1/wordpress/connect",
            headers=auth_headers,
            json={
                "site_url": "http://localhost:8080",
                "username": "admin",
                "app_password": "secret",
            },
        )

        assert response.status_code == 400
        assert "localhost" in response.json()["detail"].lower()

    async def test_connect_wordpress_private_ip_rejected(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        project_without_wp: Project,
    ):
        """SSRF protection — private IP should be rejected with 400."""
        response = await async_client.post(
            "/api/v1/wordpress/connect",
            headers=auth_headers,
            json={
                "site_url": "http://192.168.1.1",
                "username": "admin",
                "app_password": "secret",
            },
        )

        assert response.status_code == 400

    async def test_connect_wordpress_bad_credentials(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        project_without_wp: Project,
    ):
        """If the WP API returns an error, connect should return 400."""
        with patch(
            "api.routes.wordpress.test_wp_connection",
            new_callable=AsyncMock,
            return_value={"success": False, "error": "WordPress API returned status 401"},
        ):
            response = await async_client.post(
                "/api/v1/wordpress/connect",
                headers=auth_headers,
                json={
                    "site_url": "https://mysite.example.com",
                    "username": "admin",
                    "app_password": "wrongpassword",
                },
            )

        assert response.status_code == 400
        assert "WordPress connection failed" in response.json()["detail"]

    async def test_connect_wordpress_no_project(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        test_user: User,
        auth_headers: dict,
    ):
        """If the user has no current project, return 400."""
        test_user.current_project_id = None
        await db_session.commit()

        response = await async_client.post(
            "/api/v1/wordpress/connect",
            headers=auth_headers,
            json={
                "site_url": "https://mysite.example.com",
                "username": "admin",
                "app_password": "secret",
            },
        )

        assert response.status_code == 400
        assert "project" in response.json()["detail"].lower()


# ---------------------------------------------------------------------------
# Tests: POST /wordpress/disconnect
# ---------------------------------------------------------------------------

class TestDisconnectWordPress:
    """Tests for POST /api/v1/wordpress/disconnect."""

    async def test_disconnect_wordpress_success(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        project_with_wp: Project,
        db_session: AsyncSession,
    ):
        """Disconnecting removes credentials from the project."""
        response = await async_client.post(
            "/api/v1/wordpress/disconnect",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "disconnected_at" in data

        # Confirm credentials are gone from the DB
        await db_session.refresh(project_with_wp)
        assert project_with_wp.wordpress_credentials is None

    async def test_disconnect_when_not_connected(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        project_without_wp: Project,
    ):
        """Disconnecting when no credentials are stored should return 404."""
        response = await async_client.post(
            "/api/v1/wordpress/disconnect",
            headers=auth_headers,
        )

        assert response.status_code == 404

    async def test_disconnect_unauthorized(self, async_client: AsyncClient):
        """Disconnecting without auth should return 401."""
        response = await async_client.post("/api/v1/wordpress/disconnect")
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# Tests: GET /wordpress/status (test-connection variant)
# ---------------------------------------------------------------------------

class TestWordPressStatus:
    """Tests for GET /api/v1/wordpress/status."""

    async def test_get_status_connected(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        project_with_wp: Project,
    ):
        """Status endpoint returns connection info when credentials exist."""
        response = await async_client.get(
            "/api/v1/wordpress/status",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["is_connected"] is True
        assert data["site_url"] == "https://mysite.example.com"

    async def test_get_status_with_live_test(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        project_with_wp: Project,
    ):
        """Status with test_connection=true should probe the WP REST API."""
        with patch(
            "api.routes.wordpress.test_wp_connection",
            new_callable=AsyncMock,
            return_value={"success": True, "error": None},
        ):
            response = await async_client.get(
                "/api/v1/wordpress/status?test_connection=true",
                headers=auth_headers,
            )

        assert response.status_code == 200
        data = response.json()
        assert data["connection_valid"] is True
        assert data["last_tested_at"] is not None

    async def test_get_status_not_configured(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        project_without_wp: Project,
    ):
        """Status returns 404 when no WP credentials are configured."""
        response = await async_client.get(
            "/api/v1/wordpress/status",
            headers=auth_headers,
        )

        assert response.status_code == 404


# ---------------------------------------------------------------------------
# Tests: POST /wordpress/publish
# ---------------------------------------------------------------------------

class TestPublishToWordPress:
    """Tests for POST /api/v1/wordpress/publish."""

    async def test_publish_article_success(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        article_with_content: Article,
        db_session: AsyncSession,
    ):
        """
        Publish creates a WP post and stores wordpress_post_id +
        published_url on the article.
        """
        mock_wp_post = {
            "id": 42,
            "link": "https://mysite.example.com/my-seo-article/",
            "status": "draft",
        }

        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = mock_wp_post
        mock_response.text = ""

        mock_async_client = AsyncMock()
        mock_async_client.__aenter__.return_value.post.return_value = mock_response

        with patch("api.routes.wordpress.httpx.AsyncClient", return_value=mock_async_client):
            response = await async_client.post(
                "/api/v1/wordpress/publish",
                headers=auth_headers,
                json={
                    "article_id": article_with_content.id,
                    "status": "draft",
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert data["wordpress_post_id"] == 42
        assert data["wordpress_url"] == "https://mysite.example.com/my-seo-article/"
        assert data["status"] == "draft"

        # Verify the article was updated in the DB
        await db_session.refresh(article_with_content)
        assert article_with_content.wordpress_post_id == 42
        assert article_with_content.published_url == "https://mysite.example.com/my-seo-article/"

    async def test_publish_article_not_found(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        project_with_wp: Project,
    ):
        """Publishing a non-existent article returns 404."""
        response = await async_client.post(
            "/api/v1/wordpress/publish",
            headers=auth_headers,
            json={
                "article_id": str(uuid4()),
                "status": "draft",
            },
        )

        assert response.status_code == 404

    async def test_publish_without_credentials(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        test_user: User,
    ):
        """
        If the article's project has no WP credentials (and no fallback),
        the endpoint returns 404.
        """
        # Create a project with no WP credentials
        project = Project(
            id=str(uuid4()),
            name="No-WP Project B",
            slug=f"no-wp-b-{uuid4().hex[:8]}",
            owner_id=test_user.id,
            wordpress_credentials=None,
        )
        db_session.add(project)

        member = ProjectMember(
            id=str(uuid4()),
            project_id=project.id,
            user_id=test_user.id,
            role=ProjectMemberRole.OWNER.value,
        )
        db_session.add(member)

        test_user.current_project_id = project.id

        article = Article(
            id=str(uuid4()),
            user_id=test_user.id,
            project_id=project.id,
            title="Article Without WP",
            keyword="test",
            content="Some content",
            status=ContentStatus.COMPLETED.value,
        )
        db_session.add(article)
        await db_session.commit()

        response = await async_client.post(
            "/api/v1/wordpress/publish",
            headers=auth_headers,
            json={
                "article_id": article.id,
                "status": "draft",
            },
        )

        assert response.status_code == 404
        assert "wordpress" in response.json()["detail"].lower()

    async def test_publish_article_no_content(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        test_user: User,
        project_with_wp: Project,
    ):
        """Publishing an article with no content body returns 400."""
        article = Article(
            id=str(uuid4()),
            user_id=test_user.id,
            project_id=project_with_wp.id,
            title="Empty Article",
            keyword="empty",
            content=None,
            status=ContentStatus.DRAFT.value,
        )
        db_session.add(article)
        await db_session.commit()

        response = await async_client.post(
            "/api/v1/wordpress/publish",
            headers=auth_headers,
            json={
                "article_id": article.id,
                "status": "draft",
            },
        )

        assert response.status_code == 400
        assert "no content" in response.json()["detail"].lower()

    async def test_publish_unauthorized(self, async_client: AsyncClient):
        """Publishing without auth returns 401."""
        response = await async_client.post(
            "/api/v1/wordpress/publish",
            json={"article_id": str(uuid4()), "status": "draft"},
        )
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# Tests: POST /wordpress/upload-media
# ---------------------------------------------------------------------------

class TestUploadMedia:
    """Tests for POST /api/v1/wordpress/upload-media."""

    async def test_upload_media_success_webp_conversion(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        generated_image: GeneratedImage,
    ):
        """
        Upload-media should download the image, convert it to WebP, and push
        it to the WP media library.  We verify the content-type sent to
        WordPress becomes image/webp when conversion succeeds.
        """
        # Minimal 1x1 PNG so PIL can open it
        import base64
        png_1x1 = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9Q"
            "DwADhgGAWjR9awAAAABJRU5ErkJggg=="
        )

        # Mock: download returns real PNG bytes
        mock_download_response = MagicMock()
        mock_download_response.status_code = 200
        mock_download_response.content = png_1x1
        mock_download_response.headers = {"content-type": "image/png"}

        # Mock: WP media upload succeeds
        mock_upload_response = MagicMock()
        mock_upload_response.status_code = 201
        mock_upload_response.json.return_value = {
            "id": 99,
            "source_url": "https://mysite.example.com/wp-content/uploads/ai-image.webp",
            "guid": {"rendered": "https://mysite.example.com/wp-content/uploads/ai-image.webp"},
        }

        # Mock: PATCH for title/alt_text
        mock_patch_response = MagicMock()
        mock_patch_response.status_code = 200

        # The route uses _wp_client() which returns httpx.AsyncClient(...)
        # We need to mock the context manager and the sequential calls made
        # on the client: get (download), post (upload), post (patch title).
        mock_client_instance = AsyncMock()
        mock_client_instance.get.return_value = mock_download_response
        mock_client_instance.post.side_effect = [
            mock_upload_response,
            mock_patch_response,
        ]

        mock_async_client = AsyncMock()
        mock_async_client.__aenter__.return_value = mock_client_instance
        mock_async_client.__aexit__.return_value = None

        with patch("api.routes.wordpress.httpx.AsyncClient", return_value=mock_async_client):
            response = await async_client.post(
                "/api/v1/wordpress/upload-media",
                headers=auth_headers,
                json={
                    "image_id": generated_image.id,
                    "title": "Sunset Mountain",
                    "alt_text": "Mountain landscape at sunset",
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert data["wordpress_media_id"] == 99
        assert "mysite.example.com" in data["source_url"]

        # Verify the upload call sent image/webp content-type
        # (PIL converted the PNG to WebP before uploading)
        upload_call_headers = mock_client_instance.post.call_args_list[0].kwargs["headers"]
        assert upload_call_headers["Content-Type"] == "image/webp"

    async def test_upload_media_image_not_found(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        project_with_wp: Project,
    ):
        """Uploading a non-existent image returns 404."""
        response = await async_client.post(
            "/api/v1/wordpress/upload-media",
            headers=auth_headers,
            json={"image_id": str(uuid4())},
        )

        assert response.status_code == 404

    async def test_upload_media_no_wp_connection(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession,
        test_user: User,
        generated_image: GeneratedImage,
        project_without_wp: Project,
    ):
        """Upload returns 404 when no WP credentials are configured."""
        # Switch user to project without WP credentials
        test_user.current_project_id = project_without_wp.id
        await db_session.commit()

        response = await async_client.post(
            "/api/v1/wordpress/upload-media",
            headers=auth_headers,
            json={"image_id": generated_image.id},
        )

        assert response.status_code == 404

    async def test_upload_media_unauthorized(self, async_client: AsyncClient):
        """Upload without auth returns 401."""
        response = await async_client.post(
            "/api/v1/wordpress/upload-media",
            json={"image_id": str(uuid4())},
        )
        assert response.status_code == 401
