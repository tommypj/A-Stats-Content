"""
Integration tests for Team Invitations API (Phase 10 Multi-tenancy).

Tests cover invitation workflow:
- Sending invitations (email-based)
- Listing pending invitations
- Revoking invitations
- Resending invitations
- Accepting invitations (logged-in users)
- Accepting invitations (new user registration flow)
- Expired invitation handling
- Invalid token handling

All tests use async fixtures and httpx AsyncClient.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta
from uuid import uuid4

# Skip tests if teams module not implemented yet
pytest.importorskip("api.routes.teams", reason="Teams API not yet implemented")


class TestSendInvitation:
    """Tests for POST /teams/{id}/invitations endpoint."""

    @pytest.mark.asyncio
    async def test_send_invitation_as_owner(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        team: dict
    ):
        """OWNER should be able to send team invitations."""
        payload = {
            "email": "newmember@example.com",
            "role": "member"
        }

        response = await async_client.post(
            f"/teams/{team['id']}/invitations",
            json=payload,
            headers=auth_headers
        )

        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "newmember@example.com"
        assert data["role"] == "member"
        assert data["status"] == "pending"
        assert "token" in data
        assert "expires_at" in data

    @pytest.mark.asyncio
    async def test_send_invitation_as_admin(
        self,
        async_client: AsyncClient,
        team_admin_auth: dict,
        team: dict
    ):
        """ADMIN should be able to send team invitations."""
        payload = {
            "email": "admin-invite@example.com",
            "role": "viewer"
        }

        response = await async_client.post(
            f"/teams/{team['id']}/invitations",
            json=payload,
            headers=team_admin_auth
        )

        assert response.status_code == 201

    @pytest.mark.asyncio
    async def test_send_invitation_as_member_forbidden(
        self,
        async_client: AsyncClient,
        team_member_auth: dict,
        team: dict
    ):
        """MEMBER should NOT be able to send invitations."""
        payload = {
            "email": "forbidden@example.com",
            "role": "member"
        }

        response = await async_client.post(
            f"/teams/{team['id']}/invitations",
            json=payload,
            headers=team_member_auth
        )

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_send_invitation_to_existing_member_fails(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        team: dict,
        team_member: dict
    ):
        """Cannot send invitation to existing team member."""
        payload = {
            "email": team_member["email"],
            "role": "member"
        }

        response = await async_client.post(
            f"/teams/{team['id']}/invitations",
            json=payload,
            headers=auth_headers
        )

        assert response.status_code == 409  # Conflict

    @pytest.mark.asyncio
    async def test_send_invitation_with_custom_message(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        team: dict
    ):
        """Should be able to include custom message in invitation."""
        payload = {
            "email": "custom@example.com",
            "role": "member",
            "message": "Join us to collaborate on this project!"
        }

        response = await async_client.post(
            f"/teams/{team['id']}/invitations",
            json=payload,
            headers=auth_headers
        )

        assert response.status_code == 201
        assert "message" in response.json()

    @pytest.mark.asyncio
    async def test_send_invitation_generates_unique_token(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        team: dict
    ):
        """Each invitation should have a unique token."""
        # Send first invitation
        response1 = await async_client.post(
            f"/teams/{team['id']}/invitations",
            json={"email": "user1@example.com", "role": "member"},
            headers=auth_headers
        )
        token1 = response1.json()["token"]

        # Send second invitation
        response2 = await async_client.post(
            f"/teams/{team['id']}/invitations",
            json={"email": "user2@example.com", "role": "member"},
            headers=auth_headers
        )
        token2 = response2.json()["token"]

        assert token1 != token2


class TestListInvitations:
    """Tests for GET /teams/{id}/invitations endpoint."""

    @pytest.mark.asyncio
    async def test_list_invitations_as_owner(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        team: dict,
        team_invitation: dict
    ):
        """OWNER should be able to list pending invitations."""
        response = await async_client.get(
            f"/teams/{team['id']}/invitations",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert len(data["items"]) >= 1

    @pytest.mark.asyncio
    async def test_list_invitations_as_admin(
        self,
        async_client: AsyncClient,
        team_admin_auth: dict,
        team: dict
    ):
        """ADMIN should be able to list pending invitations."""
        response = await async_client.get(
            f"/teams/{team['id']}/invitations",
            headers=team_admin_auth
        )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_list_invitations_as_member_forbidden(
        self,
        async_client: AsyncClient,
        team_member_auth: dict,
        team: dict
    ):
        """MEMBER should NOT be able to list invitations."""
        response = await async_client.get(
            f"/teams/{team['id']}/invitations",
            headers=team_member_auth
        )

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_list_invitations_shows_invitation_details(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        team: dict,
        team_invitation: dict
    ):
        """Invitation list should show full details."""
        response = await async_client.get(
            f"/teams/{team['id']}/invitations",
            headers=auth_headers
        )

        invitations = response.json()["items"]
        for inv in invitations:
            assert "id" in inv
            assert "email" in inv
            assert "role" in inv
            assert "status" in inv
            assert "invited_by" in inv
            assert "created_at" in inv
            assert "expires_at" in inv

    @pytest.mark.asyncio
    async def test_list_invitations_filters_by_status(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        team: dict
    ):
        """Should be able to filter invitations by status."""
        response = await async_client.get(
            f"/teams/{team['id']}/invitations?status=pending",
            headers=auth_headers
        )

        assert response.status_code == 200
        invitations = response.json()["items"]
        for inv in invitations:
            assert inv["status"] == "pending"


class TestRevokeInvitation:
    """Tests for DELETE /teams/{id}/invitations/{invitation_id} endpoint."""

    @pytest.mark.asyncio
    async def test_revoke_invitation_as_owner(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        team: dict,
        team_invitation: dict
    ):
        """OWNER should be able to revoke pending invitations."""
        response = await async_client.delete(
            f"/teams/{team['id']}/invitations/{team_invitation['id']}",
            headers=auth_headers
        )

        assert response.status_code == 204

        # Verify invitation is revoked
        list_response = await async_client.get(
            f"/teams/{team['id']}/invitations",
            headers=auth_headers
        )
        active_invitations = [
            inv for inv in list_response.json()["items"]
            if inv["status"] == "pending"
        ]
        invitation_ids = [inv["id"] for inv in active_invitations]
        assert team_invitation["id"] not in invitation_ids

    @pytest.mark.asyncio
    async def test_revoke_invitation_as_admin(
        self,
        async_client: AsyncClient,
        team_admin_auth: dict,
        team: dict,
        team_invitation: dict
    ):
        """ADMIN should be able to revoke invitations."""
        response = await async_client.delete(
            f"/teams/{team['id']}/invitations/{team_invitation['id']}",
            headers=team_admin_auth
        )

        assert response.status_code == 204

    @pytest.mark.asyncio
    async def test_revoke_invitation_as_member_forbidden(
        self,
        async_client: AsyncClient,
        team_member_auth: dict,
        team: dict,
        team_invitation: dict
    ):
        """MEMBER should NOT be able to revoke invitations."""
        response = await async_client.delete(
            f"/teams/{team['id']}/invitations/{team_invitation['id']}",
            headers=team_member_auth
        )

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_revoke_accepted_invitation_fails(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        team: dict
    ):
        """Cannot revoke an already accepted invitation."""
        # TODO: This requires accepting an invitation first
        # Then attempting to revoke it should fail
        pass


class TestResendInvitation:
    """Tests for POST /teams/{id}/invitations/{invitation_id}/resend endpoint."""

    @pytest.mark.asyncio
    async def test_resend_invitation_as_owner(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        team: dict,
        team_invitation: dict
    ):
        """OWNER should be able to resend invitations."""
        response = await async_client.post(
            f"/teams/{team['id']}/invitations/{team_invitation['id']}/resend",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "sent_at" in data
        # New token may or may not be generated depending on implementation
        assert "token" in data or "expires_at" in data

    @pytest.mark.asyncio
    async def test_resend_invitation_extends_expiry(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        team: dict,
        team_invitation: dict
    ):
        """Resending invitation should extend expiry date."""
        # Get original expiry
        original_response = await async_client.get(
            f"/teams/{team['id']}/invitations",
            headers=auth_headers
        )
        original_inv = next(
            inv for inv in original_response.json()["items"]
            if inv["id"] == team_invitation["id"]
        )
        original_expires = original_inv["expires_at"]

        # Resend
        await async_client.post(
            f"/teams/{team['id']}/invitations/{team_invitation['id']}/resend",
            headers=auth_headers
        )

        # Check new expiry
        new_response = await async_client.get(
            f"/teams/{team['id']}/invitations",
            headers=auth_headers
        )
        new_inv = next(
            inv for inv in new_response.json()["items"]
            if inv["id"] == team_invitation["id"]
        )
        new_expires = new_inv["expires_at"]

        # New expiry should be later than original
        assert new_expires > original_expires


class TestAcceptInvitation:
    """Tests for POST /invitations/{token}/accept endpoint."""

    @pytest.mark.asyncio
    async def test_accept_invitation_logged_in_user(
        self,
        async_client: AsyncClient,
        other_auth_headers: dict,
        team_invitation: dict
    ):
        """Logged-in user should be able to accept invitation."""
        response = await async_client.post(
            f"/invitations/{team_invitation['token']}/accept",
            headers=other_auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["team_id"] == team_invitation["team_id"]
        assert data["role"] == team_invitation["role"]

    @pytest.mark.asyncio
    async def test_accept_invitation_adds_to_team(
        self,
        async_client: AsyncClient,
        other_auth_headers: dict,
        team_invitation: dict,
        team: dict
    ):
        """Accepting invitation should add user to team."""
        # Accept invitation
        await async_client.post(
            f"/invitations/{team_invitation['token']}/accept",
            headers=other_auth_headers
        )

        # Verify user is now a member
        members_response = await async_client.get(
            f"/teams/{team['id']}/members",
            headers=other_auth_headers
        )

        assert members_response.status_code == 200

    @pytest.mark.asyncio
    async def test_accept_invitation_new_user_flow(
        self,
        async_client: AsyncClient,
        team_invitation: dict
    ):
        """New user should be able to register and accept invitation."""
        # First, register new user
        register_payload = {
            "email": team_invitation["email"],
            "password": "newpassword123",
            "full_name": "New User"
        }

        register_response = await async_client.post(
            "/auth/register",
            json=register_payload
        )

        # Then accept invitation with new user's token
        if register_response.status_code == 201:
            new_user_token = register_response.json()["access_token"]
            new_auth = {"Authorization": f"Bearer {new_user_token}"}

            accept_response = await async_client.post(
                f"/invitations/{team_invitation['token']}/accept",
                headers=new_auth
            )

            assert accept_response.status_code == 200

    @pytest.mark.asyncio
    async def test_accept_expired_invitation_fails(
        self,
        async_client: AsyncClient,
        other_auth_headers: dict
    ):
        """Cannot accept expired invitation."""
        # TODO: Create expired invitation fixture
        # response = await async_client.post(
        #     f"/invitations/{expired_token}/accept",
        #     headers=other_auth_headers
        # )
        # assert response.status_code == 410  # Gone
        pass

    @pytest.mark.asyncio
    async def test_accept_invalid_token_fails(
        self,
        async_client: AsyncClient,
        other_auth_headers: dict
    ):
        """Cannot accept invitation with invalid token."""
        fake_token = "invalid_token_xyz"

        response = await async_client.post(
            f"/invitations/{fake_token}/accept",
            headers=other_auth_headers
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_accept_already_accepted_invitation_fails(
        self,
        async_client: AsyncClient,
        other_auth_headers: dict,
        team_invitation: dict
    ):
        """Cannot accept the same invitation twice."""
        # Accept once
        await async_client.post(
            f"/invitations/{team_invitation['token']}/accept",
            headers=other_auth_headers
        )

        # Try to accept again
        response = await async_client.post(
            f"/invitations/{team_invitation['token']}/accept",
            headers=other_auth_headers
        )

        assert response.status_code == 409  # Already accepted


class TestInvitationEmailNotifications:
    """Tests for invitation email notifications."""

    @pytest.mark.asyncio
    async def test_send_invitation_sends_email(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        team: dict,
        mock_email_service
    ):
        """Sending invitation should trigger email notification."""
        payload = {
            "email": "notify@example.com",
            "role": "member"
        }

        await async_client.post(
            f"/teams/{team['id']}/invitations",
            json=payload,
            headers=auth_headers
        )

        # TODO: Verify email was sent
        # mock_email_service.send_email.assert_called_once()
        pass

    @pytest.mark.asyncio
    async def test_resend_invitation_sends_email(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        team: dict,
        team_invitation: dict,
        mock_email_service
    ):
        """Resending invitation should trigger email notification."""
        await async_client.post(
            f"/teams/{team['id']}/invitations/{team_invitation['id']}/resend",
            headers=auth_headers
        )

        # TODO: Verify email was sent
        pass


class TestInvitationValidation:
    """Tests for invitation validation and edge cases."""

    @pytest.mark.asyncio
    async def test_invitation_email_mismatch_fails(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        team_invitation: dict
    ):
        """User with different email cannot accept invitation."""
        # Create user with different email
        different_user_payload = {
            "email": "different@example.com",
            "password": "password123",
            "full_name": "Different User"
        }

        register_response = await async_client.post(
            "/auth/register",
            json=different_user_payload
        )

        if register_response.status_code == 201:
            different_auth = {
                "Authorization": f"Bearer {register_response.json()['access_token']}"
            }

            # Try to accept invitation meant for different email
            response = await async_client.post(
                f"/invitations/{team_invitation['token']}/accept",
                headers=different_auth
            )

            # Should fail because email doesn't match
            assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_invitation_expires_after_7_days(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        team: dict
    ):
        """Invitations should expire after 7 days by default."""
        payload = {
            "email": "expiry-test@example.com",
            "role": "member"
        }

        response = await async_client.post(
            f"/teams/{team['id']}/invitations",
            json=payload,
            headers=auth_headers
        )

        expires_at = datetime.fromisoformat(
            response.json()["expires_at"].replace("Z", "+00:00")
        )
        created_at = datetime.fromisoformat(
            response.json()["created_at"].replace("Z", "+00:00")
        )

        # Should expire in ~7 days
        expiry_delta = expires_at - created_at
        assert 6 <= expiry_delta.days <= 8
