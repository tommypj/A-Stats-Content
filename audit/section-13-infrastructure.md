# Audit Section 13 — Infrastructure & Cross-Cutting Concerns
**Date**: 2026-02-27
**Status**: Complete

---

## Scope
- Application startup, CORS, and security headers
- Database connection pooling, session management, migrations
- Background task scheduling and graceful shutdown
- Logging, error handling middleware, request tracing
- Environment variable validation and secrets handling
- Deployment configuration (Dockerfile, docker-compose)
- Rate limiting architecture and Redis fallback behavior
- Cross-cutting: health checks, request IDs, error response format

---

## Files Audited
- `backend/main.py`
- `backend/infrastructure/config/settings.py`
- `backend/infrastructure/database/connection.py`
- `backend/infrastructure/database/migrations/versions/` (all)
- `backend/infrastructure/logging_config.py`
- `backend/api/middleware/rate_limit.py`
- `backend/adapters/knowledge/chroma_adapter.py`
- `backend/Dockerfile`
- `docker-compose.yml`
- `frontend/next.config.mjs` (or `.js`)

---

## Findings

### CRITICAL

#### INFRA-01 — Missing HTTP security headers — XSS, clickjacking, MIME-sniffing unmitigated
- **Severity**: CRITICAL
- **File**: `backend/main.py`
- **Description**: No security headers are set anywhere in the application middleware stack. Missing headers include: `Content-Security-Policy`, `X-Frame-Options`, `X-Content-Type-Options: nosniff`, `X-XSS-Protection`, `Referrer-Policy`, and `Strict-Transport-Security`. Without these headers, the app is vulnerable to clickjacking (no frame-options), MIME-type sniffing attacks (no nosniff), and has no CSP to mitigate injected scripts.
- **Fix**: Add a security headers middleware (before CORS middleware) that sets all required headers on every response. Use the `secure` package (`pip install secure`) or manual `response.headers.update({...})`. For CSP, start with `default-src 'self'; script-src 'self' 'unsafe-inline'` and tighten gradually.

#### INFRA-02 — `asyncio.get_event_loop()` anti-pattern in ChromaAdapter — crashes in Python 3.10+
- **Severity**: CRITICAL
- **File**: `backend/adapters/knowledge/chroma_adapter.py:328`
- **Description**: The code calls `asyncio.get_event_loop()` to schedule coroutines from a thread executor callback. In Python 3.10+, `asyncio.get_event_loop()` emits a DeprecationWarning and in Python 3.12+ it raises `RuntimeError` if there is no current event loop set in the thread. This is a latent crash waiting to manifest under specific threading conditions or during Python upgrade.
- **Fix**: Replace with `asyncio.get_running_loop()` inside async functions, or restructure the executor pattern to avoid needing to retrieve the loop from within a thread.

#### INFRA-03 — CORS origin validation uses string manipulation — regex/partial bypass possible
- **Severity**: CRITICAL
- **File**: `backend/infrastructure/config/settings.py:80-92`, `backend/main.py:206-212`
- **Description**: `cors_origins_list` splits the env var string on commas with `rstrip("/")` but performs no URL parsing or validation. If the environment variable contains malformed values, trailing wildcards, or protocol-relative URIs, the CORS middleware will accept them without error. With `allow_credentials=True` set globally, a misconfigured wildcard origin would create a critical security vulnerability (per CORS spec, credentials + wildcard is forbidden, but the middleware would silently accept it). No startup validation checks for this.
- **Fix**: Parse each origin through `urllib.parse.urlparse()` at startup. Reject origins with no scheme, empty hostname, or `*`. Add a startup validation step in `validate_production_secrets()`: `for origin in cors_origins_list: assert urlparse(origin).scheme in ("http", "https") and urlparse(origin).netloc`.

---

### HIGH

#### INFRA-04 — Request ID not stored in request state — cannot be correlated across logs
- **Severity**: HIGH
- **File**: `backend/main.py:198-202`
- **Description**: The request ID is generated (or taken from `X-Request-ID` header) and added to the response header, but it is never stored in `request.state.request_id` or in a contextvar. The logging middleware (lines 181-193) logs method, path, status_code, and duration_ms but does NOT include `request_id`. Services and route handlers have no access to the request ID for structured logging. Distributed tracing and log correlation are impossible.
- **Fix**: Store `request.state.request_id = request_id` in the request ID middleware. Expose a `get_request_id()` contextvar helper. Update the logging middleware's `extra={}` dict to include `request_id`.

