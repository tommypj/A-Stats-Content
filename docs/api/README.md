# A-Stats-Online API Reference

Complete reference for all backend API endpoints (~287 endpoints across 21+ namespaces).

---

## Authentication

All authenticated endpoints use **HttpOnly cookie-based JWT tokens**. After login, the server sets `access_token` and `refresh_token` cookies automatically.

| Auth Level | Description |
|------------|-------------|
| **Public** | No authentication required |
| **User** | Requires valid access token cookie (any logged-in user) |
| **Admin** | Requires `role = admin` or `super_admin` |
| **Super Admin** | Requires `role = super_admin` |

### Tier Gating

Some endpoints require a minimum subscription tier:

| Tier | Level |
|------|-------|
| `free` | 0 |
| `starter` | 1 |
| `professional` | 2 |
| `enterprise` | 3 |

---

## Base URL

```
Production: https://api.a-stats.online/api/v1
Development: http://localhost:8000/api/v1
```

---

## 1. Health (`/health`)

System health and readiness probes.

| Method | Path | Description | Auth | Rate Limit |
|--------|------|-------------|------|------------|
| GET | `/health` | Basic health check | Public | — |
| GET | `/health/db` | Database connectivity check | Public | — |
| GET | `/health/redis` | Redis connectivity check | Public | — |
| GET | `/health/ready` | Readiness probe (DB + Redis) | Public | — |
| GET | `/health/live` | Liveness probe | Public | — |
| GET | `/health/services` | Detailed service status (DB, Redis, external APIs) | Admin | — |

**Response** (all health endpoints):
- `status`: `"healthy"` or `"unhealthy"`
- `details`: Object with component-specific status info

---

## 2. Authentication (`/auth`)

User registration, login, profile management, and OAuth flows.

### Registration & Login

| Method | Path | Description | Auth | Rate Limit |
|--------|------|-------------|------|------------|
| POST | `/auth/register` | Create new account | Public | 3/min |
| POST | `/auth/login` | Login with email/password | Public | 5/min |
| POST | `/auth/refresh` | Refresh access token | User | 5/min |
| POST | `/auth/logout` | Logout and revoke session | User | 20/min |

**POST `/auth/register`** — Request:
- `email` (string, required)
- `password` (string, required, min 8 chars)
- `name` (string, required)

**POST `/auth/login`** — Request:
- `email` (string, required)
- `password` (string, required)

**Response** (login/register): `UserResponse` with `id`, `email`, `name`, `role`, `subscription_tier`, `is_active`, `created_at`. Tokens set as HttpOnly cookies.

### Profile

| Method | Path | Description | Auth | Rate Limit |
|--------|------|-------------|------|------------|
| GET | `/auth/me` | Get current user profile | User | 30/min |
| PUT | `/auth/me` | Update profile (name, etc.) | User | — |
| POST | `/auth/me/avatar` | Upload avatar image | User | 10/min |
| GET | `/auth/me/export` | Export all personal data (GDPR) | User | 1/hour |
| DELETE | `/auth/account` | Soft-delete account | User | 3/hour |

**POST `/auth/me/avatar`** — Request: multipart file upload (`file` field).

### Password Management

| Method | Path | Description | Auth | Rate Limit |
|--------|------|-------------|------|------------|
| POST | `/auth/password/reset-request` | Request password reset email | Public | 3/hour |
| POST | `/auth/password/reset` | Reset password with token | Public | 3/hour |
| POST | `/auth/password/change` | Change password (authenticated) | User | 5/min |

**POST `/auth/password/reset-request`** — Request: `email` (string).
**POST `/auth/password/reset`** — Request: `token` (string), `new_password` (string).
**POST `/auth/password/change`** — Request: `current_password`, `new_password`.

### Email Verification & Change

| Method | Path | Description | Auth | Rate Limit |
|--------|------|-------------|------|------------|
| POST | `/auth/verify-email` | Verify email with token | Public | 5/hour |
| POST | `/auth/resend-verification` | Resend verification email | User | 5/hour |
| POST | `/auth/change-email` | Request email change | User | 3/min |
| POST | `/auth/verify-email-change` | Confirm email change with token | User | 10/min |

### Google OAuth

| Method | Path | Description | Auth | Rate Limit |
|--------|------|-------------|------|------------|
| GET | `/auth/google` | Get Google OAuth redirect URL | Public | 20/min |
| GET | `/auth/google/callback` | Google OAuth callback handler | Public | — |

---

## 3. Articles (`/articles`)

Article CRUD, AI generation, SEO analysis, and content management.

### Core CRUD

| Method | Path | Description | Auth | Rate Limit |
|--------|------|-------------|------|------------|
| POST | `/articles` | Create article manually | User | 20/min |
| GET | `/articles` | List articles (paginated, filterable) | User | — |
| GET | `/articles/{article_id}` | Get article by ID | User | — |
| PUT | `/articles/{article_id}` | Update article | User | 30/min |
| DELETE | `/articles/{article_id}` | Delete article | User | 30/min |
| POST | `/articles/bulk-delete` | Bulk delete articles | User | 10/min |

**POST `/articles`** — Request:
- `title` (string, required)
- `content` (string)
- `keyword` (string)
- `outline_id` (string, optional)
- `project_id` (string, required)

**GET `/articles`** — Query params: `page`, `page_size`, `project_id`, `status`, `search`, `sort_by`, `sort_order`.

