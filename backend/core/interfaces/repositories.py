"""Repository interfaces for data access."""

from abc import ABC, abstractmethod
from uuid import UUID

from ..domain.content import Article, Outline
from ..domain.user import User


class UserRepository(ABC):
    """Abstract repository for User entities."""

    @abstractmethod
    async def create(self, user: User) -> User:
        """Create a new user."""
        ...

    @abstractmethod
    async def get_by_id(self, user_id: UUID) -> User | None:
        """Get user by ID."""
        ...

    @abstractmethod
    async def get_by_email(self, email: str) -> User | None:
        """Get user by email."""
        ...

    @abstractmethod
    async def update(self, user: User) -> User:
        """Update an existing user."""
        ...

    @abstractmethod
    async def delete(self, user_id: UUID) -> bool:
        """Delete a user."""
        ...

    @abstractmethod
    async def list_all(self, skip: int = 0, limit: int = 100) -> list[User]:
        """List all users with pagination."""
        ...


class OutlineRepository(ABC):
    """Abstract repository for Outline entities."""

    @abstractmethod
    async def create(self, outline: Outline) -> Outline:
        """Create a new outline."""
        ...

    @abstractmethod
    async def get_by_id(self, outline_id: UUID) -> Outline | None:
        """Get outline by ID."""
        ...

    @abstractmethod
    async def get_by_user(self, user_id: UUID, skip: int = 0, limit: int = 50) -> list[Outline]:
        """Get outlines for a user."""
        ...

    @abstractmethod
    async def update(self, outline: Outline) -> Outline:
        """Update an existing outline."""
        ...

    @abstractmethod
    async def delete(self, outline_id: UUID) -> bool:
        """Delete an outline."""
        ...


class ArticleRepository(ABC):
    """Abstract repository for Article entities."""

    @abstractmethod
    async def create(self, article: Article) -> Article:
        """Create a new article."""
        ...

    @abstractmethod
    async def get_by_id(self, article_id: UUID) -> Article | None:
        """Get article by ID."""
        ...

    @abstractmethod
    async def get_by_outline(self, outline_id: UUID) -> Article | None:
        """Get article for an outline."""
        ...

    @abstractmethod
    async def update(self, article: Article) -> Article:
        """Update an existing article."""
        ...

    @abstractmethod
    async def delete(self, article_id: UUID) -> bool:
        """Delete an article."""
        ...
