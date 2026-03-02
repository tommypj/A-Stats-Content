"""
Unit tests for project role-based permissions (Phase 10).

Tests cover the permission model for project roles:
- OWNER: Full control (everything)
- ADMIN: Can manage members but not delete project
- MEMBER: Can create/edit content but not manage project
- VIEWER: Read-only access

Each test verifies the authorization logic without database or API calls.
"""

from enum import StrEnum


# Mock enums for project roles and actions
class ProjectRole(StrEnum):
    """Project member roles with different permission levels."""

    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"


class ProjectAction(StrEnum):
    """Actions that can be performed on projects and content."""

    # Project management
    DELETE_PROJECT = "delete_project"
    UPDATE_PROJECT = "update_project"
    VIEW_PROJECT = "view_project"

    # Member management
    ADD_MEMBER = "add_member"
    REMOVE_MEMBER = "remove_member"
    UPDATE_MEMBER_ROLE = "update_member_role"

    # Content management
    CREATE_CONTENT = "create_content"
    EDIT_CONTENT = "edit_content"
    DELETE_CONTENT = "delete_content"
    VIEW_CONTENT = "view_content"

    # Billing management
    MANAGE_BILLING = "manage_billing"
    VIEW_BILLING = "view_billing"


class ProjectPermissionChecker:
    """
    Permission checker for project role-based access control.

    Implements the permission matrix for multi-tenancy.
    """

    PERMISSIONS = {
        ProjectRole.OWNER: {
            ProjectAction.DELETE_PROJECT,
            ProjectAction.UPDATE_PROJECT,
            ProjectAction.VIEW_PROJECT,
            ProjectAction.ADD_MEMBER,
            ProjectAction.REMOVE_MEMBER,
            ProjectAction.UPDATE_MEMBER_ROLE,
            ProjectAction.CREATE_CONTENT,
            ProjectAction.EDIT_CONTENT,
            ProjectAction.DELETE_CONTENT,
            ProjectAction.VIEW_CONTENT,
            ProjectAction.MANAGE_BILLING,
            ProjectAction.VIEW_BILLING,
        },
        ProjectRole.ADMIN: {
            ProjectAction.UPDATE_PROJECT,
            ProjectAction.VIEW_PROJECT,
            ProjectAction.ADD_MEMBER,
            ProjectAction.REMOVE_MEMBER,
            ProjectAction.UPDATE_MEMBER_ROLE,
            ProjectAction.CREATE_CONTENT,
            ProjectAction.EDIT_CONTENT,
            ProjectAction.DELETE_CONTENT,
            ProjectAction.VIEW_CONTENT,
            ProjectAction.VIEW_BILLING,
        },
        ProjectRole.MEMBER: {
            ProjectAction.VIEW_PROJECT,
            ProjectAction.CREATE_CONTENT,
            ProjectAction.EDIT_CONTENT,
            ProjectAction.VIEW_CONTENT,
        },
        ProjectRole.VIEWER: {
            ProjectAction.VIEW_PROJECT,
            ProjectAction.VIEW_CONTENT,
        },
    }

    @classmethod
    def can_perform(cls, role: ProjectRole, action: ProjectAction) -> bool:
        """Check if a role has permission to perform an action."""
        return action in cls.PERMISSIONS.get(role, set())


# ============================================================================
# Test OWNER Permissions
# ============================================================================


def test_owner_can_delete_project():
    """OWNER should have permission to delete the project."""
    assert ProjectPermissionChecker.can_perform(ProjectRole.OWNER, ProjectAction.DELETE_PROJECT)


def test_owner_can_update_project():
    """OWNER should have permission to update project settings."""
    assert ProjectPermissionChecker.can_perform(ProjectRole.OWNER, ProjectAction.UPDATE_PROJECT)


def test_owner_can_view_project():
    """OWNER should have permission to view project details."""
    assert ProjectPermissionChecker.can_perform(ProjectRole.OWNER, ProjectAction.VIEW_PROJECT)


def test_owner_can_add_member():
    """OWNER should have permission to add project members."""
    assert ProjectPermissionChecker.can_perform(ProjectRole.OWNER, ProjectAction.ADD_MEMBER)


def test_owner_can_remove_member():
    """OWNER should have permission to remove project members."""
    assert ProjectPermissionChecker.can_perform(ProjectRole.OWNER, ProjectAction.REMOVE_MEMBER)


def test_owner_can_update_member_role():
    """OWNER should have permission to change member roles."""
    assert ProjectPermissionChecker.can_perform(ProjectRole.OWNER, ProjectAction.UPDATE_MEMBER_ROLE)


def test_owner_can_create_content():
    """OWNER should have permission to create content."""
    assert ProjectPermissionChecker.can_perform(ProjectRole.OWNER, ProjectAction.CREATE_CONTENT)