#### INFRA-05 — Global exception handler leaks stack trace context in logs — sensitive data exposure
- **Severity**: HIGH
- **File**: `backend/main.py:162-168`
- **Description**: The global unhandled exception handler logs the full exception with `exc_info=True`. While the HTTP response is safe (generic "Internal server error"), stack traces written to stdout/stderr can contain partial API keys, database connection strings, or user data embedded in exception messages. In containerized deployments with centralized log aggregation, these traces are retained and searchable.
- **Fix**: In production (`settings.environment == "production"`), log only exception type and message (no `exc_info=True`). In development, retain full stack traces. Include `request_id` in all error log entries for correlation.

#### INFRA-06 — Migration chain has a gap — migration 009 is missing
- **Severity**: HIGH
- **File**: `backend/infrastructure/database/migrations/versions/010_create_team_tables.py:14`
- **Description**: Migration 010 declares `down_revision = "008"` (skipping 009). There is no migration 009 file in the versions directory. While Alembic handles this if all migrations have always been applied together, the gap breaks incremental migration validation (`alembic check`) and confuses developers who expect a clean sequential chain. Any tooling that validates migration chains will fail.
- **Fix**: Either create a placeholder migration 009 (empty up/down) to restore the chain, or update migration 010's `down_revision` to explicitly document the skip with a comment. Run `alembic check` in CI to catch future chain breaks.

#### INFRA-07 — Background task queue cleanup has no graceful shutdown — mid-flight interruption possible
- **Severity**: HIGH
- **File**: `backend/main.py:102-109, 118-123`
- **Description**: The task queue cleanup loop is created as a background asyncio Task. On shutdown, the task receives `CancelledError` but there is no try/except to handle it gracefully. If cleanup is in the middle of deleting old tasks when cancellation occurs, the operation is interrupted mid-write. Additionally, there is no confirmation log that the cleanup loop actually started successfully.
- **Fix**: Add `try/except asyncio.CancelledError` inside the cleanup loop body. On cancellation, complete the current cleanup iteration before exiting. Add a startup confirmation log: `logger.info("Task queue cleanup loop started")`.

#### INFRA-08 — Rate limiter falls back to in-memory storage in multi-instance deployment — limits not enforced
- **Severity**: HIGH
- **File**: `backend/api/middleware/rate_limit.py:84-88`
- **Description**: If `settings.redis_url` is not configured, the rate limiter silently falls back to `"memory://"`. In a multi-worker or multi-instance deployment (the Dockerfile exposes workers), each process has its own in-memory dictionary. Rate limits are enforced per-process, not globally. A user can bypass limits by sending N requests to each of the M worker processes, getting N×M requests through.
- **Fix**: In production, require Redis for rate limiting. Add startup validation: `if not settings.redis_url and settings.environment == "production": raise RuntimeError("Redis URL required for rate limiting in production")`.

---

### MEDIUM

#### INFRA-09 — X-Request-ID header not validated — log injection via malicious header value
- **Severity**: MEDIUM
- **File**: `backend/main.py:198-202`
- **Description**: If a client sends `X-Request-ID: abc\nFAKE_LOG_ENTRY: ...`, the raw header value is echoed into the response header and potentially into log entries. JSON-structured logs are safe (the value would be a JSON string), but any text-format log appender is vulnerable to log injection.
- **Fix**: Validate that the inbound `X-Request-ID` is a valid UUID format before using it. Reject non-UUID values and generate a new UUID: `request_id = h if re.match(r'^[0-9a-f-]{36}$', h) else str(uuid.uuid4())`.

#### INFRA-10 — OAuth redirect URIs default to `localhost` — production misconfiguration risk
- **Severity**: MEDIUM
- **File**: `backend/infrastructure/config/settings.py:121, 126, 131, 136`
- **Description**: Google, Twitter, LinkedIn, and Facebook redirect URIs default to `http://localhost:3000/...` or `http://localhost:8000/...`. If an operator forgets to set these environment variables in production, OAuth flows silently redirect to localhost, failing with a confusing error. `validate_production_secrets()` does not check that redirect URIs use `https://` and a non-localhost domain.
- **Fix**: Add to `validate_production_secrets()`: for each configured OAuth redirect URI, validate it starts with `https://` and does not contain `localhost`. Raise a startup error if invalid.