**Response**: `ArticleResponse` with `id`, `title`, `content`, `keyword`, `seo_score`, `word_count`, `status`, `project_id`, `created_at`, `updated_at`.

### AI Generation

| Method | Path | Description | Auth | Rate Limit |
|--------|------|-------------|------|------------|
| POST | `/articles/generate` | Generate article from outline via AI pipeline | User | 10/min |
| GET | `/articles/{article_id}/stream` | SSE stream for generation status | User | — |
| POST | `/articles/{article_id}/improve` | AI-improve existing article | User | 10/min |
| POST | `/articles/{article_id}/analyze-seo` | Run SEO analysis | User | 10/min |
| POST | `/articles/{article_id}/generate-image-prompts` | Generate image prompts for article | User | 10/min |

**POST `/articles/generate`** — Request:
- `outline_id` (string, required)
- `project_id` (string, required)
- `tone` (string, optional)
- `target_length` (int, optional)

### SEO & AEO

| Method | Path | Description | Auth | Rate Limit |
|--------|------|-------------|------|------------|
| GET | `/articles/{article_id}/aeo-score` | Get AEO (Answer Engine Optimization) score | User | — |
| POST | `/articles/{article_id}/aeo-score` | Refresh AEO score | User | 20/min |
| POST | `/articles/{article_id}/aeo-optimize` | AI-optimize article for AEO | User | 10/min |
| GET | `/articles/{article_id}/link-suggestions` | Get internal link suggestions | User | — |
| GET | `/articles/health-summary` | Content health overview | User | — |

### Keywords

| Method | Path | Description | Auth | Rate Limit |
|--------|------|-------------|------|------------|
| POST | `/articles/keyword-suggestions` | Get AI keyword suggestions | User | 5/min |
| GET | `/articles/keyword-history` | List cached keyword research | User | — |

### Social Posts (per article)

| Method | Path | Description | Auth | Rate Limit |
|--------|------|-------------|------|------------|
| GET | `/articles/{article_id}/social-posts` | Get social posts for article | User | — |
| POST | `/articles/{article_id}/generate-social-posts` | Generate social posts from article | User | 10/min |
| PUT | `/articles/{article_id}/social-posts` | Update social posts | User | 30/min |

### Revisions

| Method | Path | Description | Auth | Rate Limit |
|--------|------|-------------|------|------------|
| GET | `/articles/{article_id}/revisions` | List article revisions | User | — |
| GET | `/articles/{article_id}/revisions/{revision_id}` | Get specific revision | User | — |
| POST | `/articles/{article_id}/revisions/{revision_id}/restore` | Restore a revision | User | 20/min |

### Export

| Method | Path | Description | Auth | Rate Limit |
|--------|------|-------------|------|------------|
| GET | `/articles/export` | Export all articles (bulk) | User | 10/hour |
| GET | `/articles/{article_id}/export` | Export single article | User | — |

---

## 4. Outlines (`/outlines`)

Content outline creation and management.

| Method | Path | Description | Auth | Rate Limit |
|--------|------|-------------|------|------------|
| POST | `/outlines` | Create new outline | User | — |
| GET | `/outlines` | List outlines (paginated) | User | — |
| GET | `/outlines/{outline_id}` | Get outline by ID | User | — |
| PUT | `/outlines/{outline_id}` | Update outline | User | — |
| DELETE | `/outlines/{outline_id}` | Delete outline | User | — |
| POST | `/outlines/{outline_id}/regenerate` | Regenerate outline via AI | User | — |
| POST | `/outlines/bulk-delete` | Bulk delete outlines | User | — |
| GET | `/outlines/export` | Export all outlines | User | — |
| GET | `/outlines/{outline_id}/export` | Export single outline | User | — |

**POST `/outlines`** — Request:
- `keyword` (string, required)
- `project_id` (string, required)
- `target_audience` (string, optional)
- `content_type` (string, optional)

**Response**: `OutlineResponse` with `id`, `keyword`, `title`, `sections` (array), `project_id`, `status`, `created_at`.

---

## 5. Images (`/images`)

AI-generated image management.

| Method | Path | Description | Auth | Rate Limit |
|--------|------|-------------|------|------------|
| POST | `/images/generate` | Generate image (returns 202, async) | User | — |
| GET | `/images` | List generated images | User | — |
| GET | `/images/{image_id}` | Get image by ID | User | — |
| DELETE | `/images/{image_id}` | Delete image | User | — |
| POST | `/images/bulk-delete` | Bulk delete images | User | — |
| POST | `/images/{image_id}/set-featured` | Set as article featured image | User | — |

**POST `/images/generate`** — Request:
- `prompt` (string, required)
- `article_id` (string, optional)
- `project_id` (string, required)

**Response** (202): `{ "task_id": "...", "status": "processing" }`

---

## 6. Analytics (`/analytics`)

Google Search Console integration, keyword/page analytics, content decay, AEO, and revenue tracking.

### GSC Connection

| Method | Path | Description | Auth | Rate Limit |
|--------|------|-------------|------|------------|
| GET | `/analytics/gsc/auth-url` | Get GSC OAuth authorization URL | User | — |
| GET | `/analytics/gsc/callback` | GSC OAuth callback | User | — |
| POST | `/analytics/gsc/disconnect` | Disconnect GSC | User | — |
| GET | `/analytics/gsc/status` | Get GSC connection status | User | — |
| GET | `/analytics/gsc/sites` | List available GSC sites | User | — |
| POST | `/analytics/gsc/select-site` | Select GSC site to track | User | — |
| POST | `/analytics/gsc/sync` | Trigger manual GSC data sync | User | — |

