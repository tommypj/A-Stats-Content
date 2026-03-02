"""
JWT token service for authentication.
"""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from jose import JWTError, jwt


@dataclass
class TokenPayload:
    """JWT token payload structure."""

    sub: str  # Subject (user ID)
    exp: datetime  # Expiration time
    iat: datetime  # Issued at
    type: str  # Token type: "access" or "refresh"
    email: str | None = None
    role: str | None = None


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
        email: str | None = None,
        role: str | None = None,
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
        now = datetime.now(UTC)
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

    def create_refresh_token(self, user_id: str, expire_days: int | None = None) -> str:
        """
        Create a refresh token.

        Args:
            user_id: User ID to encode in the token
            expire_days: Override expiration in days. Defaults to the service-level
                ``refresh_token_expire_days`` setting.

        Returns:
            Encoded JWT refresh token
        """
        now = datetime.now(UTC)
        days = expire_days if expire_days is not None else self._refresh_token_expire_days
        expire = now + timedelta(days=days)

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
        email: str | None = None,
        role: str | None = None,
        refresh_expire_days: int | None = None,
    ) -> tuple[str, str]:
        """
        Create both access and refresh tokens.

        Args:
            user_id: User ID to encode in the tokens
            email: Optional email to include in access token
            role: Optional role to include in access token
            refresh_expire_days: Override refresh token expiry in days (e.g. 30 for
                "remember me" sessions). Defaults to the service-level setting.

        Returns:
            Tuple of (access_token, refresh_token)
        """
        access_token = self.create_access_token(user_id, email, role)
        refresh_token = self.create_refresh_token(user_id, expire_days=refresh_expire_days)
        return access_token, refresh_token

    def decode_token(self, token: str) -> TokenPayload | None:
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

            # INFRA-AUTH-01: Validate required fields exist before accessing them
            required_fields = ["sub", "exp", "type"]
            for field in required_fields:
                if field not in payload:
                    raise JWTError(f"Missing required field: {field}")

            return TokenPayload(
                sub=payload.get("sub"),
                exp=datetime.fromtimestamp(payload.get("exp"), tz=UTC),
                iat=datetime.fromtimestamp(payload.get("iat", 0), tz=UTC),
                type=payload.get("type"),
                email=payload.get("email"),
                role=payload.get("role"),
            )
        except JWTError:
            return None

    def verify_access_token(self, token: str) -> TokenPayload | None:
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

    def verify_refresh_token(self, token: str) -> TokenPayload | None:
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
        now = datetime.now(UTC)
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
        now = datetime.now(UTC)
        expire = now + timedelta(hours=1)

        payload = {
            "sub": user_id,
            "exp": expire,
            "iat": now,
            "type": "password_reset",
        }

        return jwt.encode(payload, self._secret_key, algorithm=self._algorithm)

    def verify_email_verification_token(self, token: str) -> tuple[str, str] | None:
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

    def verify_password_reset_token(self, token: str) -> str | None:
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