#### INFRA-11 — No startup validation for Redis connectivity — app silently degrades
- **Severity**: MEDIUM
- **File**: `backend/main.py:94-99`
- **Description**: During startup, the social post queue attempts to connect to Redis. If Redis is unavailable, the error is logged but the application continues starting. Rate limiting (INFRA-08) and any Redis-backed feature will silently fail open. There is no health check endpoint that tests actual Redis connectivity (only `settings.redis_url` is checked).
- **Fix**: On startup, attempt a Redis PING and raise `RuntimeError` (or log CRITICAL and refuse to serve) if it fails in production. Update `GET /health/services` to perform a real Redis PING, not just check configuration presence.

#### INFRA-12 — Database pool size not validated for multi-worker deployments
- **Severity**: MEDIUM
- **File**: `backend/infrastructure/config/settings.py:43-44`, `backend/main.py:243`
- **Description**: The default pool size is 20 with max_overflow 40 (60 total connections per process). If `workers=4` (from settings), total potential connections = 4 × 60 = 240. Most managed PostgreSQL instances (Supabase, RDS free tier) cap at 100 connections. Startup does not validate that `workers × (pool_size + max_overflow) ≤ database_max_connections`.
- **Fix**: Add a startup log: `logger.info("DB pool: %d workers × %d max connections = %d total", workers, pool_size + max_overflow, workers * (pool_size + max_overflow))`. Add validation that this total is within an acceptable range.

#### INFRA-13 — No request body size limit — large payloads not rejected
- **Severity**: MEDIUM
- **File**: `backend/main.py:238-243`
- **Description**: The uvicorn configuration has no `--limit-max-requests` or request body size limit. FastAPI does not impose a default body size limit. Large JSON payloads (e.g., articles with megabytes of content, or bulk job keyword lists) are accepted and processed without bound. A malicious user can submit an arbitrarily large article body, consuming memory and potentially causing OOM.
- **Fix**: Add a `MaxBodySizeMiddleware` that rejects requests with `Content-Length` > a configured threshold (e.g., 5MB). For file upload endpoints, enforce limits at the field level.

#### INFRA-14 — Docker image system packages not pinned — non-reproducible builds
- **Severity**: MEDIUM
- **File**: `backend/Dockerfile:13-17`
- **Description**: `apt-get install build-essential libpq-dev curl` installs whatever latest versions are available at build time without version pins. Two builds on different days may install different library versions. A system package security patch could introduce a regression. This violates reproducible build principles.
- **Fix**: Pin system package versions: `apt-get install -y build-essential=12.* libpq-dev=15.*`. Update Dockerfile comments to show pinned versions. Add Docker image scanning to CI/CD (e.g., `docker scout` or `trivy`).

#### INFRA-15 — `database_echo` not validated off in production — SQL queries with sensitive data logged
- **Severity**: MEDIUM
- **File**: `backend/infrastructure/config/settings.py:42`
- **Description**: `database_echo` defaults to `False`, but there is no assertion in `validate_production_secrets()` that ensures it is `False` in production. If an operator accidentally sets `DATABASE_ECHO=true` in the production environment, all SQL queries (including those filtering on user passwords, API keys, or PII) are logged to stdout unencrypted.
- **Fix**: Add to `validate_production_secrets()`: `if self.database_echo and self.environment == "production": raise ValueError("DATABASE_ECHO must be False in production")`.

#### INFRA-16 — docker-compose.yml uses hardcoded default credentials
- **Severity**: MEDIUM
- **File**: `docker-compose.yml:6-8, 54-60`
- **Description**: PostgreSQL credentials `POSTGRES_USER: postgres / POSTGRES_PASSWORD: postgres` are hardcoded in docker-compose.yml. While acceptable for local development, this file is committed to version control. Developers who forget to use a `.env.local` override and deploy this file directly (e.g., on a dev server) expose a postgres superuser account with a known-weak password.
- **Fix**: Replace hardcoded credentials with `${POSTGRES_PASSWORD:-postgres}` (env var with local default). Create `.env.local.example` with placeholder values. Document in README that `.env.local` must be created before first run.

---

### LOW

