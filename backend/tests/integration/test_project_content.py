"""
Integration tests for Project Content isolation (Phase 10 Multi-tenancy).

Tests cover content ownership and access control:
- Creating content with project_id
- Listing project content (member access)
- Listing project content (non-member denied)
- Editing project content (MEMBER+ permissions)
- Editing project content (VIEWER denied)
- Deleting project content
- Content cascade deletion when project deleted
- Content isolation between projects

All tests use async fixtures and httpx AsyncClient.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

# Skip tests if projects module not implemented yet
pytest.importorskip("api.routes.projects", reason="Projects API not yet implemented")

# The articles API does not support project_id filtering or project-scoped access control yet.
# These tests require project_id on ArticleCreateRequest and project_id query param on list.
pytestmark = pytest.mark.skip(
    reason="Project content isolation not yet implemented in articles API"
)


class TestCreateProjectContent:
    """Tests for creating content associated with projects."""

    @pytest.mark.asyncio
    async def test_create_article_with_project_id(
        self, async_client: AsyncClient, auth_headers: dict, project: dict
    ):
        """Should be able to create article with project_id."""
        payload = {
            "title": "Project Article",
            "content": "Content for project",
            "project_id": project["id"],
        }

        response = await async_client.post("/api/v1/articles", json=payload, headers=auth_headers)

        assert response.status_code == 201
        assert response.json()["project_id"] == project["id"]

    @pytest.mark.asyncio
    async def test_create_content_as_member(
        self, async_client: AsyncClient, project_member_auth: dict, project: dict
    ):
        """MEMBER should be able to create project content."""
        payload = {"title": "Member Created", "project_id": project["id"]}

        response = await async_client.post(
            "/api/v1/articles", json=payload, headers=project_member_auth
        )

        assert response.status_code == 201

    @pytest.mark.asyncio
    async def test_create_content_as_viewer_forbidden(
        self, async_client: AsyncClient, project_viewer_auth: dict, project: dict
    ):
        """VIEWER should NOT be able to create project content."""
        payload = {"title": "Viewer Cannot Create", "project_id": project["id"]}

        response = await async_client.post(
            "/api/v1/articles", json=payload, headers=project_viewer_auth
        )

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_create_content_for_non_member_project_forbidden(
        self, async_client: AsyncClient, other_auth_headers: dict, project: dict
    ):
        """Cannot create content for project you're not a member of."""
        payload = {"title": "Non-member Article", "project_id": project["id"]}

        response = await async_client.post(
            "/api/v1/articles", json=payload, headers=other_auth_headers
        )

        assert response.status_code == 403


class TestListProjectContent:
    """Tests for listing project content."""

    @pytest.mark.asyncio
    async def test_list_project_articles_as_member(
        self, async_client: AsyncClient, project_member_auth: dict, project: dict
    ):
        """Project members should be able to list project articles."""
        response = await async_client.get(
            f"/api/v1/articles?project_id={project['id']}", headers=project_member_auth
        )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_list_project_articles_as_viewer(
        self, async_client: AsyncClient, project_viewer_auth: dict, project: dict
    ):
        """VIEWER should be able to list project articles."""
        response = await async_client.get(
            f"/api/v1/articles?project_id={project['id']}", headers=project_viewer_auth
        )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_list_project_articles_as_non_member_forbidden(
        self, async_client: AsyncClient, other_auth_headers: dict, project: dict
    ):
        """Non-members should NOT be able to list project articles."""
        response = await async_client.get(
            f"/api/v1/articles?project_id={project['id']}", headers=other_auth_headers
        )

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_list_articles_shows_only_project_content(
        self, async_client: AsyncClient, auth_headers: dict, project: dict
    ):
        """Filtering by project_id should only show that project's content."""
        # Create project article
        await async_client.post(
            "/api/v1/articles",
            json={"title": "Project Article", "project_id": project["id"]},
            headers=auth_headers,
        )

        # Create personal article (no project_id)
        await async_client.post(
            "/api/v1/articles", json={"title": "Personal Article"}, headers=auth_headers
        )

        # List project articles
        response = await async_client.get(
            f"/api/v1/articles?project_id={project['id']}", headers=auth_headers
        )

        articles = response.json()["items"]
        # All articles should have this project_id
        for article in articles:
            assert article["project_id"] == project["id"]