def test_owner_can_edit_content():
    """OWNER should have permission to edit content."""
    assert ProjectPermissionChecker.can_perform(ProjectRole.OWNER, ProjectAction.EDIT_CONTENT)


def test_owner_can_delete_content():
    """OWNER should have permission to delete content."""
    assert ProjectPermissionChecker.can_perform(ProjectRole.OWNER, ProjectAction.DELETE_CONTENT)


def test_owner_can_view_content():
    """OWNER should have permission to view content."""
    assert ProjectPermissionChecker.can_perform(ProjectRole.OWNER, ProjectAction.VIEW_CONTENT)


def test_owner_can_manage_billing():
    """OWNER should have permission to manage project billing."""
    assert ProjectPermissionChecker.can_perform(ProjectRole.OWNER, ProjectAction.MANAGE_BILLING)


def test_owner_can_view_billing():
    """OWNER should have permission to view billing information."""
    assert ProjectPermissionChecker.can_perform(ProjectRole.OWNER, ProjectAction.VIEW_BILLING)


# ============================================================================
# Test ADMIN Permissions
# ============================================================================


def test_admin_cannot_delete_project():
    """ADMIN should NOT have permission to delete the project (OWNER only)."""
    assert not ProjectPermissionChecker.can_perform(ProjectRole.ADMIN, ProjectAction.DELETE_PROJECT)


def test_admin_can_update_project():
    """ADMIN should have permission to update project settings."""
    assert ProjectPermissionChecker.can_perform(ProjectRole.ADMIN, ProjectAction.UPDATE_PROJECT)


def test_admin_can_add_member():
    """ADMIN should have permission to add project members."""
    assert ProjectPermissionChecker.can_perform(ProjectRole.ADMIN, ProjectAction.ADD_MEMBER)


def test_admin_can_remove_member():
    """ADMIN should have permission to remove project members."""
    assert ProjectPermissionChecker.can_perform(ProjectRole.ADMIN, ProjectAction.REMOVE_MEMBER)


def test_admin_can_update_member_role():
    """ADMIN should have permission to change member roles."""
    assert ProjectPermissionChecker.can_perform(ProjectRole.ADMIN, ProjectAction.UPDATE_MEMBER_ROLE)


def test_admin_can_create_content():
    """ADMIN should have permission to create content."""
    assert ProjectPermissionChecker.can_perform(ProjectRole.ADMIN, ProjectAction.CREATE_CONTENT)


def test_admin_cannot_manage_billing():
    """ADMIN should NOT have permission to manage billing (OWNER only)."""
    assert not ProjectPermissionChecker.can_perform(ProjectRole.ADMIN, ProjectAction.MANAGE_BILLING)


def test_admin_can_view_billing():
    """ADMIN should have permission to view billing information."""
    assert ProjectPermissionChecker.can_perform(ProjectRole.ADMIN, ProjectAction.VIEW_BILLING)


# ============================================================================
# Test MEMBER Permissions
# ============================================================================


def test_member_cannot_delete_project():
    """MEMBER should NOT have permission to delete the project."""
    assert not ProjectPermissionChecker.can_perform(
        ProjectRole.MEMBER, ProjectAction.DELETE_PROJECT
    )


def test_member_cannot_update_project():
    """MEMBER should NOT have permission to update project settings."""
    assert not ProjectPermissionChecker.can_perform(
        ProjectRole.MEMBER, ProjectAction.UPDATE_PROJECT
    )


def test_member_cannot_add_member():
    """MEMBER should NOT have permission to add project members."""
    assert not ProjectPermissionChecker.can_perform(ProjectRole.MEMBER, ProjectAction.ADD_MEMBER)


def test_member_cannot_remove_member():
    """MEMBER should NOT have permission to remove project members."""
    assert not ProjectPermissionChecker.can_perform(ProjectRole.MEMBER, ProjectAction.REMOVE_MEMBER)


def test_member_can_create_content():
    """MEMBER should have permission to create content."""
    assert ProjectPermissionChecker.can_perform(ProjectRole.MEMBER, ProjectAction.CREATE_CONTENT)


def test_member_can_edit_content():
    """MEMBER should have permission to edit content."""
    assert ProjectPermissionChecker.can_perform(ProjectRole.MEMBER, ProjectAction.EDIT_CONTENT)


def test_member_can_view_content():
    """MEMBER should have permission to view content."""
    assert ProjectPermissionChecker.can_perform(ProjectRole.MEMBER, ProjectAction.VIEW_CONTENT)


def test_member_cannot_manage_billing():
    """MEMBER should NOT have permission to manage billing."""
    assert not ProjectPermissionChecker.can_perform(
        ProjectRole.MEMBER, ProjectAction.MANAGE_BILLING
    )


