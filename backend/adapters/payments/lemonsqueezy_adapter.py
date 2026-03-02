"""
LemonSqueezy billing adapter for subscription management.

Provides integration with LemonSqueezy API for handling subscriptions,
customer management, webhook events, and checkout URL generation.
"""

import hashlib
import hmac
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlencode

import httpx

from infrastructure.config.settings import settings

logger = logging.getLogger(__name__)


# Custom Exceptions
class LemonSqueezyError(Exception):
    """Base exception for LemonSqueezy adapter errors."""

    pass


class LemonSqueezyAPIError(LemonSqueezyError):
    """Raised when LemonSqueezy API returns an error."""

    pass


class LemonSqueezyWebhookError(LemonSqueezyError):
    """Raised when webhook verification or processing fails."""

    pass


class LemonSqueezyAuthError(LemonSqueezyError):
    """Raised when API authentication fails."""

    pass


# Dataclasses
@dataclass
class LemonSqueezyCustomer:
    """LemonSqueezy customer information."""

    id: str
    email: str
    name: str
    status: str
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_api_response(cls, data: dict[str, Any]) -> "LemonSqueezyCustomer":
        """Create customer from API response data."""
        attributes = data.get("attributes", {})
        return cls(
            id=data.get("id", ""),
            email=attributes.get("email", ""),
            name=attributes.get("name", ""),
            status=attributes.get("status", ""),
            created_at=datetime.fromisoformat(
                attributes.get("created_at", "").replace("Z", "+00:00")
            ),
            updated_at=datetime.fromisoformat(
                attributes.get("updated_at", "").replace("Z", "+00:00")
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert customer to dictionary format."""
        return {
            "id": self.id,
            "email": self.email,
            "name": self.name,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


@dataclass
class LemonSqueezySubscription:
    """LemonSqueezy subscription information."""

    id: str
    customer_id: str
    variant_id: str
    status: str  # active, cancelled, paused, past_due, expired
    current_period_end: datetime
    renews_at: datetime | None
    ends_at: datetime | None
    trial_ends_at: datetime | None
    created_at: datetime
    updated_at: datetime
    card_brand: str | None
    card_last_four: str | None

    @classmethod
    def from_api_response(cls, data: dict[str, Any]) -> "LemonSqueezySubscription":
        """Create subscription from API response data."""
        attributes = data.get("attributes", {})
        relationships = data.get("relationships", {})

        # Extract customer ID from relationships
        customer_data = relationships.get("customer", {}).get("data", {})
        customer_id = customer_data.get("id", "")

        # Extract variant ID from relationships
        variant_data = relationships.get("variant", {}).get("data", {})
        variant_id = variant_data.get("id", "")

        return cls(
            id=data.get("id", ""),
            customer_id=customer_id,
            variant_id=variant_id,
            status=attributes.get("status", ""),
            current_period_end=datetime.fromisoformat(
                attributes.get("renews_at", "").replace("Z", "+00:00")
            )
            if attributes.get("renews_at")
            else datetime.now(UTC),
            renews_at=datetime.fromisoformat(attributes.get("renews_at", "").replace("Z", "+00:00"))
            if attributes.get("renews_at")
            else None,
            ends_at=datetime.fromisoformat(attributes.get("ends_at", "").replace("Z", "+00:00"))
            if attributes.get("ends_at")
            else None,
            trial_ends_at=datetime.fromisoformat(
                attributes.get("trial_ends_at", "").replace("Z", "+00:00")
            )
            if attributes.get("trial_ends_at")
            else None,
            created_at=datetime.fromisoformat(
                attributes.get("created_at", "").replace("Z", "+00:00")
            ),
            updated_at=datetime.fromisoformat(
                attributes.get("updated_at", "").replace("Z", "+00:00")
            ),
            card_brand=attributes.get("card_brand"),
            card_last_four=attributes.get("card_last_four"),
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert subscription to dictionary format."""
        return {
            "id": self.id,
            "customer_id": self.customer_id,
            "variant_id": self.variant_id,
            "status": self.status,
            "current_period_end": self.current_period_end.isoformat(),
            "renews_at": self.renews_at.isoformat() if self.renews_at else None,
            "ends_at": self.ends_at.isoformat() if self.ends_at else None,
            "trial_ends_at": self.trial_ends_at.isoformat() if self.trial_ends_at else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "card_brand": self.card_brand,
            "card_last_four": self.card_last_four,
        }


@dataclass
class WebhookEvent:
    """LemonSqueezy webhook event data."""

    event_name: str  # subscription_created, subscription_updated, etc.
    subscription_id: str | None
    customer_id: str | None
    variant_id: str | None
    status: str | None
    data: dict[str, Any]

    @classmethod
    def from_webhook_payload(cls, payload: dict[str, Any]) -> "WebhookEvent":
        """Create webhook event from payload."""
        meta = payload.get("meta", {})
        event_name = meta.get("event_name", "")

        data = payload.get("data", {})
        attributes = data.get("attributes", {})
        relationships = data.get("relationships", {})

        # Extract IDs from data
        subscription_id = data.get("id") if "subscription" in event_name else None

        customer_data = relationships.get("customer", {}).get("data", {})
        customer_id = customer_data.get("id")

        variant_data = relationships.get("variant", {}).get("data", {})
        variant_id = variant_data.get("id")

        status = attributes.get("status")

        return cls(
            event_name=event_name,
            subscription_id=subscription_id,
            customer_id=customer_id,
            variant_id=variant_id,
            status=status,
            data=payload,
        )


class LemonSqueezyAdapter:
    """
    LemonSqueezy API adapter for subscription billing.

    Provides methods for managing subscriptions, customers, webhooks,
    and checkout URL generation for the LemonSqueezy payment platform.
    """

    # API settings
    API_BASE_URL = "https://api.lemonsqueezy.com/v1"
    CHECKOUT_BASE_URL = "https://{store_slug}.lemonsqueezy.com/checkout/buy/{variant_id}"

    def __init__(
        self,
        api_key: str | None = None,
        store_id: str | None = None,
        webhook_secret: str | None = None,
    ):
        """
        Initialize LemonSqueezy adapter.

        Args:
            api_key: LemonSqueezy API key (defaults to settings)
            store_id: LemonSqueezy store ID (defaults to settings)
            webhook_secret: Webhook signing secret (defaults to settings)
        """
        self.api_key = api_key or settings.lemonsqueezy_api_key
        self.store_id = store_id or settings.lemonsqueezy_store_id
        self.webhook_secret = webhook_secret or settings.lemonsqueezy_webhook_secret

        if not self.api_key:
            logger.warning(
                "LemonSqueezy API key not configured. Set lemonsqueezy_api_key in settings."
            )

    def _get_headers(self) -> dict[str, str]:
        """Get HTTP headers for API requests."""
        if not self.api_key:
            raise LemonSqueezyAuthError(
                "LemonSqueezy API key not configured. Set lemonsqueezy_api_key in settings."
            )

        return {
            "Accept": "application/vnd.api+json",
            "Content-Type": "application/vnd.api+json",
            "Authorization": f"Bearer {self.api_key}",
        }

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Make HTTP request to LemonSqueezy API.

        Args:
            method: HTTP method (GET, POST, PATCH, DELETE)
            endpoint: API endpoint path
            data: Request body data (for POST/PATCH)

        Returns:
            API response as dictionary

        Raises:
            LemonSqueezyAPIError: If API request fails
        """
        url = f"{self.API_BASE_URL}/{endpoint}"
        headers = self._get_headers()

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                logger.info(f"Making {method} request to {endpoint}")

                if method == "GET":
                    response = await client.get(url, headers=headers)
                elif method == "POST":
                    response = await client.post(url, headers=headers, json=data)
                elif method == "PATCH":
                    response = await client.patch(url, headers=headers, json=data)
                elif method == "DELETE":
                    response = await client.delete(url, headers=headers)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")

                response.raise_for_status()

                # Handle empty responses (e.g., DELETE)
                if response.status_code == 204 or not response.content:
                    return {}

                return response.json()

        except httpx.HTTPStatusError as e:
            error_detail = ""
            try:
                error_data = e.response.json()
                errors = error_data.get("errors", [])
                if errors and isinstance(errors[0], dict):
                    error_detail = errors[0].get("detail", str(e))
            except Exception:
                error_detail = str(e)

            logger.error(f"LemonSqueezy API error: {error_detail}")
            raise LemonSqueezyAPIError(f"API request failed: {error_detail}")
        except httpx.RequestError as e:
            logger.error(f"HTTP request error: {e}")
            raise LemonSqueezyAPIError(f"Request failed: {e}")
        except Exception as e:
            logger.error(f"Unexpected error during API request: {e}")
            raise LemonSqueezyAPIError(f"API request failed: {e}")

    async def get_customer(self, customer_id: str) -> LemonSqueezyCustomer:
        """
        Get customer information by ID.

        Args:
            customer_id: LemonSqueezy customer ID

        Returns:
            LemonSqueezyCustomer object

        Raises:
            LemonSqueezyAPIError: If API request fails
        """
        logger.info(f"Fetching customer {customer_id}")
        response = await self._make_request("GET", f"customers/{customer_id}")

        data = response.get("data", {})
        return LemonSqueezyCustomer.from_api_response(data)

    async def get_subscription(self, subscription_id: str) -> LemonSqueezySubscription:
        """
        Get subscription information by ID.

        Args:
            subscription_id: LemonSqueezy subscription ID

        Returns:
            LemonSqueezySubscription object

        Raises:
            LemonSqueezyAPIError: If API request fails
        """
        logger.info(f"Fetching subscription {subscription_id}")
        response = await self._make_request("GET", f"subscriptions/{subscription_id}")

        data = response.get("data", {})
        return LemonSqueezySubscription.from_api_response(data)

    async def list_subscriptions(
        self,
        customer_id: str | None = None,
        status: str | None = None,
    ) -> list[LemonSqueezySubscription]:
        """
        List subscriptions with optional filters.

        Args:
            customer_id: Filter by customer ID
            status: Filter by status (active, cancelled, paused, past_due, expired)

        Returns:
            List of LemonSqueezySubscription objects

        Raises:
            LemonSqueezyAPIError: If API request fails
        """
        endpoint = "subscriptions"
        filters = []

        if customer_id:
            filters.append(f"filter[customer_id]={customer_id}")
        if status:
            filters.append(f"filter[status]={status}")

        if filters:
            endpoint += "?" + "&".join(filters)

        logger.info(f"Listing subscriptions with filters: {filters}")
        response = await self._make_request("GET", endpoint)

        data_list = response.get("data", [])
        return [LemonSqueezySubscription.from_api_response(item) for item in data_list]

    async def cancel_subscription(self, subscription_id: str) -> bool:
        """
        Cancel a subscription (will remain active until end of period).

        Args:
            subscription_id: LemonSqueezy subscription ID

        Returns:
            True if cancellation successful

        Raises:
            LemonSqueezyAPIError: If API request fails
        """
        logger.info(f"Cancelling subscription {subscription_id}")

        # LemonSqueezy uses DELETE to cancel subscriptions
        await self._make_request("DELETE", f"subscriptions/{subscription_id}")

        logger.info(f"Successfully cancelled subscription {subscription_id}")
        return True

    async def pause_subscription(
        self,
        subscription_id: str,
        mode: str = "void",
    ) -> LemonSqueezySubscription:
        """
        Pause a subscription.

        Args:
            subscription_id: LemonSqueezy subscription ID
            mode: Pause mode - "void" (pause immediately) or "free" (pause at period end)

        Returns:
            Updated LemonSqueezySubscription object

        Raises:
            LemonSqueezyAPIError: If API request fails
        """
        logger.info(f"Pausing subscription {subscription_id} with mode {mode}")

        data = {
            "data": {
                "type": "subscriptions",
                "id": subscription_id,
                "attributes": {
                    "pause": {
                        "mode": mode,
                    }
                },
            }
        }

        response = await self._make_request(
            "PATCH",
            f"subscriptions/{subscription_id}",
            data=data,
        )

        response_data = response.get("data", {})
        logger.info(f"Successfully paused subscription {subscription_id}")
        return LemonSqueezySubscription.from_api_response(response_data)

    async def resume_subscription(self, subscription_id: str) -> LemonSqueezySubscription:
        """
        Resume a paused subscription.

        Args:
            subscription_id: LemonSqueezy subscription ID

        Returns:
            Updated LemonSqueezySubscription object

        Raises:
            LemonSqueezyAPIError: If API request fails
        """
        logger.info(f"Resuming subscription {subscription_id}")

        data = {
            "data": {
                "type": "subscriptions",
                "id": subscription_id,
                "attributes": {
                    "pause": None,
                },
            }
        }

        response = await self._make_request(
            "PATCH",
            f"subscriptions/{subscription_id}",
            data=data,
        )

        response_data = response.get("data", {})
        logger.info(f"Successfully resumed subscription {subscription_id}")
        return LemonSqueezySubscription.from_api_response(response_data)

    async def get_customer_portal_url(self, customer_id: str) -> str:
        """
        Get customer portal URL for managing subscription.

        Args:
            customer_id: LemonSqueezy customer ID

        Returns:
            Customer portal URL

        Raises:
            LemonSqueezyAPIError: If API request fails
        """
        logger.info(f"Fetching customer portal URL for {customer_id}")

        # Fetch customer to get the portal URL from attributes
        await self.get_customer(customer_id)

        # The portal URL is typically in the customer data
        # For now, return a constructed URL (may need adjustment based on actual API)
        portal_url = "https://app.lemonsqueezy.com/my-orders"

        logger.info("Retrieved customer portal URL")
        return portal_url

    def get_checkout_url(
        self,
        variant_id: str,
        email: str,
        user_id: str,
        store_slug: str = "astats",
        custom_data: dict[str, Any] | None = None,
    ) -> str:
        """
        Generate checkout URL for a product variant.

        Args:
            variant_id: LemonSqueezy variant ID
            email: Customer email address
            user_id: User ID to include in custom data
            store_slug: Store slug (subdomain)
            custom_data: Additional custom data to pass through checkout

        Returns:
            Checkout URL
        """
        logger.info(f"Generating checkout URL for variant {variant_id}")

        # Build checkout URL base
        base_url = self.CHECKOUT_BASE_URL.format(
            store_slug=store_slug,
            variant_id=variant_id,
        )

        # Build checkout parameters
        checkout_params = {
            "checkout[email]": email,
            "checkout[custom][user_id]": user_id,
        }

        # Add custom data if provided
        if custom_data:
            for key, value in custom_data.items():
                checkout_params[f"checkout[custom][{key}]"] = value

        # Construct full URL with query parameters
        checkout_url = f"{base_url}?{urlencode(checkout_params)}"

        logger.info(f"Generated checkout URL for user {user_id}")
        return checkout_url

    def verify_webhook_signature(self, payload: bytes, signature: str) -> bool:
        """
        Verify webhook signature using HMAC SHA256.

        Args:
            payload: Raw webhook payload (bytes)
            signature: Signature from X-Signature header

        Returns:
            True if signature is valid, False otherwise

        Raises:
            LemonSqueezyWebhookError: If webhook secret not configured
        """
        if not self.webhook_secret:
            raise LemonSqueezyWebhookError(
                "Webhook secret not configured. Set lemonsqueezy_webhook_secret in settings."
            )

        try:
            # Calculate HMAC SHA256 signature
            expected_signature = hmac.new(
                key=self.webhook_secret.encode("utf-8"),
                msg=payload,
                digestmod=hashlib.sha256,
            ).hexdigest()

            # Compare signatures
            is_valid = hmac.compare_digest(expected_signature, signature)

            if is_valid:
                logger.info("Webhook signature verified successfully")
            else:
                logger.warning("Webhook signature verification failed")

            return is_valid

        except Exception as e:
            logger.error(f"Error verifying webhook signature: {e}")
            raise LemonSqueezyWebhookError(f"Signature verification failed: {e}")

    def parse_webhook_event(self, payload: dict[str, Any]) -> WebhookEvent:
        """
        Parse webhook payload into WebhookEvent object.

        Args:
            payload: Webhook payload dictionary

        Returns:
            WebhookEvent object

        Raises:
            LemonSqueezyWebhookError: If payload parsing fails
        """
        try:
            logger.info("Parsing webhook event")
            event = WebhookEvent.from_webhook_payload(payload)
            logger.info(f"Parsed webhook event: {event.event_name}")
            return event

        except Exception as e:
            logger.error(f"Error parsing webhook event: {e}")
            raise LemonSqueezyWebhookError(f"Failed to parse webhook event: {e}")


# Factory function for easy instantiation
def create_lemonsqueezy_adapter(
    api_key: str | None = None,
    store_id: str | None = None,
    webhook_secret: str | None = None,
) -> LemonSqueezyAdapter:
    """
    Create a LemonSqueezy adapter instance.

    Args:
        api_key: LemonSqueezy API key (defaults to settings)
        store_id: LemonSqueezy store ID (defaults to settings)
        webhook_secret: Webhook signing secret (defaults to settings)

    Returns:
        LemonSqueezyAdapter instance
    """
    return LemonSqueezyAdapter(
        api_key=api_key,
        store_id=store_id,
        webhook_secret=webhook_secret,
    )
