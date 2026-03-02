"""
Integration tests for admin users API.

Tests admin user management endpoints:
- List users with pagination and filters
- Get single user details
- Update user role
- Suspend/unsuspend users
- Delete users (super_admin only)
- Authorization and permission checks
"""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi import status
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.database.models import User
from infrastructure.database.models.user import UserRole, UserStatus

# Skip all tests if admin routes are not available
try:
    from api.routes import admin

    ADMIN_ROUTES_AVAILABLE = True
except (ImportError, AttributeError):
    ADMIN_ROUTES_AVAILABLE = False
    pytestmark = pytest.mark.skip(reason="Admin routes not implemented yet")


class TestListUsersEndpoint:
    """Tests for GET /admin/users endpoint."""

    @pytest.mark.asyncio
    async def test_admin_can_list_users(
        self,
        async_client: AsyncClient,
        admin_token: dict,
        db_session: AsyncSession,
        test_user: User,
    ):
        """Test that admin can list all users."""
        if not ADMIN_ROUTES_AVAILABLE:
            pytest.skip("Admin routes not available")

        response = await async_client.get(
            "/api/v1/admin/users",
            headers=admin_token,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "users" in data
        assert "total" in data
        assert "page" in data
        assert "per_page" in data
        assert len(data["users"]) > 0

        # Verify user structure
        user = data["users"][0]
        assert "id" in user
        assert "email" in user
        assert "name" in user
        assert "role" in user
        assert "status" in user
        assert "subscription_tier" in user
        assert "created_at" in user

    @pytest.mark.asyncio
    async def test_super_admin_can_list_users(
        self,
        async_client: AsyncClient,
        super_admin_token: dict,
    ):
        """Test that super admin can list all users."""
        if not ADMIN_ROUTES_AVAILABLE:
            pytest.skip("Admin routes not available")

        response = await async_client.get(
            "/api/v1/admin/users",
            headers=super_admin_token,
        )

        assert response.status_code == status.HTTP_200_OK

    @pytest.mark.asyncio
    async def test_regular_user_cannot_list_users(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
    ):
        """Test that regular user cannot list users."""
        if not ADMIN_ROUTES_AVAILABLE:
            pytest.skip("Admin routes not available")

        response = await async_client.get(
            "/api/v1/admin/users",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.asyncio
    async def test_unauthenticated_cannot_list_users(
        self,
        async_client: AsyncClient,
    ):
        """Test that unauthenticated user cannot list users."""
        if not ADMIN_ROUTES_AVAILABLE:
            pytest.skip("Admin routes not available")

        response = await async_client.get("/api/v1/admin/users")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_list_users_pagination(
        self,
        async_client: AsyncClient,
        admin_token: dict,
        db_session: AsyncSession,
    ):
        """Test pagination in user listing."""
        if not ADMIN_ROUTES_AVAILABLE:
            pytest.skip("Admin routes not available")

        # Create multiple users for pagination test
        for i in range(15):
            user = User(
                id=str(uuid4()),
                email=f"user{i}@example.com",
                password_hash="hashed",
                name=f"User {i}",
                role=UserRole.USER.value,
                status=UserStatus.ACTIVE.value,
                email_verified=True,
            )
            db_session.add(user)
        await db_session.commit()

        # Get first page
        response = await async_client.get(
            "/api/v1/admin/users?page=1&per_page=10",
            headers=admin_token,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["page"] == 1
        assert data["per_page"] == 10
        assert len(data["users"]) == 10

        # Get second page
        response = await async_client.get(
            "/api/v1/admin/users?page=2&per_page=10",
            headers=admin_token,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["page"] == 2
        assert len(data["users"]) > 0

    @pytest.mark.asyncio
    async def test_filter_users_by_role(
        self,
        async_client: AsyncClient,
        admin_token: dict,
        db_session: AsyncSession,
    ):
        """Test filtering users by role."""
        if not ADMIN_ROUTES_AVAILABLE:
            pytest.skip("Admin routes not available")

        # Create users with different roles
        admin = User(
            id=str(uuid4()),
            email="another_admin@example.com",
            password_hash="hashed",
            name="Another Admin",
            role=UserRole.ADMIN.value,
            status=UserStatus.ACTIVE.value,
            email_verified=True,
        )
        db_session.add(admin)
        await db_session.commit()

        # Filter by admin role
        response = await async_client.get(
            "/api/v1/admin/users?role=admin",
            headers=admin_token,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        # All returned users should be admins or super_admins
        for user in data["users"]:
            assert user["role"] in ["admin", "super_admin"]

    @pytest.mark.asyncio
    async def test_filter_users_by_status(
        self,
        async_client: AsyncClient,
        admin_token: dict,
        db_session: AsyncSession,
        suspended_user: User,
    ):
        """Test filtering users by status."""
        if not ADMIN_ROUTES_AVAILABLE:
            pytest.skip("Admin routes not available")

        response = await async_client.get(
            "/api/v1/admin/users?status=suspended",
            headers=admin_token,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        # All returned users should be suspended
        for user in data["users"]:
            assert user["status"] == "suspended"

    @pytest.mark.asyncio
    async def test_filter_users_by_subscription_tier(
        self,
        async_client: AsyncClient,
        admin_token: dict,
    ):
        """Test filtering users by subscription tier."""
        if not ADMIN_ROUTES_AVAILABLE:
            pytest.skip("Admin routes not available")

        response = await async_client.get(
            "/api/v1/admin/users?subscription_tier=professional",
            headers=admin_token,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        # All returned users should have professional tier
        for user in data["users"]:
            assert user["subscription_tier"] == "professional"

    @pytest.mark.asyncio
    async def test_search_users_by_email(
        self,
        async_client: AsyncClient,
        admin_token: dict,
        test_user: User,
    ):
        """Test searching users by email."""
        if not ADMIN_ROUTES_AVAILABLE:
            pytest.skip("Admin routes not available")

        response = await async_client.get(
            f"/api/v1/admin/users?search={test_user.email}",
            headers=admin_token,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["users"]) >= 1
        # At least one user should have matching email
        emails = [u["email"] for u in data["users"]]
        assert test_user.email in emails

    @pytest.mark.asyncio
    async def test_search_users_by_name(
        self,
        async_client: AsyncClient,
        admin_token: dict,
        test_user: User,
    ):
        """Test searching users by name."""
        if not ADMIN_ROUTES_AVAILABLE:
            pytest.skip("Admin routes not available")

        response = await async_client.get(
            f"/api/v1/admin/users?search={test_user.name}",
            headers=admin_token,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        # At least one user should have matching name
        names = [u["name"] for u in data["users"]]
        assert any(test_user.name in name for name in names)


class TestGetUserEndpoint:
    """Tests for GET /admin/users/{user_id} endpoint."""

    @pytest.mark.asyncio
    async def test_admin_can_get_user_details(
        self,
        async_client: AsyncClient,
        admin_token: dict,
        test_user: User,
    ):
        """Test that admin can get user details."""
        if not ADMIN_ROUTES_AVAILABLE:
            pytest.skip("Admin routes not available")

        response = await async_client.get(
            f"/api/v1/admin/users/{test_user.id}",
            headers=admin_token,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == test_user.id
        assert data["email"] == test_user.email
        assert data["name"] == test_user.name
        assert "subscription_tier" in data
        assert "created_at" in data
        assert "last_login" in data

    @pytest.mark.asyncio
    async def test_regular_user_cannot_get_user_details(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        admin_user: User,
    ):
        """Test that regular user cannot get other user's details."""
        if not ADMIN_ROUTES_AVAILABLE:
            pytest.skip("Admin routes not available")

        response = await async_client.get(
            f"/api/v1/admin/users/{admin_user.id}",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.asyncio
    async def test_get_nonexistent_user_returns_404(
        self,
        async_client: AsyncClient,
        admin_token: dict,
    ):
        """Test that getting nonexistent user returns 404."""
        if not ADMIN_ROUTES_AVAILABLE:
            pytest.skip("Admin routes not available")

        fake_id = str(uuid4())
        response = await async_client.get(
            f"/api/v1/admin/users/{fake_id}",
            headers=admin_token,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestUpdateUserRoleEndpoint:
    """Tests for PUT /admin/users/{user_id}/role endpoint."""

    @pytest.mark.asyncio
    async def test_admin_can_change_user_to_admin(
        self,
        async_client: AsyncClient,
        admin_token: dict,
        test_user: User,
        db_session: AsyncSession,
    ):
        """Test that admin can promote user to admin role."""
        if not ADMIN_ROUTES_AVAILABLE:
            pytest.skip("Admin routes not available")

        response = await async_client.put(
            f"/api/v1/admin/users/{test_user.id}/role",
            headers=admin_token,
            json={"role": "admin"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["role"] == "admin"

        # Verify in database
        await db_session.refresh(test_user)
        assert test_user.role == UserRole.ADMIN.value

    @pytest.mark.asyncio
    async def test_super_admin_can_change_user_to_super_admin(
        self,
        async_client: AsyncClient,
        super_admin_token: dict,
        test_user: User,
        db_session: AsyncSession,
    ):
        """Test that super admin can promote user to super admin."""
        if not ADMIN_ROUTES_AVAILABLE:
            pytest.skip("Admin routes not available")

        response = await async_client.put(
            f"/api/v1/admin/users/{test_user.id}/role",
            headers=super_admin_token,
            json={"role": "super_admin"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["role"] == "super_admin"

    @pytest.mark.asyncio
    async def test_admin_cannot_promote_to_super_admin(
        self,
        async_client: AsyncClient,
        admin_token: dict,
        test_user: User,
    ):
        """Test that regular admin cannot promote user to super admin."""
        if not ADMIN_ROUTES_AVAILABLE:
            pytest.skip("Admin routes not available")

        response = await async_client.put(
            f"/api/v1/admin/users/{test_user.id}/role",
            headers=admin_token,
            json={"role": "super_admin"},
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.asyncio
    async def test_admin_cannot_demote_themselves(
        self,
        async_client: AsyncClient,
        admin_token: dict,
        admin_user: User,
    ):
        """Test that admin cannot demote their own role."""
        if not ADMIN_ROUTES_AVAILABLE:
            pytest.skip("Admin routes not available")

        response = await async_client.put(
            f"/api/v1/admin/users/{admin_user.id}/role",
            headers=admin_token,
            json={"role": "user"},
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "yourself" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_invalid_role_returns_422(
        self,
        async_client: AsyncClient,
        admin_token: dict,
        test_user: User,
    ):
        """Test that invalid role returns validation error."""
        if not ADMIN_ROUTES_AVAILABLE:
            pytest.skip("Admin routes not available")

        response = await async_client.put(
            f"/api/v1/admin/users/{test_user.id}/role",
            headers=admin_token,
            json={"role": "invalid_role"},
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestSuspendUserEndpoint:
    """Tests for POST /admin/users/{user_id}/suspend endpoint."""

    @pytest.mark.asyncio
    async def test_admin_can_suspend_user(
        self,
        async_client: AsyncClient,
        admin_token: dict,
        test_user: User,
        db_session: AsyncSession,
    ):
        """Test that admin can suspend a user."""
        if not ADMIN_ROUTES_AVAILABLE:
            pytest.skip("Admin routes not available")

        response = await async_client.post(
            f"/api/v1/admin/users/{test_user.id}/suspend",
            headers=admin_token,
            json={"reason": "Terms of service violation"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "suspended"

        # Verify in database
        await db_session.refresh(test_user)
        assert test_user.status == UserStatus.SUSPENDED.value

    @pytest.mark.asyncio
    async def test_suspend_user_with_optional_reason(
        self,
        async_client: AsyncClient,
        admin_token: dict,
        test_user: User,
    ):
        """Test suspending user with optional reason field."""
        if not ADMIN_ROUTES_AVAILABLE:
            pytest.skip("Admin routes not available")

        response = await async_client.post(
            f"/api/v1/admin/users/{test_user.id}/suspend",
            headers=admin_token,
            json={},
        )

        assert response.status_code == status.HTTP_200_OK

    @pytest.mark.asyncio
    async def test_admin_cannot_suspend_themselves(
        self,
        async_client: AsyncClient,
        admin_token: dict,
        admin_user: User,
    ):
        """Test that admin cannot suspend their own account."""
        if not ADMIN_ROUTES_AVAILABLE:
            pytest.skip("Admin routes not available")

        response = await async_client.post(
            f"/api/v1/admin/users/{admin_user.id}/suspend",
            headers=admin_token,
            json={},
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.asyncio
    async def test_suspend_already_suspended_user(
        self,
        async_client: AsyncClient,
        admin_token: dict,
        suspended_user: User,
    ):
        """Test suspending an already suspended user (should be idempotent)."""
        if not ADMIN_ROUTES_AVAILABLE:
            pytest.skip("Admin routes not available")

        response = await async_client.post(
            f"/api/v1/admin/users/{suspended_user.id}/suspend",
            headers=admin_token,
            json={},
        )

        # Should succeed (idempotent operation)
        assert response.status_code == status.HTTP_200_OK


class TestUnsuspendUserEndpoint:
    """Tests for POST /admin/users/{user_id}/unsuspend endpoint."""

    @pytest.mark.asyncio
    async def test_admin_can_unsuspend_user(
        self,
        async_client: AsyncClient,
        admin_token: dict,
        suspended_user: User,
        db_session: AsyncSession,
    ):
        """Test that admin can unsuspend a user."""
        if not ADMIN_ROUTES_AVAILABLE:
            pytest.skip("Admin routes not available")

        response = await async_client.post(
            f"/api/v1/admin/users/{suspended_user.id}/unsuspend",
            headers=admin_token,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "active"

        # Verify in database
        await db_session.refresh(suspended_user)
        assert suspended_user.status == UserStatus.ACTIVE.value

    @pytest.mark.asyncio
    async def test_unsuspend_active_user(
        self,
        async_client: AsyncClient,
        admin_token: dict,
        test_user: User,
    ):
        """Test unsuspending an already active user (should be idempotent)."""
        if not ADMIN_ROUTES_AVAILABLE:
            pytest.skip("Admin routes not available")

        response = await async_client.post(
            f"/api/v1/admin/users/{test_user.id}/unsuspend",
            headers=admin_token,
        )

        # Should succeed (idempotent operation)
        assert response.status_code == status.HTTP_200_OK


class TestDeleteUserEndpoint:
    """Tests for DELETE /admin/users/{user_id} endpoint."""

    @pytest.mark.asyncio
    async def test_super_admin_can_delete_user(
        self,
        async_client: AsyncClient,
        super_admin_token: dict,
        test_user: User,
        db_session: AsyncSession,
    ):
        """Test that super admin can delete a user (soft delete)."""
        if not ADMIN_ROUTES_AVAILABLE:
            pytest.skip("Admin routes not available")

        response = await async_client.delete(
            f"/api/v1/admin/users/{test_user.id}",
            headers=super_admin_token,
        )

        assert response.status_code == status.HTTP_200_OK

        # Verify soft delete in database
        await db_session.refresh(test_user)
        assert test_user.deleted_at is not None
        assert test_user.status == UserStatus.DELETED.value

    @pytest.mark.asyncio
    async def test_regular_admin_cannot_delete_user(
        self,
        async_client: AsyncClient,
        admin_token: dict,
        test_user: User,
    ):
        """Test that regular admin cannot delete users."""
        if not ADMIN_ROUTES_AVAILABLE:
            pytest.skip("Admin routes not available")

        response = await async_client.delete(
            f"/api/v1/admin/users/{test_user.id}",
            headers=admin_token,
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.asyncio
    async def test_super_admin_cannot_delete_themselves(
        self,
        async_client: AsyncClient,
        super_admin_token: dict,
        super_admin_user: User,
    ):
        """Test that super admin cannot delete their own account."""
        if not ADMIN_ROUTES_AVAILABLE:
            pytest.skip("Admin routes not available")

        response = await async_client.delete(
            f"/api/v1/admin/users/{super_admin_user.id}",
            headers=super_admin_token,
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.asyncio
    async def test_delete_already_deleted_user(
        self,
        async_client: AsyncClient,
        super_admin_token: dict,
        test_user: User,
        db_session: AsyncSession,
    ):
        """Test deleting an already deleted user."""
        if not ADMIN_ROUTES_AVAILABLE:
            pytest.skip("Admin routes not available")

        # Soft delete the user first
        test_user.deleted_at = datetime.now(UTC)
        test_user.status = UserStatus.DELETED.value
        await db_session.commit()

        response = await async_client.delete(
            f"/api/v1/admin/users/{test_user.id}",
            headers=super_admin_token,
        )

        # Should still succeed (idempotent)
        assert response.status_code == status.HTTP_200_OK
