"""Integration tests for authentication endpoints."""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.database.models.user import User, UserStatus

pytestmark = pytest.mark.asyncio


class TestRegistration:
    """Tests for user registration."""

    async def test_register_success(self, async_client: AsyncClient):
        """Test successful user registration."""
        with patch("api.routes.auth.email_service.send_verification_email", new_callable=AsyncMock):
            response = await async_client.post(
                "/api/v1/auth/register",
                json={
                    "email": "newuser@example.com",
                    "password": "SecurePass123!",
                    "name": "New User",
                    "language": "en",
                },
            )

        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "newuser@example.com"
        assert data["name"] == "New User"
        assert data["email_verified"] is False
        assert "password" not in data
        assert "password_hash" not in data

    async def test_register_duplicate_email(self, async_client: AsyncClient, test_user: User):
        """Test registration with existing email fails."""
        response = await async_client.post(
            "/api/v1/auth/register",
            json={
                "email": test_user.email,
                "password": "SecurePass123!",
                "name": "Duplicate User",
                "language": "en",
            },
        )
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"].lower()

    async def test_register_weak_password(self, async_client: AsyncClient):
        """Test registration with weak password fails."""
        response = await async_client.post(
            "/api/v1/auth/register",
            json={
                "email": "weak@example.com",
                "password": "123",
                "name": "Weak Password",
                "language": "en",
            },
        )
        assert response.status_code == 422

    async def test_register_invalid_email(self, async_client: AsyncClient):
        """Test registration with invalid email fails."""
        response = await async_client.post(
            "/api/v1/auth/register",
            json={
                "email": "not-an-email",
                "password": "SecurePass123!",
                "name": "Invalid Email",
                "language": "en",
            },
        )
        assert response.status_code == 422

    async def test_register_missing_fields(self, async_client: AsyncClient):
        """Test registration with missing required fields."""
        response = await async_client.post(
            "/api/v1/auth/register", json={"email": "incomplete@example.com"}
        )
        assert response.status_code == 422

    async def test_register_email_case_insensitive(
        self, async_client: AsyncClient, test_user: User
    ):
        """Test that email is case-insensitive."""
        response = await async_client.post(
            "/api/v1/auth/register",
            json={
                "email": test_user.email.upper(),
                "password": "SecurePass123!",
                "name": "Duplicate Upper",
                "language": "en",
            },
        )
        assert response.status_code == 400