class TestEditProjectContent:
    """Tests for editing project content."""

    @pytest.mark.asyncio
    async def test_edit_project_content_as_member(
        self, async_client: AsyncClient, project_member_auth: dict, project: dict
    ):
        """MEMBER should be able to edit project content."""
        # Create article
        create_response = await async_client.post(
            "/api/v1/articles",
            json={"title": "Original", "project_id": project["id"]},
            headers=project_member_auth,
        )
        article_id = create_response.json()["id"]

        # Edit article
        response = await async_client.put(
            f"/api/v1/articles/{article_id}",
            json={"title": "Updated by Member"},
            headers=project_member_auth,
        )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_edit_project_content_as_viewer_forbidden(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        project_viewer_auth: dict,
        project: dict,
    ):
        """VIEWER should NOT be able to edit project content."""
        # Create article as owner
        create_response = await async_client.post(
            "/api/v1/articles",
            json={"title": "Protected", "project_id": project["id"]},
            headers=auth_headers,
        )
        article_id = create_response.json()["id"]

        # Try to edit as viewer
        response = await async_client.put(
            f"/api/v1/articles/{article_id}",
            json={"title": "Viewer Cannot Edit"},
            headers=project_viewer_auth,
        )

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_edit_project_content_as_non_member_forbidden(
        self, async_client: AsyncClient, auth_headers: dict, other_auth_headers: dict, project: dict
    ):
        """Non-members should NOT be able to edit project content."""
        # Create article
        create_response = await async_client.post(
            "/api/v1/articles",
            json={"title": "Project Only", "project_id": project["id"]},
            headers=auth_headers,
        )
        article_id = create_response.json()["id"]

        # Try to edit as non-member
        response = await async_client.put(
            f"/api/v1/articles/{article_id}", json={"title": "Hacked"}, headers=other_auth_headers
        )

        assert response.status_code == 403


class TestDeleteProjectContent:
    """Tests for deleting project content."""

    @pytest.mark.asyncio
    async def test_delete_project_content_as_owner(
        self, async_client: AsyncClient, auth_headers: dict, project: dict
    ):
        """OWNER should be able to delete project content."""
        # Create article
        create_response = await async_client.post(
            "/api/v1/articles",
            json={"title": "To Delete", "project_id": project["id"]},
            headers=auth_headers,
        )
        article_id = create_response.json()["id"]

        # Delete article
        response = await async_client.delete(f"/api/v1/articles/{article_id}", headers=auth_headers)

        assert response.status_code == 204

    @pytest.mark.asyncio
    async def test_delete_project_content_as_admin(
        self, async_client: AsyncClient, project_admin_auth: dict, project: dict
    ):
        """ADMIN should be able to delete project content."""
        # Create article
        create_response = await async_client.post(
            "/api/v1/articles",
            json={"title": "Admin Delete", "project_id": project["id"]},
            headers=project_admin_auth,
        )
        article_id = create_response.json()["id"]

        # Delete article
        response = await async_client.delete(
            f"/api/v1/articles/{article_id}", headers=project_admin_auth
        )

        assert response.status_code == 204

    @pytest.mark.asyncio
    async def test_delete_project_content_as_member(
        self, async_client: AsyncClient, project_member_auth: dict, project: dict
    ):
        """MEMBER should be able to delete their own content."""
        # Create article as member
        create_response = await async_client.post(
            "/api/v1/articles",
            json={"title": "My Article", "project_id": project["id"]},
            headers=project_member_auth,
        )
        article_id = create_response.json()["id"]

        # Delete own article
        response = await async_client.delete(
            f"/api/v1/articles/{article_id}", headers=project_member_auth
        )

        assert response.status_code == 204

    @pytest.mark.asyncio
    async def test_delete_project_content_as_viewer_forbidden(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        project_viewer_auth: dict,
        project: dict,
    ):
        """VIEWER should NOT be able to delete project content."""
        # Create article as owner
        create_response = await async_client.post(
            "/api/v1/articles",
            json={"title": "Protected", "project_id": project["id"]},
            headers=auth_headers,
        )
        article_id = create_response.json()["id"]

        # Try to delete as viewer
        response = await async_client.delete(
            f"/api/v1/articles/{article_id}", headers=project_viewer_auth
        )

        assert response.status_code == 403


