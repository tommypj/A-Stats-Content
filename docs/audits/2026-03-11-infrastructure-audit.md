# Infrastructure, Configuration & Dependency Audit -- 2026-03-11

Auditor: Claude Opus 4.6
Scope: Configuration, dependencies, build/deploy, performance, logging/monitoring, Redis usage

---

## Summary

| Severity | Count |
|----------|-------|
| Critical | 4     |
| Warning  | 18    |
| Info     | 12    |

---

## 1. Configuration Issues

### Missing Environment Variables in .env.example

- **Warning** -- `backend/infrastructure/config/settings.py:174` -- `GEMINI_API_KEY` is used by the Gemini adapter (`backend/adapters/ai/gemini_adapter.py:52`) but is missing from `.env.example`. Deployers won't know to set it.

- **Warning** -- `backend/infrastructure/config/settings.py:175` -- `GEMINI_MODEL` (default `gemini-2.5-flash`) is not documented in `.env.example`.

- **Warning** -- `backend/infrastructure/config/settings.py:196` -- `API_BASE_URL` (used for permanent image URLs) is missing from `.env.example`. Production deployers must set this but have no documentation hint.

- **Warning** -- `backend/infrastructure/config/settings.py:199` -- `COOKIE_DOMAIN` is missing from `.env.example`. Required for cross-subdomain auth (e.g., `api.a-stats.app` + `a-stats.app`).

- **Warning** -- `backend/infrastructure/config/settings.py:131` -- `LEMONSQUEEZY_STORE_SLUG` is missing from `.env.example`. Used in `backend/api/routes/billing.py:315` for the customer portal URL; will return 500 if unset.

- **Info** -- `backend/infrastructure/config/settings.py:109` -- `ANTHROPIC_HAIKU_MODEL` is configurable via env but not documented in `.env.example`.

- **Info** -- `backend/infrastructure/config/settings.py:171` -- `OPENAI_OUTLINE_MODEL` (default `gpt-4o-mini`) is not documented in `.env.example`.

- **Info** -- `backend/infrastructure/config/settings.py:114-115` -- `AI_REQUEST_TIMEOUT` and `BULK_ITEM_SLEEP_SECONDS` are tunable settings missing from `.env.example`.

- **Info** -- `backend/infrastructure/config/settings.py:47-48` -- `DB_POOL_SIZE` and `DB_MAX_OVERFLOW` are configurable but not documented in `.env.example`. Important for Railway where connection limits are tight.

### Inconsistent Config Defaults

- **Warning** -- `.env.example:61` vs `backend/infrastructure/config/settings.py:108` -- `.env.example` documents `ANTHROPIC_MODEL=claude-sonnet-4-20250514` but settings.py defaults to `claude-sonnet-4-6`. These are different model specifiers.

- **Warning** -- `.env.example:46` vs `backend/infrastructure/config/settings.py:81` -- `.env.example` says `JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30` but settings.py defaults to `60`. Deployers relying on the example will get unexpected behavior.

---

## 2. Dependency Audit

### Unused Dependencies (installed but never imported in production code)

- **Warning** -- `backend/pyproject.toml:49` -- `stripe>=7.0.0` is listed as a dependency but is never imported in any production Python file. The billing system uses LemonSqueezy. Only referenced in old migration comments. This adds ~5MB to the Docker image.

- **Warning** -- `backend/pyproject.toml:64` -- `arq>=0.25.0` (async job queue) is listed but never imported anywhere in the codebase. Background tasks use in-process `asyncio.create_task()` instead. Dead dependency.

- **Warning** -- `backend/pyproject.toml:57` -- `rich>=13.7.0` is listed but never imported in any backend Python file. Unnecessary in production.

- **Info** -- `backend/pyproject.toml:60` -- `aiohttp>=3.9.0` is only imported in `backend/adapters/storage/image_storage.py:16`. Consider whether httpx (already a dependency) could replace it to reduce dependency surface.

### Security-Sensitive Dependencies

- **Critical** -- `backend/pyproject.toml:29` -- `python-jose[cryptography]>=3.3.0` is used for JWT operations. python-jose is unmaintained (last release Dec 2021) and has known CVEs (CVE-2024-33663, CVE-2024-33664). Migrate to `PyJWT` or `joserfc`. Affected code: `backend/core/security/tokens.py:8`.

- **Warning** -- `backend/pyproject.toml:31` -- `bcrypt>=3.2.0,<4.1.0` pins to an old range. bcrypt 4.1+ is available with passlib compatibility. The upper bound may prevent security patches. Verify passlib compatibility and widen.

### Version Pinning

- **Info** -- `frontend/package.json:30` -- Next.js is pinned to `14.1.0` (exact, not caret). This is now over 2 years old. Next.js 14.2.x had significant security and performance fixes. Consider updating to at least `14.2.x`.

