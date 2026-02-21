# Billing Module Test Documentation

## Overview

Comprehensive test suite for the LemonSqueezy billing integration covering adapter unit tests, API integration tests, and webhook processing.

## Test Structure

```
backend/tests/
├── conftest.py                              # Shared fixtures + billing fixtures
├── unit/
│   └── test_lemonsqueezy_adapter.py        # Adapter unit tests (16 tests)
└── integration/
    └── test_billing_api.py                 # API integration tests (~40 tests)
```

## Unit Tests: LemonSqueezy Adapter

**File:** `backend/tests/unit/test_lemonsqueezy_adapter.py`

### Test Coverage

| Test Case | Description | Mocks |
|-----------|-------------|-------|
| `test_adapter_initialization` | Verify adapter initializes with credentials | None |
| `test_adapter_initialization_with_defaults` | Test using settings defaults | `settings` |
| `test_get_customer_success` | Mock successful customer fetch | `httpx.AsyncClient.get` |
| `test_get_customer_not_found` | Mock 404 response for missing customer | `httpx.AsyncClient.get` |
| `test_get_subscription_success` | Mock successful subscription fetch | `httpx.AsyncClient.get` |
| `test_get_subscription_not_found` | Mock 404 response for missing subscription | `httpx.AsyncClient.get` |
| `test_get_customer_portal_url` | Mock portal URL generation | `httpx.AsyncClient.get` |
| `test_cancel_subscription_success` | Mock successful cancellation | `httpx.AsyncClient.delete` |
| `test_cancel_subscription_already_cancelled` | Handle already cancelled subscription | `httpx.AsyncClient.delete` |
| `test_pause_subscription_success` | Mock successful pause | `httpx.AsyncClient.patch` |
| `test_resume_subscription_success` | Mock successful resume | `httpx.AsyncClient.patch` |
| `test_verify_webhook_signature_valid` | Validate correct HMAC signature | None |
| `test_verify_webhook_signature_invalid` | Reject invalid signature | None |
| `test_parse_webhook_subscription_created` | Parse subscription_created event | None |
| `test_parse_webhook_subscription_cancelled` | Parse subscription_cancelled event | None |
| `test_parse_webhook_payment_failed` | Parse payment_failed event | None |
| `test_get_checkout_url` | Generate checkout URL with params | None |
| `test_api_error_handling` | Handle network errors gracefully | `httpx.AsyncClient.get` |
| `test_api_authentication_error` | Handle 401 authentication errors | `httpx.AsyncClient.get` |
| `test_create_lemonsqueezy_adapter_factory` | Test factory function | None |

### Running Unit Tests

```bash
# Run all unit tests
pytest backend/tests/unit/test_lemonsqueezy_adapter.py -v

# Run specific test
pytest backend/tests/unit/test_lemonsqueezy_adapter.py::TestLemonSqueezyAdapter::test_get_customer_success -v

# Run with coverage
pytest backend/tests/unit/test_lemonsqueezy_adapter.py --cov=adapters.billing.lemonsqueezy_adapter --cov-report=html
```

## Integration Tests: Billing API

**File:** `backend/tests/integration/test_billing_api.py`

### Endpoint Coverage

#### 1. Pricing Endpoint (`GET /billing/pricing`)

| Test | Validates |
|------|-----------|
| `test_get_pricing_returns_all_plans` | Returns 4 plans with correct structure |
| `test_pricing_no_auth_required` | Works without authentication |

#### 2. Subscription Status (`GET /billing/subscription`)

| Test | Validates |
|------|-----------|
| `test_get_subscription_authenticated` | Returns subscription data with auth |
| `test_get_subscription_unauthorized` | Returns 401 without auth |
| `test_subscription_free_user` | Free user shows correct tier/status |

#### 3. Checkout (`POST /billing/checkout`)

| Test | Validates |
|------|-----------|
| `test_checkout_generates_url` | Generates valid checkout URL |
| `test_checkout_invalid_plan` | Returns 400 for invalid plan |
| `test_checkout_invalid_billing_cycle` | Returns 400 for invalid cycle |

#### 4. Customer Portal (`GET /billing/portal`)

| Test | Validates |
|------|-----------|
| `test_portal_with_customer_id` | Returns portal URL for subscribed user |
| `test_portal_without_customer_id` | Returns 404 for free user |

#### 5. Subscription Cancellation (`POST /billing/cancel`)

| Test | Validates |
|------|-----------|
| `test_cancel_active_subscription` | Successfully cancels active subscription |
| `test_cancel_no_subscription` | Returns 404 for users without subscription |

#### 6. Webhook Processing (`POST /billing/webhook`)

| Test | Validates |
|------|-----------|
| `test_webhook_valid_signature` | Processes events with valid signature |
| `test_webhook_invalid_signature` | Rejects invalid signatures (401) |
| `test_webhook_subscription_created` | Updates user on subscription creation |
| `test_webhook_subscription_cancelled` | Updates status on cancellation |
| `test_webhook_payment_failed` | Sets status to past_due on failure |

#### 7. Pause/Resume (`POST /billing/pause`, `POST /billing/resume`)

| Test | Validates |
|------|-----------|
| `test_pause_subscription` | Pauses active subscription |
| `test_resume_subscription` | Resumes paused subscription |

### Running Integration Tests

```bash
# Run all billing integration tests
pytest backend/tests/integration/test_billing_api.py -v

# Run specific test class
pytest backend/tests/integration/test_billing_api.py::TestWebhookEndpoint -v

# Run with database output
pytest backend/tests/integration/test_billing_api.py -v -s
```