**POST `/analytics/gsc/select-site`** — Request: `site_url` (string).

### Performance Data

| Method | Path | Description | Auth | Rate Limit |
|--------|------|-------------|------|------------|
| GET | `/analytics/summary` | Analytics summary (clicks, impressions, CTR, position) | User | — |
| GET | `/analytics/daily` | Daily analytics time series | User | — |
| GET | `/analytics/keywords` | Keyword rankings (paginated) | User | — |
| GET | `/analytics/pages` | Page performance (paginated) | User | — |
| GET | `/analytics/device-breakdown` | Traffic by device type | User | — |
| GET | `/analytics/country-breakdown` | Traffic by country | User | — |

**Query params** (common): `project_id`, `date_from`, `date_to`, `page`, `page_size`.

### Article Performance

| Method | Path | Description | Auth | Rate Limit |
|--------|------|-------------|------|------------|
| GET | `/analytics/article-performance` | Performance metrics for all articles | User | — |
| GET | `/analytics/article-performance/{article_id}` | Detailed performance for one article | User | — |
| GET | `/analytics/article-performance/{article_id}/index-status` | Google indexing status | User | — |

### Content Opportunities

| Method | Path | Description | Auth | Rate Limit |
|--------|------|-------------|------|------------|
| GET | `/analytics/opportunities` | Content optimization opportunities | User | — |
| POST | `/analytics/opportunities/suggest` | AI-generated content suggestions | User | — |

### Content Decay Detection

| Method | Path | Description | Auth | Rate Limit |
|--------|------|-------------|------|------------|
| GET | `/analytics/decay/health` | Content health summary | User | — |
| GET | `/analytics/decay/alerts` | List decay alerts | User | — |
| POST | `/analytics/decay/detect` | Trigger decay detection scan | User | — |
| POST | `/analytics/decay/alerts/{alert_id}/read` | Mark alert as read | User | — |
| POST | `/analytics/decay/alerts/{alert_id}/resolve` | Resolve decay alert | User | — |
| POST | `/analytics/decay/alerts/{alert_id}/suggest` | Get recovery suggestions | User | — |
| POST | `/analytics/decay/alerts/mark-all-read` | Mark all alerts as read | User | — |

### AEO (Answer Engine Optimization)

| Method | Path | Description | Auth | Rate Limit |
|--------|------|-------------|------|------------|
| GET | `/analytics/aeo/overview` | AEO overview metrics | User | — |

### Revenue Attribution

| Method | Path | Description | Auth | Rate Limit |
|--------|------|-------------|------|------------|
| GET | `/analytics/revenue/overview` | Revenue overview dashboard | User | — |
| GET | `/analytics/revenue/by-article` | Revenue attribution by article | User | — |
| GET | `/analytics/revenue/by-keyword` | Revenue attribution by keyword | User | — |
| POST | `/analytics/revenue/goals` | Create conversion goal | User | — |
| GET | `/analytics/revenue/goals` | List conversion goals | User | — |
| PUT | `/analytics/revenue/goals/{goal_id}` | Update conversion goal | User | — |
| DELETE | `/analytics/revenue/goals/{goal_id}` | Delete conversion goal | User | — |
| POST | `/analytics/revenue/import` | Import conversion data | User | — |
| POST | `/analytics/revenue/report` | Generate revenue report | User | — |

---

## 7. Billing (`/billing`)

Subscription management via LemonSqueezy.

| Method | Path | Description | Auth | Rate Limit |
|--------|------|-------------|------|------------|
| GET | `/billing/pricing` | Get pricing plans and variant IDs | Public | — |
| GET | `/billing/subscription` | Get current subscription status | User | — |
| POST | `/billing/checkout` | Create checkout session (overlay URL) | User | — |
| POST | `/billing/portal` | Get LemonSqueezy customer portal URL | User | — |
| POST | `/billing/cancel` | Cancel subscription (grace period) | User | — |
| POST | `/billing/refund` | Request refund (14-day window) | User | — |
| POST | `/billing/webhook` | LemonSqueezy webhook handler | Public | — |

**POST `/billing/checkout`** — Request:
- `variant_id` (int, required)
- `redirect_url` (string, optional)

**POST `/billing/webhook`** — Validates HMAC SHA-256 signature. Processes `subscription_created`, `subscription_updated`, `subscription_expired`, `subscription_payment_success` events.

### Admin Refund Blocklist

| Method | Path | Description | Auth | Rate Limit |
|--------|------|-------------|------|------------|
| GET | `/billing/admin/refund-blocked-emails` | List blocked emails | Admin | — |
| POST | `/billing/admin/refund-blocked-emails` | Add email to blocklist | Admin | — |
| DELETE | `/billing/admin/refund-blocked-emails/{email}` | Remove from blocklist | Admin | — |

---

## 8. WordPress (`/wordpress`)

WordPress publishing integration. **Requires: starter+ tier.**

