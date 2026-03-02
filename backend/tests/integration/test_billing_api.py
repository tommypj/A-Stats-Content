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

import hashlib
import hmac
import json
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from fastapi import status
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.database.models import User

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

        # Verify plan structure - matches PlanInfo schema fields
        plan = data["plans"][0]
        assert "name" in plan
        assert "id" in plan
        assert "price_monthly" in plan
        assert "price_yearly" in plan
        assert "features" in plan
        assert "limits" in plan

    @pytest.mark.asyncio
    async def test_pricing_no_auth_required(self, async_client: AsyncClient):
        """Test that pricing endpoint works without authentication."""
        if not BILLING_AVAILABLE:
            pytest.skip("Billing routes not available")

        # Call without auth headers
        response = await async_client.get("/api/v1/billing/pricing")

        assert response.status_code == status.HTTP_200_OK


class TestSubscriptionEndpoint:
    """Tests for GET /billing/subscription endpoint.

    SubscriptionStatus schema fields:
    subscription_tier, subscription_status, subscription_expires,
    customer_id, subscription_id, can_manage,
    articles_generated_this_month, outlines_generated_this_month,
    images_generated_this_month, usage_reset_date.

    Note: There is NO 'tier', 'status', 'expires_at', or 'features' field.
    """

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
        # Actual schema field names
        assert "subscription_tier" in data
        assert "subscription_status" in data
        assert "subscription_expires" in data
        assert "can_manage" in data

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
        assert data["subscription_tier"] == "free"
        assert data["subscription_status"] in ["active", "none"]


class TestCheckoutEndpoint:
    """Tests for POST /billing/checkout endpoint."""

    @pytest.mark.asyncio
    async def test_checkout_generates_url(
        self,
        async_client: AsyncClient,
        test_user: User,
        auth_headers: dict,
    ):
        """Test checkout endpoint generates valid checkout URL.

        The route builds the checkout URL directly from settings (no external
        adapter class). We patch 'api.routes.billing.settings' to supply all
        required config values.
        """
        if not BILLING_AVAILABLE:
            pytest.skip("Billing routes not available")

        with patch("api.routes.billing.settings") as mock_settings:
            mock_settings.lemonsqueezy_api_key = "test_api_key"
            mock_settings.lemonsqueezy_store_id = "example"
            mock_settings.lemonsqueezy_variant_professional_monthly = "variant_abc"
            mock_settings.anthropic_model = "claude-3-haiku-20240307"

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

        # Generate auth token using jwt_secret_key (same key the route uses)
        from core.security import TokenService
        from infrastructure.config import get_settings

        app_settings = get_settings()
        token_service = TokenService(secret_key=app_settings.jwt_secret_key)
        access_token = token_service.create_access_token(user_id=user.id)
        headers = {"Authorization": f"Bearer {access_token}"}

        # The portal route builds the URL from settings.lemonsqueezy_store_id
        # directly - no external adapter is called.
        with patch("api.routes.billing.settings") as mock_settings:
            mock_settings.lemonsqueezy_store_id = "example"

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
        # Actual detail: "No active subscription found"
        assert "No active subscription" in response.json()["detail"]