## Test Fixtures

### Billing-Specific Fixtures (in `conftest.py`)

#### `free_user`
Creates a user with free tier and no subscription.

**Usage:**
```python
async def test_checkout(async_client, free_user):
    # free_user has no lemonsqueezy_customer_id
    ...
```

**Properties:**
- `subscription_tier`: "free"
- `subscription_status`: "active"
- `lemonsqueezy_customer_id`: None
- `lemonsqueezy_subscription_id`: None

#### `subscribed_user`
Creates a user with professional tier and active subscription.

**Usage:**
```python
async def test_portal(async_client, subscribed_user):
    # subscribed_user has valid LemonSqueezy IDs
    ...
```

**Properties:**
- `subscription_tier`: "professional"
- `subscription_status`: "active"
- `lemonsqueezy_customer_id`: "12345"
- `lemonsqueezy_subscription_id`: "67890"
- `subscription_expires`: 30 days from now

#### `valid_webhook_payload`
Sample `subscription_created` webhook payload.

**Structure:**
```python
{
    "meta": {
        "event_name": "subscription_created",
        "custom_data": {"user_id": "..."}
    },
    "data": {
        "type": "subscriptions",
        "id": "1",
        "attributes": {...}
    }
}
```

#### `valid_webhook_signature`
Generates valid HMAC-SHA256 signature for webhook payload.

**Usage:**
```python
def test_webhook(async_client, valid_webhook_payload, valid_webhook_signature):
    response = await async_client.post(
        "/billing/webhook",
        json=valid_webhook_payload,
        headers={"X-Signature": valid_webhook_signature}
    )
```

#### `mock_lemonsqueezy_api`
Mock httpx client for LemonSqueezy API calls.

**Usage:**
```python
async def test_adapter(mock_lemonsqueezy_api):
    with mock_lemonsqueezy_api as mock_client:
        mock_client.get.return_value = mock_response
        # Test adapter methods
```

## Test Patterns

### 1. Mocking External API Calls

```python
@pytest.mark.asyncio
async def test_get_customer_success(adapter, mock_customer_response):
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_customer_response
        mock_get.return_value = mock_response

        customer = await adapter.get_customer("1")
        assert customer["id"] == "1"
```

### 2. Testing Webhook Signatures

```python
def test_verify_webhook_signature_valid(adapter):
    payload = b'{"event": "test"}'
    signature = hmac.new(
        adapter.webhook_secret.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()

    # Should not raise
    adapter.verify_webhook_signature(payload, signature)
```

### 3. Testing Database Updates

```python
@pytest.mark.asyncio
async def test_webhook_updates_user(async_client, db_session):
    user = User(...)
    db_session.add(user)
    await db_session.commit()

    # Send webhook
    response = await async_client.post("/billing/webhook", ...)

    # Verify database was updated
    await db_session.refresh(user)
    assert user.subscription_status == "active"
```

### 4. Testing Authentication

```python
@pytest.mark.asyncio
async def test_endpoint_requires_auth(async_client):
    # Without auth headers
    response = await async_client.get("/billing/subscription")
    assert response.status_code == 401
```

## Expected Behavior

### Skipped Tests
Tests will automatically skip if the implementation is not available:

```
SKIPPED [1] test_lemonsqueezy_adapter.py:18: LemonSqueezy adapter not implemented yet
```

This is expected during Phase 6 development. Tests will run once:
- `backend/adapters/billing/lemonsqueezy_adapter.py` is created
- `backend/api/routes/billing.py` is created

### Test Execution Order
1. Unit tests run first (fast, no DB)
2. Integration tests run second (slower, uses DB)

## Coverage Goals

| Component | Target Coverage | Status |
|-----------|----------------|--------|
| LemonSqueezy Adapter | 100% | ⏳ Pending implementation |
| Billing API Routes | 95%+ | ⏳ Pending implementation |
| Webhook Processing | 100% | ⏳ Pending implementation |
| Error Handling | 100% | ⏳ Pending implementation |

## Common Issues & Solutions

### Issue: "Module not found: adapters.billing"
**Solution:** Tests will skip until adapter is implemented. This is expected.

### Issue: "User fixture has no attribute 'hashed_password'"
**Solution:** User model uses `password_hash`, not `hashed_password`. Check test fixtures.

### Issue: "Webhook signature validation fails"
**Solution:** Ensure payload is JSON-encoded and signature uses correct secret.

## Next Steps

1. **Implement LemonSqueezy Adapter** (`backend/adapters/billing/lemonsqueezy_adapter.py`)
   - All test cases defined in unit tests
   - Use test fixtures as implementation guide

2. **Implement Billing API Routes** (`backend/api/routes/billing.py`)
   - All endpoints defined in integration tests
   - Follow existing route patterns (see `analytics.py`)

3. **Run Tests**
   ```bash
   pytest backend/tests/unit/test_lemonsqueezy_adapter.py -v
   pytest backend/tests/integration/test_billing_api.py -v
   ```

4. **Verify Coverage**
   ```bash
   pytest --cov=adapters.billing --cov=api.routes.billing --cov-report=html
   open htmlcov/index.html
   ```

## Related Documentation

- [LemonSqueezy API Docs](https://docs.lemonsqueezy.com/api)
- [Webhook Signature Verification](https://docs.lemonsqueezy.com/api/webhooks#webhook-signature)
- [Testing Best Practices](../tests/README.md)