class TestProjectContentCascadeDelete:
    """Tests for cascade deletion when project is deleted."""

    @pytest.mark.asyncio
    async def test_deleting_project_cascades_to_content(
        self, async_client: AsyncClient, auth_headers: dict, db_session: AsyncSession
    ):
        """Deleting project should also delete all project content."""
        # Create project
        project_response = await async_client.post(
            "/api/v1/projects", json={"name": "Project to Delete"}, headers=auth_headers
        )
        project_id = project_response.json()["id"]

        # Create project content
        article_response = await async_client.post(
            "/api/v1/articles",
            json={"title": "Project Article", "project_id": project_id},
            headers=auth_headers,
        )
        article_id = article_response.json()["id"]

        # Delete project
        await async_client.delete(f"/api/v1/projects/{project_id}", headers=auth_headers)

        # Verify article is also deleted
        get_response = await async_client.get(
            f"/api/v1/articles/{article_id}", headers=auth_headers
        )

        assert get_response.status_code == 404


class TestProjectContentIsolation:
    """Tests for content isolation between projects."""

    @pytest.mark.asyncio
    async def test_content_isolated_between_projects(
        self, async_client: AsyncClient, auth_headers: dict, other_auth_headers: dict
    ):
        """Content should be isolated between different projects."""
        # User 1 creates project and article
        project1_response = await async_client.post(
            "/api/v1/projects", json={"name": "Project 1"}, headers=auth_headers
        )
        project1_id = project1_response.json()["id"]

        article1_response = await async_client.post(
            "/api/v1/articles",
            json={"title": "Project 1 Article", "project_id": project1_id},
            headers=auth_headers,
        )
        article1_id = article1_response.json()["id"]

        # User 2 creates project
        project2_response = await async_client.post(
            "/api/v1/projects", json={"name": "Project 2"}, headers=other_auth_headers
        )
        project2_id = project2_response.json()["id"]

        # User 2 should not see User 1's project article
        list_response = await async_client.get(
            f"/api/v1/articles?project_id={project2_id}", headers=other_auth_headers
        )

        articles = list_response.json()["items"]
        article_ids = [a["id"] for a in articles]
        assert article1_id not in article_ids

        # User 2 should not be able to access User 1's article
        get_response = await async_client.get(
            f"/api/v1/articles/{article1_id}", headers=other_auth_headers
        )

        assert get_response.status_code == 403

    @pytest.mark.asyncio
    async def test_personal_content_separate_from_project_content(
        self, async_client: AsyncClient, auth_headers: dict, project: dict
    ):
        """Personal content should be separate from project content."""
        # Create personal article
        personal_response = await async_client.post(
            "/api/v1/articles", json={"title": "Personal Article"}, headers=auth_headers
        )

        # Create project article
        await async_client.post(
            "/api/v1/articles",
            json={"title": "Project Article", "project_id": project["id"]},
            headers=auth_headers,
        )

        # List project articles
        project_list = await async_client.get(
            f"/api/v1/articles?project_id={project['id']}", headers=auth_headers
        )
        project_articles = project_list.json()["items"]

        # Personal article should not appear in project list
        personal_id = personal_response.json()["id"]
        project_article_ids = [a["id"] for a in project_articles]
        assert personal_id not in project_article_ids
