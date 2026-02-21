"""
Integration tests for Team Content isolation (Phase 10 Multi-tenancy).

Tests cover content ownership and access control:
- Creating content with team_id
- Listing team content (member access)
- Listing team content (non-member denied)
- Editing team content (MEMBER+ permissions)
- Editing team content (VIEWER denied)
- Deleting team content
- Content cascade deletion when team deleted
- Content isolation between teams

All tests use async fixtures and httpx AsyncClient.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import uuid4

# Skip tests if teams module not implemented yet
pytest.importorskip("api.routes.teams", reason="Teams API not yet implemented")


class TestCreateTeamContent:
    """Tests for creating content associated with teams."""

    @pytest.mark.asyncio
    async def test_create_article_with_team_id(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        team: dict
    ):
        """Should be able to create article with team_id."""
        payload = {
            "title": "Team Article",
            "content": "Content for team",
            "team_id": team["id"]
        }

        response = await async_client.post(
            "/articles",
            json=payload,
            headers=auth_headers
        )

        assert response.status_code == 201
        assert response.json()["team_id"] == team["id"]

    @pytest.mark.asyncio
    async def test_create_content_as_member(
        self,
        async_client: AsyncClient,
        team_member_auth: dict,
        team: dict
    ):
        """MEMBER should be able to create team content."""
        payload = {
            "title": "Member Created",
            "team_id": team["id"]
        }

        response = await async_client.post(
            "/articles",
            json=payload,
            headers=team_member_auth
        )

        assert response.status_code == 201

    @pytest.mark.asyncio
    async def test_create_content_as_viewer_forbidden(
        self,
        async_client: AsyncClient,
        team_viewer_auth: dict,
        team: dict
    ):
        """VIEWER should NOT be able to create team content."""
        payload = {
            "title": "Viewer Cannot Create",
            "team_id": team["id"]
        }

        response = await async_client.post(
            "/articles",
            json=payload,
            headers=team_viewer_auth
        )

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_create_content_for_non_member_team_forbidden(
        self,
        async_client: AsyncClient,
        other_auth_headers: dict,
        team: dict
    ):
        """Cannot create content for team you're not a member of."""
        payload = {
            "title": "Non-member Article",
            "team_id": team["id"]
        }

        response = await async_client.post(
            "/articles",
            json=payload,
            headers=other_auth_headers
        )

        assert response.status_code == 403


class TestListTeamContent:
    """Tests for listing team content."""

    @pytest.mark.asyncio
    async def test_list_team_articles_as_member(
        self,
        async_client: AsyncClient,
        team_member_auth: dict,
        team: dict
    ):
        """Team members should be able to list team articles."""
        response = await async_client.get(
            f"/articles?team_id={team['id']}",
            headers=team_member_auth
        )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_list_team_articles_as_viewer(
        self,
        async_client: AsyncClient,
        team_viewer_auth: dict,
        team: dict
    ):
        """VIEWER should be able to list team articles."""
        response = await async_client.get(
            f"/articles?team_id={team['id']}",
            headers=team_viewer_auth
        )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_list_team_articles_as_non_member_forbidden(
        self,
        async_client: AsyncClient,
        other_auth_headers: dict,
        team: dict
    ):
        """Non-members should NOT be able to list team articles."""
        response = await async_client.get(
            f"/articles?team_id={team['id']}",
            headers=other_auth_headers
        )

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_list_articles_shows_only_team_content(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        team: dict
    ):
        """Filtering by team_id should only show that team's content."""
        # Create team article
        await async_client.post(
            "/articles",
            json={"title": "Team Article", "team_id": team["id"]},
            headers=auth_headers
        )

        # Create personal article (no team_id)
        await async_client.post(
            "/articles",
            json={"title": "Personal Article"},
            headers=auth_headers
        )

        # List team articles
        response = await async_client.get(
            f"/articles?team_id={team['id']}",
            headers=auth_headers
        )

        articles = response.json()["items"]
        # All articles should have this team_id
        for article in articles:
            assert article["team_id"] == team["id"]


class TestEditTeamContent:
    """Tests for editing team content."""

    @pytest.mark.asyncio
    async def test_edit_team_content_as_member(
        self,
        async_client: AsyncClient,
        team_member_auth: dict,
        team: dict
    ):
        """MEMBER should be able to edit team content."""
        # Create article
        create_response = await async_client.post(
            "/articles",
            json={"title": "Original", "team_id": team["id"]},
            headers=team_member_auth
        )
        article_id = create_response.json()["id"]

        # Edit article
        response = await async_client.put(
            f"/articles/{article_id}",
            json={"title": "Updated by Member"},
            headers=team_member_auth
        )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_edit_team_content_as_viewer_forbidden(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        team_viewer_auth: dict,
        team: dict
    ):
        """VIEWER should NOT be able to edit team content."""
        # Create article as owner
        create_response = await async_client.post(
            "/articles",
            json={"title": "Protected", "team_id": team["id"]},
            headers=auth_headers
        )
        article_id = create_response.json()["id"]

        # Try to edit as viewer
        response = await async_client.put(
            f"/articles/{article_id}",
            json={"title": "Viewer Cannot Edit"},
            headers=team_viewer_auth
        )

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_edit_team_content_as_non_member_forbidden(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        other_auth_headers: dict,
        team: dict
    ):
        """Non-members should NOT be able to edit team content."""
        # Create article
        create_response = await async_client.post(
            "/articles",
            json={"title": "Team Only", "team_id": team["id"]},
            headers=auth_headers
        )
        article_id = create_response.json()["id"]

        # Try to edit as non-member
        response = await async_client.put(
            f"/articles/{article_id}",
            json={"title": "Hacked"},
            headers=other_auth_headers
        )

        assert response.status_code == 403