---

## 3. Build & Deployment

### Docker / Railway

- **Info** -- `backend/Dockerfile:37-38` -- HEALTHCHECK uses `curl` which is installed explicitly. This is good but the health check start period is 10s, while `start.sh` runs Alembic migrations first. Long migration chains could cause the health check to fail before the app is ready. Consider increasing `--start-period` to 60s.

- **Info** -- `backend/Dockerfile:21-22` -- Dependencies are installed with `pip install --no-cache-dir .` but there's no lock file (no `pip freeze` or `pip-compile` output). Builds are not reproducible -- different builds may get different transitive dependency versions.

### CI/CD

- **Warning** -- `.github/workflows/ci.yml:51` -- `pip install aiosqlite` is installed separately outside of pyproject.toml dev extras. This should be added to `[project.optional-dependencies] dev` for consistency.

- **Info** -- `.github/workflows/ci.yml` -- No caching of pip dependencies beyond the built-in `cache: "pip"` setup-python action. The `pip install -e ".[dev]"` step reinstalls everything each run. Consider a `pip cache` or hashing the lock file.

### Vercel

- **Info** -- `frontend/vercel.json` -- No `headers` configuration for security headers (CSP, X-Frame-Options, etc.) on the frontend. The backend adds these headers, but static assets and SSR pages served by Vercel bypass the backend entirely.

---

## 4. Performance Concerns

### N+1 Query Risk Areas

- **Warning** -- `backend/infrastructure/database/models/project.py:85-96` -- Project model has 4 relationships with `lazy="select"` (owner, members, invitations, user). Any iteration over a list of projects that accesses these attributes triggers N+1 queries. Most route handlers use `selectinload()` correctly, but accessing these relationships outside of explicitly loaded contexts will silently fire individual queries.

### Frontend Bundle

- **Info** -- `frontend/components/PostHogProvider.tsx` and `frontend/components/providers/posthog-provider.tsx` -- There are TWO duplicate PostHog provider implementations. `PostHogProvider.tsx` is used in the dashboard layout, while `posthog-provider.tsx` is used in the root `Providers` component. This means PostHog is initialized twice with slightly different configurations (different default hosts: `us.i.posthog.com` vs `app.posthog.com`, and the providers wrapper creates separate react context trees). Only one should exist.

- **Warning** -- `frontend/components/social/post-preview.tsx:47,75,110,132,164,183,212,224` and multiple other files -- At least 20 instances of raw `<img>` tags instead of Next.js `<Image>` component. These bypass automatic optimization (WebP conversion, lazy loading, responsive srcset). Most are for user-uploaded content or external URLs, but they should still use `next/image` with `unoptimized` prop for consistency with loading/error handling.

### Missing Redis Caching Opportunities

- **Warning** -- `backend/api/routes/analytics.py` -- GSC analytics endpoints make external API calls on every request without Redis caching. These are expensive and rate-limited by Google. The keyword research endpoint (`backend/api/routes/articles.py:985`) already has Redis caching -- analytics should follow the same pattern.

---

## 5. Logging & Monitoring

### Sensitive Data in Logs

- **Info** -- `backend/main.py:80` -- `logger.info("CORS origins raw: %r", settings.cors_origins)` logs the raw CORS origins which is not sensitive, but the pattern is close to logging config values. Verified: no secrets are logged.

- **Info** -- `backend/adapters/social/twitter_adapter.py:219,321,341` and `backend/adapters/search/gsc_adapter.py:166,185,226,243,280` -- Multiple `logger.info()` calls mention "tokens" in their message (e.g., "Exchanging authorization code for tokens"). Verified: these log only the operation name, not token values. However, if log level is changed to DEBUG, the httpx/aiohttp clients may log full request/response bodies including tokens. Ensure HTTP client debug logging is suppressed in production.

### f-string Logging (Performance)

- **Warning** -- 14 files across `backend/` use f-string formatting in logger calls (132 total occurrences). Examples: `backend/services/post_queue.py` (17 occurrences), `backend/adapters/search/gsc_adapter.py` (24 occurrences). f-strings are evaluated eagerly even when the log level is suppressed. Use `%s` formatting (lazy evaluation) instead. Top offenders:
  - `backend/adapters/search/gsc_adapter.py` -- 24 occurrences
  - `backend/adapters/cms/wordpress_adapter.py` -- 24 occurrences
  - `backend/services/knowledge_service.py` -- 18 occurrences
  - `backend/services/post_queue.py` -- 17 occurrences

### Sentry Coverage

- **Warning** -- `backend/main.py:34-63` -- Sentry is only initialized on the backend if the DSN is set AND contains `sentry.io`. The validation (`"sentry.io" not in _dsn`) would reject self-hosted Sentry instances. Also, Sentry is only imported/initialized in `main.py`, meaning any exception during module-level imports in other files (before `main.py` runs) would not be captured.