def test_member_cannot_view_billing():
    """MEMBER should NOT have permission to view billing information."""
    assert not ProjectPermissionChecker.can_perform(ProjectRole.MEMBER, ProjectAction.VIEW_BILLING)


# ============================================================================
# Test VIEWER Permissions
# ============================================================================


def test_viewer_cannot_delete_project():
    """VIEWER should NOT have permission to delete the project."""
    assert not ProjectPermissionChecker.can_perform(
        ProjectRole.VIEWER, ProjectAction.DELETE_PROJECT
    )


def test_viewer_cannot_update_project():
    """VIEWER should NOT have permission to update project settings."""
    assert not ProjectPermissionChecker.can_perform(
        ProjectRole.VIEWER, ProjectAction.UPDATE_PROJECT
    )


def test_viewer_cannot_add_member():
    """VIEWER should NOT have permission to add project members."""
    assert not ProjectPermissionChecker.can_perform(ProjectRole.VIEWER, ProjectAction.ADD_MEMBER)


def test_viewer_cannot_create_content():
    """VIEWER should NOT have permission to create content."""
    assert not ProjectPermissionChecker.can_perform(
        ProjectRole.VIEWER, ProjectAction.CREATE_CONTENT
    )


def test_viewer_cannot_edit_content():
    """VIEWER should NOT have permission to edit content."""
    assert not ProjectPermissionChecker.can_perform(ProjectRole.VIEWER, ProjectAction.EDIT_CONTENT)


def test_viewer_cannot_delete_content():
    """VIEWER should NOT have permission to delete content."""
    assert not ProjectPermissionChecker.can_perform(
        ProjectRole.VIEWER, ProjectAction.DELETE_CONTENT
    )


def test_viewer_can_view_content():
    """VIEWER should have permission to view content."""
    assert ProjectPermissionChecker.can_perform(ProjectRole.VIEWER, ProjectAction.VIEW_CONTENT)


def test_viewer_can_view_project():
    """VIEWER should have permission to view project details."""
    assert ProjectPermissionChecker.can_perform(ProjectRole.VIEWER, ProjectAction.VIEW_PROJECT)


def test_viewer_cannot_manage_billing():
    """VIEWER should NOT have permission to manage billing."""
    assert not ProjectPermissionChecker.can_perform(
        ProjectRole.VIEWER, ProjectAction.MANAGE_BILLING
    )


def test_viewer_cannot_view_billing():
    """VIEWER should NOT have permission to view billing information."""
    assert not ProjectPermissionChecker.can_perform(ProjectRole.VIEWER, ProjectAction.VIEW_BILLING)


# ============================================================================
# Permission Matrix Tests
# ============================================================================


def test_permission_hierarchy():
    """Test that permission hierarchy is correct: OWNER > ADMIN > MEMBER > VIEWER."""
    # Count permissions for each role
    owner_perms = len(ProjectPermissionChecker.PERMISSIONS[ProjectRole.OWNER])
    admin_perms = len(ProjectPermissionChecker.PERMISSIONS[ProjectRole.ADMIN])
    member_perms = len(ProjectPermissionChecker.PERMISSIONS[ProjectRole.MEMBER])
    viewer_perms = len(ProjectPermissionChecker.PERMISSIONS[ProjectRole.VIEWER])

    # Verify hierarchy
    assert owner_perms > admin_perms > member_perms > viewer_perms


def test_all_roles_can_view_project():
    """Test that all roles have permission to view project details."""
    for role in ProjectRole:
        assert ProjectPermissionChecker.can_perform(role, ProjectAction.VIEW_PROJECT)


def test_all_roles_can_view_content():
    """Test that all roles have permission to view content."""
    for role in ProjectRole:
        assert ProjectPermissionChecker.can_perform(role, ProjectAction.VIEW_CONTENT)


def test_only_owner_can_delete_project():
    """Test that only OWNER can delete the project."""
    for role in ProjectRole:
        can_delete = ProjectPermissionChecker.can_perform(role, ProjectAction.DELETE_PROJECT)
        if role == ProjectRole.OWNER:
            assert can_delete
        else:
            assert not can_delete


def test_only_owner_can_manage_billing():
    """Test that only OWNER can manage billing."""
    for role in ProjectRole:
        can_manage = ProjectPermissionChecker.can_perform(role, ProjectAction.MANAGE_BILLING)
        if role == ProjectRole.OWNER:
            assert can_manage
        else:
            assert not can_manage


def test_viewer_has_minimum_permissions():
    """Test that VIEWER has the most restrictive permissions."""
    viewer_perms = ProjectPermissionChecker.PERMISSIONS[ProjectRole.VIEWER]

    # VIEWER should only be able to view
    assert viewer_perms == {ProjectAction.VIEW_PROJECT, ProjectAction.VIEW_CONTENT}
