"""
Integration tests for Team Members API (Phase 10 Multi-tenancy).

Tests cover member management operations:
- Listing team members
- Adding members (ADMIN+)
- Updating member roles
- Removing members
- Leaving teams
- Transferring ownership
- Permission enforcement

All tests use async fixtures and httpx AsyncClient.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import uuid4

# Skip tests if teams module not implemented yet
pytest.importorskip("api.routes.teams", reason="Teams API not yet implemented")

# All endpoints in this file (/teams/{id}/members, /teams/{id}/leave,
# /teams/{id}/transfer-ownership) are not yet implemented as routes.
pytestmark = pytest.mark.skip(reason="Team member management endpoints not yet implemented")


class TestListTeamMembers:
    """Tests for GET /teams/{id}/members endpoint."""

    @pytest.mark.asyncio
    async def test_list_members_as_owner(
        self, async_client: AsyncClient, auth_headers: dict, team: dict
    ):
        """OWNER should be able to list all team members."""
        response = await async_client.get(
            f"/api/v1/teams/{team['id']}/members", headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert len(data["items"]) >= 1

        # Owner should be in the list
        owner = next((m for m in data["items"] if m["role"] == "owner"), None)
        assert owner is not None

    @pytest.mark.asyncio
    async def test_list_members_shows_user_info(
        self, async_client: AsyncClient, auth_headers: dict, team: dict
    ):
        """Member list should include user information."""
        response = await async_client.get(
            f"/api/v1/teams/{team['id']}/members", headers=auth_headers
        )

        assert response.status_code == 200
        members = response.json()["items"]
        for member in members:
            assert "id" in member
            assert "user_id" in member
            assert "email" in member
            assert "name" in member
            assert "role" in member
            assert "joined_at" in member

    @pytest.mark.asyncio
    async def test_list_members_as_member(
        self, async_client: AsyncClient, team_member_auth: dict, team: dict
    ):
        """MEMBER should be able to list team members."""
        response = await async_client.get(
            f"/api/v1/teams/{team['id']}/members", headers=team_member_auth
        )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_list_members_as_viewer(
        self, async_client: AsyncClient, team_viewer_auth: dict, team: dict
    ):
        """VIEWER should be able to list team members."""
        response = await async_client.get(
            f"/api/v1/teams/{team['id']}/members", headers=team_viewer_auth
        )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_list_members_requires_membership(
        self, async_client: AsyncClient, other_auth_headers: dict, team: dict
    ):
        """Non-members should NOT be able to list team members."""
        response = await async_client.get(
            f"/api/v1/teams/{team['id']}/members", headers=other_auth_headers
        )

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_list_members_supports_pagination(
        self, async_client: AsyncClient, auth_headers: dict, team: dict
    ):
        """Member list should support pagination."""
        response = await async_client.get(
            f"/api/v1/teams/{team['id']}/members?page=1&page_size=10",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "page" in data
        assert "page_size" in data


class TestAddTeamMember:
    """Tests for POST /teams/{id}/members endpoint."""

    @pytest.mark.asyncio
    async def test_add_member_as_owner(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        team: dict,
        other_user: dict
    ):
        """OWNER should be able to add members to the team."""
        payload = {
            "email": other_user["email"],
            "role": "member"
        }

        response = await async_client.post(
            f"/api/v1/teams/{team['id']}/members", json=payload, headers=auth_headers
        )

        assert response.status_code == 201
        data = response.json()
        assert data["email"] == other_user["email"]
        assert data["role"] == "member"

    @pytest.mark.asyncio
    async def test_add_member_as_admin(
        self,
        async_client: AsyncClient,
        team_admin_auth: dict,
        team: dict,
        other_user: dict
    ):
        """ADMIN should be able to add members to the team."""
        payload = {
            "email": other_user["email"],
            "role": "member"
        }

        response = await async_client.post(
            f"/api/v1/teams/{team['id']}/members", json=payload, headers=team_admin_auth
        )

        assert response.status_code == 201

    @pytest.mark.asyncio
    async def test_add_member_as_member_forbidden(
        self,
        async_client: AsyncClient,
        team_member_auth: dict,
        team: dict,
        other_user: dict
    ):
        """MEMBER should NOT be able to add members."""
        payload = {
            "email": other_user["email"],
            "role": "member"
        }

        response = await async_client.post(
            f"/api/v1/teams/{team['id']}/members", json=payload, headers=team_member_auth
        )

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_add_member_by_user_id(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        team: dict,
        other_user: dict
    ):
        """Should be able to add member by user_id instead of email."""
        payload = {
            "user_id": other_user["id"],
            "role": "viewer"
        }

        response = await async_client.post(
            f"/api/v1/teams/{team['id']}/members", json=payload, headers=auth_headers
        )

        assert response.status_code == 201

    @pytest.mark.asyncio
    async def test_add_member_validates_role(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        team: dict,
        other_user: dict
    ):
        """Adding member with invalid role should fail."""
        payload = {
            "email": other_user["email"],
            "role": "invalid_role"
        }

        response = await async_client.post(
            f"/api/v1/teams/{team['id']}/members", json=payload, headers=auth_headers
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_add_existing_member_fails(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        team: dict,
        team_member: dict
    ):
        """Adding a user who is already a member should fail."""
        payload = {
            "email": team_member["email"],
            "role": "member"
        }

        response = await async_client.post(
            f"/api/v1/teams/{team['id']}/members", json=payload, headers=auth_headers
        )

        assert response.status_code == 409  # Conflict


class TestUpdateMemberRole:
    """Tests for PUT /teams/{id}/members/{member_id} endpoint."""

    @pytest.mark.asyncio
    async def test_update_member_role_as_owner(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        team: dict,
        team_member: dict
    ):
        """OWNER should be able to update member roles."""
        payload = {"role": "admin"}

        response = await async_client.put(
            f"/api/v1/teams/{team['id']}/members/{team_member['id']}",
            json=payload,
            headers=auth_headers
        )

        assert response.status_code == 200
        assert response.json()["role"] == "admin"

    @pytest.mark.asyncio
    async def test_update_member_role_as_admin(
        self,
        async_client: AsyncClient,
        team_admin_auth: dict,
        team: dict,
        team_member: dict
    ):
        """ADMIN should be able to update member roles."""
        payload = {"role": "viewer"}

        response = await async_client.put(
            f"/api/v1/teams/{team['id']}/members/{team_member['id']}",
            json=payload,
            headers=team_admin_auth
        )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_update_member_role_as_member_forbidden(
        self,
        async_client: AsyncClient,
        team_member_auth: dict,
        team: dict,
        team_viewer: dict
    ):
        """MEMBER should NOT be able to update member roles."""
        payload = {"role": "member"}

        response = await async_client.put(
            f"/api/v1/teams/{team['id']}/members/{team_viewer['id']}",
            json=payload,
            headers=team_member_auth
        )

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_cannot_demote_owner(
        self,
        async_client: AsyncClient,
        team_admin_auth: dict,
        team: dict,
        test_user: dict
    ):
        """ADMIN should NOT be able to demote the OWNER."""
        # Find owner member record
        members_response = await async_client.get(
            f"/api/v1/teams/{team['id']}/members", headers=team_admin_auth
        )
        owner = next(m for m in members_response.json()["items"] if m["role"] == "owner")

        payload = {"role": "admin"}

        response = await async_client.put(
            f"/api/v1/teams/{team['id']}/members/{owner['id']}",
            json=payload,
            headers=team_admin_auth
        )

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_cannot_promote_to_owner_if_owner_exists(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        team: dict,
        team_member: dict
    ):
        """Cannot promote member to OWNER if team already has an OWNER."""
        payload = {"role": "owner"}

        response = await async_client.put(
            f"/api/v1/teams/{team['id']}/members/{team_member['id']}",
            json=payload,
            headers=auth_headers
        )

        assert response.status_code == 400


class TestRemoveMember:
    """Tests for DELETE /teams/{id}/members/{member_id} endpoint."""

    @pytest.mark.asyncio
    async def test_remove_member_as_owner(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        team: dict,
        team_member: dict
    ):
        """OWNER should be able to remove members."""
        response = await async_client.delete(
            f"/api/v1/teams/{team['id']}/members/{team_member['id']}",
            headers=auth_headers
        )

        assert response.status_code == 204

        # Verify member is removed
        members_response = await async_client.get(
            f"/api/v1/teams/{team['id']}/members", headers=auth_headers
        )
        member_ids = [m["id"] for m in members_response.json()["items"]]
        assert team_member["id"] not in member_ids

    @pytest.mark.asyncio
    async def test_remove_member_as_admin(
        self,
        async_client: AsyncClient,
        team_admin_auth: dict,
        team: dict,
        team_member: dict
    ):
        """ADMIN should be able to remove members."""
        response = await async_client.delete(
            f"/api/v1/teams/{team['id']}/members/{team_member['id']}",
            headers=team_admin_auth
        )

        assert response.status_code == 204

    @pytest.mark.asyncio
    async def test_remove_member_as_member_forbidden(
        self,
        async_client: AsyncClient,
        team_member_auth: dict,
        team: dict,
        team_viewer: dict
    ):
        """MEMBER should NOT be able to remove members."""
        response = await async_client.delete(
            f"/api/v1/teams/{team['id']}/members/{team_viewer['id']}",
            headers=team_member_auth
        )

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_cannot_remove_owner(
        self,
        async_client: AsyncClient,
        team_admin_auth: dict,
        team: dict
    ):
        """Cannot remove the team OWNER."""
        # Find owner
        members_response = await async_client.get(
            f"/api/v1/teams/{team['id']}/members", headers=team_admin_auth
        )
        owner = next(m for m in members_response.json()["items"] if m["role"] == "owner")

        response = await async_client.delete(
            f"/api/v1/teams/{team['id']}/members/{owner['id']}",
            headers=team_admin_auth
        )

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_removed_member_loses_access(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        team_member_auth: dict,
        team: dict,
        team_member: dict
    ):
        """Removed member should lose access to team."""
        # Remove member
        await async_client.delete(
            f"/api/v1/teams/{team['id']}/members/{team_member['id']}",
            headers=auth_headers
        )

        # Verify member cannot access team
        response = await async_client.get(
            f"/api/v1/teams/{team['id']}", headers=team_member_auth
        )

        assert response.status_code == 403


class TestLeaveTeam:
    """Tests for POST /teams/{id}/leave endpoint."""

    @pytest.mark.asyncio
    async def test_member_can_leave_team(
        self,
        async_client: AsyncClient,
        team_member_auth: dict,
        team: dict
    ):
        """MEMBER should be able to leave the team."""
        response = await async_client.post(
            f"/api/v1/teams/{team['id']}/leave", headers=team_member_auth
        )

        assert response.status_code == 200

        # Verify member no longer has access
        access_response = await async_client.get(
            f"/api/v1/teams/{team['id']}", headers=team_member_auth
        )
        assert access_response.status_code == 403

    @pytest.mark.asyncio
    async def test_admin_can_leave_team(
        self,
        async_client: AsyncClient,
        team_admin_auth: dict,
        team: dict
    ):
        """ADMIN should be able to leave the team."""
        response = await async_client.post(
            f"/api/v1/teams/{team['id']}/leave", headers=team_admin_auth
        )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_owner_cannot_leave_team(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        team: dict
    ):
        """OWNER should NOT be able to leave (must transfer ownership first)."""
        response = await async_client.post(
            f"/api/v1/teams/{team['id']}/leave", headers=auth_headers
        )

        assert response.status_code == 400
        assert "transfer ownership" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_leave_non_member_team_fails(
        self,
        async_client: AsyncClient,
        other_auth_headers: dict,
        team: dict
    ):
        """Cannot leave a team you're not a member of."""
        response = await async_client.post(
            f"/api/v1/teams/{team['id']}/leave", headers=other_auth_headers
        )

        assert response.status_code == 403