| Method | Path | Description | Auth | Rate Limit |
|--------|------|-------------|------|------------|
| POST | `/wordpress/connect` | Connect WordPress site | User (starter+) | — |
| POST | `/wordpress/disconnect` | Disconnect WordPress site | User (starter+) | — |
| GET | `/wordpress/status` | Get WordPress connection status | User (starter+) | — |
| GET | `/wordpress/categories` | List WordPress categories | User (starter+) | — |
| GET | `/wordpress/tags` | List WordPress tags | User (starter+) | — |
| POST | `/wordpress/publish` | Publish article to WordPress | User (starter+) | — |
| POST | `/wordpress/upload-media` | Upload media to WordPress | User (starter+) | — |

**POST `/wordpress/connect`** — Request:
- `site_url` (string, required, SSRF-validated)
- `username` (string, required)
- `application_password` (string, required)

**POST `/wordpress/publish`** — Request:
- `article_id` (string, required)
- `category_ids` (int[], optional)
- `tag_ids` (int[], optional)
- `status` (string: `"publish"` or `"draft"`)
- `featured_image_url` (string, optional)

---

## 9. Knowledge Base (`/knowledge`)

RAG knowledge base for article generation. **Requires: professional+ tier.**

| Method | Path | Description | Auth | Rate Limit |
|--------|------|-------------|------|------------|
| POST | `/knowledge/upload` | Upload knowledge source (file/URL) | User (pro+) | — |
| GET | `/knowledge/sources` | List knowledge sources | User (pro+) | — |
| GET | `/knowledge/sources/{source_id}` | Get knowledge source details | User (pro+) | — |
| PUT | `/knowledge/sources/{source_id}` | Update knowledge source | User (pro+) | — |
| DELETE | `/knowledge/sources/{source_id}` | Delete knowledge source | User (pro+) | — |
| POST | `/knowledge/query` | Query knowledge base (semantic search) | User (pro+) | — |
| GET | `/knowledge/stats` | Knowledge base statistics | User (pro+) | — |
| POST | `/knowledge/sources/{source_id}/reprocess` | Reprocess a source | User (pro+) | — |

**POST `/knowledge/upload`** — Request: multipart file or `{ "url": "..." }`.
**POST `/knowledge/query`** — Request: `query` (string), `project_id` (string), `top_k` (int, default 5).

---

## 10. Social Media (`/social`)

Social account management, post scheduling, and analytics.

### Account Management

| Method | Path | Description | Auth | Rate Limit |
|--------|------|-------------|------|------------|
| GET | `/social/accounts` | List connected social accounts | User | — |
| GET | `/social/{platform}/connect` | Get OAuth URL for platform | User | 10/min |
| GET | `/social/{platform}/callback` | OAuth callback handler | User | 20/min |
| DELETE | `/social/accounts/{account_id}` | Disconnect social account | User | 5/min |
| POST | `/social/accounts/{account_id}/verify` | Verify account token validity | User | 20/min |

Supported platforms: `facebook`, `twitter`, `linkedin`.

### Post Management

| Method | Path | Description | Auth | Rate Limit |
|--------|------|-------------|------|------------|
| POST | `/social/posts` | Create scheduled post | User | 30/min |
| GET | `/social/posts` | List scheduled posts | User | — |
| GET | `/social/posts/{post_id}` | Get post details | User | — |
| PUT | `/social/posts/{post_id}` | Update scheduled post | User | 30/min |
| DELETE | `/social/posts/{post_id}` | Delete scheduled post | User | 5/min |
| POST | `/social/posts/{post_id}/publish-now` | Publish post immediately | User | 20/min |

**POST `/social/posts`** — Request:
- `content` (string, required)
- `platform` (string, required)
- `account_id` (string, required)
- `scheduled_at` (datetime, optional)
- `article_id` (string, optional)
- `project_id` (string, required)

### Calendar & Analytics

| Method | Path | Description | Auth | Rate Limit |
|--------|------|-------------|------|------------|
| GET | `/social/calendar` | Get posting calendar | User | — |
| GET | `/social/stats` | Social posting statistics | User | — |
| GET | `/social/posts/{post_id}/analytics` | Get post engagement analytics | User | — |
| POST | `/social/preview` | Preview post rendering | User | 20/min |
| GET | `/social/best-times` | Get best posting times by platform | User | — |

### Facebook Compliance

| Method | Path | Description | Auth | Rate Limit |
|--------|------|-------------|------|------------|
| POST | `/social/facebook/data-deletion` | Facebook data deletion callback | Public | 20/min |

---

## 11. Projects (`/projects`)

Multi-project workspace management.

| Method | Path | Description | Auth | Rate Limit |
|--------|------|-------------|------|------------|
| POST | `/projects` | Create new project | User | — |
| GET | `/projects` | List user's projects | User | — |
| GET | `/projects/{project_id}` | Get project details | User | — |
| PUT | `/projects/{project_id}` | Update project | User | — |
| DELETE | `/projects/{project_id}` | Delete project (soft) | User | — |
| PUT | `/projects/{project_id}/brand-voice` | Update brand voice settings | User | — |
| POST | `/projects/{project_id}/switch` | Switch active project | User | — |

**POST `/projects`** — Request:
- `name` (string, required)
- `website_url` (string, optional)
- `description` (string, optional)

**Response**: `{ "projects": [...], "total": N, "page": N, "total_pages": N }`

### Team Members

