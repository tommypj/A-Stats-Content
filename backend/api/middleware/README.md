# API Middleware

This directory contains middleware components for the A-Stats API.

## Rate Limiting

**File:** `rate_limit.py`

### Overview

The rate limiting middleware protects API endpoints from brute force attacks and abuse by limiting the number of requests per time period based on the client's IP address.

### Implementation

Uses [slowapi](https://github.com/laurentS/slowapi) - a rate limiting library for FastAPI that's compatible with Flask-Limiter.

### Configuration

Rate limits are configured in the `RATE_LIMITS` dictionary:

```python
RATE_LIMITS = {
    "login": "5/minute",           # Login attempts
    "register": "3/minute",        # New registrations
    "password_reset": "3/hour",    # Password reset requests
    "email_verification": "5/hour", # Email verification attempts
    "resend_verification": "5/hour", # Resend verification emails
    "default": "100/minute",       # Default for all endpoints
}
```

### Usage in Routes

To apply rate limiting to an endpoint:

```python
from fastapi import Request
from api.middleware.rate_limit import limiter

@router.post("/login")
@limiter.limit("5/minute")
async def login(
    request: Request,  # Required by slowapi for IP extraction
    login_data: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    # Your endpoint logic
    pass
```

**Important:** The endpoint must accept `request: Request` as the first parameter for slowapi to extract the client IP address.

### Response Codes

- **200/201**: Request successful, within rate limit
- **429 Too Many Requests**: Rate limit exceeded

When rate limit is exceeded, the response includes:
- `X-RateLimit-Limit`: The rate limit ceiling
- `X-RateLimit-Remaining`: Remaining requests in current window
- `X-RateLimit-Reset`: Timestamp when the rate limit resets

### Storage

Currently uses **in-memory storage** which is suitable for:
- Single-server deployments
- Development environments
- Small-scale production

For production with multiple servers, use Redis:

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(
    key_func=get_remote_address,
    storage_uri="redis://localhost:6379"
)
```

### Protected Endpoints

The following authentication endpoints are rate-limited:

| Endpoint | Limit | Reason |
|----------|-------|--------|
| `/auth/login` | 5/minute | Prevents brute force password attacks |
| `/auth/register` | 3/minute | Prevents mass account creation |
| `/auth/password/reset-request` | 3/hour | Prevents email flooding |
| `/auth/verify-email` | 5/hour | Limits verification attempts |
| `/auth/resend-verification` | 5/hour | Limits verification email sends |

### Testing

Test cases are located in `backend/tests/integration/test_rate_limiting.py` and cover:
- Rate limit enforcement on each protected endpoint
- Proper 429 responses when limits exceeded
- Independent rate limits per endpoint
- Rate limit headers in responses

### Architecture Notes

- **Layer:** API/Adapter layer (not Core domain)
- **Dependencies:** FastAPI, slowapi, limits
- **Key Function:** IP-based via `get_remote_address()`
- **No domain coupling:** Pure infrastructure concern

### Customization

To add rate limiting to new endpoints:

1. Import the limiter:
   ```python
   from api.middleware.rate_limit import limiter
   ```

2. Apply the decorator with desired limit:
   ```python
   @limiter.limit("10/minute")
   ```

3. Add `request: Request` as first parameter:
   ```python
   async def my_endpoint(request: Request, ...):
   ```

4. Optionally add custom limits to the `RATE_LIMITS` dictionary for reusability.

### Production Considerations

1. **Redis Storage:** For multi-server deployments, configure Redis backend
2. **Monitoring:** Track 429 responses to identify abuse patterns
3. **Whitelisting:** Consider whitelisting trusted IPs (API clients, internal services)
4. **Custom Key Functions:** For authenticated endpoints, consider user-based limiting instead of IP-based
5. **Dynamic Limits:** Adjust limits based on subscription tier or user behavior

### Resources

- [slowapi Documentation](https://github.com/laurentS/slowapi)
- [Flask-Limiter Documentation](https://flask-limiter.readthedocs.io/) (compatible API)
- [Rate Limiting Strategies](https://www.nginx.com/blog/rate-limiting-nginx/)
