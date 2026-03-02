"""
Unit tests for LemonSqueezy billing adapter.

Tests the LemonSqueezy API integration including:
- Customer management
- Subscription operations
- Webhook signature verification
- Webhook payload parsing
- Checkout URL generation
- Error handling
"""

import hashlib
import hmac
from typing import Any
from unittest.mock import Mock, patch

import pytest

# These imports will work once the adapter is created
# For now, we'll use pytest.importorskip to make tests conditional
try:
    from adapters.billing.lemonsqueezy_adapter import (
        LemonSqueezyAdapter,
        LemonSqueezyAuthError,
        LemonSqueezyError,
        LemonSqueezyWebhookError,
        create_lemonsqueezy_adapter,
    )

    ADAPTER_AVAILABLE = True
except ImportError:
    ADAPTER_AVAILABLE = False
    pytestmark = pytest.mark.skip(reason="LemonSqueezy adapter not implemented yet")


@pytest.fixture
def adapter():
    """Create LemonSqueezyAdapter instance with test credentials."""
    if not ADAPTER_AVAILABLE:
        pytest.skip("LemonSqueezy adapter not available")
    return LemonSqueezyAdapter(
        api_key="test_api_key_123",
        store_id="12345",
        webhook_secret="test_webhook_secret",
    )


@pytest.fixture
def mock_customer_response() -> dict[str, Any]:
    """Mock successful customer API response."""
    return {
        "data": {
            "type": "customers",
            "id": "1",
            "attributes": {
                "store_id": 12345,
                "name": "Test User",
                "email": "test@example.com",
                "status": "active",
                "created_at": "2024-01-01T00:00:00.000000Z",
                "updated_at": "2024-01-01T00:00:00.000000Z",
            },
        }
    }


@pytest.fixture
def mock_subscription_response() -> dict[str, Any]:
    """Mock successful subscription API response."""
    return {
        "data": {
            "type": "subscriptions",
            "id": "1",
            "attributes": {
                "store_id": 12345,
                "customer_id": 1,
                "order_id": 1,
                "product_id": 1,
                "variant_id": 1,
                "product_name": "Professional Plan",
                "variant_name": "Monthly",
                "status": "active",
                "status_formatted": "Active",
                "card_brand": "visa",
                "card_last_four": "4242",
                "pause": None,
                "cancelled": False,
                "trial_ends_at": None,
                "billing_anchor": 1,
                "first_subscription_item": {
                    "id": 1,
                    "subscription_id": 1,
                    "price_id": 1,
                    "quantity": 1,
                },
                "urls": {
                    "update_payment_method": "https://example.com/update",
                    "customer_portal": "https://example.com/portal",
                },
                "renews_at": "2024-02-01T00:00:00.000000Z",
                "ends_at": None,
                "created_at": "2024-01-01T00:00:00.000000Z",
                "updated_at": "2024-01-01T00:00:00.000000Z",
            },
        }
    }


@pytest.fixture
def webhook_payload_subscription_created() -> dict[str, Any]:
    """Sample subscription_created webhook payload."""
    return {
        "meta": {
            "event_name": "subscription_created",
            "custom_data": {},
        },
        "data": {
            "type": "subscriptions",
            "id": "1",
            "attributes": {
                "store_id": 12345,
                "customer_id": 1,
                "order_id": 1,
                "product_id": 1,
                "variant_id": 1,
                "status": "active",
                "renews_at": "2024-02-01T00:00:00.000000Z",
                "created_at": "2024-01-01T00:00:00.000000Z",
                "updated_at": "2024-01-01T00:00:00.000000Z",
            },
        },
    }


@pytest.fixture
def webhook_payload_subscription_cancelled() -> dict[str, Any]:
    """Sample subscription_cancelled webhook payload."""
    return {
        "meta": {
            "event_name": "subscription_cancelled",
            "custom_data": {},
        },
        "data": {
            "type": "subscriptions",
            "id": "1",
            "attributes": {
                "store_id": 12345,
                "customer_id": 1,
                "status": "cancelled",
                "cancelled": True,
                "ends_at": "2024-02-01T00:00:00.000000Z",
            },
        },
    }