| Method | Path | Description | Auth | Rate Limit |
|--------|------|-------------|------|------------|
| GET | `/projects/{project_id}/members` | List project members | User | — |
| PUT | `/projects/{project_id}/members/{user_id}` | Update member role | User (owner/admin) | — |
| DELETE | `/projects/{project_id}/members/{user_id}` | Remove member | User (owner/admin) | — |
| POST | `/projects/{project_id}/leave` | Leave project | User | — |
| POST | `/projects/{project_id}/transfer` | Transfer ownership | User (owner) | — |

Valid roles: `owner`, `admin`, `editor`, `viewer`.

---

## 12. Project Invitations (`/projects/{project_id}/invitations`)

Team invitation management.

| Method | Path | Description | Auth | Rate Limit |
|--------|------|-------------|------|------------|
| GET | `/projects/{project_id}/invitations` | List pending invitations | User (owner/admin) | — |
| POST | `/projects/{project_id}/invitations` | Create invitation | User (owner/admin) | — |
| DELETE | `/projects/{project_id}/invitations/{invitation_id}` | Revoke invitation | User (owner/admin) | — |
| POST | `/projects/{project_id}/invitations/{invitation_id}/resend` | Resend invitation email | User (owner/admin) | — |

**POST** — Request: `email` (string), `role` (string: admin/editor/viewer).

### Public Invitation Endpoints

| Method | Path | Description | Auth | Rate Limit |
|--------|------|-------------|------|------------|
| GET | `/invitations/{token}` | Get invitation details by token | Public | — |
| POST | `/invitations/{token}/accept` | Accept invitation | User | — |

---

## 13. Notifications (`/notifications`)

Generation status, task tracking, and email preferences.

| Method | Path | Description | Auth | Rate Limit |
|--------|------|-------------|------|------------|
| GET | `/notifications/generation-status` | SSE stream for generation updates | User | — |
| GET | `/notifications/tasks/{task_id}` | Get background task status | User | — |
| GET | `/notifications/preferences` | Get email journey preferences | User | — |
| PUT | `/notifications/preferences` | Update email journey preferences | User | — |
| POST | `/notifications/unsubscribe` | Unsubscribe via JWT token (RFC 8058) | Public | — |
| GET | `/notifications/unsubscribe` | One-click unsubscribe (GET, RFC 8058) | Public | — |
| GET | `/notifications/resubscribe` | Resubscribe via token | Public | — |

**PUT `/notifications/preferences`** — Request:
- `onboarding_emails` (bool)
- `product_update_emails` (bool)
- `usage_alert_emails` (bool)
- `weekly_digest_emails` (bool)
- `retention_emails` (bool)

---

## 14. Bulk Content (`/bulk`)

Programmatic SEO / bulk content workflows.

### Templates

| Method | Path | Description | Auth | Rate Limit |
|--------|------|-------------|------|------------|
| GET | `/bulk/templates` | List bulk templates | User | — |
| POST | `/bulk/templates` | Create bulk template | User | — |
| GET | `/bulk/templates/{template_id}` | Get template details | User | — |
| PUT | `/bulk/templates/{template_id}` | Update template | User | — |

### Jobs

| Method | Path | Description | Auth | Rate Limit |
|--------|------|-------------|------|------------|
| GET | `/bulk/jobs` | List bulk jobs | User | — |
| GET | `/bulk/jobs/{job_id}` | Get job status and progress | User | — |
| POST | `/bulk/jobs/{job_id}/create-outlines` | Generate outlines from job | User | — |
| POST | `/bulk/jobs/{job_id}/cancel` | Cancel running job | User | — |
| POST | `/bulk/jobs/{job_id}/retry-failed` | Retry failed items in job | User | — |

---

## 15. Agency (`/agency`)

White-label agency mode. **Requires: enterprise tier.**

### Agency Profile

| Method | Path | Description | Auth | Rate Limit |
|--------|------|-------------|------|------------|
| POST | `/agency/profile` | Create agency profile | User (enterprise) | 20/min |
| GET | `/agency/profile` | Get agency profile | User (enterprise) | — |
| PUT | `/agency/profile` | Update agency profile | User (enterprise) | 30/min |
| DELETE | `/agency/profile` | Delete agency profile | User (enterprise) | 5/min |

**POST/PUT `/agency/profile`** — Request:
- `agency_name` (string, required)
- `logo_url` (string, optional)
- `primary_color` (string, optional)
- `custom_domain` (string, optional)

### Client Workspaces

| Method | Path | Description | Auth | Rate Limit |
|--------|------|-------------|------|------------|
| GET | `/agency/clients` | List client workspaces | User (enterprise) | — |
| POST | `/agency/clients` | Create client workspace | User (enterprise) | 20/min |
| GET | `/agency/clients/{workspace_id}` | Get client workspace | User (enterprise) | — |
| PUT | `/agency/clients/{workspace_id}` | Update client workspace | User (enterprise) | 30/min |
| DELETE | `/agency/clients/{workspace_id}` | Delete client workspace | User (enterprise) | 5/min |
| POST | `/agency/clients/{workspace_id}/enable-portal` | Enable client portal | User (enterprise) | 5/min |
| POST | `/agency/clients/{workspace_id}/disable-portal` | Disable client portal | User (enterprise) | 5/min |

### Report Templates

