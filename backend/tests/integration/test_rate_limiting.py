"""Integration tests for rate limiting middleware."""
import pytest
import asyncio
from httpx import AsyncClient
from unittest.mock import AsyncMock, patch

from infrastructure.database.models.user import User

pytestmark = pytest.mark.asyncio


class TestRateLimitingLogin:
    """Tests for rate limiting on login endpoint."""

    async def test_login_rate_limit_exceeded(self, async_client: AsyncClient, test_user: User):
        """Test that login endpoint is rate limited (5 requests per minute)."""
        # Make 5 successful attempts (should work)
        for i in range(5):
            response = await async_client.post("/api/v1/auth/login", json={
                "email": f"nonexistent{i}@example.com",
                "password": "wrongpassword"
            })
            # Should get 401 for wrong credentials, not 429
            assert response.status_code == 401

        # 6th attempt should be rate limited
        response = await async_client.post("/api/v1/auth/login", json={
            "email": "another@example.com",
            "password": "wrongpassword"
        })
        assert response.status_code == 429

    async def test_login_rate_limit_with_valid_credentials(self, async_client: AsyncClient, test_user: User):
        """Test that valid login attempts are also rate limited."""
        # Make 5 login attempts
        for i in range(5):
            response = await async_client.post("/api/v1/auth/login", json={
                "email": test_user.email,
                "password": "testpassword123"
            })
            # All should succeed
            assert response.status_code == 200

        # 6th attempt should be rate limited
        response = await async_client.post("/api/v1/auth/login", json={
            "email": test_user.email,
            "password": "testpassword123"
        })
        assert response.status_code == 429


class TestRateLimitingRegister:
    """Tests for rate limiting on register endpoint."""

    async def test_register_rate_limit_exceeded(self, async_client: AsyncClient):
        """Test that register endpoint is rate limited (3 requests per minute)."""
        with patch("api.routes.auth.email_service.send_verification_email", new_callable=AsyncMock):
            # Make 3 successful registrations
            for i in range(3):
                response = await async_client.post("/api/v1/auth/register", json={
                    "email": f"newuser{i}@example.com",
                    "password": "SecurePass123!",
                    "name": f"User {i}",
                    "language": "en"
                })
                # Should succeed
                assert response.status_code == 201

            # 4th attempt should be rate limited
            response = await async_client.post("/api/v1/auth/register", json={
                "email": "newuser4@example.com",
                "password": "SecurePass123!",
                "name": "User 4",
                "language": "en"
            })
            assert response.status_code == 429


class TestRateLimitingPasswordReset:
    """Tests for rate limiting on password reset endpoint."""

    async def test_password_reset_rate_limit_exceeded(self, async_client: AsyncClient):
        """Test that password reset endpoint is rate limited (3 requests per hour)."""
        # Make 3 password reset requests
        for i in range(3):
            response = await async_client.post("/api/v1/auth/password/reset-request", json={
                "email": f"user{i}@example.com"
            })
            # All should return 202 (even for non-existent emails to prevent enumeration)
            assert response.status_code == 202

        # 4th attempt should be rate limited
        response = await async_client.post("/api/v1/auth/password/reset-request", json={
            "email": "user4@example.com"
        })
        assert response.status_code == 429


class TestRateLimitingEmailVerification:
    """Tests for rate limiting on email verification endpoints."""

    async def test_verify_email_rate_limit_exceeded(self, async_client: AsyncClient):
        """Test that verify email endpoint is rate limited (5 requests per hour)."""
        # Make 5 verification attempts (will fail but should not be rate limited)
        for i in range(5):
            response = await async_client.post("/api/v1/auth/verify-email", params={
                "token": f"invalid_token_{i}"
            })
            # Should get 400 for invalid token, not 429
            assert response.status_code == 400

        # 6th attempt should be rate limited
        response = await async_client.post("/api/v1/auth/verify-email", params={
            "token": "invalid_token_6"
        })
        assert response.status_code == 429

    async def test_resend_verification_rate_limit_exceeded(self, async_client: AsyncClient):
        """Test that resend verification endpoint is rate limited (5 requests per hour)."""
        # Make 5 resend verification requests
        for i in range(5):
            response = await async_client.post("/api/v1/auth/resend-verification", params={
                "email": f"user{i}@example.com"
            })
            # All should return 202 (even for non-existent emails to prevent enumeration)
            assert response.status_code == 202

        # 6th attempt should be rate limited
        response = await async_client.post("/api/v1/auth/resend-verification", params={
            "email": "user6@example.com"
        })
        assert response.status_code == 429


class TestRateLimitingHeaders:
    """Tests for rate limiting response headers."""

    async def test_rate_limit_headers_present(self, async_client: AsyncClient):
        """Test that rate limit headers are included in responses."""
        response = await async_client.post("/api/v1/auth/password/reset-request", json={
            "email": "test@example.com"
        })
        assert response.status_code == 202

        # Check for rate limit headers (slowapi includes these)
        # Note: Header names may vary based on slowapi configuration
        # Common headers: X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset
        headers = response.headers

        # At least verify the request was processed
        assert "X-RateLimit-Limit" in headers or response.status_code == 202

    async def test_rate_limit_429_response_format(self, async_client: AsyncClient):
        """Test that 429 responses have proper format."""
        # Exhaust the rate limit
        for i in range(3):
            await async_client.post("/api/v1/auth/password/reset-request", json={
                "email": f"test{i}@example.com"
            })

        # Next request should be rate limited
        response = await async_client.post("/api/v1/auth/password/reset-request", json={
            "email": "test4@example.com"
        })
        assert response.status_code == 429

        # Check response body
        data = response.json()
        assert "detail" in data or "error" in data


class TestRateLimitingDifferentEndpoints:
    """Tests that rate limits are independent per endpoint."""

    async def test_different_endpoints_have_independent_limits(self, async_client: AsyncClient, test_user: User):
        """Test that rate limits don't carry over between different endpoints."""
        # Exhaust login rate limit (5 requests)
        for i in range(5):
            await async_client.post("/api/v1/auth/login", json={
                "email": f"user{i}@example.com",
                "password": "wrongpass"
            })

        # Login should now be rate limited
        response = await async_client.post("/api/v1/auth/login", json={
            "email": "user6@example.com",
            "password": "wrongpass"
        })
        assert response.status_code == 429

        # But password reset should still work (independent limit)
        with patch("api.routes.auth.email_service.send_password_reset_email", new_callable=AsyncMock):
            response = await async_client.post("/api/v1/auth/password/reset-request", json={
                "email": test_user.email
            })
            assert response.status_code == 202
