"""
API dependencies for authentication and authorization.
"""

from typing import Annotated

from fastapi import Depends, HTTPException, status

from infrastructure.database.models.user import User, UserRole
from api.routes.auth import get_current_user


async def get_current_admin_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """
    Dependency to get the current authenticated admin user.

    Ensures the user has admin or super_admin role.
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user
