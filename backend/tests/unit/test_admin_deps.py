"""
Unit tests for admin dependencies and role-based access control.

Tests admin authentication dependencies:
- get_current_admin_user - Requires admin or super_admin role
- get_current_super_admin - Requires super_admin role only
- Suspended user access
- Role validation
"""

import pytest
from datetime import datetime, timezone
from uuid import uuid4
from unittest.mock import Mock, AsyncMock

from fastapi import HTTPException, status

# Skip all tests if admin dependencies are not available
try:
    from api.dependencies.admin import (
        get_current_admin_user,
        get_current_super_admin,
    )
    from infrastructure.database.models import User
    from infrastructure.database.models.user import UserRole, UserStatus
    ADMIN_DEPS_AVAILABLE = True
except (ImportError, AttributeError):
    ADMIN_DEPS_AVAILABLE = False
    pytestmark = pytest.mark.skip(reason="Admin dependencies not implemented yet")


@pytest.fixture
def regular_user():
    """Create a regular user without admin privileges."""
    return User(
        id=str(uuid4()),
        email="user@example.com",
        password_hash="hashed_password",
        name="Regular User",
        role=UserRole.USER.value,
        status=UserStatus.ACTIVE.value,
        email_verified=True,
    )


@pytest.fixture
def admin_user():
    """Create an admin user."""
    return User(
        id=str(uuid4()),
        email="admin@example.com",
        password_hash="hashed_password",
        name="Admin User",
        role=UserRole.ADMIN.value,
        status=UserStatus.ACTIVE.value,
        email_verified=True,
    )


@pytest.fixture
def super_admin_user():
    """Create a super admin user."""
    return User(
        id=str(uuid4()),
        email="superadmin@example.com",
        password_hash="hashed_password",
        name="Super Admin User",
        role=UserRole.SUPER_ADMIN.value,
        status=UserStatus.ACTIVE.value,
        email_verified=True,
    )


@pytest.fixture
def suspended_admin_user():
    """Create a suspended admin user."""
    return User(
        id=str(uuid4()),
        email="suspended@example.com",
        password_hash="hashed_password",
        name="Suspended Admin",
        role=UserRole.ADMIN.value,
        status=UserStatus.SUSPENDED.value,
        email_verified=True,
    )


class TestGetCurrentAdminUser:
    """Tests for get_current_admin_user dependency."""

    @pytest.mark.asyncio
    async def test_admin_user_access_granted(self, admin_user):
        """Test that admin user can access admin endpoints."""
        if not ADMIN_DEPS_AVAILABLE:
            pytest.skip("Admin dependencies not available")

        # get_current_admin_user should accept the user
        result = await get_current_admin_user(current_user=admin_user)
        assert result == admin_user
        assert result.role == UserRole.ADMIN.value

    @pytest.mark.asyncio
    async def test_super_admin_user_access_granted(self, super_admin_user):
        """Test that super admin user can access admin endpoints."""
        if not ADMIN_DEPS_AVAILABLE:
            pytest.skip("Admin dependencies not available")

        result = await get_current_admin_user(current_user=super_admin_user)
        assert result == super_admin_user
        assert result.role == UserRole.SUPER_ADMIN.value

    @pytest.mark.asyncio
    async def test_regular_user_access_denied(self, regular_user):
        """Test that regular user cannot access admin endpoints."""
        if not ADMIN_DEPS_AVAILABLE:
            pytest.skip("Admin dependencies not available")

        with pytest.raises(HTTPException) as exc_info:
            await get_current_admin_user(current_user=regular_user)

        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        assert "admin" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_suspended_admin_access_denied(self, suspended_admin_user):
        """Test that suspended admin cannot access admin endpoints."""
        if not ADMIN_DEPS_AVAILABLE:
            pytest.skip("Admin dependencies not available")

        with pytest.raises(HTTPException) as exc_info:
            await get_current_admin_user(current_user=suspended_admin_user)

        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        assert "suspended" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_deleted_admin_access_denied(self, admin_user):
        """Test that soft-deleted admin cannot access admin endpoints."""
        if not ADMIN_DEPS_AVAILABLE:
            pytest.skip("Admin dependencies not available")

        admin_user.deleted_at = datetime.now(timezone.utc)

        with pytest.raises(HTTPException) as exc_info:
            await get_current_admin_user(current_user=admin_user)

        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN


class TestGetCurrentSuperAdmin:
    """Tests for get_current_super_admin dependency."""

    @pytest.mark.asyncio
    async def test_super_admin_access_granted(self, super_admin_user):
        """Test that super admin user can access super admin endpoints."""
        if not ADMIN_DEPS_AVAILABLE:
            pytest.skip("Admin dependencies not available")

        result = await get_current_super_admin(current_user=super_admin_user)
        assert result == super_admin_user
        assert result.role == UserRole.SUPER_ADMIN.value

    @pytest.mark.asyncio
    async def test_regular_admin_access_denied(self, admin_user):
        """Test that regular admin cannot access super admin endpoints."""
        if not ADMIN_DEPS_AVAILABLE:
            pytest.skip("Admin dependencies not available")

        with pytest.raises(HTTPException) as exc_info:
            await get_current_super_admin(current_user=admin_user)

        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        assert "super admin" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_regular_user_access_denied(self, regular_user):
        """Test that regular user cannot access super admin endpoints."""
        if not ADMIN_DEPS_AVAILABLE:
            pytest.skip("Admin dependencies not available")

        with pytest.raises(HTTPException) as exc_info:
            await get_current_super_admin(current_user=regular_user)

        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        assert "super admin" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_suspended_super_admin_access_denied(self, super_admin_user):
        """Test that suspended super admin cannot access super admin endpoints."""
        if not ADMIN_DEPS_AVAILABLE:
            pytest.skip("Admin dependencies not available")

        super_admin_user.status = UserStatus.SUSPENDED.value

        with pytest.raises(HTTPException) as exc_info:
            await get_current_super_admin(current_user=super_admin_user)

        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        assert "suspended" in exc_info.value.detail.lower()


class TestRoleValidation:
    """Tests for role-based access control logic."""

    def test_is_admin_property_for_admin(self, admin_user):
        """Test that admin user has is_admin property True."""
        if not ADMIN_DEPS_AVAILABLE:
            pytest.skip("Admin dependencies not available")

        assert admin_user.is_admin is True

    def test_is_admin_property_for_super_admin(self, super_admin_user):
        """Test that super admin user has is_admin property True."""
        if not ADMIN_DEPS_AVAILABLE:
            pytest.skip("Admin dependencies not available")

        assert super_admin_user.is_admin is True

    def test_is_admin_property_for_regular_user(self, regular_user):
        """Test that regular user has is_admin property False."""
        if not ADMIN_DEPS_AVAILABLE:
            pytest.skip("Admin dependencies not available")

        assert regular_user.is_admin is False

    def test_role_comparison(self, admin_user, super_admin_user, regular_user):
        """Test role comparison logic."""
        if not ADMIN_DEPS_AVAILABLE:
            pytest.skip("Admin dependencies not available")

        assert admin_user.role == UserRole.ADMIN.value
        assert super_admin_user.role == UserRole.SUPER_ADMIN.value
        assert regular_user.role == UserRole.USER.value

        # Verify hierarchy
        assert super_admin_user.role != admin_user.role
        assert admin_user.role != regular_user.role
