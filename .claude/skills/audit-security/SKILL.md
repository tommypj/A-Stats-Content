---
name: audit-security
description: Run targeted security checks on auth, billing, admin, and webhook code paths. Checks for OWASP top 10, authorization gaps, injection risks, and race conditions. Triggers when editing files in routes/auth/, routes/billing/, adapters/payments/, or routes/admin/.
user-invocable: false
---

# Security Audit (Auto-Triggered)

Targeted security review for high-risk code paths. This skill is invoked automatically by Claude when editing security-sensitive files.

## Trigger Files

Run this audit when ANY of these paths are modified:
- `backend/api/routes/auth/` — Authentication & session management
- `backend/api/routes/billing.py` — Payment processing & webhooks
- `backend/adapters/payments/` — LemonSqueezy API adapter
- `backend/api/routes/admin/` — Admin endpoints
- `backend/api/deps.py` or `backend/api/deps_admin.py` — Auth dependencies
- `backend/infrastructure/security/` — JWT, password hashing

## Check 1: Authentication & Authorization

### 1a. All protected endpoints use auth dependency
```
Verify every route in the modified file uses one of:
- current_user: User = Depends(get_current_user)
- current_admin: User = Depends(get_current_admin_user)
```

**Red flag:** Any endpoint missing auth that reads/writes user data.

### 1b. Admin endpoints use admin dependency
```
All routes in routes/admin/ must use get_current_admin_user, NOT get_current_user.
```

### 1c. Resource ownership checks
```
After fetching a resource by ID, verify:
- resource.user_id == current_user.id (or admin check)
- NOT just checking if resource exists
```

## Check 2: Webhook Security

### 2a. Signature verification
```
The webhook endpoint MUST verify X-Signature header using HMAC-SHA256
before processing ANY payload data. Verification must happen BEFORE
parsing the JSON body.
```

### 2b. Refund guard intact
```
The webhook handler MUST check:
if user.subscription_status == "refunded":
    return skip

This MUST appear BEFORE any tier/status updates.
```

### 2c. Variant ID validation
```
Webhook must validate variant_id maps to a known tier.
Unknown variant IDs must NOT set tier to None or empty string.
```

## Check 3: Injection Prevention

### 3a. SQL injection
```
Scan for raw SQL that interpolates user input:
- f"SELECT ... {user_input}" — VULNERABLE
- text(f"...{user_input}...") — VULNERABLE
- text("... :param").bindparams(param=value) — SAFE
- ORM queries with .filter() — SAFE
```

### 3b. Command injection
```
Scan for subprocess/os.system calls that include user input.
```

### 3c. XSS in API responses
```
Verify HTML content is sanitized before storage/return.
Check that user-provided content isn't rendered as raw HTML.
```

## Check 4: Data Exposure

### 4a. Password/token leaks
```
Verify these are NEVER returned in API responses:
- password_hash / hashed_password
- access_token / refresh_token (except in login response)
- webhook secrets
- API keys
```

### 4b. Admin data in user endpoints
```
User-facing endpoints must NOT expose:
- Other users' data (check query filters)
- Admin-only fields (is_admin, is_superuser)
- Internal IDs (lemonsqueezy_customer_id, etc.) unless needed
```

## Check 5: Rate Limiting

### 5a. Sensitive endpoints are rate-limited
```
These endpoints MUST have slowapi rate limits:
- /auth/login — prevent brute force
- /auth/register — prevent spam
- /billing/webhook — prevent flood (100/minute)
- /auth/forgot-password — prevent enumeration
```

### 5b. slowapi parameter naming
```
For slowapi to work, the first parameter MUST be named "request":
  async def endpoint(request: Request, body: Schema, ...)
NOT:
  async def endpoint(http_request: Request, ...)
```

## Check 6: Race Conditions

### 6a. Billing state transitions
```
Check that state transitions are atomic:
- Refund: downgrade + set status in same transaction
- Cancel: set status + expires in same transaction
- Webhook: check status BEFORE updating (not after)
```

### 6b. Concurrent request safety
```
Check for read-then-write patterns without proper locking:
- Read user tier → check → update (TOCTOU vulnerability)
- Should use SELECT ... FOR UPDATE or optimistic locking
```

## Report Format

After checking, report:

```
## Security Audit — <file modified>

### Passed
- [x] Auth dependency on all endpoints
- [x] Webhook signature verification
- [x] No SQL injection vectors
- ...

### Issues Found
- [ ] CRITICAL: <description> — line <N>
- [ ] HIGH: <description> — line <N>
- [ ] MEDIUM: <description> — line <N>

### Recommended Fixes
1. <specific fix with code>
```

**Severity guide:**
- **CRITICAL:** Auth bypass, injection, data exposure
- **HIGH:** Missing rate limit, race condition, weak validation
- **MEDIUM:** Information disclosure, missing logging, error handling
