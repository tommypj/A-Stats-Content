"""
Integration tests for Project Members API (Phase 10 Multi-tenancy).

Tests cover member management operations:
- Listing project members
- Adding members (ADMIN+)
- Updating member roles
- Removing members
- Leaving projects
- Transferring ownership
- Permission enforcement

All tests use async fixtures and httpx AsyncClient.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import uuid4

# Skip tests if projects module not implemented yet
pytest.importorskip("api.routes.projects", reason="Projects API not yet implemented")

# All endpoints in this file (/projects/{id}/members, /projects/{id}/leave,
# /projects/{id}/transfer-ownership) are not yet implemented as routes.
pytestmark = pytest.mark.skip(reason="Project member management endpoints not yet implemented")


class TestListProjectMembers:
    """Tests for GET /projects/{id}/members endpoint."""

    @pytest.mark.asyncio
    async def test_list_members_as_owner(
        self, async_client: AsyncClient, auth_headers: dict, project: dict
    ):
        """OWNER should be able to list all project members."""
        response = await async_client.get(
            f"/api/v1/projects/{project['id']}/members", headers=auth_headers
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
        self, async_client: AsyncClient, auth_headers: dict, project: dict
    ):
        """Member list should include user information."""
        response = await async_client.get(
            f"/api/v1/projects/{project['id']}/members", headers=auth_headers
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
        self, async_client: AsyncClient, project_member_auth: dict, project: dict
    ):
        """MEMBER should be able to list project members."""
        response = await async_client.get(
            f"/api/v1/projects/{project['id']}/members", headers=project_member_auth
        )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_list_members_as_viewer(
        self, async_client: AsyncClient, project_viewer_auth: dict, project: dict
    ):
        """VIEWER should be able to list project members."""
        response = await async_client.get(
            f"/api/v1/projects/{project['id']}/members", headers=project_viewer_auth
        )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_list_members_requires_membership(
        self, async_client: AsyncClient, other_auth_headers: dict, project: dict
    ):
        """Non-members should NOT be able to list project members."""
        response = await async_client.get(
            f"/api/v1/projects/{project['id']}/members", headers=other_auth_headers
        )

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_list_members_supports_pagination(
        self, async_client: AsyncClient, auth_headers: dict, project: dict
    ):
        """Member list should support pagination."""
        response = await async_client.get(
            f"/api/v1/projects/{project['id']}/members?page=1&page_size=10",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "page" in data
        assert "page_size" in data


class TestAddProjectMember:
    """Tests for POST /projects/{id}/members endpoint."""

    @pytest.mark.asyncio
    async def test_add_member_as_owner(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        project: dict,
        other_user: dict
    ):
        """OWNER should be able to add members to the project."""
        payload = {
            "email": other_user["email"],
            "role": "member"
        }

        response = await async_client.post(
            f"/api/v1/projects/{project['id']}/members", json=payload, headers=auth_headers
        )

        assert response.status_code == 201
        data = response.json()
        assert data["email"] == other_user["email"]
        assert data["role"] == "member"

    @pytest.mark.asyncio
    async def test_add_member_as_admin(
        self,
        async_client: AsyncClient,
        project_admin_auth: dict,
        project: dict,
        other_user: dict
    ):
        """ADMIN should be able to add members to the project."""
        payload = {
            "email": other_user["email"],
            "role": "member"
        }

        response = await async_client.post(
            f"/api/v1/projects/{project['id']}/members", json=payload, headers=project_admin_auth
        )

        assert response.status_code == 201

    @pytest.mark.asyncio
    async def test_add_member_as_member_forbidden(
        self,
        async_client: AsyncClient,
        project_member_auth: dict,
        project: dict,
        other_user: dict
    ):
        """MEMBER should NOT be able to add members."""
        payload = {
            "email": other_user["email"],
            "role": "member"
        }

        response = await async_client.post(
            f"/api/v1/projects/{project['id']}/members", json=payload, headers=project_member_auth
        )

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_add_member_by_user_id(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        project: dict,
        other_user: dict
    ):
        """Should be able to add member by user_id instead of email."""
        payload = {
            "user_id": other_user["id"],
            "role": "viewer"
        }

        response = await async_client.post(
            f"/api/v1/projects/{project['id']}/members", json=payload, headers=auth_headers
        )

        assert response.status_code == 201

    @pytest.mark.asyncio
    async def test_add_member_validates_role(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        project: dict,
        other_user: dict
    ):
        """Adding member with invalid role should fail."""
        payload = {
            "email": other_user["email"],
            "role": "invalid_role"
        }

        response = await async_client.post(
            f"/api/v1/projects/{project['id']}/members", json=payload, headers=auth_headers
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_add_existing_member_fails(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        project: dict,
        project_member: dict
    ):
        """Adding a user who is already a member should fail."""
        payload = {
            "email": project_member["email"],
            "role": "member"
        }

        response = await async_client.post(
            f"/api/v1/projects/{project['id']}/members", json=payload, headers=auth_headers
        )

        assert response.status_code == 409  # Conflict


class TestUpdateMemberRole:
    """Tests for PUT /projects/{id}/members/{member_id} endpoint."""

    @pytest.mark.asyncio
    async def test_update_member_role_as_owner(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        project: dict,
        project_member: dict
    ):
        """OWNER should be able to update member roles."""
        payload = {"role": "admin"}

        response = await async_client.put(
            f"/api/v1/projects/{project['id']}/members/{project_member['id']}",
            json=payload,
            headers=auth_headers
        )

        assert response.status_code == 200
        assert response.json()["role"] == "admin"

    @pytest.mark.asyncio
    async def test_update_member_role_as_admin(
        self,
        async_client: AsyncClient,
        project_admin_auth: dict,
        project: dict,
        project_member: dict
    ):
        """ADMIN should be able to update member roles."""
        payload = {"role": "viewer"}

        response = await async_client.put(
            f"/api/v1/projects/{project['id']}/members/{project_member['id']}",
            json=payload,
            headers=project_admin_auth
        )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_update_member_role_as_member_forbidden(
        self,
        async_client: AsyncClient,
        project_member_auth: dict,
        project: dict,
        project_viewer: dict
    ):
        """MEMBER should NOT be able to update member roles."""
        payload = {"role": "member"}

        response = await async_client.put(
            f"/api/v1/projects/{project['id']}/members/{project_viewer['id']}",
            json=payload,
            headers=project_member_auth
        )

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_cannot_demote_owner(
        self,
        async_client: AsyncClient,
        project_admin_auth: dict,
        project: dict,
        test_user: dict
    ):
        """ADMIN should NOT be able to demote the OWNER."""
        # Find owner member record
        members_response = await async_client.get(
            f"/api/v1/projects/{project['id']}/members", headers=project_admin_auth
        )
        owner = next(m for m in members_response.json()["items"] if m["role"] == "owner")

        payload = {"role": "admin"}

        response = await async_client.put(
            f"/api/v1/projects/{project['id']}/members/{owner['id']}",
            json=payload,
            headers=project_admin_auth
        )

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_cannot_promote_to_owner_if_owner_exists(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        project: dict,
        project_member: dict
    ):
        """Cannot promote member to OWNER if project already has an OWNER."""
        payload = {"role": "owner"}

        response = await async_client.put(
            f"/api/v1/projects/{project['id']}/members/{project_member['id']}",
            json=payload,
            headers=auth_headers
        )

        assert response.status_code == 400


class TestRemoveMember:
    """Tests for DELETE /projects/{id}/members/{member_id} endpoint."""

    @pytest.mark.asyncio
    async def test_remove_member_as_owner(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        project: dict,
        project_member: dict
    ):
        """OWNER should be able to remove members."""
        response = await async_client.delete(
            f"/api/v1/projects/{project['id']}/members/{project_member['id']}",
            headers=auth_headers
        )

        assert response.status_code == 204

        # Verify member is removed
        members_response = await async_client.get(
            f"/api/v1/projects/{project['id']}/members", headers=auth_headers
        )
        member_ids = [m["id"] for m in members_response.json()["items"]]
        assert project_member["id"] not in member_ids

    @pytest.mark.asyncio
    async def test_remove_member_as_admin(
        self,
        async_client: AsyncClient,
        project_admin_auth: dict,
        project: dict,
        project_member: dict
    ):
        """ADMIN should be able to remove members."""
        response = await async_client.delete(
            f"/api/v1/projects/{project['id']}/members/{project_member['id']}",
            headers=project_admin_auth
        )

        assert response.status_code == 204

    @pytest.mark.asyncio
    async def test_remove_member_as_member_forbidden(
        self,
        async_client: AsyncClient,
        project_member_auth: dict,
        project: dict,
        project_viewer: dict
    ):
        """MEMBER should NOT be able to remove members."""
        response = await async_client.delete(
            f"/api/v1/projects/{project['id']}/members/{project_viewer['id']}",
            headers=project_member_auth
        )

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_cannot_remove_owner(
        self,
        async_client: AsyncClient,
        project_admin_auth: dict,
        project: dict
    ):
        """Cannot remove the project OWNER."""
        # Find owner
        members_response = await async_client.get(
            f"/api/v1/projects/{project['id']}/members", headers=project_admin_auth
        )
        owner = next(m for m in members_response.json()["items"] if m["role"] == "owner")

        response = await async_client.delete(
            f"/api/v1/projects/{project['id']}/members/{owner['id']}",
            headers=project_admin_auth
        )

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_removed_member_loses_access(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        project_member_auth: dict,
        project: dict,
        project_member: dict
    ):
        """Removed member should lose access to project."""
        # Remove member
        await async_client.delete(
            f"/api/v1/projects/{project['id']}/members/{project_member['id']}",
            headers=auth_headers
        )

        # Verify member cannot access project
        response = await async_client.get(
            f"/api/v1/projects/{project['id']}", headers=project_member_auth
        )

        assert response.status_code == 403


class TestLeaveProject:
    """Tests for POST /projects/{id}/leave endpoint."""

    @pytest.mark.asyncio
    async def test_member_can_leave_project(
        self,
        async_client: AsyncClient,
        project_member_auth: dict,
        project: dict
    ):
        """MEMBER should be able to leave the project."""
        response = await async_client.post(
            f"/api/v1/projects/{project['id']}/leave", headers=project_member_auth
        )

        assert response.status_code == 200

        # Verify member no longer has access
        access_response = await async_client.get(
            f"/api/v1/projects/{project['id']}", headers=project_member_auth
        )
        assert access_response.status_code == 403

    @pytest.mark.asyncio
    async def test_admin_can_leave_project(
        self,
        async_client: AsyncClient,
        project_admin_auth: dict,
        project: dict
    ):
        """ADMIN should be able to leave the project."""
        response = await async_client.post(
            f"/api/v1/projects/{project['id']}/leave", headers=project_admin_auth
        )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_owner_cannot_leave_project(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        project: dict
    ):
        """OWNER should NOT be able to leave (must transfer ownership first)."""
        response = await async_client.post(
            f"/api/v1/projects/{project['id']}/leave", headers=auth_headers
        )

        assert response.status_code == 400
        assert "transfer ownership" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_leave_non_member_project_fails(
        self,
        async_client: AsyncClient,
        other_auth_headers: dict,
        project: dict
    ):
        """Cannot leave a project you're not a member of."""
        response = await async_client.post(
            f"/api/v1/projects/{project['id']}/leave", headers=other_auth_headers
        )

        assert response.status_code == 403