#### INFRA-17 — Logging configuration cannot be adjusted at runtime — requires restart
- **Severity**: LOW
- **File**: `backend/main.py:35-38`, `backend/infrastructure/logging_config.py:41-45`
- **Description**: Log level is configured once at startup. There is no mechanism to change log levels in a running production instance without a full restart. This makes live debugging of production issues harder.
- **Fix**: Add an admin-only endpoint `PATCH /admin/logging/level` body `{"level": "DEBUG"}`. Use `logging.getLogger().setLevel(level)` to update the root logger dynamically.

#### INFRA-18 — No Prometheus metrics endpoint — application health is opaque
- **Severity**: LOW
- **File**: `backend/main.py`
- **Description**: The application has no `GET /metrics` endpoint exposing request rates, latency percentiles, error rates, or queue depths. The only visibility into runtime behavior is logs. Without metrics, setting up alerting on SLOs (e.g., 99th percentile latency, error rate > 1%) is impossible.
- **Fix**: Add `prometheus-fastapi-instrumentator` middleware. Expose `/metrics` endpoint (gated behind internal-network access or basic auth). Define SLOs and configure Prometheus alerts.

#### INFRA-19 — No connection pool `pre_ping` documentation or monitoring
- **Severity**: LOW
- **File**: `backend/infrastructure/database/connection.py:20`
- **Description**: `pool_pre_ping=True` is correctly set, which is good. However, there is no monitoring of how often pre-ping recycles connections (a high recycle rate indicates unstable DB connections). Log statements for pool events are absent.
- **Fix**: Add SQLAlchemy pool event listeners to log `checkout`, `checkin`, and `invalidate` events at DEBUG level. In production, monitor pool checkout failures as an indicator of connection exhaustion.

#### INFRA-20 — `alembic.ini` `sqlalchemy.url` is a placeholder — migration run without env var will use wrong DB
- **Severity**: LOW
- **File**: `alembic.ini`
- **Description**: `alembic.ini` typically contains a hardcoded or placeholder `sqlalchemy.url`. The `env.py` overrides this from `settings.DATABASE_URL` at runtime, which is correct. However, if a developer runs `alembic upgrade head` without the proper env vars set, Alembic falls back to the placeholder URL in `alembic.ini`, potentially targeting a wrong or non-existent database and producing a confusing error.
- **Fix**: Set `sqlalchemy.url =` (empty) in `alembic.ini` and add a guard in `env.py`: `if not config.get_main_option("sqlalchemy.url"): raise RuntimeError("DATABASE_URL env var must be set to run migrations")`.

---

## What's Working Well
- Structured JSON logging for production (`logging_config.py`) — parseable by log aggregators
- `validate_production_secrets()` catches missing Anthropic key and other critical env vars
- `pool_pre_ping=True` prevents stale connection errors
- Health check endpoints exist at `/health` and `/health/services`
- CORS is configured from environment variables (not hardcoded)
- Request ID generation with UUID4 (cryptographically random)
- Single-process graceful shutdown via lifespan context manager
- `alembic env.py` correctly pulls `DATABASE_URL` from settings at migration time

---

## Fix Priority Order
1. INFRA-01 — Missing HTTP security headers (CRITICAL)
2. INFRA-02 — asyncio.get_event_loop() anti-pattern (CRITICAL)
3. INFRA-03 — CORS origin validation uses string manipulation (CRITICAL)
4. INFRA-04 — Request ID not propagated to logging context (HIGH)
5. INFRA-05 — Stack traces logged with sensitive data in production (HIGH)
6. INFRA-06 — Migration chain gap — missing 009 (HIGH)
7. INFRA-07 — Background task no graceful shutdown (HIGH)
8. INFRA-08 — Rate limiter in-memory fallback not safe for multi-instance (HIGH)
9. INFRA-09 — X-Request-ID not validated — log injection (MEDIUM)
10. INFRA-10 — OAuth redirect URIs default to localhost (MEDIUM)
11. INFRA-11 — No startup Redis connectivity check (MEDIUM)
12. INFRA-12 — DB pool size not validated for multi-worker (MEDIUM)
13. INFRA-13 — No request body size limit (MEDIUM)
14. INFRA-14 — Docker system packages not pinned (MEDIUM)
15. INFRA-15 — database_echo not validated off in production (MEDIUM)
16. INFRA-16 — docker-compose hardcoded credentials (MEDIUM)
17. INFRA-17 through INFRA-20 — Low severity (LOW)