---

## 6. Redis Usage

### Remaining Inline Redis Connection

- **Critical** -- `backend/services/post_queue.py:54` -- `PostQueueManager.connect()` creates its own Redis connection via `redis.from_url(settings.redis_url, ...)` instead of using the centralized pool from `infrastructure/redis.py`. This bypasses the shared pool's connection limits and lifecycle management. The `post_queue.disconnect()` in `main.py:335` closes this connection, but it's outside the centralized `close_redis()` call.

### Cache Key Collision Risks

- **Warning** -- Redis keys across the codebase use ad-hoc prefixes without a central registry:
  - `token_blacklist:{hash}` -- `backend/api/routes/auth.py:76`
  - `oauth_state:{state}` -- `backend/api/oauth_helpers.py:63`
  - `webhook:processed:{event_id}` -- `backend/api/routes/billing.py:655`
  - `kw_research:{user_id}:{keyword}` -- `backend/api/routes/articles.py:985`
  - `serp:{keyword}:{lang}` and `research:{keyword}:{lang}` -- `backend/services/content_pipeline.py:114`
  - `social:post_queue`, `social:scheduled_posts`, `social:processing_posts` -- `backend/services/post_queue.py:32-34`
  - Rate limiter keys (managed by slowapi)

  There is no central KEY_PREFIX or namespace. If multiple environments share the same Redis instance (common in development), keys will collide. Consider adding an environment prefix (e.g., `astats:{env}:token_blacklist:{hash}`).

---

## 7. Miscellaneous

### Rogue Files

- **Info** -- `D:\A-Stats-Online\nul`, `D:\A-Stats-Online\backend\nul`, `D:\A-Stats-Online\frontend\NUL` -- These are Windows NUL device artifacts (created when a command redirects to `/dev/null` on Windows). They are gitignored but clutter the workspace. Safe to delete.

### Duplicate PostHog Implementation

- **Critical** -- `frontend/components/PostHogProvider.tsx` and `frontend/components/providers/posthog-provider.tsx` -- Two separate PostHog provider implementations exist with different configurations. The dashboard layout (`frontend/app/(dashboard)/layout.tsx:59,927`) wraps content in `PostHogProvider` from `PostHogProvider.tsx`, while the root layout uses `Providers` from `providers.tsx` which wraps in `PosthogProvider` from `providers/posthog-provider.tsx`. This causes:
  1. PostHog `init()` called twice with different `api_host` values (`us.i.posthog.com` vs `app.posthog.com`)
  2. Double pageview tracking (both providers track pageviews)
  3. Potential data inconsistency

  **Fix**: Remove one implementation and standardize on a single provider.

### Stripe Dependency Residue

- **Critical** -- `backend/pyproject.toml:49` -- `stripe>=7.0.0` is still listed as a production dependency despite the billing system being fully migrated to LemonSqueezy. The stripe package is 5MB+ and exposes an unnecessary attack surface. Only referenced in old Alembic migration comments and `core/domain/subscription.py` (which defines plan constants, not Stripe API calls). Remove from dependencies.

---

## Prioritized Action Items

### Critical (fix before next deploy)
1. Replace `python-jose` with `PyJWT` or `joserfc` -- known CVEs
2. Remove `stripe` from pyproject.toml dependencies -- unused, large attack surface
3. Migrate `PostQueueManager` to use centralized Redis pool
4. Consolidate duplicate PostHog providers into one

### Warning (fix this sprint)
5. Add missing env vars to `.env.example`: `GEMINI_API_KEY`, `API_BASE_URL`, `COOKIE_DOMAIN`, `LEMONSQUEEZY_STORE_SLUG`, `GEMINI_MODEL`
6. Fix `.env.example` defaults to match `settings.py` (JWT expiry 30 vs 60, Anthropic model name)
7. Remove unused dependencies: `arq`, `rich`, `stripe`
8. Add `aiosqlite` to pyproject.toml dev extras
9. Convert 132 f-string logger calls to lazy `%s` formatting
10. Add Redis key namespace prefix for environment isolation
11. Add Redis caching to GSC analytics endpoints
12. Use `next/image` instead of raw `<img>` tags (20+ instances)
13. Widen bcrypt version pin to allow 4.1+

### Info (backlog)
14. Pin Next.js to at least 14.2.x for security fixes
15. Increase Dockerfile HEALTHCHECK `--start-period` to 60s
16. Add Vercel security headers config
17. Add pip lock file for reproducible backend builds
18. Delete rogue `nul`/`NUL` files from workspace
19. Document `DB_POOL_SIZE`, `DB_MAX_OVERFLOW`, `AI_REQUEST_TIMEOUT` in `.env.example`