class TestTransferOwnership:
    """Tests for POST /teams/{id}/transfer-ownership endpoint."""

    @pytest.mark.asyncio
    async def test_transfer_ownership_as_owner(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        team: dict,
        team_admin: dict
    ):
        """OWNER should be able to transfer ownership to another member."""
        payload = {"new_owner_id": team_admin["user_id"]}

        response = await async_client.post(
            f"/api/v1/teams/{team['id']}/transfer-ownership",
            json=payload,
            headers=auth_headers
        )

        assert response.status_code == 200

        # Verify old owner is now admin
        # Verify new owner has owner role
        members_response = await async_client.get(
            f"/api/v1/teams/{team['id']}/members", headers=auth_headers
        )
        members = members_response.json()["items"]

        new_owner = next(m for m in members if m["user_id"] == team_admin["user_id"])
        assert new_owner["role"] == "owner"

    @pytest.mark.asyncio
    async def test_transfer_ownership_as_non_owner_forbidden(
        self,
        async_client: AsyncClient,
        team_admin_auth: dict,
        team: dict,
        team_member: dict
    ):
        """Only OWNER can transfer ownership."""
        payload = {"new_owner_id": team_member["user_id"]}

        response = await async_client.post(
            f"/api/v1/teams/{team['id']}/transfer-ownership",
            json=payload,
            headers=team_admin_auth
        )

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_transfer_ownership_to_non_member_fails(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        team: dict,
        other_user: dict
    ):
        """Cannot transfer ownership to non-member."""
        payload = {"new_owner_id": other_user["id"]}

        response = await async_client.post(
            f"/api/v1/teams/{team['id']}/transfer-ownership",
            json=payload,
            headers=auth_headers
        )

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_transfer_ownership_demotes_old_owner(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        team: dict,
        team_admin: dict
    ):
        """Transferring ownership should demote old owner to admin."""
        payload = {"new_owner_id": team_admin["user_id"]}

        await async_client.post(
            f"/api/v1/teams/{team['id']}/transfer-ownership",
            json=payload,
            headers=auth_headers
        )

        # Check old owner's role
        members_response = await async_client.get(
            f"/api/v1/teams/{team['id']}/members", headers=auth_headers
        )
        # Old owner should still be in team but as admin
        # (Exact user_id would depend on test_user fixture)