@pytest.fixture
def webhook_payload_payment_failed() -> dict[str, Any]:
    """Sample order_payment_failed webhook payload."""
    return {
        "meta": {
            "event_name": "order_payment_failed",
            "custom_data": {},
        },
        "data": {
            "type": "orders",
            "id": "1",
            "attributes": {
                "store_id": 12345,
                "customer_id": 1,
                "status": "failed",
            },
        },
    }


class TestLemonSqueezyAdapter:
    """Tests for LemonSqueezyAdapter core functionality."""

    def test_adapter_initialization(self, adapter):
        """Test adapter initialization with credentials."""
        if not ADAPTER_AVAILABLE:
            pytest.skip("LemonSqueezy adapter not available")

        assert adapter.api_key == "test_api_key_123"
        assert adapter.store_id == "12345"
        assert adapter.webhook_secret == "test_webhook_secret"
        assert adapter.base_url == "https://api.lemonsqueezy.com/v1"

    def test_adapter_initialization_with_defaults(self):
        """Test adapter initialization with settings defaults."""
        if not ADAPTER_AVAILABLE:
            pytest.skip("LemonSqueezy adapter not available")

        with patch("adapters.billing.lemonsqueezy_adapter.settings") as mock_settings:
            mock_settings.lemonsqueezy_api_key = "settings_api_key"
            mock_settings.lemonsqueezy_store_id = "67890"
            mock_settings.lemonsqueezy_webhook_secret = "settings_webhook_secret"

            adapter = LemonSqueezyAdapter()
            assert adapter.api_key == "settings_api_key"
            assert adapter.store_id == "67890"
            assert adapter.webhook_secret == "settings_webhook_secret"

    @pytest.mark.asyncio
    async def test_get_customer_success(self, adapter, mock_customer_response):
        """Test successful customer retrieval."""
        if not ADAPTER_AVAILABLE:
            pytest.skip("LemonSqueezy adapter not available")

        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_customer_response
            mock_get.return_value = mock_response

            customer = await adapter.get_customer("1")

            assert customer["id"] == "1"
            assert customer["email"] == "test@example.com"
            assert customer["name"] == "Test User"
            mock_get.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_customer_not_found(self, adapter):
        """Test customer retrieval when customer doesn't exist (404)."""
        if not ADAPTER_AVAILABLE:
            pytest.skip("LemonSqueezy adapter not available")

        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 404
            mock_response.json.return_value = {"errors": [{"detail": "Not found"}]}
            mock_get.return_value = mock_response

            with pytest.raises(LemonSqueezyError, match="Customer not found"):
                await adapter.get_customer("999")

    @pytest.mark.asyncio
    async def test_get_subscription_success(self, adapter, mock_subscription_response):
        """Test successful subscription retrieval."""
        if not ADAPTER_AVAILABLE:
            pytest.skip("LemonSqueezy adapter not available")

        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_subscription_response
            mock_get.return_value = mock_response

            subscription = await adapter.get_subscription("1")

            assert subscription["id"] == "1"
            assert subscription["status"] == "active"
            assert subscription["product_name"] == "Professional Plan"
            assert subscription["variant_name"] == "Monthly"

    @pytest.mark.asyncio
    async def test_get_subscription_not_found(self, adapter):
        """Test subscription retrieval when subscription doesn't exist (404)."""
        if not ADAPTER_AVAILABLE:
            pytest.skip("LemonSqueezy adapter not available")

        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 404
            mock_response.json.return_value = {"errors": [{"detail": "Not found"}]}
            mock_get.return_value = mock_response

            with pytest.raises(LemonSqueezyError, match="Subscription not found"):
                await adapter.get_subscription("999")

    @pytest.mark.asyncio
    async def test_get_customer_portal_url(self, adapter, mock_subscription_response):
        """Test customer portal URL generation."""
        if not ADAPTER_AVAILABLE:
            pytest.skip("LemonSqueezy adapter not available")

        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_subscription_response
            mock_get.return_value = mock_response

            portal_url = await adapter.get_customer_portal_url("1")

            assert portal_url == "https://example.com/portal"

    @pytest.mark.asyncio
    async def test_cancel_subscription_success(self, adapter):
        """Test successful subscription cancellation."""
        if not ADAPTER_AVAILABLE:
            pytest.skip("LemonSqueezy adapter not available")

        with patch("httpx.AsyncClient.delete") as mock_delete:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "data": {
                    "type": "subscriptions",
                    "id": "1",
                    "attributes": {
                        "status": "cancelled",
                        "cancelled": True,
                        "ends_at": "2024-02-01T00:00:00.000000Z",
                    },
                }
            }
            mock_delete.return_value = mock_response

            result = await adapter.cancel_subscription("1")

            assert result["status"] == "cancelled"
            assert result["cancelled"] is True
            mock_delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_cancel_subscription_already_cancelled(self, adapter):
        """Test cancellation of already cancelled subscription."""
        if not ADAPTER_AVAILABLE:
            pytest.skip("LemonSqueezy adapter not available")

        with patch("httpx.AsyncClient.delete") as mock_delete:
            mock_response = Mock()
            mock_response.status_code = 400
            mock_response.json.return_value = {
                "errors": [{"detail": "Subscription already cancelled"}]
            }
            mock_delete.return_value = mock_response

            with pytest.raises(LemonSqueezyError, match="already cancelled"):
                await adapter.cancel_subscription("1")

    @pytest.mark.asyncio
    async def test_pause_subscription_success(self, adapter):
        """Test successful subscription pause."""
        if not ADAPTER_AVAILABLE:
            pytest.skip("LemonSqueezy adapter not available")

        with patch("httpx.AsyncClient.patch") as mock_patch:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "data": {
                    "type": "subscriptions",
                    "id": "1",
                    "attributes": {
                        "status": "active",
                        "pause": {
                            "mode": "void",
                            "resumes_at": "2024-02-01T00:00:00.000000Z",
                        },
                    },
                }
            }
            mock_patch.return_value = mock_response

            result = await adapter.pause_subscription("1", mode="void")

            assert result["pause"]["mode"] == "void"
            mock_patch.assert_called_once()

    @pytest.mark.asyncio
    async def test_resume_subscription_success(self, adapter):
        """Test successful subscription resume."""
        if not ADAPTER_AVAILABLE:
            pytest.skip("LemonSqueezy adapter not available")

        with patch("httpx.AsyncClient.patch") as mock_patch:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "data": {
                    "type": "subscriptions",
                    "id": "1",
                    "attributes": {
                        "status": "active",
                        "pause": None,
                    },
                }
            }
            mock_patch.return_value = mock_response

            result = await adapter.resume_subscription("1")

            assert result["pause"] is None
            mock_patch.assert_called_once()

    def test_verify_webhook_signature_valid(self, adapter):
        """Test webhook signature verification with valid signature."""
        if not ADAPTER_AVAILABLE:
            pytest.skip("LemonSqueezy adapter not available")

        payload = b'{"event": "test"}'
        signature = hmac.new(adapter.webhook_secret.encode(), payload, hashlib.sha256).hexdigest()

        # Should not raise any exception
        adapter.verify_webhook_signature(payload, signature)

    def test_verify_webhook_signature_invalid(self, adapter):
        """Test webhook signature verification with invalid signature."""
        if not ADAPTER_AVAILABLE:
            pytest.skip("LemonSqueezy adapter not available")

        payload = b'{"event": "test"}'
        invalid_signature = "invalid_signature_hash"

        with pytest.raises(LemonSqueezyWebhookError, match="Invalid webhook signature"):
            adapter.verify_webhook_signature(payload, invalid_signature)

    def test_parse_webhook_subscription_created(
        self, adapter, webhook_payload_subscription_created
    ):
        """Test parsing subscription_created webhook event."""
        if not ADAPTER_AVAILABLE:
            pytest.skip("LemonSqueezy adapter not available")

        event = adapter.parse_webhook_payload(webhook_payload_subscription_created)

        assert event["event_name"] == "subscription_created"
        assert event["subscription_id"] == "1"
        assert event["customer_id"] == 1
        assert event["variant_id"] == 1
        assert event["status"] == "active"

    def test_parse_webhook_subscription_cancelled(
        self, adapter, webhook_payload_subscription_cancelled
    ):
        """Test parsing subscription_cancelled webhook event."""
        if not ADAPTER_AVAILABLE:
            pytest.skip("LemonSqueezy adapter not available")

        event = adapter.parse_webhook_payload(webhook_payload_subscription_cancelled)

        assert event["event_name"] == "subscription_cancelled"
        assert event["subscription_id"] == "1"
        assert event["status"] == "cancelled"
        assert event["cancelled"] is True

    def test_parse_webhook_payment_failed(self, adapter, webhook_payload_payment_failed):
        """Test parsing payment_failed webhook event."""
        if not ADAPTER_AVAILABLE:
            pytest.skip("LemonSqueezy adapter not available")

        event = adapter.parse_webhook_payload(webhook_payload_payment_failed)

        assert event["event_name"] == "order_payment_failed"
        assert event["customer_id"] == 1
        assert event["status"] == "failed"

    def test_get_checkout_url(self, adapter):
        """Test checkout URL generation with correct parameters."""
        if not ADAPTER_AVAILABLE:
            pytest.skip("LemonSqueezy adapter not available")

        variant_id = "12345"
        checkout_data = {
            "email": "test@example.com",
            "name": "Test User",
        }

        checkout_url = adapter.get_checkout_url(
            variant_id=variant_id,
            checkout_data=checkout_data,
        )

        assert "lemonsqueezy.com/checkout" in checkout_url
        assert variant_id in checkout_url
        assert "email=test@example.com" in checkout_url

    @pytest.mark.asyncio
    async def test_api_error_handling(self, adapter):
        """Test graceful handling of API errors."""
        if not ADAPTER_AVAILABLE:
            pytest.skip("LemonSqueezy adapter not available")

        with patch("httpx.AsyncClient.get") as mock_get:
            # Simulate network error
            import httpx

            mock_get.side_effect = httpx.HTTPError("Network error")

            with pytest.raises(LemonSqueezyError, match="API request failed"):
                await adapter.get_customer("1")

    @pytest.mark.asyncio
    async def test_api_authentication_error(self, adapter):
        """Test handling of authentication errors (401)."""
        if not ADAPTER_AVAILABLE:
            pytest.skip("LemonSqueezy adapter not available")

        with patch("httpx.AsyncClient.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 401
            mock_response.json.return_value = {"errors": [{"detail": "Unauthorized"}]}
            mock_get.return_value = mock_response

            with pytest.raises(LemonSqueezyAuthError, match="Authentication failed"):
                await adapter.get_customer("1")

    def test_create_lemonsqueezy_adapter_factory(self):
        """Test factory function for creating adapter."""
        if not ADAPTER_AVAILABLE:
            pytest.skip("LemonSqueezy adapter not available")

        adapter = create_lemonsqueezy_adapter(
            api_key="factory_api_key",
            store_id="99999",
            webhook_secret="factory_webhook_secret",
        )

        assert isinstance(adapter, LemonSqueezyAdapter)
        assert adapter.api_key == "factory_api_key"
        assert adapter.store_id == "99999"
        assert adapter.webhook_secret == "factory_webhook_secret"