| Method | Path | Description | Auth | Rate Limit |
|--------|------|-------------|------|------------|
| GET | `/agency/templates` | List report templates | User (enterprise) | — |
| POST | `/agency/templates` | Create report template | User (enterprise) | 20/min |
| PUT | `/agency/templates/{template_id}` | Update report template | User (enterprise) | 30/min |
| DELETE | `/agency/templates/{template_id}` | Delete report template | User (enterprise) | 5/min |

### Reports

| Method | Path | Description | Auth | Rate Limit |
|--------|------|-------------|------|------------|
| POST | `/agency/reports/generate` | Generate client report | User (enterprise) | 20/min |
| GET | `/agency/reports` | List generated reports | User (enterprise) | — |
| GET | `/agency/reports/{report_id}` | Get report details | User (enterprise) | — |

### Client Portal (Public)

| Method | Path | Description | Auth | Rate Limit |
|--------|------|-------------|------|------------|
| GET | `/agency/portal/{token}` | Access client portal via token | Public | 30/min |

---

## 16. Competitor Analysis (`/competitors`)

Keyword extraction, gap analysis, and competitive intelligence.

| Method | Path | Description | Auth | Rate Limit |
|--------|------|-------------|------|------------|
| POST | `/competitors/analyze` | Run competitor analysis | User | — |
| GET | `/competitors` | List previous analyses | User | — |
| GET | `/competitors/{analysis_id}` | Get analysis details | User | — |
| DELETE | `/competitors/{analysis_id}` | Delete analysis | User | — |
| GET | `/competitors/{analysis_id}/keywords` | Get extracted keywords | User | — |
| GET | `/competitors/{analysis_id}/gaps` | Get keyword gaps | User | — |

**POST `/competitors/analyze`** — Request:
- `competitor_url` (string, required)
- `project_id` (string, required)

---

## 17. Site Audit (`/site-audit`)

Website crawling and technical SEO issue detection.

| Method | Path | Description | Auth | Rate Limit |
|--------|------|-------------|------|------------|
| POST | `/site-audit/start` | Start new site audit | User | — |
| GET | `/site-audit` | List audits | User | — |
| GET | `/site-audit/{audit_id}` | Get audit summary | User | — |
| GET | `/site-audit/{audit_id}/pages` | List crawled pages | User | — |
| GET | `/site-audit/{audit_id}/issues` | List detected issues | User | — |
| DELETE | `/site-audit/{audit_id}` | Delete audit | User | — |
| GET | `/site-audit/{audit_id}/export` | Export audit as CSV | User | — |

**POST `/site-audit/start`** — Request:
- `url` (string, required)
- `project_id` (string, required)
- `max_pages` (int, optional, default 100)

22 issue detectors: missing titles, duplicate meta, broken links, slow pages, missing alt text, etc.

---

## 18. Article Templates (`/templates`)

Reusable article generation templates. **Requires: professional+ tier.**

| Method | Path | Description | Auth | Rate Limit |
|--------|------|-------------|------|------------|
| GET | `/templates` | List templates | User (pro+) | — |
| POST | `/templates` | Create template | User (pro+) | — |
| GET | `/templates/{template_id}` | Get template | User (pro+) | — |
| PUT | `/templates/{template_id}` | Update template | User (pro+) | — |
| DELETE | `/templates/{template_id}` | Delete template | User (pro+) | — |

**POST `/templates`** — Request:
- `name` (string, required)
- `description` (string, optional)
- `structure` (object, content structure definition)
- `project_id` (string, required)

---

## 19. SEO Reports (`/reports`)

Generated SEO performance reports. **Requires: professional+ tier.**

| Method | Path | Description | Auth | Rate Limit |
|--------|------|-------------|------|------------|
| GET | `/reports` | List SEO reports | User (pro+) | — |
| POST | `/reports` | Create SEO report | User (pro+) | — |
| GET | `/reports/{report_id}` | Get report | User (pro+) | — |
| DELETE | `/reports/{report_id}` | Delete report | User (pro+) | — |

---

## 20. Tags (`/tags`)

Tag management for articles and outlines.

### Tag CRUD

| Method | Path | Description | Auth | Rate Limit |
|--------|------|-------------|------|------------|
| GET | `/tags` | List tags | User | — |
| POST | `/tags` | Create tag | User | — |
| PUT | `/tags/{tag_id}` | Update tag | User | — |
| DELETE | `/tags/{tag_id}` | Delete tag | User | — |

### Article Tags

| Method | Path | Description | Auth | Rate Limit |
|--------|------|-------------|------|------------|
| POST | `/tags/articles/{article_id}` | Assign tags to article | User | — |
| GET | `/tags/articles/{article_id}` | Get article's tags | User | — |

### Outline Tags

| Method | Path | Description | Auth | Rate Limit |
|--------|------|-------------|------|------------|
| POST | `/tags/outlines/{outline_id}` | Assign tags to outline | User | — |
| GET | `/tags/outlines/{outline_id}` | Get outline's tags | User | — |

---

## 21. Blog (`/blog`)

Public blog with RSS feed (marketing site content).

| Method | Path | Description | Auth | Rate Limit |
|--------|------|-------------|------|------------|
| GET | `/blog/posts` | List published blog posts | Public | — |
| GET | `/blog/posts/{slug}` | Get blog post by slug | Public | — |
| GET | `/blog/categories` | List blog categories | Public | — |
| GET | `/blog/tags` | List blog tags | Public | — |
| GET | `/blog/rss` | RSS feed (XML) | Public | — |