class TestDeleteTeamContent:
    """Tests for deleting team content."""

    @pytest.mark.asyncio
    async def test_delete_team_content_as_owner(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        team: dict
    ):
        """OWNER should be able to delete team content."""
        # Create article
        create_response = await async_client.post(
            "/articles",
            json={"title": "To Delete", "team_id": team["id"]},
            headers=auth_headers
        )
        article_id = create_response.json()["id"]

        # Delete article
        response = await async_client.delete(
            f"/articles/{article_id}",
            headers=auth_headers
        )

        assert response.status_code == 204

    @pytest.mark.asyncio
    async def test_delete_team_content_as_admin(
        self,
        async_client: AsyncClient,
        team_admin_auth: dict,
        team: dict
    ):
        """ADMIN should be able to delete team content."""
        # Create article
        create_response = await async_client.post(
            "/articles",
            json={"title": "Admin Delete", "team_id": team["id"]},
            headers=team_admin_auth
        )
        article_id = create_response.json()["id"]

        # Delete article
        response = await async_client.delete(
            f"/articles/{article_id}",
            headers=team_admin_auth
        )

        assert response.status_code == 204

    @pytest.mark.asyncio
    async def test_delete_team_content_as_member(
        self,
        async_client: AsyncClient,
        team_member_auth: dict,
        team: dict
    ):
        """MEMBER should be able to delete their own content."""
        # Create article as member
        create_response = await async_client.post(
            "/articles",
            json={"title": "My Article", "team_id": team["id"]},
            headers=team_member_auth
        )
        article_id = create_response.json()["id"]

        # Delete own article
        response = await async_client.delete(
            f"/articles/{article_id}",
            headers=team_member_auth
        )

        assert response.status_code == 204

    @pytest.mark.asyncio
    async def test_delete_team_content_as_viewer_forbidden(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        team_viewer_auth: dict,
        team: dict
    ):
        """VIEWER should NOT be able to delete team content."""
        # Create article as owner
        create_response = await async_client.post(
            "/articles",
            json={"title": "Protected", "team_id": team["id"]},
            headers=auth_headers
        )
        article_id = create_response.json()["id"]

        # Try to delete as viewer
        response = await async_client.delete(
            f"/articles/{article_id}",
            headers=team_viewer_auth
        )

        assert response.status_code == 403


class TestTeamContentCascadeDelete:
    """Tests for cascade deletion when team is deleted."""

    @pytest.mark.asyncio
    async def test_deleting_team_cascades_to_content(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        db_session: AsyncSession
    ):
        """Deleting team should also delete all team content."""
        # Create team
        team_response = await async_client.post(
            "/teams",
            json={"name": "Team to Delete"},
            headers=auth_headers
        )
        team_id = team_response.json()["id"]

        # Create team content
        article_response = await async_client.post(
            "/articles",
            json={"title": "Team Article", "team_id": team_id},
            headers=auth_headers
        )
        article_id = article_response.json()["id"]

        # Delete team
        await async_client.delete(
            f"/teams/{team_id}",
            headers=auth_headers
        )

        # Verify article is also deleted
        get_response = await async_client.get(
            f"/articles/{article_id}",
            headers=auth_headers
        )

        assert get_response.status_code == 404


class TestTeamContentIsolation:
    """Tests for content isolation between teams."""

    @pytest.mark.asyncio
    async def test_content_isolated_between_teams(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        other_auth_headers: dict
    ):
        """Content should be isolated between different teams."""
        # User 1 creates team and article
        team1_response = await async_client.post(
            "/teams",
            json={"name": "Team 1"},
            headers=auth_headers
        )
        team1_id = team1_response.json()["id"]

        article1_response = await async_client.post(
            "/articles",
            json={"title": "Team 1 Article", "team_id": team1_id},
            headers=auth_headers
        )
        article1_id = article1_response.json()["id"]

        # User 2 creates team
        team2_response = await async_client.post(
            "/teams",
            json={"name": "Team 2"},
            headers=other_auth_headers
        )
        team2_id = team2_response.json()["id"]

        # User 2 should not see User 1's team article
        list_response = await async_client.get(
            f"/articles?team_id={team2_id}",
            headers=other_auth_headers
        )

        articles = list_response.json()["items"]
        article_ids = [a["id"] for a in articles]
        assert article1_id not in article_ids

        # User 2 should not be able to access User 1's article
        get_response = await async_client.get(
            f"/articles/{article1_id}",
            headers=other_auth_headers
        )

        assert get_response.status_code == 403

    @pytest.mark.asyncio
    async def test_personal_content_separate_from_team_content(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        team: dict
    ):
        """Personal content should be separate from team content."""
        # Create personal article
        personal_response = await async_client.post(
            "/articles",
            json={"title": "Personal Article"},
            headers=auth_headers
        )

        # Create team article
        team_response = await async_client.post(
            "/articles",
            json={"title": "Team Article", "team_id": team["id"]},
            headers=auth_headers
        )

        # List team articles
        team_list = await async_client.get(
            f"/articles?team_id={team['id']}",
            headers=auth_headers
        )
        team_articles = team_list.json()["items"]

        # Personal article should not appear in team list
        personal_id = personal_response.json()["id"]
        team_article_ids = [a["id"] for a in team_articles]
        assert personal_id not in team_article_ids
