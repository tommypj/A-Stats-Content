"""
Integration tests for billing API routes.

Tests all billing endpoints including:
- Pricing information
- Subscription status
- Checkout session creation
- Customer portal access
- Subscription cancellation
- Webhook event processing
"""

import pytest
import hmac
import hashlib
import json
from datetime import datetime, date, timedelta
from unittest.mock import AsyncMock, patch, Mock
from uuid import uuid4

from fastapi import status
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.database.models import User
from infrastructure.database.models.user import SubscriptionTier

# Skip all tests if billing routes are not available
try:
    from api.routes import billing
    BILLING_AVAILABLE = True
except (ImportError, AttributeError):
    BILLING_AVAILABLE = False
    pytestmark = pytest.mark.skip(reason="Billing routes not implemented yet")


class TestPricingEndpoint:
    """Tests for GET /billing/pricing endpoint."""

    @pytest.mark.asyncio
    async def test_get_pricing_returns_all_plans(self, async_client: AsyncClient):
        """Test that pricing endpoint returns all 4 subscription plans."""
        if not BILLING_AVAILABLE:
            pytest.skip("Billing routes not available")

        response = await async_client.get("/api/v1/billing/pricing")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "plans" in data
        assert len(data["plans"]) == 4  # Free, Starter, Professional, Enterprise

        # Verify plan structure
        plan = data["plans"][0]
        assert "name" in plan
        assert "tier" in plan
        assert "monthly_price" in plan
        assert "yearly_price" in plan
        assert "features" in plan
        assert "variant_id_monthly" in plan
        assert "variant_id_yearly" in plan

    @pytest.mark.asyncio
    async def test_pricing_no_auth_required(self, async_client: AsyncClient):
        """Test that pricing endpoint works without authentication."""
        if not BILLING_AVAILABLE:
            pytest.skip("Billing routes not available")

        # Call without auth headers
        response = await async_client.get("/api/v1/billing/pricing")

        assert response.status_code == status.HTTP_200_OK


