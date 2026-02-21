"""
Admin authentication dependencies.
"""

from typing import Annotated

from fastapi import Depends, HTTPException, status

from infrastructure.database.models.user import User, UserRole
from api.routes.auth import get_current_user


async def get_current_admin_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """
    Dependency to verify current user is an admin.

    Requires user to have ADMIN or SUPER_ADMIN role.

    Args:
        current_user: The authenticated user from get_current_user dependency

    Returns:
        User: The admin user if authorized

    Raises:
        HTTPException: 403 if user is not an admin
    """
    if current_user.role not in (UserRole.ADMIN.value, UserRole.SUPER_ADMIN.value):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required. You do not have permission to access this resource.",
        )

    return current_user


async def get_current_super_admin_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """
    Dependency to verify current user is a super admin.

    Requires user to have SUPER_ADMIN role.

    Args:
        current_user: The authenticated user from get_current_user dependency

    Returns:
        User: The super admin user if authorized

    Raises:
        HTTPException: 403 if user is not a super admin
    """
    if current_user.role != UserRole.SUPER_ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super admin access required. You do not have permission to access this resource.",
        )

    return current_user