class TestLogin:
    """Tests for user login."""

    async def test_login_success(self, async_client: AsyncClient, test_user: User):
        """Test successful login."""
        response = await async_client.post(
            "/api/v1/auth/login", json={"email": test_user.email, "password": "testpassword123"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert "expires_in" in data

    async def test_login_wrong_password(self, async_client: AsyncClient, test_user: User):
        """Test login with wrong password."""
        response = await async_client.post(
            "/api/v1/auth/login", json={"email": test_user.email, "password": "wrongpassword"}
        )
        assert response.status_code == 401
        assert "invalid" in response.json()["detail"].lower()

    async def test_login_nonexistent_user(self, async_client: AsyncClient):
        """Test login with non-existent user."""
        response = await async_client.post(
            "/api/v1/auth/login", json={"email": "nobody@example.com", "password": "password123"}
        )
        assert response.status_code == 401
        assert "invalid" in response.json()["detail"].lower()

    async def test_login_suspended_user(self, async_client: AsyncClient, suspended_user: User):
        """Test login with suspended user account."""
        response = await async_client.post(
            "/api/v1/auth/login",
            json={"email": suspended_user.email, "password": "testpassword123"},
        )
        assert response.status_code == 403
        assert "suspended" in response.json()["detail"].lower()

    async def test_login_email_case_insensitive(self, async_client: AsyncClient, test_user: User):
        """Test that login email is case-insensitive."""
        response = await async_client.post(
            "/api/v1/auth/login",
            json={"email": test_user.email.upper(), "password": "testpassword123"},
        )
        assert response.status_code == 200
        assert "access_token" in response.json()

    async def test_login_updates_last_login(
        self, async_client: AsyncClient, test_user: User, db_session: AsyncSession
    ):
        """Test that login updates last_login timestamp."""
        initial_login = test_user.last_login
        initial_count = test_user.login_count

        await async_client.post(
            "/api/v1/auth/login", json={"email": test_user.email, "password": "testpassword123"}
        )

        await db_session.refresh(test_user)
        assert test_user.last_login != initial_login
        assert test_user.login_count == initial_count + 1


class TestTokenRefresh:
    """Tests for token refresh."""

    async def test_refresh_token_success(self, async_client: AsyncClient, test_user: User):
        """Test successful token refresh."""
        # First login to get tokens
        login = await async_client.post(
            "/api/v1/auth/login", json={"email": test_user.email, "password": "testpassword123"}
        )
        refresh_token = login.json()["refresh_token"]

        # Refresh
        response = await async_client.post(
            "/api/v1/auth/refresh", json={"refresh_token": refresh_token}
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    async def test_refresh_token_invalid(self, async_client: AsyncClient):
        """Test refresh with invalid token."""
        response = await async_client.post(
            "/api/v1/auth/refresh", json={"refresh_token": "invalid.token.here"}
        )
        assert response.status_code == 401
        assert "invalid" in response.json()["detail"].lower()

    async def test_refresh_token_expired(self, async_client: AsyncClient):
        """Test refresh with expired token."""
        # Create an expired token (this would require mocking time or using an actual expired token)
        expired_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyLCJleHAiOjE1MTYyMzkwMjJ9.4Adcj0vbD2Hg4LfBcFJa8kU6w4V0XeXqTLxZN8hQjzM"
        response = await async_client.post(
            "/api/v1/auth/refresh", json={"refresh_token": expired_token}
        )
        assert response.status_code == 401


class TestCurrentUser:
    """Tests for getting current user."""

    async def test_get_me_authenticated(
        self, async_client: AsyncClient, auth_headers: dict, test_user: User
    ):
        """Test getting current user when authenticated."""
        response = await async_client.get("/api/v1/auth/me", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == test_user.email
        assert data["name"] == test_user.name
        assert "password" not in data
        assert "password_hash" not in data

    async def test_get_me_unauthenticated(self, async_client: AsyncClient):
        """Test getting current user without auth fails."""
        response = await async_client.get("/api/v1/auth/me")
        assert response.status_code == 401
        assert "authenticated" in response.json()["detail"].lower()

    async def test_get_me_invalid_token(self, async_client: AsyncClient):
        """Test getting current user with invalid token."""
        response = await async_client.get(
            "/api/v1/auth/me", headers={"Authorization": "Bearer invalid.token.here"}
        )
        assert response.status_code == 401

    async def test_get_me_malformed_header(self, async_client: AsyncClient):
        """Test getting current user with malformed auth header."""
        response = await async_client.get(
            "/api/v1/auth/me", headers={"Authorization": "InvalidFormat token"}
        )
        assert response.status_code == 401


class TestPasswordReset:
    """Tests for password reset flow."""

    async def test_request_password_reset_existing_user(
        self, async_client: AsyncClient, test_user: User
    ):
        """Test requesting password reset for existing user."""
        with patch(
            "api.routes.auth.email_service.send_password_reset_email", new_callable=AsyncMock
        ):
            response = await async_client.post(
                "/api/v1/auth/password/reset-request", json={"email": test_user.email}
            )

        # Should return 202 even for existing emails (prevent enumeration)
        assert response.status_code == 202
        assert "sent" in response.json()["message"].lower()

    async def test_request_password_reset_nonexistent_user(self, async_client: AsyncClient):
        """Test requesting password reset for non-existent email."""
        response = await async_client.post(
            "/api/v1/auth/password/reset-request", json={"email": "nobody@example.com"}
        )
        # Should return 202 even for non-existent emails (prevent enumeration)
        assert response.status_code == 202
        assert "sent" in response.json()["message"].lower()

    async def test_password_reset_invalid_token(self, async_client: AsyncClient):
        """Test password reset with invalid token."""
        response = await async_client.post(
            "/api/v1/auth/password/reset",
            json={"token": "invalid-token", "new_password": "NewSecurePass123!"},
        )
        assert response.status_code == 400
        assert "invalid" in response.json()["detail"].lower()

    async def test_password_reset_weak_new_password(self, async_client: AsyncClient):
        """Test password reset with weak new password."""
        response = await async_client.post(
            "/api/v1/auth/password/reset", json={"token": "some-token", "new_password": "123"}
        )
        assert response.status_code == 422


class TestPasswordChange:
    """Tests for password change."""

    async def test_change_password_success(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        test_user: User,
        db_session: AsyncSession,
    ):
        """Test successful password change."""
        response = await async_client.post(
            "/api/v1/auth/password/change",
            headers=auth_headers,
            json={"current_password": "testpassword123", "new_password": "NewSecurePass456!"},
        )
        assert response.status_code == 200
        assert "changed successfully" in response.json()["message"].lower()

        # Verify can login with new password
        login_response = await async_client.post(
            "/api/v1/auth/login", json={"email": test_user.email, "password": "NewSecurePass456!"}
        )
        assert login_response.status_code == 200

    async def test_change_password_wrong_current(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        """Test password change with wrong current password."""
        response = await async_client.post(
            "/api/v1/auth/password/change",
            headers=auth_headers,
            json={"current_password": "wrongpassword", "new_password": "NewSecurePass456!"},
        )
        assert response.status_code == 400
        assert "incorrect" in response.json()["detail"].lower()

    async def test_change_password_unauthenticated(self, async_client: AsyncClient):
        """Test password change without authentication."""
        response = await async_client.post(
            "/api/v1/auth/password/change",
            json={"current_password": "testpassword123", "new_password": "NewSecurePass456!"},
        )
        assert response.status_code == 401

    async def test_change_password_weak_new_password(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        """Test password change with weak new password."""
        response = await async_client.post(
            "/api/v1/auth/password/change",
            headers=auth_headers,
            json={"current_password": "testpassword123", "new_password": "weak"},
        )
        assert response.status_code == 422


class TestEmailVerification:
    """Tests for email verification."""

    async def test_verify_email_success(self, async_client: AsyncClient, db_session: AsyncSession):
        """Test successful email verification."""
        from uuid import uuid4

        from core.security.password import password_hasher
        from core.security.tokens import TokenService
        from infrastructure.config.settings import settings

        # Create unverified user
        user = User(
            id=str(uuid4()),
            email="unverified@example.com",
            password_hash=password_hasher.hash("testpassword123"),
            name="Unverified User",
            status=UserStatus.PENDING.value,
            email_verified=False,
        )
        db_session.add(user)
        await db_session.commit()

        # Create verification token
        token_service = TokenService(secret_key=settings.jwt_secret_key)
        token = token_service.create_email_verification_token(user.id, user.email)

        response = await async_client.post("/api/v1/auth/verify-email", json={"token": token})
        assert response.status_code == 200
        assert "verified successfully" in response.json()["message"].lower()

        # Verify user status updated
        await db_session.refresh(user)
        assert user.email_verified is True
        assert user.status == UserStatus.ACTIVE.value

    async def test_verify_email_invalid_token(self, async_client: AsyncClient):
        """Test email verification with invalid token."""
        response = await async_client.post(
            "/api/v1/auth/verify-email", json={"token": "invalid-token"}
        )
        assert response.status_code == 400
        assert "invalid" in response.json()["detail"].lower()

    async def test_resend_verification_existing_unverified(
        self, async_client: AsyncClient, db_session: AsyncSession
    ):
        """Test resending verification for unverified user."""
        from uuid import uuid4

        from core.security.password import password_hasher

        user = User(
            id=str(uuid4()),
            email="unverified2@example.com",
            password_hash=password_hasher.hash("testpassword123"),
            name="Unverified User 2",
            status=UserStatus.PENDING.value,
            email_verified=False,
        )
        db_session.add(user)
        await db_session.commit()

        response = await async_client.post(
            "/api/v1/auth/resend-verification", json={"email": user.email}
        )
        assert response.status_code == 202


class TestLogout:
    """Tests for logout endpoint."""

    async def test_logout_success(self, async_client: AsyncClient, auth_headers: dict):
        """Test successful logout."""
        response = await async_client.post("/api/v1/auth/logout", headers=auth_headers)
        assert response.status_code == 200
        assert "logged out" in response.json()["message"].lower()

    async def test_logout_unauthenticated(self, async_client: AsyncClient):
        """Test logout without authentication."""
        response = await async_client.post("/api/v1/auth/logout")
        assert response.status_code == 401


class TestDeleteAccount:
    """Tests for the DELETE /auth/account endpoint."""

    async def test_delete_account_success(
        self,
        async_client: AsyncClient,
        test_user: User,
        auth_headers: dict,
        db_session,
    ):
        """Authenticated user can delete their account with correct confirmation."""
        import json as json_lib

        from sqlalchemy import select

        from infrastructure.database.models.user import User as UserModel

        response = await async_client.request(
            "DELETE",
            "/api/v1/auth/account",
            content=json_lib.dumps({"confirmation": "DELETE MY ACCOUNT"}),
            headers={**auth_headers, "Content-Type": "application/json"},
        )
        assert response.status_code == 200
        assert response.json()["message"] == "Account deleted successfully"

        # Verify the user row no longer exists in the database
        result = await db_session.execute(select(UserModel).where(UserModel.id == test_user.id))
        assert result.scalar_one_or_none() is None

    async def test_delete_account_wrong_confirmation(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
    ):
        """Request with wrong confirmation phrase is rejected."""
        import json as json_lib

        response = await async_client.request(
            "DELETE",
            "/api/v1/auth/account",
            content=json_lib.dumps({"confirmation": "delete my account"}),
            headers={**auth_headers, "Content-Type": "application/json"},
        )
        assert response.status_code == 400
        assert "DELETE MY ACCOUNT" in response.json()["detail"]

    async def test_delete_account_missing_confirmation(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
    ):
        """Request with missing body field is rejected with 422."""
        import json as json_lib

        response = await async_client.request(
            "DELETE",
            "/api/v1/auth/account",
            content=json_lib.dumps({}),
            headers={**auth_headers, "Content-Type": "application/json"},
        )
        assert response.status_code == 422

    async def test_delete_account_unauthenticated(self, async_client: AsyncClient):
        """Unauthenticated request is rejected with 401."""
        import json as json_lib

        response = await async_client.request(
            "DELETE",
            "/api/v1/auth/account",
            content=json_lib.dumps({"confirmation": "DELETE MY ACCOUNT"}),
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 401

    async def test_delete_account_deletes_owned_project(
        self,
        async_client: AsyncClient,
        test_user: User,
        auth_headers: dict,
        db_session,
    ):
        """Sole-owner projects are deleted along with the account."""
        import json as json_lib

        from sqlalchemy import select

        from infrastructure.database.models.project import Project, ProjectMember, ProjectMemberRole

        # Create a project owned by the test user
        project = Project(
            name="Test Project",
            slug=f"test-project-{test_user.id[:8]}",
            owner_id=test_user.id,
        )
        db_session.add(project)
        await db_session.commit()
        await db_session.refresh(project)
        project_id = project.id

        # Add the owner as a member
        member = ProjectMember(
            project_id=project_id,
            user_id=test_user.id,
            role=ProjectMemberRole.OWNER.value,
        )
        db_session.add(member)
        await db_session.commit()

        response = await async_client.request(
            "DELETE",
            "/api/v1/auth/account",
            content=json_lib.dumps({"confirmation": "DELETE MY ACCOUNT"}),
            headers={**auth_headers, "Content-Type": "application/json"},
        )
        assert response.status_code == 200

        # The sole-owner project should have been deleted
        result = await db_session.execute(select(Project).where(Project.id == project_id))
        assert result.scalar_one_or_none() is None