class TestCancelEndpoint:
    """Tests for POST /billing/cancel endpoint.

    SubscriptionCancelResponse schema: success (bool), message (str).
    There is no 'cancelled_at' or 'status' field in the response.
    The route does not call an external adapter - it validates the subscription
    ID exists then returns a success message.
    """

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

        # Generate auth token using jwt_secret_key (same key the route uses)
        from core.security import TokenService
        from infrastructure.config import get_settings

        app_settings = get_settings()
        token_service = TokenService(secret_key=app_settings.jwt_secret_key)
        access_token = token_service.create_access_token(user_id=user.id)
        headers = {"Authorization": f"Bearer {access_token}"}

        # Mock the LemonSqueezy API call so the test doesn't make a real request
        mock_ls_response = AsyncMock()
        mock_ls_response.status_code = 200

        with patch("api.routes.billing.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.delete = AsyncMock(return_value=mock_ls_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_cls.return_value = mock_client

            response = await async_client.post(
                "/api/v1/billing/cancel",
                headers=headers,
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        # SubscriptionCancelResponse has 'success' and 'message' fields
        assert "success" in data
        assert data["success"] is True
        assert "message" in data

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
        # Actual detail message from billing.py
        assert "No active subscription" in response.json()["detail"]


class TestWebhookEndpoint:
    """Tests for POST /billing/webhook endpoint."""

    def generate_signature(self, payload: dict, secret: str) -> str:
        """Generate valid HMAC signature for webhook payload.

        Uses compact JSON encoding (no spaces) to match httpx's json= parameter
        serialization, which is what the route receives as the raw request body.
        """
        payload_bytes = json.dumps(payload, separators=(",", ":")).encode()
        return hmac.new(secret.encode(), payload_bytes, hashlib.sha256).hexdigest()

    @pytest.mark.asyncio
    async def test_webhook_valid_signature(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
    ):
        """Test webhook with valid signature processes event.

        The billing route reads settings from 'api.routes.billing.settings'.
        user_id in custom_data must match an actual DB user; here we use a
        non-existent UUID so the handler returns 200 with an error message
        (the route always returns 200 to acknowledge receipt).
        """
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

        with patch("api.routes.billing.settings") as mock_settings:
            mock_settings.lemonsqueezy_webhook_secret = "test_secret"
            mock_settings.lemonsqueezy_variant_starter_monthly = None
            mock_settings.lemonsqueezy_variant_starter_yearly = None
            mock_settings.lemonsqueezy_variant_professional_monthly = None
            mock_settings.lemonsqueezy_variant_professional_yearly = None
            mock_settings.lemonsqueezy_variant_enterprise_monthly = None
            mock_settings.lemonsqueezy_variant_enterprise_yearly = None
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

        with patch("api.routes.billing.settings") as mock_settings:
            mock_settings.lemonsqueezy_webhook_secret = "test_secret"

            response = await async_client.post(
                "/api/v1/billing/webhook",
                json=payload,
                headers={"X-Signature": "invalid_signature"},
            )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        # Actual detail from billing.py: "Invalid webhook signature"
        assert "Invalid webhook signature" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_webhook_subscription_created(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
    ):
        """Test subscription_created webhook creates/updates user subscription.

        The route patches 'api.routes.billing.settings' (not the config module).
        After the webhook the user's lemonsqueezy_subscription_id and
        lemonsqueezy_customer_id are updated; the route does not set
        subscription_status on the user object directly.
        """
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

        with patch("api.routes.billing.settings") as mock_settings:
            mock_settings.lemonsqueezy_webhook_secret = "test_secret"
            mock_settings.lemonsqueezy_variant_starter_monthly = None
            mock_settings.lemonsqueezy_variant_starter_yearly = None
            mock_settings.lemonsqueezy_variant_professional_monthly = None
            mock_settings.lemonsqueezy_variant_professional_yearly = None
            mock_settings.lemonsqueezy_variant_enterprise_monthly = None
            mock_settings.lemonsqueezy_variant_enterprise_yearly = None
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

    @pytest.mark.asyncio
    async def test_webhook_subscription_cancelled(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
    ):
        """Test subscription_cancelled webhook returns 200.

        The route handles 'subscription_cancelled' by updating subscription_expires
        (if renews_at is present) but does NOT set a subscription_status column on the
        user; the User model tracks tier via subscription_tier and expiry via
        subscription_expires.
        """
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

        with patch("api.routes.billing.settings") as mock_settings:
            mock_settings.lemonsqueezy_webhook_secret = "test_secret"
            mock_settings.lemonsqueezy_variant_starter_monthly = None
            mock_settings.lemonsqueezy_variant_starter_yearly = None
            mock_settings.lemonsqueezy_variant_professional_monthly = None
            mock_settings.lemonsqueezy_variant_professional_yearly = None
            mock_settings.lemonsqueezy_variant_enterprise_monthly = None
            mock_settings.lemonsqueezy_variant_enterprise_yearly = None
            signature = self.generate_signature(payload, "test_secret")

            response = await async_client.post(
                "/api/v1/billing/webhook",
                json=payload,
                headers={"X-Signature": signature},
            )

            assert response.status_code == status.HTTP_200_OK

    @pytest.mark.asyncio
    async def test_webhook_payment_failed(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
    ):
        """Test payment_failed (subscription_payment_failed) webhook returns 200.

        The route handles 'subscription_payment_failed' by logging a warning
        but does NOT change any user field (no past_due status column).
        The event name must match WebhookEventType enum values;
        'order_payment_failed' is not a recognised event type.
        """
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
            status="active",
            email_verified=True,
        )
        db_session.add(user)
        await db_session.commit()

        payload = {
            "meta": {
                # Correct event name from WebhookEventType enum
                "event_name": "subscription_payment_failed",
                "custom_data": {"user_id": user.id},
            },
            "data": {
                "type": "subscriptions",
                "id": "67890",
                "attributes": {
                    "customer_id": 12345,
                    "status": "past_due",
                },
            },
        }

        with patch("api.routes.billing.settings") as mock_settings:
            mock_settings.lemonsqueezy_webhook_secret = "test_secret"
            mock_settings.lemonsqueezy_variant_starter_monthly = None
            mock_settings.lemonsqueezy_variant_starter_yearly = None
            mock_settings.lemonsqueezy_variant_professional_monthly = None
            mock_settings.lemonsqueezy_variant_professional_yearly = None
            mock_settings.lemonsqueezy_variant_enterprise_monthly = None
            mock_settings.lemonsqueezy_variant_enterprise_yearly = None
            signature = self.generate_signature(payload, "test_secret")

            response = await async_client.post(
                "/api/v1/billing/webhook",
                json=payload,
                headers={"X-Signature": signature},
            )

            assert response.status_code == status.HTTP_200_OK


@pytest.mark.skip(
    reason="POST /billing/pause and POST /billing/resume endpoints do not exist in billing.py"
)
class TestPauseResumeEndpoints:
    """Tests for subscription pause/resume functionality.

    These tests are skipped because the routes POST /billing/pause and
    POST /billing/resume have not been implemented in api/routes/billing.py.
    Pause/resume events are handled via LemonSqueezy webhooks only.
    """

    @pytest.mark.asyncio
    async def test_pause_subscription(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
    ):
        """Test pausing an active subscription."""
        if not BILLING_AVAILABLE:
            pytest.skip("Billing routes not available")

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
            status="active",
            email_verified=True,
        )
        db_session.add(user)
        await db_session.commit()

        from core.security import TokenService
        from infrastructure.config import get_settings

        settings = get_settings()
        token_service = TokenService(secret_key=settings.secret_key)
        access_token = token_service.create_access_token(user_id=user.id)
        headers = {"Authorization": f"Bearer {access_token}"}

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
            status="active",
            email_verified=True,
        )
        db_session.add(user)
        await db_session.commit()

        from core.security import TokenService
        from infrastructure.config import get_settings

        settings = get_settings()
        token_service = TokenService(secret_key=settings.secret_key)
        access_token = token_service.create_access_token(user_id=user.id)
        headers = {"Authorization": f"Bearer {access_token}"}

        response = await async_client.post(
            "/api/v1/billing/resume",
            headers=headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["resumed"] is True