**GET `/blog/posts`** — Query params: `page`, `page_size`, `category`, `tag`.

**Response**: Posts include `title`, `slug`, `excerpt`, `content_html`, `featured_image_url`, `author`, `published_at`, `categories`, `tags`.

---

## 22. Admin — Users (`/admin/users`)

User management and audit logging. **Requires: admin role.**

| Method | Path | Description | Auth | Rate Limit |
|--------|------|-------------|------|------------|
| GET | `/admin/users/users` | List all users (paginated, searchable) | Admin | — |
| GET | `/admin/users/users/{user_id}` | Get user details | Admin | — |
| PUT | `/admin/users/users/{user_id}` | Update user (role, tier, etc.) | Admin | 20/min |
| POST | `/admin/users/users/{user_id}/suspend` | Suspend user account | Admin | 20/min |
| POST | `/admin/users/users/{user_id}/unsuspend` | Unsuspend user account | Admin | 20/min |
| DELETE | `/admin/users/users/{user_id}` | Hard delete user | Super Admin | 20/min |
| POST | `/admin/users/users/{user_id}/reset-password` | Force password reset | Admin | 20/min |
| POST | `/admin/users/users/{user_id}/reset-usage` | Reset user's usage counters | Admin | 20/min |
| GET | `/admin/users/audit-logs` | List admin audit logs | Admin | — |

**GET `/admin/users/users`** — Query params: `page`, `page_size`, `search`, `role`, `subscription_tier`, `is_active`, `sort_by`, `sort_order`.

**PUT `/admin/users/users/{user_id}`** — Request:
- `role` (string, optional)
- `subscription_tier` (string, optional)
- `is_active` (bool, optional)
- `name` (string, optional)

---

## 23. Admin — Content (`/admin/content`)

Cross-user content management. **Requires: admin role.**

| Method | Path | Description | Auth | Rate Limit |
|--------|------|-------------|------|------------|
| GET | `/admin/content/articles` | List all articles (all users) | Admin | — |
| GET | `/admin/content/articles/{article_id}` | Get article detail | Admin | — |
| DELETE | `/admin/content/articles/{article_id}` | Delete article | Admin | 20/min |
| GET | `/admin/content/outlines` | List all outlines | Admin | — |
| DELETE | `/admin/content/outlines/{outline_id}` | Delete outline | Admin | 20/min |
| GET | `/admin/content/images` | List all images | Admin | — |
| DELETE | `/admin/content/images/{image_id}` | Delete image | Admin | 20/min |
| GET | `/admin/content/social-posts` | List all social posts | Admin | — |
| DELETE | `/admin/content/social-posts/{post_id}` | Delete social post | Admin | 20/min |
| POST | `/admin/content/bulk-delete` | Bulk delete content | Admin | 10/min |

**POST `/admin/content/bulk-delete`** — Request:
- `content_type` (string: `"article"`, `"outline"`, `"image"`, `"social_post"`)
- `ids` (string[], required)

---

## 24. Admin — Analytics (`/admin/analytics`)

Platform-wide analytics dashboard. **Requires: admin role.**

| Method | Path | Description | Auth | Rate Limit |
|--------|------|-------------|------|------------|
| GET | `/admin/analytics/dashboard` | Dashboard overview stats | Admin | 10/min |
| GET | `/admin/analytics/users` | User growth and activity analytics | Admin | 10/min |
| GET | `/admin/analytics/content` | Content creation analytics | Admin | 10/min |
| GET | `/admin/analytics/revenue` | Revenue and subscription analytics | Admin | 10/min |
| GET | `/admin/analytics/system` | System health metrics | Admin | 10/min |

**Dashboard response** includes: `total_users`, `active_users`, `total_articles`, `total_outlines`, `total_images`, `revenue_summary`, `recent_signups`, `system_health`.

---

## 25. Admin — Blog (`/admin/blog`)

Blog content management (admin CMS). **Requires: admin role.**

### Posts

| Method | Path | Description | Auth | Rate Limit |
|--------|------|-------------|------|------------|
| GET | `/admin/blog/posts` | List all blog posts (incl. drafts) | Admin | 60/min |
| POST | `/admin/blog/posts` | Create blog post | Admin | 30/min |
| GET | `/admin/blog/posts/{post_id}` | Get blog post | Admin | 60/min |
| PATCH | `/admin/blog/posts/{post_id}` | Update blog post | Admin | 30/min |
| DELETE | `/admin/blog/posts/{post_id}` | Delete blog post | Admin | 20/min |
| POST | `/admin/blog/posts/{post_id}/publish` | Publish draft post | Admin | 20/min |
| POST | `/admin/blog/posts/{post_id}/unpublish` | Unpublish post | Admin | 20/min |
| POST | `/admin/blog/posts/from-article` | Create blog post from user article | Admin | 20/min |
| POST | `/admin/blog/posts/persist-images` | Download and persist external images | Admin | 5/min |

### Categories

| Method | Path | Description | Auth | Rate Limit |
|--------|------|-------------|------|------------|
| GET | `/admin/blog/categories` | List categories | Admin | 60/min |
| POST | `/admin/blog/categories` | Create category | Admin | 20/min |
| PATCH | `/admin/blog/categories/{cat_id}` | Update category | Admin | 20/min |
| DELETE | `/admin/blog/categories/{cat_id}` | Delete category | Admin | 10/min |

