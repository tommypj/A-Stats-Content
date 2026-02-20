"""
Password hashing utilities using bcrypt.
"""

from passlib.context import CryptContext


class PasswordHasher:
    """Password hashing and verification using bcrypt."""

    def __init__(self):
        self._context = CryptContext(
            schemes=["bcrypt"],
            deprecated="auto",
            bcrypt__rounds=12,
        )

    def hash(self, password: str) -> str:
        """
        Hash a password using bcrypt.

        Args:
            password: Plain text password to hash

        Returns:
            Hashed password string
        """
        return self._context.hash(password)

    def verify(self, plain_password: str, hashed_password: str) -> bool:
        """
        Verify a password against a hash.

        Args:
            plain_password: Plain text password to verify
            hashed_password: Hashed password to check against

        Returns:
            True if password matches, False otherwise
        """
        return self._context.verify(plain_password, hashed_password)

    def needs_rehash(self, hashed_password: str) -> bool:
        """
        Check if a password hash needs to be rehashed.

        This is useful when upgrading the hashing algorithm or parameters.

        Args:
            hashed_password: Hashed password to check

        Returns:
            True if rehash is needed, False otherwise
        """
        return self._context.needs_update(hashed_password)


# Singleton instance
password_hasher = PasswordHasher()