class TestSubscriptionEndpoint:
    """Tests for GET /billing/subscription endpoint."""

    @pytest.mark.asyncio
    async def test_get_subscription_authenticated(
        self,
        async_client: AsyncClient,
        test_user: User,
        auth_headers: dict,
    ):
        """Test getting subscription status with authentication."""
        if not BILLING_AVAILABLE:
            pytest.skip("Billing routes not available")

        response = await async_client.get(
            "/api/v1/billing/subscription",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "tier" in data
        assert "status" in data
        assert "expires_at" in data
        assert "features" in data

    @pytest.mark.asyncio
    async def test_get_subscription_unauthorized(self, async_client: AsyncClient):
        """Test getting subscription without authentication returns 401."""
        if not BILLING_AVAILABLE:
            pytest.skip("Billing routes not available")

        response = await async_client.get("/api/v1/billing/subscription")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_subscription_free_user(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        auth_headers: dict,
    ):
        """Test free user subscription status."""
        if not BILLING_AVAILABLE:
            pytest.skip("Billing routes not available")

        response = await async_client.get(
            "/api/v1/billing/subscription",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["tier"] == "free"
        assert data["status"] in ["active", "none"]


class TestCheckoutEndpoint:
    """Tests for POST /billing/checkout endpoint."""

    @pytest.mark.asyncio
    async def test_checkout_generates_url(
        self,
        async_client: AsyncClient,
        test_user: User,
        auth_headers: dict,
    ):
        """Test checkout endpoint generates valid checkout URL."""
        if not BILLING_AVAILABLE:
            pytest.skip("Billing routes not available")

        with patch("adapters.billing.lemonsqueezy_adapter.LemonSqueezyAdapter") as mock_adapter:
            mock_instance = Mock()
            mock_instance.get_checkout_url.return_value = "https://example.lemonsqueezy.com/checkout/test"
            mock_adapter.return_value = mock_instance

            response = await async_client.post(
                "/api/v1/billing/checkout",
                headers=auth_headers,
                json={
                    "plan": "professional",
                    "billing_cycle": "monthly",
                },
            )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert "checkout_url" in data
            assert "lemonsqueezy.com" in data["checkout_url"]

    @pytest.mark.asyncio
    async def test_checkout_invalid_plan(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
    ):
        """Test checkout with invalid plan returns 400."""
        if not BILLING_AVAILABLE:
            pytest.skip("Billing routes not available")

        response = await async_client.post(
            "/api/v1/billing/checkout",
            headers=auth_headers,
            json={
                "plan": "invalid_plan",
                "billing_cycle": "monthly",
            },
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Invalid plan" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_checkout_invalid_billing_cycle(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
    ):
        """Test checkout with invalid billing cycle returns 400."""
        if not BILLING_AVAILABLE:
            pytest.skip("Billing routes not available")

        response = await async_client.post(
            "/api/v1/billing/checkout",
            headers=auth_headers,
            json={
                "plan": "professional",
                "billing_cycle": "invalid_cycle",
            },
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Invalid billing cycle" in response.json()["detail"]


class TestCustomerPortalEndpoint:
    """Tests for GET /billing/portal endpoint."""

    @pytest.mark.asyncio
    async def test_portal_with_customer_id(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
    ):
        """Test portal access for user with customer ID."""
        if not BILLING_AVAILABLE:
            pytest.skip("Billing routes not available")

        # Create subscribed user
        from core.security import PasswordHasher
        password_hasher = PasswordHasher()

        user = User(
            id=str(uuid4()),
            email="subscribed@example.com",
            password_hash=password_hasher.hash("password123"),
            name="Subscribed User",
            subscription_tier="professional",
            lemonsqueezy_customer_id="12345",
            lemonsqueezy_subscription_id="67890",
            status="active",
            email_verified=True,
        )
        db_session.add(user)
        await db_session.commit()

        # Generate auth token
        from core.security import TokenService
        from infrastructure.config import get_settings
        settings = get_settings()
        token_service = TokenService(secret_key=settings.secret_key)
        access_token = token_service.create_access_token(user_id=user.id)
        headers = {"Authorization": f"Bearer {access_token}"}

        with patch("adapters.billing.lemonsqueezy_adapter.LemonSqueezyAdapter") as mock_adapter:
            mock_instance = AsyncMock()
            mock_instance.get_customer_portal_url.return_value = "https://example.lemonsqueezy.com/portal"
            mock_adapter.return_value = mock_instance

            response = await async_client.get(
                "/api/v1/billing/portal",
                headers=headers,
            )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert "portal_url" in data
            assert "lemonsqueezy.com" in data["portal_url"]

    @pytest.mark.asyncio
    async def test_portal_without_customer_id(
        self,
        async_client: AsyncClient,
        test_user: User,
        auth_headers: dict,
    ):
        """Test portal access for user without customer ID returns 404."""
        if not BILLING_AVAILABLE:
            pytest.skip("Billing routes not available")

        response = await async_client.get(
            "/api/v1/billing/portal",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "No active subscription" in response.json()["detail"]


class TestCancelEndpoint:
    """Tests for POST /billing/cancel endpoint."""

    @pytest.mark.asyncio
    async def test_cancel_active_subscription(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
    ):
        """Test cancelling an active subscription."""
        if not BILLING_AVAILABLE:
            pytest.skip("Billing routes not available")

        # Create subscribed user
        from core.security import PasswordHasher
        password_hasher = PasswordHasher()

        user = User(
            id=str(uuid4()),
            email="subscribed2@example.com",
            password_hash=password_hasher.hash("password123"),
            name="Subscribed User 2",
            subscription_tier="professional",
            lemonsqueezy_customer_id="12345",
            lemonsqueezy_subscription_id="67890",
            subscription_status="active",
            status="active",
            email_verified=True,
        )
        db_session.add(user)
        await db_session.commit()

        # Generate auth token
        from core.security import TokenService
        from infrastructure.config import get_settings
        settings = get_settings()
        token_service = TokenService(secret_key=settings.secret_key)
        access_token = token_service.create_access_token(user_id=user.id)
        headers = {"Authorization": f"Bearer {access_token}"}

        with patch("adapters.billing.lemonsqueezy_adapter.LemonSqueezyAdapter") as mock_adapter:
            mock_instance = AsyncMock()
            mock_instance.cancel_subscription.return_value = {
                "status": "cancelled",
                "cancelled": True,
                "ends_at": "2024-02-01T00:00:00.000000Z",
            }
            mock_adapter.return_value = mock_instance

            response = await async_client.post(
                "/api/v1/billing/cancel",
                headers=headers,
            )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert "cancelled_at" in data
            assert data["status"] == "cancelled"

    @pytest.mark.asyncio
    async def test_cancel_no_subscription(
        self,
        async_client: AsyncClient,
        test_user: User,
        auth_headers: dict,
    ):
        """Test cancelling when user has no subscription returns 404."""
        if not BILLING_AVAILABLE:
            pytest.skip("Billing routes not available")

        response = await async_client.post(
            "/api/v1/billing/cancel",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "No active subscription" in response.json()["detail"]


class TestWebhookEndpoint:
    """Tests for POST /billing/webhook endpoint."""

    def generate_signature(self, payload: dict, secret: str) -> str:
        """Generate valid HMAC signature for webhook payload."""
        payload_bytes = json.dumps(payload).encode()
        return hmac.new(
            secret.encode(),
            payload_bytes,
            hashlib.sha256
        ).hexdigest()

    @pytest.mark.asyncio
    async def test_webhook_valid_signature(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
    ):
        """Test webhook with valid signature processes event."""
        if not BILLING_AVAILABLE:
            pytest.skip("Billing routes not available")

        payload = {
            "meta": {
                "event_name": "subscription_created",
                "custom_data": {"user_id": str(uuid4())},
            },
            "data": {
                "type": "subscriptions",
                "id": "1",
                "attributes": {
                    "customer_id": 1,
                    "variant_id": 1,
                    "status": "active",
                },
            },
        }

        with patch("infrastructure.config.settings.settings") as mock_settings:
            mock_settings.lemonsqueezy_webhook_secret = "test_secret"
            signature = self.generate_signature(payload, "test_secret")

            response = await async_client.post(
                "/api/v1/billing/webhook",
                json=payload,
                headers={"X-Signature": signature},
            )

            assert response.status_code == status.HTTP_200_OK

    @pytest.mark.asyncio
    async def test_webhook_invalid_signature(
        self,
        async_client: AsyncClient,
    ):
        """Test webhook with invalid signature returns 401."""
        if not BILLING_AVAILABLE:
            pytest.skip("Billing routes not available")

        payload = {
            "meta": {"event_name": "subscription_created"},
            "data": {"type": "subscriptions"},
        }

        response = await async_client.post(
            "/api/v1/billing/webhook",
            json=payload,
            headers={"X-Signature": "invalid_signature"},
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Invalid signature" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_webhook_subscription_created(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
    ):
        """Test subscription_created webhook creates/updates user subscription."""
        if not BILLING_AVAILABLE:
            pytest.skip("Billing routes not available")

        # Create test user
        from core.security import PasswordHasher
        password_hasher = PasswordHasher()

        user = User(
            id=str(uuid4()),
            email="webhook@example.com",
            password_hash=password_hasher.hash("password123"),
            name="Webhook Test User",
            status="active",
            email_verified=True,
        )
        db_session.add(user)
        await db_session.commit()

        payload = {
            "meta": {
                "event_name": "subscription_created",
                "custom_data": {"user_id": user.id},
            },
            "data": {
                "type": "subscriptions",
                "id": "12345",
                "attributes": {
                    "customer_id": 67890,
                    "variant_id": 1,
                    "status": "active",
                    "product_name": "Professional Plan",
                },
            },
        }

        with patch("infrastructure.config.settings.settings") as mock_settings:
            mock_settings.lemonsqueezy_webhook_secret = "test_secret"
            signature = self.generate_signature(payload, "test_secret")

            response = await async_client.post(
                "/api/v1/billing/webhook",
                json=payload,
                headers={"X-Signature": signature},
            )

            assert response.status_code == status.HTTP_200_OK

            # Verify user was updated
            await db_session.refresh(user)
            assert user.lemonsqueezy_subscription_id == "12345"
            assert user.lemonsqueezy_customer_id == "67890"
            assert user.subscription_status == "active"

    @pytest.mark.asyncio
    async def test_webhook_subscription_cancelled(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
    ):
        """Test subscription_cancelled webhook updates user status."""
        if not BILLING_AVAILABLE:
            pytest.skip("Billing routes not available")

        # Create subscribed user
        from core.security import PasswordHasher
        password_hasher = PasswordHasher()

        user = User(
            id=str(uuid4()),
            email="webhook2@example.com",
            password_hash=password_hasher.hash("password123"),
            name="Webhook Test User 2",
            subscription_tier="professional",
            lemonsqueezy_customer_id="12345",
            lemonsqueezy_subscription_id="67890",
            subscription_status="active",
            status="active",
            email_verified=True,
        )
        db_session.add(user)
        await db_session.commit()

        payload = {
            "meta": {
                "event_name": "subscription_cancelled",
                "custom_data": {"user_id": user.id},
            },
            "data": {
                "type": "subscriptions",
                "id": "67890",
                "attributes": {
                    "status": "cancelled",
                    "cancelled": True,
                    "ends_at": "2024-02-01T00:00:00.000000Z",
                },
            },
        }

        with patch("infrastructure.config.settings.settings") as mock_settings:
            mock_settings.lemonsqueezy_webhook_secret = "test_secret"
            signature = self.generate_signature(payload, "test_secret")

            response = await async_client.post(
                "/api/v1/billing/webhook",
                json=payload,
                headers={"X-Signature": signature},
            )

            assert response.status_code == status.HTTP_200_OK

            # Verify user was updated
            await db_session.refresh(user)
            assert user.subscription_status == "cancelled"

    @pytest.mark.asyncio
    async def test_webhook_payment_failed(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
    ):
        """Test payment_failed webhook updates user status to past_due."""
        if not BILLING_AVAILABLE:
            pytest.skip("Billing routes not available")

        # Create subscribed user
        from core.security import PasswordHasher
        password_hasher = PasswordHasher()

        user = User(
            id=str(uuid4()),
            email="webhook3@example.com",
            password_hash=password_hasher.hash("password123"),
            name="Webhook Test User 3",
            subscription_tier="professional",
            lemonsqueezy_customer_id="12345",
            lemonsqueezy_subscription_id="67890",
            subscription_status="active",
            status="active",
            email_verified=True,
        )
        db_session.add(user)
        await db_session.commit()

        payload = {
            "meta": {
                "event_name": "order_payment_failed",
                "custom_data": {"user_id": user.id},
            },
            "data": {
                "type": "orders",
                "id": "1",
                "attributes": {
                    "customer_id": 12345,
                    "status": "failed",
                },
            },
        }

        with patch("infrastructure.config.settings.settings") as mock_settings:
            mock_settings.lemonsqueezy_webhook_secret = "test_secret"
            signature = self.generate_signature(payload, "test_secret")

            response = await async_client.post(
                "/api/v1/billing/webhook",
                json=payload,
                headers={"X-Signature": signature},
            )

            assert response.status_code == status.HTTP_200_OK

            # Verify user status changed to past_due
            await db_session.refresh(user)
            assert user.subscription_status == "past_due"


class TestPauseResumeEndpoints:
    """Tests for subscription pause/resume functionality."""

    @pytest.mark.asyncio
    async def test_pause_subscription(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
    ):
        """Test pausing an active subscription."""
        if not BILLING_AVAILABLE:
            pytest.skip("Billing routes not available")

        # Create subscribed user
        from core.security import PasswordHasher
        password_hasher = PasswordHasher()

        user = User(
            id=str(uuid4()),
            email="pause@example.com",
            password_hash=password_hasher.hash("password123"),
            name="Pause Test User",
            subscription_tier="professional",
            lemonsqueezy_customer_id="12345",
            lemonsqueezy_subscription_id="67890",
            subscription_status="active",
            status="active",
            email_verified=True,
        )
        db_session.add(user)
        await db_session.commit()

        # Generate auth token
        from core.security import TokenService
        from infrastructure.config import get_settings
        settings = get_settings()
        token_service = TokenService(secret_key=settings.secret_key)
        access_token = token_service.create_access_token(user_id=user.id)
        headers = {"Authorization": f"Bearer {access_token}"}

        with patch("adapters.billing.lemonsqueezy_adapter.LemonSqueezyAdapter") as mock_adapter:
            mock_instance = AsyncMock()
            mock_instance.pause_subscription.return_value = {
                "status": "active",
                "pause": {"mode": "void", "resumes_at": "2024-02-01"},
            }
            mock_adapter.return_value = mock_instance

            response = await async_client.post(
                "/api/v1/billing/pause",
                headers=headers,
                json={"mode": "void"},
            )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["paused"] is True

    @pytest.mark.asyncio
    async def test_resume_subscription(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
    ):
        """Test resuming a paused subscription."""
        if not BILLING_AVAILABLE:
            pytest.skip("Billing routes not available")

        # Create paused user
        from core.security import PasswordHasher
        password_hasher = PasswordHasher()

        user = User(
            id=str(uuid4()),
            email="resume@example.com",
            password_hash=password_hasher.hash("password123"),
            name="Resume Test User",
            subscription_tier="professional",
            lemonsqueezy_customer_id="12345",
            lemonsqueezy_subscription_id="67890",
            subscription_status="active",
            status="active",
            email_verified=True,
        )
        db_session.add(user)
        await db_session.commit()

        # Generate auth token
        from core.security import TokenService
        from infrastructure.config import get_settings
        settings = get_settings()
        token_service = TokenService(secret_key=settings.secret_key)
        access_token = token_service.create_access_token(user_id=user.id)
        headers = {"Authorization": f"Bearer {access_token}"}

        with patch("adapters.billing.lemonsqueezy_adapter.LemonSqueezyAdapter") as mock_adapter:
            mock_instance = AsyncMock()
            mock_instance.resume_subscription.return_value = {
                "status": "active",
                "pause": None,
            }
            mock_adapter.return_value = mock_instance

            response = await async_client.post(
                "/api/v1/billing/resume",
                headers=headers,
            )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["resumed"] is True