### Tags

| Method | Path | Description | Auth | Rate Limit |
|--------|------|-------------|------|------------|
| GET | `/admin/blog/tags` | List tags | Admin | 60/min |
| POST | `/admin/blog/tags` | Create tag | Admin | 20/min |
| DELETE | `/admin/blog/tags/{tag_id}` | Delete tag | Admin | 10/min |

### AI Content Generation

| Method | Path | Description | Auth | Rate Limit |
|--------|------|-------------|------|------------|
| POST | `/admin/blog/generate-content` | Generate blog content via AI | Admin | 10/min |

---

## 26. Admin — Generations (`/admin/generations`)

Generation log monitoring. **Requires: admin role.**

| Method | Path | Description | Auth | Rate Limit |
|--------|------|-------------|------|------------|
| GET | `/admin/generations` | List generation logs (paginated) | Admin | — |
| GET | `/admin/generations/stats` | Generation statistics | Admin | — |

**Query params**: `page`, `page_size`, `user_id`, `generation_type`, `status`.

---

## 27. Admin — Alerts (`/admin/alerts`)

System alert management. **Requires: admin role.**

| Method | Path | Description | Auth | Rate Limit |
|--------|------|-------------|------|------------|
| GET | `/admin/alerts/count` | Get unread/critical alert counts | Admin | — |
| GET | `/admin/alerts` | List alerts (paginated, filterable) | Admin | — |
| PUT | `/admin/alerts/{alert_id}` | Update alert (mark read/resolved) | Admin | 20/min |
| POST | `/admin/alerts/mark-all-read` | Mark all alerts as read | Admin | 20/min |

**GET `/admin/alerts`** — Query params: `page`, `page_size`, `is_read`, `severity`, `alert_type`.

**Response**: `AdminAlertResponse` with `id`, `alert_type`, `severity`, `title`, `message`, `resource_type`, `resource_id`, `user_id`, `is_read`, `is_resolved`, `created_at`, `user_email`, `user_name`.

---

## 28. Admin — Error Logs (`/admin/error-logs`)

System error log monitoring and resolution. **Requires: admin role.**

| Method | Path | Description | Auth | Rate Limit |
|--------|------|-------------|------|------------|
| GET | `/admin/error-logs` | List error logs (paginated, filterable) | Admin | — |
| GET | `/admin/error-logs/filters/options` | Get filter dropdown values | Admin | — |
| GET | `/admin/error-logs/stats` | Aggregated error statistics | Admin | — |
| GET | `/admin/error-logs/{error_id}` | Get error log by ID | Admin | — |
| PUT | `/admin/error-logs/{error_id}` | Resolve/unresolve error | Admin | 20/min |

**GET `/admin/error-logs`** — Query params: `page`, `page_size`, `severity`, `error_type`, `service`, `is_resolved`, `search`.

**Stats response** includes: `total_errors`, `unresolved_errors`, `critical_errors`, `errors_today`, `errors_this_week`, `errors_this_month`, `by_type`, `by_service`, `daily_trend`, `top_recurring`.

---

## 29. Admin — Emails (`/admin/emails`)

Email journey template preview and testing. **Requires: admin role.**

| Method | Path | Description | Auth | Rate Limit |
|--------|------|-------------|------|------------|
| GET | `/admin/emails/templates` | List all email journey templates | Admin | — |
| POST | `/admin/emails/preview` | Preview rendered email template | Admin | 20/min |
| POST | `/admin/emails/send-test` | Send test email to address | Admin | 20/min |

**POST `/admin/emails/preview`** — Request:
- `email_key` (string, required, e.g. `"onboarding.welcome"`)
- `user_name` (string, default `"Test User"`)

**POST `/admin/emails/send-test`** — Request:
- `email_key` (string, required)
- `recipient_email` (string, required)
- `user_name` (string, default `"Test User"`)

Available template keys: `onboarding.welcome`, `onboarding.first_outline_nudge`, `onboarding.outline_to_article`, `onboarding.outline_reminder`, `onboarding.connect_tools`, `onboarding.week_one_recap`, `conversion.usage_80`, `conversion.usage_100`, `conversion.power_user`, `conversion.audit_upsell`, `retention.inactive_7d`, `retention.inactive_21d`, `retention.inactive_45d`, `ongoing.weekly_digest`, `ongoing.content_decay`, `system.unsubscribe_confirmation`, `system.resubscribe_confirmation`.

---

## Common Response Patterns

### Paginated Lists

All paginated endpoints return:
```json
{
  "items": [...],
  "total": 100,
  "page": 1,
  "page_size": 20,
  "pages": 5
}
```

### Error Responses

```json
{
  "detail": "Error message describing what went wrong"
}
```

| Status Code | Meaning |
|-------------|---------|
| 400 | Bad request / validation error |
| 401 | Not authenticated |
| 403 | Forbidden (insufficient role or tier) |
| 404 | Resource not found |
| 409 | Conflict (duplicate resource) |
| 422 | Unprocessable entity (Pydantic validation) |
| 429 | Rate limit exceeded |
| 500 | Internal server error |

### Soft Delete

Most resources use soft deletion (`deleted_at` timestamp). Deleted items are excluded from list queries but remain in the database for recovery.

### Ownership Scoping

User endpoints automatically filter by the authenticated user's ownership. The `scoped_query()` helper ensures users can only access their own resources within their active project.