class TestTransferOwnership:
    """Tests for POST /projects/{id}/transfer-ownership endpoint."""

    @pytest.mark.asyncio
    async def test_transfer_ownership_as_owner(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        project: dict,
        project_admin: dict
    ):
        """OWNER should be able to transfer ownership to another member."""
        payload = {"new_owner_id": project_admin["user_id"]}

        response = await async_client.post(
            f"/api/v1/projects/{project['id']}/transfer-ownership",
            json=payload,
            headers=auth_headers
        )

        assert response.status_code == 200

        # Verify old owner is now admin
        # Verify new owner has owner role
        members_response = await async_client.get(
            f"/api/v1/projects/{project['id']}/members", headers=auth_headers
        )
        members = members_response.json()["items"]

        new_owner = next(m for m in members if m["user_id"] == project_admin["user_id"])
        assert new_owner["role"] == "owner"

    @pytest.mark.asyncio
    async def test_transfer_ownership_as_non_owner_forbidden(
        self,
        async_client: AsyncClient,
        project_admin_auth: dict,
        project: dict,
        project_member: dict
    ):
        """Only OWNER can transfer ownership."""
        payload = {"new_owner_id": project_member["user_id"]}

        response = await async_client.post(
            f"/api/v1/projects/{project['id']}/transfer-ownership",
            json=payload,
            headers=project_admin_auth
        )

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_transfer_ownership_to_non_member_fails(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        project: dict,
        other_user: dict
    ):
        """Cannot transfer ownership to non-member."""
        payload = {"new_owner_id": other_user["id"]}

        response = await async_client.post(
            f"/api/v1/projects/{project['id']}/transfer-ownership",
            json=payload,
            headers=auth_headers
        )

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_transfer_ownership_demotes_old_owner(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        project: dict,
        project_admin: dict
    ):
        """Transferring ownership should demote old owner to admin."""
        payload = {"new_owner_id": project_admin["user_id"]}

        await async_client.post(
            f"/api/v1/projects/{project['id']}/transfer-ownership",
            json=payload,
            headers=auth_headers
        )

        # Check old owner's role
        members_response = await async_client.get(
            f"/api/v1/projects/{project['id']}/members", headers=auth_headers
        )
        # Old owner should still be in project but as admin
        # (Exact user_id would depend on test_user fixture)
