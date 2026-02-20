"""
JWT token service for authentication.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional
from dataclasses import dataclass

from jose import JWTError, jwt


@dataclass
class TokenPayload:
    """JWT token payload structure."""

    sub: str  # Subject (user ID)
    exp: datetime  # Expiration time
    iat: datetime  # Issued at
    type: str  # Token type: "access" or "refresh"
    email: Optional[str] = None
    role: Optional[str] = None


class TokenService:
    """Service for creating and validating JWT tokens."""

    def __init__(
        self,
        secret_key: str,
        algorithm: str = "HS256",
        access_token_expire_minutes: int = 30,
        refresh_token_expire_days: int = 7,
    ):
        """
        Initialize the token service.

        Args:
            secret_key: Secret key for signing tokens
            algorithm: JWT algorithm (default: HS256)
            access_token_expire_minutes: Access token expiration in minutes
            refresh_token_expire_days: Refresh token expiration in days
        """
        self._secret_key = secret_key
        self._algorithm = algorithm
        self._access_token_expire_minutes = access_token_expire_minutes
        self._refresh_token_expire_days = refresh_token_expire_days

    def create_access_token(
        self,
        user_id: str,
        email: Optional[str] = None,
        role: Optional[str] = None,
    ) -> str:
        """
        Create an access token.

        Args:
            user_id: User ID to encode in the token
            email: Optional email to include
            role: Optional role to include

        Returns:
            Encoded JWT access token
        """
        now = datetime.now(timezone.utc)
        expire = now + timedelta(minutes=self._access_token_expire_minutes)

        payload = {
            "sub": user_id,
            "exp": expire,
            "iat": now,
            "type": "access",
        }

        if email:
            payload["email"] = email
        if role:
            payload["role"] = role

        return jwt.encode(payload, self._secret_key, algorithm=self._algorithm)

    def create_refresh_token(self, user_id: str) -> str:
        """
        Create a refresh token.

        Args:
            user_id: User ID to encode in the token

        Returns:
            Encoded JWT refresh token
        """
        now = datetime.now(timezone.utc)
        expire = now + timedelta(days=self._refresh_token_expire_days)

        payload = {
            "sub": user_id,
            "exp": expire,
            "iat": now,
            "type": "refresh",
        }

        return jwt.encode(payload, self._secret_key, algorithm=self._algorithm)

    def create_token_pair(
        self,
        user_id: str,
        email: Optional[str] = None,
        role: Optional[str] = None,
    ) -> tuple[str, str]:
        """
        Create both access and refresh tokens.

        Args:
            user_id: User ID to encode in the tokens
            email: Optional email to include in access token
            role: Optional role to include in access token

        Returns:
            Tuple of (access_token, refresh_token)
        """
        access_token = self.create_access_token(user_id, email, role)
        refresh_token = self.create_refresh_token(user_id)
        return access_token, refresh_token

    def decode_token(self, token: str) -> Optional[TokenPayload]:
        """
        Decode and validate a JWT token.

        Args:
            token: JWT token to decode

        Returns:
            TokenPayload if valid, None if invalid or expired
        """
        try:
            payload = jwt.decode(
                token,
                self._secret_key,
                algorithms=[self._algorithm],
            )

            return TokenPayload(
                sub=payload.get("sub"),
                exp=datetime.fromtimestamp(payload.get("exp"), tz=timezone.utc),
                iat=datetime.fromtimestamp(payload.get("iat"), tz=timezone.utc),
                type=payload.get("type"),
                email=payload.get("email"),
                role=payload.get("role"),
            )
        except JWTError:
            return None

    def verify_access_token(self, token: str) -> Optional[TokenPayload]:
        """
        Verify an access token.

        Args:
            token: JWT token to verify

        Returns:
            TokenPayload if valid access token, None otherwise
        """
        payload = self.decode_token(token)
        if payload and payload.type == "access":
            return payload
        return None

    def verify_refresh_token(self, token: str) -> Optional[TokenPayload]:
        """
        Verify a refresh token.

        Args:
            token: JWT token to verify

        Returns:
            TokenPayload if valid refresh token, None otherwise
        """
        payload = self.decode_token(token)
        if payload and payload.type == "refresh":
            return payload
        return None

    def create_email_verification_token(self, user_id: str, email: str) -> str:
        """
        Create an email verification token.

        Args:
            user_id: User ID
            email: Email to verify

        Returns:
            Encoded JWT token for email verification
        """
        now = datetime.now(timezone.utc)
        expire = now + timedelta(hours=24)

        payload = {
            "sub": user_id,
            "email": email,
            "exp": expire,
            "iat": now,
            "type": "email_verification",
        }

        return jwt.encode(payload, self._secret_key, algorithm=self._algorithm)

    def create_password_reset_token(self, user_id: str) -> str:
        """
        Create a password reset token.

        Args:
            user_id: User ID

        Returns:
            Encoded JWT token for password reset
        """
        now = datetime.now(timezone.utc)
        expire = now + timedelta(hours=1)

        payload = {
            "sub": user_id,
            "exp": expire,
            "iat": now,
            "type": "password_reset",
        }

        return jwt.encode(payload, self._secret_key, algorithm=self._algorithm)

    def verify_email_verification_token(
        self, token: str
    ) -> Optional[tuple[str, str]]:
        """
        Verify an email verification token.

        Args:
            token: JWT token to verify

        Returns:
            Tuple of (user_id, email) if valid, None otherwise
        """
        try:
            payload = jwt.decode(
                token,
                self._secret_key,
                algorithms=[self._algorithm],
            )

            if payload.get("type") != "email_verification":
                return None

            return payload.get("sub"), payload.get("email")
        except JWTError:
            return None

    def verify_password_reset_token(self, token: str) -> Optional[str]:
        """
        Verify a password reset token.

        Args:
            token: JWT token to verify

        Returns:
            User ID if valid, None otherwise
        """
        try:
            payload = jwt.decode(
                token,
                self._secret_key,
                algorithms=[self._algorithm],
            )

            if payload.get("type") != "password_reset":
                return None

            return payload.get("sub")
        except JWTError:
            return None
