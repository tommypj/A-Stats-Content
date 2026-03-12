# Backend Architecture

## 1. Overview

A-Stats Engine is the backend for the A-Stats-Online SaaS platform -- an AI-powered content generation and SEO analytics system. It is built on:

- **FastAPI** (async Python web framework) with Uvicorn
- **SQLAlchemy 2.0** (async ORM with `asyncpg` driver)
- **PostgreSQL** (primary database)
- **Redis** (caching, rate limiting, task queues, distributed locks)
- **Alembic** (database migrations)

Deployed on **Railway** with auto-deploy on push to `master`. The frontend (Next.js 14) is deployed separately on Vercel.

Application entry point: `backend/main.py`
Application version: 2.0.0

---

## 2. Directory Structure

```
backend/
├── main.py                          # FastAPI app, lifespan, middleware, exception handlers
├── start.sh                         # Railway startup script
├── Dockerfile                       # Container build
├── pyproject.toml                   # Python dependencies
├── railway.toml                     # Railway deployment config
├── alembic.ini                      # Alembic configuration
│
├── adapters/                        # External service integrations
│   ├── ai/                          # AI model adapters
│   │   ├── anthropic_adapter.py     #   Claude Sonnet/Haiku (articles, fact-check, image prompts)
│   │   ├── gemini_adapter.py        #   Gemini Flash (SERP analysis, research, SEO check)
│   │   ├── openai_adapter.py        #   GPT-4o mini (structured outline generation)
│   │   └── replicate_adapter.py     #   Ideogram V3 Turbo (image generation)
│   ├── cms/
│   │   └── wordpress_adapter.py     #   WordPress REST API (publish, featured image, SEO meta)
│   ├── email/
│   │   ├── resend_adapter.py        #   Resend API (transactional email)
│   │   └── journey_templates.py     #   HTML email templates for lifecycle journeys
│   ├── knowledge/
│   │   ├── chroma_adapter.py        #   ChromaDB HTTP client (vector storage/retrieval)
│   │   ├── document_processor.py    #   Text extraction and chunking (PDF, TXT, MD, DOCX, HTML)
│   │   └── embedding_service.py     #   OpenAI text-embedding-3-small (or mock for dev)
│   ├── payments/
│   │   └── lemonsqueezy_adapter.py  #   LemonSqueezy API (checkout, subscription, refund, webhooks)
│   ├── search/
│   │   └── gsc_adapter.py           #   Google Search Console API (keyword rankings, page perf)
│   ├── social/
│   │   ├── base.py                  #   Abstract SocialAdapter base class + data structures
│   │   ├── twitter_adapter.py       #   Twitter/X OAuth 2.0 + tweet posting
│   │   ├── linkedin_adapter.py      #   LinkedIn OAuth 2.0 + share posting
│   │   ├── facebook_adapter.py      #   Facebook Graph API + page posting
│   │   └── instagram_adapter.py     #   Instagram Graph API (via Facebook)
│   └── storage/
│       └── image_storage.py         #   Local filesystem + S3 storage adapters
│
├── api/                             # HTTP layer
│   ├── routes/                      #   33 route modules (see below)
│   │   ├── __init__.py              #     Central router registration
│   │   ├── auth.py                  #     Login, register, JWT, OAuth, verify, password reset
│   │   ├── articles.py              #     CRUD, generate, improve SEO, regenerate sections
│   │   ├── outlines.py              #     CRUD, generate, bulk
│   │   ├── images.py                #     Generate, list, delete AI images
│   │   ├── billing.py               #     LemonSqueezy checkout, webhooks, refund, subscription
│   │   ├── analytics.py             #     GSC data, content decay, AEO scores
│   │   ├── social.py                #     Social accounts, scheduled posts, OAuth callbacks
│   │   ├── wordpress.py             #     WordPress connection, publish, categories
│   │   ├── knowledge.py             #     Knowledge vault upload, query, sources
│   │   ├── projects.py              #     Project CRUD, members, switching
│   │   ├── project_invitations.py   #     Invite, accept, revoke, resend
│   │   ├── bulk.py                  #     Bulk generation jobs (outlines + articles)
│   │   ├── competitor.py            #     Competitor analysis, gap analysis
│   │   ├── agency.py                #     Agency mode, client workspaces, reports
│   │   ├── site_audit.py            #     Site audit CRUD, crawl trigger, issues
│   │   ├── blog.py                  #     Public blog posts, RSS, categories, tags
│   │   ├── templates.py             #     Article template CRUD
│   │   ├── reports.py               #     SEO report generation and management
│   │   ├── tags.py                  #     Tag CRUD, article/outline tagging
│   │   ├── notifications.py         #     Notification preferences, email journey prefs
│   │   ├── health.py                #     Health check endpoint
│   │   ├── admin_users.py           #     Admin user management (suspend, delete, role change)
│   │   ├── admin_content.py         #     Admin content moderation
│   │   ├── admin_analytics.py       #     Admin platform analytics
│   │   ├── admin_generations.py     #     Admin generation logs and stats
│   │   ├── admin_alerts.py          #     Admin alert management
│   │   ├── admin_emails.py          #     Admin email template preview and test send
│   │   ├── admin_error_logs.py      #     Admin system error log viewer
│   │   └── admin_blog.py            #     Admin blog post management
│   ├── schemas/                     #   Pydantic request/response schemas (18 modules)
│   │   ├── auth.py, billing.py, content.py, analytics.py, social.py,
│   │   │   knowledge.py, project.py, competitor.py, site_audit.py,
│   │   │   blog.py, template.py, tag.py, report.py, generation.py,
│   │   │   admin.py, admin_content.py, error_log.py,
│   │   │   notification_preferences.py, wordpress.py
│   │   └── __init__.py
│   ├── dependencies.py              #   Tier checking (require_tier, get_effective_tier)
│   ├── deps_admin.py                #   Admin auth dependencies (get_current_admin_user)
│   ├── deps_project.py              #   Project membership/access verification
│   ├── utils.py                     #   scoped_query(), escape_like()
│   ├── oauth_helpers.py             #   OAuth state management helpers
│   └── middleware/
│       └── rate_limit.py            #   slowapi rate limiter configuration
│
├── core/                            # Domain logic and security (no framework deps)
│   ├── domain/
│   │   ├── content.py               #   Content domain types
│   │   ├── subscription.py          #   Subscription domain logic
│   │   └── user.py                  #   User domain types
│   ├── security/
│   │   ├── tokens.py                #   JWT TokenService (create/verify access+refresh tokens)
│   │   ├── password.py              #   bcrypt PasswordHasher (hash, verify, needs_rehash)
│   │   └── encryption.py            #   Fernet CredentialEncryption (encrypt/decrypt OAuth tokens)
│   ├── plans.py                     #   Subscription plan limits/features (single source of truth)
│   └── interfaces/                  #   Abstract interfaces (reserved)
│
├── infrastructure/                  # Framework and platform concerns
│   ├── config/
│   │   └── settings.py              #   Pydantic BaseSettings (all env vars, validators)
│   ├── database/
│   │   ├── connection.py            #   Async engine, session factory, get_db dependency
│   │   ├── models/                  #   SQLAlchemy models (26 files, 47+ models)
│   │   │   ├── base.py              #     Base, TimestampMixin, UUIDMixin
│   │   │   ├── user.py              #     User, UserRole, UserStatus, SubscriptionTier
│   │   │   ├── content.py           #     Outline, Article, ArticleRevision, GeneratedImage
│   │   │   ├── analytics.py         #     GSCConnection, KeywordRanking, PagePerformance,
│   │   │   │                        #     DailyAnalytics, ContentDecayAlert
│   │   │   ├── social.py            #     SocialAccount, ScheduledPost, PostTarget
│   │   │   ├── knowledge.py         #     KnowledgeSource, KnowledgeChunk, KnowledgeQuery
│   │   │   ├── project.py           #     Project, ProjectMember, ProjectInvitation
│   │   │   ├── admin.py             #     AdminAuditLog
│   │   │   ├── aeo.py               #     AEOScore, AEOCitation
│   │   │   ├── agency.py            #     AgencyProfile, ClientWorkspace, ReportTemplate,
│   │   │   │                        #     GeneratedReport
│   │   │   ├── blog.py              #     BlogCategory, BlogTag, BlogPostTag, BlogPost
│   │   │   ├── bulk.py              #     ContentTemplate, BulkJob, BulkJobItem
│   │   │   ├── competitor.py        #     CompetitorAnalysis, CompetitorArticle
│   │   │   ├── site_audit.py        #     SiteAudit, AuditPage, AuditIssue
│   │   │   ├── generation.py        #     GenerationLog, AdminAlert
│   │   │   ├── revenue.py           #     ConversionGoal, ContentConversion, RevenueReport
│   │   │   ├── tag.py               #     Tag, ArticleTag, OutlineTag
│   │   │   ├── template.py          #     ArticleTemplate
│   │   │   ├── report.py            #     SEOReport
│   │   │   ├── error_log.py         #     SystemErrorLog
│   │   │   ├── email_journey_event.py  EmailJourneyEvent
│   │   │   ├── notification_preferences.py  NotificationPreferences
│   │   │   ├── keyword_cache.py     #     KeywordResearchCache
│   │   │   ├── refund_blocked_email.py  RefundBlockedEmail
│   │   │   └── __init__.py          #     Re-exports all models
│   │   └── migrations/
│   │       ├── env.py               #   Alembic migration environment
│   │       └── versions/            #   61 migration files (001-060 + placeholders)
│   ├── redis.py                     #   Centralized Redis connection pool (get_redis, get_redis_text)
│   └── logging_config.py            #   JSON/text logging, sensitive data redaction filter
│
├── services/                        # Business logic orchestration
│   ├── content_pipeline.py          #   Multi-model AI content generation pipeline
│   ├── generation_tracker.py        #   Usage tracking, generation logs, admin alerts
│   ├── aeo_scoring.py               #   Answer Engine Optimization scoring
│   ├── content_decay.py             #   Content decay detection from GSC data
│   ├── content_scheduler.py         #   Content calendar auto-publish scheduler
│   ├── knowledge_service.py         #   Knowledge vault RAG operations
│   ├── knowledge_processor.py       #   Document processing orchestration
│   ├── site_auditor.py              #   BFS website crawler + 22 SEO issue detectors
│   ├── competitor_analyzer.py       #   Sitemap crawling + algorithmic keyword extraction
│   ├── revenue_attribution.py       #   Content-to-revenue ROI calculation
│   ├── email_journey.py             #   Email journey event orchestrator
│   ├── email_journey_worker.py      #   Background worker for sending journey emails
│   ├── email_journey_unsubscribe.py #   JWT-based unsubscribe token generation/verification
│   ├── error_logger.py              #   Centralized error logging to system_error_logs
│   ├── post_queue.py                #   Redis sorted-set queue for social post scheduling
│   ├── schema_generator.py          #   JSON-LD structured data (Article + FAQPage schemas)
│   ├── social_scheduler.py          #   Background social media post publisher
│   ├── bulk_generation.py           #   Bulk content generation job processing
│   ├── pagespeed.py                 #   Google PageSpeed Insights API client
│   ├── project_invitations.py       #   Project invitation logic
│   └── task_queue.py                #   In-memory async task queue for background operations
│
├── prompts/                         # AI prompt templates (versioned via manifest)
│   └── loader.py                    #   Prompt loader with version tracking
│
├── data/                            # Runtime data (uploads, ChromaDB persistence)
│   ├── uploads/                     #   Local image storage
│   └── chroma/                      #   ChromaDB persistence directory
│
├── storage/                         # Additional storage artifacts
│
└── tests/                           # Test suite
    ├── conftest.py                  #   Shared fixtures, test database setup
    ├── unit/                        #   18 unit test files
    ├── integration/                 #   15 integration test files
    └── services/                    #   2 service test files
```

---

## 3. Database Models

All models inherit from `Base` (SQLAlchemy `DeclarativeBase`). Most also use `TimestampMixin` which adds `created_at` and `updated_at` columns with `server_default=func.now()` and `onupdate=func.now()`. Primary keys are UUID strings generated via `uuid4()`.

### 3.1 User (`users`)

**File:** `infrastructure/database/models/user.py`

| Field | Type | Notes |
|---|---|---|
| `id` | UUID (PK) | |
| `email` | String(255) | unique, indexed |
| `name` | String(255) | |
| `avatar_url` | String(500) | nullable |
| `password_hash` | Text | bcrypt hash |
| `role` | String(50) | `user`, `admin`, `super_admin` |
| `status` | String(50) | `pending`, `active`, `suspended`, `deleted` |
| `email_verified` | Boolean | |
| `email_verification_token` | Text | nullable |
| `email_verification_expires` | DateTime(tz) | nullable |
| `password_reset_token` | Text | nullable |
| `password_reset_expires` | DateTime(tz) | nullable |
| `password_changed_at` | DateTime(tz) | bumped on password change to invalidate tokens |
| `subscription_tier` | String(50) | `free`, `starter`, `professional`, `enterprise` |
| `subscription_status` | String(50) | `active`, `cancelled`, `paused`, `past_due`, `expired` |
| `subscription_expires` | DateTime(tz) | nullable |
| `lemonsqueezy_customer_id` | String(255) | unique, nullable |
| `lemonsqueezy_subscription_id` | String(255) | nullable |
| `lemonsqueezy_variant_id` | String(255) | nullable |
| `refund_count` | Integer | default 0 |
| `language` | String(10) | default `en` |
| `timezone` | String(50) | default `UTC` |
| `articles_generated_this_month` | Integer | usage counter |
| `outlines_generated_this_month` | Integer | usage counter |
| `images_generated_this_month` | Integer | usage counter |
| `social_posts_generated_this_month` | Integer | usage counter |
| `usage_reset_date` | DateTime(tz) | nullable |
| `last_login` | DateTime(tz) | nullable |
| `last_active_at` | DateTime(tz) | nullable |
| `login_count` | Integer | |
| `is_suspended` | Boolean | legacy field |
| `suspended_at` | DateTime(tz) | nullable |
| `suspended_reason` | Text | nullable |
| `current_project_id` | UUID FK -> `projects.id` | nullable |
| `deleted_at` | DateTime(tz) | soft delete |

**Indexes:** `ix_users_email_status`, `ix_users_subscription`, `ix_users_lemonsqueezy`, `ix_users_role`, `ix_users_current_project_id`

### 3.2 Outline (`outlines`)

**File:** `infrastructure/database/models/content.py`

| Field | Type | Notes |
|---|---|---|
| `id` | UUID (PK) | |
| `user_id` | UUID FK -> `users.id` | CASCADE |
| `project_id` | UUID FK -> `projects.id` | nullable, CASCADE |
| `title` | String(500) | |
| `keyword` | String(255) | indexed |
| `target_audience` | String(500) | nullable |
| `tone` | String(50) | default `professional` |
| `sections` | JSON | array of section objects |
| `status` | String(50) | `draft`, `generating`, `completed`, `published`, `failed` |
| `word_count_target` | Integer | default 1500 |
| `estimated_read_time` | Integer | minutes, nullable |
| `ai_model` | String(100) | nullable |
| `generation_prompt` | Text | nullable |
| `generation_error` | Text | nullable |
| `deleted_at` | DateTime(tz) | soft delete |

**Relationships:** `articles` (one-to-many -> Article)
**Indexes:** `ix_outlines_created_at`

### 3.3 Article (`articles`)

**File:** `infrastructure/database/models/content.py`

| Field | Type | Notes |
|---|---|---|
| `id` | UUID (PK) | |
| `user_id` | UUID FK -> `users.id` | CASCADE |
| `project_id` | UUID FK -> `projects.id` | nullable, CASCADE |
| `outline_id` | UUID FK -> `outlines.id` | nullable, SET NULL |
| `title` | String(500) | |
| `slug` | String(500) | nullable |
| `keyword` | String(255) | indexed |
| `meta_description` | String(320) | nullable |
| `content` | Text | markdown |
| `content_html` | Text | rendered HTML |
| `status` | String(50) | indexed |
| `word_count` | Integer | default 0 |
| `read_time` | Integer | minutes, nullable |
| `improve_count` | Integer | AI improvement passes used (max 3) |
| `seo_score` | Float | nullable |
| `seo_analysis` | JSON | structured SEO breakdown |
| `ai_model` | String(100) | nullable |
| `generation_prompt` | Text | nullable |
| `generation_error` | Text | nullable |
| `image_prompts` | JSON | array of prompt strings |
| `quality_tier` | String(10) | `A`, `B`, or `C` |
| `schemas` | JSONB | Article + FAQPage JSON-LD |
| `run_metadata` | JSONB | pipeline step metrics |
| `deleted_at` | DateTime(tz) | soft delete |
| `planned_date` | DateTime(tz) | content calendar, indexed |
| `auto_publish` | Boolean | default false |
| `published_at` | DateTime(tz) | nullable |
| `published_url` | String(500) | nullable |
| `wordpress_post_id` | Integer | nullable |
| `social_posts` | JSON | AI-generated social media content |
| `featured_image_id` | UUID FK -> `generated_images.id` | nullable, SET NULL |

**Relationships:** `outline` (many-to-one), `images` (one-to-many -> GeneratedImage)
**Constraints:** `uq_article_project_slug` (unique project_id + slug)
**Indexes:** `ix_articles_created_at`

### 3.4 ArticleRevision (`article_revisions`)

**File:** `infrastructure/database/models/content.py`

Snapshot of article content at a point in time. Fields: `id`, `article_id` (FK), `created_by` (FK -> users), `content`, `content_html`, `title`, `meta_description`, `word_count`, `revision_type` (manual_edit, before_ai_improve_seo, restore), `created_at`.

### 3.5 GeneratedImage (`generated_images`)

**File:** `infrastructure/database/models/content.py`

Fields: `id`, `user_id` (FK), `project_id` (FK), `article_id` (FK, nullable), `prompt`, `url`, `local_path`, `alt_text`, `style`, `model`, `width`, `height`, `status`. Relationship: `article` (many-to-one).

### 3.6 Analytics Models

**File:** `infrastructure/database/models/analytics.py`

- **GSCConnection** (`gsc_connections`) -- OAuth connection to Google Search Console. Stores `access_token_encrypted`, `refresh_token_encrypted`, `token_expiry`, `site_url`, `is_active`. Tokens are Fernet-encrypted.
- **KeywordRanking** (`keyword_rankings`) -- Daily keyword performance data. Fields: `keyword`, `date`, `clicks`, `impressions`, `ctr`, `position`. Unique constraint on `(user_id, site_url, keyword, date)`.
- **PagePerformance** (`page_performances`) -- Daily page-level performance. Fields: `page_url`, `date`, `clicks`, `impressions`, `ctr`, `position`. Unique constraint on `(user_id, site_url, page_url, date)`.
- **DailyAnalytics** (`daily_analytics`) -- Aggregated daily metrics. Fields: `total_clicks`, `total_impressions`, `avg_ctr`, `avg_position`. Unique constraint on `(user_id, site_url, date)`.
- **ContentDecayAlert** (`content_decay_alerts`) -- Alerts for declining content. Fields: `alert_type`, `severity`, `keyword`, `page_url`, `metric_name`, `metric_before`, `metric_after`, `period_days`, `percentage_change`, `suggested_actions` (JSON), `is_read`, `is_resolved`. Auto-cleaned after 90 days.

### 3.7 Social Models

**File:** `infrastructure/database/models/social.py`

- **SocialAccount** (`social_accounts`) -- Connected platform accounts. Stores encrypted OAuth tokens (`access_token_encrypted`, `refresh_token_encrypted`), `platform`, `platform_user_id`, `platform_username`, `is_active`. Unique index on `(platform, platform_user_id)`.
- **ScheduledPost** (`scheduled_posts`) -- Posts scheduled for publishing. Fields: `content`, `media_urls` (JSON), `link_url`, `scheduled_at`, `status` (draft/scheduled/publishing/published/failed), `article_id` (optional linkage). Relationship: `targets` (one-to-many -> PostTarget).
- **PostTarget** (`post_targets`) -- Individual platform target for a scheduled post. Fields: `scheduled_post_id` (FK), `social_account_id` (FK), `platform_content`, `is_published`, `platform_post_id`, `platform_post_url`, `publish_error`, `analytics_data` (JSON).

### 3.8 Knowledge Models

**File:** `infrastructure/database/models/knowledge.py`

- **KnowledgeSource** (`knowledge_sources`) -- Uploaded document for RAG. Fields: `title`, `filename`, `file_type` (pdf/txt/md/docx/html), `file_size`, `status` (pending/processing/completed/failed), `chunk_count`, `char_count`. Relationship: `chunks` (one-to-many, cascade delete-orphan).
- **KnowledgeChunk** (`knowledge_chunks`) -- Immutable text chunk. Fields: `source_id` (FK), `chunk_index`, `content`, `char_count`.
- **KnowledgeQuery** (`knowledge_queries`) -- Query audit log. Fields: `query_text`, `response_text`, `sources_used` (JSON), `query_time_ms`, `chunks_retrieved`, `success`.

### 3.9 Project Models

**File:** `infrastructure/database/models/project.py`

- **Project** (`projects`) -- Multi-tenant project/organization. Fields: `name`, `slug`, `owner_id` (FK -> users), `is_personal`, `max_members`, `wordpress_credentials` (JSON), `brand_voice` (JSON). Unique constraint: `(owner_id, slug)`. Relationships: `members`, `invitations`.
- **ProjectMember** (`project_members`) -- Junction table. Fields: `project_id` (FK), `user_id` (FK), `role` (owner/admin/editor/viewer), `invited_by`, `joined_at`. Unique index on `(project_id, user_id)`.
- **ProjectInvitation** (`project_invitations`) -- Invitation with secure token. Fields: `email`, `role`, `token` (unique URL-safe), `status` (pending/accepted/revoked/expired), `expires_at` (7-day default).

### 3.10 AEO Models

**File:** `infrastructure/database/models/aeo.py`

- **AEOScore** (`aeo_scores`) -- AI-readability score (0-100) with `score_breakdown` (JSON: structure, FAQ, entity, conciseness, schema, citation readiness), `suggestions` (JSON), `previous_score` for trends.
- **AEOCitation** (`aeo_citations`) -- Tracks content appearing in AI answers. Fields: `source` (chatgpt/perplexity/gemini/bing_copilot), `query`, `citation_url`, `citation_snippet`.

### 3.11 Agency Models

**File:** `infrastructure/database/models/agency.py`

- **AgencyProfile** (`agency_profiles`) -- White-label agency configuration. One per user (`user_id` unique). Fields: `agency_name`, `logo_url`, `brand_colors` (JSON), `custom_domain`, `max_clients`.
- **ClientWorkspace** (`client_workspaces`) -- Client-facing workspace scoped to a project. Fields: `agency_id` (FK), `project_id` (FK, unique), `client_name`, `client_email`, `is_portal_enabled`, `portal_access_token`, `allowed_features` (JSON).
- **ReportTemplate** (`report_templates`) -- Reusable report template. Fields: `agency_id` (FK), `name`, `template_config` (JSON).
- **GeneratedReport** (`generated_reports`) -- Report for a client. Fields: `agency_id` (FK), `client_workspace_id` (FK), `report_template_id` (FK, nullable), `report_type`, `period_start`, `period_end`, `report_data` (JSON), `pdf_url`.

### 3.12 Blog Models

**File:** `infrastructure/database/models/blog.py`

Platform-level models (not scoped to user projects). Admin-managed.

- **BlogCategory** (`blog_categories`) -- Fields: `name` (unique), `slug` (unique). Relationship: `posts`.
- **BlogTag** (`blog_tags`) -- Fields: `name` (unique), `slug` (unique). Relationship: `post_tags`.
- **BlogPostTag** (`blog_post_tags`) -- Association table, composite PK `(post_id, tag_id)`.
- **BlogPost** (`blog_posts`) -- Fields: `slug` (unique), `title`, `meta_title`, `meta_description`, `excerpt`, `content_html`, `status` (draft/published), `featured_image_url`, `og_image_url`, `author_id` (FK), `category_id` (FK), `published_at`, `schema_faq` (JSON).

### 3.13 Bulk Generation Models

**File:** `infrastructure/database/models/bulk.py`

- **ContentTemplate** (`content_templates`) -- Reusable generation template. Fields: `name`, `description`, `template_config` (JSON with tone, writing_style, word_count_target, etc.).
- **BulkJob** (`bulk_jobs`) -- Bulk generation job. Fields: `job_type`, `status`, `total_items`, `completed_items`, `failed_items`, `input_data` (JSON), `template_id` (FK, nullable), `started_at`, `completed_at`.
- **BulkJobItem** (`bulk_job_items`) -- Individual item. Fields: `bulk_job_id` (FK), `keyword`, `title`, `status`, `resource_type`, `resource_id`, `error_message`.

### 3.14 Competitor Models

**File:** `infrastructure/database/models/competitor.py`

- **CompetitorAnalysis** (`competitor_analyses`) -- Analysis job. Fields: `domain`, `status`, `total_urls`, `scraped_urls`, `total_keywords`, `expires_at`. Relationship: `articles` (one-to-many).
- **CompetitorArticle** (`competitor_articles`) -- Scraped page. Fields: `url`, `title`, `meta_description`, `headings` (JSONB), `word_count`, `extracted_keyword`, `keyword_confidence`.

### 3.15 Site Audit Models

**File:** `infrastructure/database/models/site_audit.py`

- **SiteAudit** (`site_audits`) -- Audit job. Fields: `domain`, `status`, `pages_crawled`, `pages_discovered`, `total_issues`, `critical_issues`, `warning_issues`, `info_issues`, `score` (0-100). Relationships: `pages`, `issues`. Auto-cleaned after 90 days.
- **AuditPage** (`audit_pages`) -- Crawled page. Fields: `url`, `status_code`, `response_time_ms`, `word_count`, `title`, `meta_description`, `h1_count`, `has_canonical`, `has_og_tags`, `has_structured_data`, `performance_score`, `pagespeed_data` (JSONB), `issues` (JSONB).
- **AuditIssue** (`audit_issues`) -- Individual issue. Fields: `issue_type`, `severity` (critical/warning/info), `message`, `details` (JSONB).

### 3.16 Generation Tracking Models

**File:** `infrastructure/database/models/generation.py`

- **GenerationLog** (`generation_logs`) -- Per-generation audit entry. Fields: `user_id`, `project_id`, `resource_type` (article/outline/image), `resource_id`, `status` (started/success/failed), `ai_model`, `duration_ms`, `input_metadata` (JSON), `cost_credits`.
- **AdminAlert** (`admin_alerts`) -- Admin-facing system alerts. Fields: `alert_type`, `severity` (info/warning/critical), `title`, `message`, `resource_type`, `resource_id`, `user_id`, `is_read`, `is_resolved`.

### 3.17 Revenue Models

**File:** `infrastructure/database/models/revenue.py`

- **ConversionGoal** (`conversion_goals`) -- Named conversion goal. Fields: `name`, `goal_type`, `goal_config` (JSON), `is_active`.
- **ContentConversion** (`content_conversions`) -- Daily conversion data. Fields: `article_id` (FK), `goal_id` (FK), `page_url`, `keyword`, `date`, `visits`, `conversions`, `conversion_rate`, `revenue`, `attribution_model` (default `last_touch`).
- **RevenueReport** (`revenue_reports`) -- Pre-computed attribution report. Fields: `report_type`, `period_start`, `period_end`, `total_organic_visits`, `total_conversions`, `total_revenue`, `top_articles` (JSON), `top_keywords` (JSON).

### 3.18 Remaining Models

| Model | Table | File | Key Fields |
|---|---|---|---|
| **Tag** | `tags` | `tag.py` | `name`, `color`, `user_id`, `project_id`. Partial unique index on `(user_id, name)` where `deleted_at IS NULL`. |
| **ArticleTag** | `article_tags` | `tag.py` | Composite PK `(article_id, tag_id)`. |
| **OutlineTag** | `outline_tags` | `tag.py` | Composite PK `(outline_id, tag_id)`. |
| **ArticleTemplate** | `article_templates` | `template.py` | `name`, `target_audience`, `tone`, `word_count_target`, `writing_style`, `voice`, `custom_instructions`, `sections` (JSONB). |
| **SEOReport** | `seo_reports` | `report.py` | `name`, `report_type` (overview/keywords/pages/content_health), `date_from`, `date_to`, `status`, `report_data` (JSONB). |
| **SystemErrorLog** | `system_error_logs` | `error_log.py` | `error_type`, `error_code`, `severity`, `title`, `message`, `stack_trace`, `service`, `endpoint`, `http_method`, `http_status`, `error_fingerprint` (SHA-256), `occurrence_count`, `is_resolved`. Deduplication via fingerprint. |
| **EmailJourneyEvent** | `user_email_journey_events` | `email_journey_event.py` | `user_id`, `email_key`, `status` (scheduled/sent/cancelled/failed), `scheduled_for`, `sent_at`, `attempt_count`. Partial unique index on `(user_id, email_key)` where `status IN ('scheduled', 'sent')`. |
| **NotificationPreferences** | `notification_preferences` | `notification_preferences.py` | One per user (`user_id` unique). Boolean flags for each notification category: generation, usage, content decay, weekly digest, billing, product updates, onboarding, conversion tips, re-engagement. |
| **KeywordResearchCache** | `keyword_research_cache` | `keyword_cache.py` | `seed_keyword_normalized`, `result_json` (Text), `expires_at` (30-day TTL). |
| **RefundBlockedEmail** | `refund_blocked_emails` | `refund_blocked_email.py` | `email` (unique), `reason`, `blocked_by` (FK -> users). |
| **AdminAuditLog** | `admin_audit_logs` | `admin.py` | `admin_user_id`, `action`, `target_user_id`, `target_type`, `target_id`, `details` (JSON), `ip_address`. |

---

## 4. Services Layer

### 4.1 ContentPipeline (`content_pipeline.py`)

**Class:** `ContentPipeline` (singleton: `content_pipeline`)

Orchestrates the 10-step multi-model content generation pipeline. See Section 6 for full details.

**Key methods:**
- `run_full_pipeline(keyword, title, tone, ...) -> PipelineResult` -- Full 10-step pipeline
- `run_outline_only(keyword, ...) -> GeneratedOutline` -- Outline-only mode for bulk generation
- `generate_content_cluster(keyword, ...) -> dict` -- Topical authority cluster plan

### 4.2 GenerationTracker (`generation_tracker.py`)

**Class:** `GenerationTracker`

Logs every AI generation attempt, increments user usage counters on success, and creates admin alerts on failure. Fails open (generation proceeds even if logging fails).

**Key methods:**
- `log_start(user_id, project_id, resource_type, resource_id) -> GenerationLog`
- `log_success(log_id, ai_model, duration_ms) -> None` -- Also increments the user's monthly counter
- `log_failure(log_id, error_message) -> None` -- Creates an `AdminAlert` for admin visibility

**Usage field mapping:** `article -> articles_generated_this_month`, `outline -> outlines_generated_this_month`, `image -> images_generated_this_month`, `social_post -> social_posts_generated_this_month`

### 4.3 AEO Scoring (`aeo_scoring.py`)

Analyzes article content for AI-readability across 6 dimensions: structure (heading hierarchy, lists, tables), FAQ (question-answer patterns), entity (topic coverage, factual density), conciseness (answer-first paragraphs), schema (structured data indicators), and citation readiness (quotable snippets). Pure regex/heuristic analysis -- no AI calls.

### 4.4 Content Decay Detection (`content_decay.py`)

**Function:** `detect_keyword_decay(db, user_id, project_id, period_days)`

Compares GSC keyword performance between current and previous period. Generates `ContentDecayAlert` records when thresholds are breached:
- Position worsened by 3+ (warning) or 5+ (critical)
- Clicks dropped 20%+ (warning) or 40%+ (critical)
- Impressions dropped 25%+ (warning) or 50%+ (critical)
- CTR dropped 20%+ (warning) or 40%+ (critical)

Minimum 50 impressions required to trigger an alert.

### 4.5 Content Scheduler (`content_scheduler.py`)

**Class:** `ContentSchedulerService` (singleton: `content_scheduler`)

Background service (runs every 120 seconds) that auto-publishes articles to WordPress when their `planned_date` arrives and `auto_publish=True`. Uses a Redis distributed lock to prevent duplicate publishes in multi-worker deployments.

### 4.6 Knowledge Service (`knowledge_service.py`)

**Class:** `KnowledgeService`

RAG (Retrieval-Augmented Generation) operations for the Knowledge Vault. Coordinates document processing, embedding generation, and vector search.

**Key methods:**
- `process_document(source_id, user_id, file_path, db)` -- Extract text, chunk, generate embeddings, store in ChromaDB
- `query(user_id, query_text, db)` -- Vector search + AI answer generation via Claude

### 4.7 Site Auditor (`site_auditor.py`)

BFS website crawler with concurrency control (max 5 concurrent requests), robots.txt compliance, SSRF protection (blocks private/internal IPs), and 22 on-page SEO issue detectors. Max crawl time: 30 minutes. Integrates with Google PageSpeed Insights API.

### 4.8 Competitor Analyzer (`competitor_analyzer.py`)

Crawls competitor sitemaps, scrapes pages, and extracts keywords using weighted n-gram scoring across title, headings, URL slug, meta description, and body TF-IDF. No AI models used. Max 500 URLs, 10-minute timeout.

### 4.9 Revenue Attribution (`revenue_attribution.py`)

Calculates content ROI by cross-referencing GSC organic traffic data with conversion goals. Supports `last_touch` attribution model. Generates pre-computed `RevenueReport` records with top articles and top keywords breakdowns.

### 4.10 Email Journey (`email_journey.py`, `email_journey_worker.py`, `email_journey_unsubscribe.py`)

**Orchestrator class:** `EmailJourneyService`

Event-driven email lifecycle system with 4 phases:
1. **Onboarding** (welcome, first outline nudge, outline-to-article, connect tools, week one recap)
2. **Conversion** (usage 80%, usage 100%, power user features, audit upsell)
3. **Retention** (inactive 7d, 21d, 45d)
4. **Ongoing** (weekly digest, content decay alerts)

The orchestrator receives events and schedules emails in the database. The worker (runs every 60s for emails, every 3600s for inactivity checks) picks up due emails and sends them via Resend. Each email respects per-category notification preferences and includes JWT-based one-click unsubscribe tokens (RFC 8058 compliant).

### 4.11 Error Logger (`error_logger.py`)

**Functions:** `log_error()`, `log_exception()`

Centralized error logging to `system_error_logs` table. Uses SHA-256 fingerprinting to deduplicate errors (increments `occurrence_count` instead of creating duplicates). Captures stack traces, request context, and related entity IDs.

### 4.12 Post Queue (`post_queue.py`)

**Class:** `PostQueueManager` (singleton: `post_queue`)

Redis sorted-set based queue for social media post scheduling. Uses timestamp as score for efficient time-based queries. Falls back gracefully if Redis is unavailable.

### 4.13 Schema Generator (`schema_generator.py`)

Pure-code generator for JSON-LD structured data. Produces `Article` and `FAQPage` schemas from article content for search engine rich snippets. Extracts FAQ sections from markdown headings that end with `?`.

### 4.14 Social Scheduler (`social_scheduler.py`)

**Class:** `SocialSchedulerService` (singleton: `scheduler_service`)

Background loop (every 60 seconds) that finds due `ScheduledPost` records, publishes to each platform via the appropriate social adapter, and tracks per-target results. Decrypts OAuth tokens at publish time.

### 4.15 Bulk Generation (`bulk_generation.py`)

Creates and processes bulk content generation jobs. Supports bulk outline and bulk article generation from keyword lists. Configurable inter-item sleep (`bulk_item_sleep_seconds`, default 2s) to respect API rate limits.

### 4.16 Task Queue (`task_queue.py`)

**Class:** `TaskQueue` (singleton: `task_queue`)

Lightweight in-memory async task queue. Each task is an `asyncio.Task` on the same event loop. Provides `enqueue()`, `get_status()`, and `cleanup_old()`. Completed tasks auto-cleaned every 30 minutes (max age 1 hour).

### 4.17 PageSpeed (`pagespeed.py`)

**Function:** `fetch_pagespeed(url, strategy)`

Async client for Google PageSpeed Insights API. Returns performance score (0-100) and Core Web Vitals metrics (LCP, FID, CLS, FCP, TTFB, SI, TBT).

---

## 5. Adapters Layer

### 5.1 AI Adapters

#### Anthropic Adapter (`adapters/ai/anthropic_adapter.py`)

**Class:** `AnthropicContentService` (singleton: `content_ai_service`)

Primary content generation engine using Claude Sonnet 4.6 (articles) and Claude Haiku 4.5 (fact-checking).

**Key methods:**
- `generate_outline(keyword, ...) -> GeneratedOutline` -- Claude fallback for outline generation
- `generate_article(title, keyword, sections, ...) -> GeneratedArticle` -- Publication-quality article prose
- `fact_check_content(content) -> list[str]` -- AI fact-check, returns flagged claims
- `repair_flagged_claims(content, flagged_claims) -> str` -- Auto-fix dubious claims
- `generate_image_prompts(title, content, keyword) -> list[str]` -- 3 distinct image prompts
- `regenerate_section(full_content, section_heading, ...) -> str` -- Section-level regeneration for SEO repair
- `generate_content_cluster(keyword, ...) -> dict` -- Topical authority cluster plan
- `improve_seo(content, keyword, ...) -> str` -- Targeted SEO improvement pass

Uses exponential backoff with jitter for transient errors (rate limits, timeouts, 5xx). Configurable timeout (600s for long articles). Prompt templates loaded from versioned manifest.

#### Gemini Adapter (`adapters/ai/gemini_adapter.py`)

**Class:** `GeminiFlashService` (singleton: `gemini_service`)

Uses Gemini 2.5 Flash with Google Search grounding for live data.

**Key methods:**
- `analyze_serp(keyword, language) -> SERPAnalysis` -- Top headings, PAA questions, content gaps, search intent
- `research_topic(keyword, language) -> ResearchData` -- Key facts and statistics sourced from Google Search
- `analyze_seo_vs_serp(content, serp_analysis) -> dict` -- Compare article against SERP for missing topics

Gracefully degrades if `GEMINI_API_KEY` not set -- pipeline skips these steps.

#### OpenAI Adapter (`adapters/ai/openai_adapter.py`)

**Class:** `OpenAIOutlineService` (singleton: `openai_outline_service`)

Uses GPT-4o mini with Structured Outputs (`response_format=BaseModel`) for JSON-schema-guaranteed outlines.

**Key methods:**
- `generate_outline(keyword, serp_analysis, research_data, ...) -> GeneratedOutline`
- `is_available() -> bool` -- Returns True if API key is configured

Falls back to Claude if unavailable or on error.

#### Replicate Adapter (`adapters/ai/replicate_adapter.py`)

Uses Ideogram V3 Turbo model via Replicate API for AI image generation. Downloads generated images and stores them locally or on S3. Exponential backoff retry logic.

### 5.2 CMS Adapter

#### WordPress Adapter (`adapters/cms/wordpress_adapter.py`)

**Class:** `WordPressService`

WordPress REST API v2 integration using Application Password authentication.

**Key methods:**
- `validate_connection(connection) -> bool` -- Test connectivity
- `publish_article(connection, title, content, ...) -> dict` -- Create/update WordPress post
- `upload_media(connection, image_data, filename) -> dict` -- Upload featured image
- `get_categories(connection) -> list` -- Fetch available categories

### 5.3 Email Adapter

#### Resend Adapter (`adapters/email/resend_adapter.py`)

**Class:** `ResendEmailService`

Transactional email via Resend API. In dev mode, logs email content instead of sending.

**Key methods:**
- `send_verification_email(to, name, token)` -- Account verification
- `send_password_reset_email(to, name, token)` -- Password reset
- `send_invitation_email(to, inviter_name, project_name, token)` -- Project invitation
- `send_journey_email(to, subject, html_body, ...)` -- Lifecycle journey emails with List-Unsubscribe headers

#### Journey Templates (`adapters/email/journey_templates.py`)

**Class:** `JourneyTemplates`

Generates HTML email templates for all lifecycle journey emails (welcome, nudges, usage alerts, retention, digest). Each template includes branded header, personalized content, CTA buttons, and one-click unsubscribe link.

### 5.4 Knowledge Adapters

#### ChromaDB Adapter (`adapters/knowledge/chroma_adapter.py`)

**Class:** `ChromaAdapter`

Vector storage and retrieval using ChromaDB HTTP client. Thread-safe. User-scoped collections with configurable prefix.

**Key methods:**
- `add_documents(user_id, documents) -> None`
- `query(user_id, query_embedding, n_results) -> list[QueryResult]`
- `delete_source(user_id, source_id) -> None`

#### Document Processor (`adapters/knowledge/document_processor.py`)

**Class:** `DocumentProcessor`

Extracts text from PDF (PyMuPDF), TXT, Markdown, DOCX (python-docx), and HTML (BeautifulSoup). Chunks text at configurable size (default 1000 chars) with overlap (default 200 chars).

#### Embedding Service (`adapters/knowledge/embedding_service.py`)

**Class:** `EmbeddingService`

Generates text embeddings via OpenAI `text-embedding-3-small` (1536 dimensions). Falls back to hash-based mock embeddings for development without API key.

### 5.5 Payments Adapter

#### LemonSqueezy Adapter (`adapters/payments/lemonsqueezy_adapter.py`)

**Class:** `LemonSqueezyService`

Full subscription lifecycle management via LemonSqueezy API.

**Key methods:**
- `create_checkout(variant_id, user_email, user_name, ...) -> str` -- Generate overlay checkout URL
- `get_subscription(subscription_id) -> LemonSqueezySubscription` -- Fetch subscription status
- `cancel_subscription(subscription_id) -> None` -- Cancel (grace period until `ends_at`)
- `refund_invoice(invoice_id) -> None` -- Process refund for invoice
- `get_invoices(subscription_id) -> list` -- Fetch invoice history
- `verify_webhook(signature, body) -> bool` -- HMAC-SHA256 webhook signature verification

**Webhook events handled:** `subscription_created`, `subscription_updated`, `subscription_cancelled`, `subscription_expired`, `subscription_payment_success`, `subscription_payment_failed`

### 5.6 Search Adapter

#### Google Search Console Adapter (`adapters/search/gsc_adapter.py`)

**Class:** `GSCService`

Google Search Console API integration for SEO analytics.

**Key methods:**
- `get_oauth_url() -> str` -- Generate Google OAuth consent URL
- `exchange_code(code) -> GSCCredentials` -- Exchange auth code for tokens
- `refresh_token(credentials) -> GSCCredentials` -- Refresh expired access token
- `get_sites(credentials) -> list` -- List verified properties
- `get_search_analytics(credentials, site_url, start_date, end_date, ...) -> list` -- Fetch keyword/page performance data

### 5.7 Social Adapters

All social adapters implement the `SocialAdapter` abstract base class from `adapters/social/base.py`.

**Abstract methods:**
- `publish_post(credentials, content, media_urls) -> PostResult`
- `verify_credentials(credentials) -> bool`
- `get_profile(credentials) -> dict`

**Platform adapters:**
- **TwitterAdapter** (`twitter_adapter.py`) -- OAuth 2.0 PKCE, tweet posting via Twitter API v2
- **LinkedInAdapter** (`linkedin_adapter.py`) -- OAuth 2.0, share/post creation via LinkedIn API
- **FacebookAdapter** (`facebook_adapter.py`) -- Facebook Graph API, page posting
- **InstagramAdapter** (`instagram_adapter.py`) -- Instagram Graph API (via Facebook Business)

### 5.8 Storage Adapters

#### Image Storage (`adapters/storage/image_storage.py`)

**Abstract class:** `StorageAdapter`

**Implementations:**
- **LocalStorageAdapter** -- Saves to `backend/data/uploads/` filesystem. Images served via FastAPI `StaticFiles` mount at `/uploads/` with aggressive cache headers (1 year, immutable).
- **S3StorageAdapter** -- AWS S3 bucket storage via boto3. Configurable region, bucket, and credentials.

---

## 6. AI Content Pipeline

**File:** `backend/services/content_pipeline.py`

The content pipeline is a 10-step self-correcting multi-model pipeline that produces publication-quality SEO articles:

### Step 1: SERP Analysis (Gemini 2.5 Flash)
Uses Google Search grounding to analyze the top search results for the target keyword. Extracts: top headings from ranking pages, average word count, People Also Ask questions, content gaps, competing titles, and search intent classification (informational/commercial/transactional/navigational).

### Step 2: Research (Gemini 2.5 Flash)
Runs in parallel with Step 1. Retrieves real facts, statistics, and related topics from Google Search. All data is grounded in live search results to eliminate hallucinated statistics.

**Steps 1+2 are cached in Redis with a 24-hour TTL** (keyed by `sha256(keyword:language)`). Cache hits avoid repeat Gemini API calls for the same keyword.

### Step 3: Outline Generation (GPT-4o mini, fallback: Claude)
Generates a structured article outline using OpenAI Structured Outputs (`response_format=BaseModel`) for guaranteed JSON schema compliance. Enriched with SERP analysis and research data. Falls back to Claude Sonnet if OpenAI is unavailable or errors.

**Quality tier assigned:**
- **A** = Full pipeline (Gemini SERP + OpenAI outline)
- **B** = Partial fallback (one provider missing)
- **C** = Full Claude fallback (all-Claude path)

SERP gap coverage is validated -- a warning is logged if the outline misses all top-3 content gaps.

### Step 4: Article Generation (Claude Sonnet 4.6)
Generates the full article in markdown. The prompt is enriched with verified facts and statistics from Step 2. Configurable: tone, target audience, writing style, voice, list usage, word count target, language, secondary keywords, entities, and custom instructions.

### Step 5: SEO vs SERP Check (Gemini Flash)
Runs in parallel with Steps 6+7. Compares the generated article against the SERP analysis to identify missing topics that competitors cover. Returns a `serp_alignment_score` and `missing_topics` list.

### Step 6: Fact-Check (Claude Haiku 4.5)
Runs in parallel with Steps 5+7. AI-powered fact-checking that flags dubious statistical claims. Results are merged with regex-based statistical claim detection (percentage patterns, N-in-N ratios, `[VERIFY]` self-tags).

### Step 7: Image Prompts (Claude Sonnet 4.6)
Runs in parallel with Steps 5+6. Generates 3 distinct image prompts tailored to the article content and keyword. Prompts are stored on the article for later image generation.

### Step 8: SEO Repair Loop (Claude Sonnet 4.6)
If Step 5 identified missing topics, the last body section (before FAQ/conclusion) is regenerated with instructions to cover the gaps. Section-level regeneration preserves the rest of the article.

### Step 9: Fact-Check Repair (Claude Haiku 4.5)
If Step 6 flagged claims, they are auto-fixed. Dubious statistics are softened or removed while preserving article flow.

### Step 10: Schema Generation (Pure Code)
Generates JSON-LD structured data (Article + FAQPage schemas) from the final article content. No AI calls -- pure regex-based extraction of FAQ sections from headings ending with `?`.

### Pipeline Output

```python
@dataclass
class PipelineResult:
    outline: GeneratedOutline
    article: GeneratedArticle
    serp_analysis: SERPAnalysis | None
    research_data: ResearchData | None
    image_prompts: list[str] | None
    flagged_stats: list[str]
    serp_seo: dict
    models_used: dict[str, str]
    url_slug: str | None
    schemas: dict
    run_metadata: PipelineRunMetadata  # per-step latency, cache hits, quality tier, prompt versions
```

### Graceful Degradation

If Gemini or OpenAI API keys are absent, the pipeline transparently falls back to the all-Claude path. Steps 1+2 are skipped, and Step 3 uses Claude instead of GPT-4o mini. The `quality_tier` field records which path was taken.

---

## 7. Authentication & Security

### JWT Tokens

**File:** `core/security/tokens.py`

- **Library:** PyJWT (not python-jose)
- **Algorithm:** HS256
- **Access tokens:** 60-minute expiry, contain `sub` (user ID), `email`, `role`, `type: "access"`
- **Refresh tokens:** 7-day expiry, `type: "refresh"`
- **Token delivery:** HttpOnly cookies (`access_token`, `refresh_token`) with `SameSite=Lax`; also returned in response body for non-browser clients
- **Token blacklisting:** Redis-based; revoked tokens are stored with their remaining TTL
- **Session invalidation:** `password_changed_at` timestamp is checked on every authenticated request; tokens issued before the last password change are rejected

### Password Hashing

**File:** `core/security/password.py`

- **Library:** passlib with bcrypt backend
- **Rounds:** 12 (configurable)
- **Auto-rehash:** `needs_rehash()` checks if hash parameters have changed

### Credential Encryption

**File:** `core/security/encryption.py`

- **Library:** cryptography (Fernet symmetric encryption)
- **Key derivation:** SHA-256 hash of `SECRET_KEY` -> base64-encoded 32-byte Fernet key
- **Used for:** OAuth tokens (GSC, social accounts), WordPress application passwords
- **Column convention:** `*_encrypted` suffix (e.g., `access_token_encrypted`)

### OAuth Flows

- **Google Login/Signup:** Backend callback at `/api/v1/auth/google/callback`; creates or links user account
- **Google Search Console:** Frontend-initiated; tokens stored in `gsc_connections`
- **Twitter/LinkedIn/Facebook:** Platform OAuth 2.0 callbacks at `/api/v1/social/{platform}/callback`; tokens stored in `social_accounts`

### RBAC (Role-Based Access Control)

**User roles:** `user`, `admin`, `super_admin`
**Project roles:** `owner`, `admin`, `editor`, `viewer`

**Dependencies:**
- `get_current_user` -- Extracts and validates JWT from cookie/header, loads user from DB
- `get_current_admin_user` (`api/deps_admin.py`) -- Requires `admin` or `super_admin` role
- `get_current_super_admin_user` -- Requires `super_admin` role
- `require_project_admin` (`api/deps_project.py`) -- Requires `owner` or `admin` project role
- `require_project_owner` -- Requires `owner` project role
- `verify_content_access` -- Read access: user owns content or is a project member
- `verify_content_edit` -- Write access: user owns content or is a project member (not viewer)
- `require_tier(minimum_tier)` -- Checks `subscription_tier` against tier hierarchy (free < starter < professional < enterprise)

### Security Middleware

- **Request body size limit:** 5MB max for non-multipart requests (413 rejection)
- **Security headers:** `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: strict-origin-when-cross-origin`, HSTS in production
- **Request ID:** UUID `X-Request-ID` header (validates incoming UUIDs to prevent log injection)
- **CORS:** Configurable origins with credential support

---

## 8. Configuration

**File:** `infrastructure/config/settings.py`

All configuration is loaded from environment variables via `pydantic-settings` (`BaseSettings`). The `get_settings()` function returns a cached singleton.

### Configuration Categories

| Category | Key Settings |
|---|---|
| **Application** | `app_name`, `app_version`, `debug`, `environment` (development/staging/production) |
| **Server** | `host`, `port`, `workers` |
| **Database** | `database_url` (auto-converts `postgresql://` to `postgresql+asyncpg://`), `database_echo`, `db_pool_size` (20), `db_max_overflow` (40) |
| **Redis** | `redis_url`, `redis_key_prefix` (namespace to prevent collisions) |
| **JWT** | `secret_key`, `jwt_secret_key`, `jwt_algorithm` (HS256), `jwt_access_token_expire_minutes` (60), `jwt_refresh_token_expire_days` (7) |
| **CORS** | `cors_origins` (comma-separated or JSON array, trailing slashes stripped) |
| **Anthropic** | `anthropic_api_key`, `anthropic_model` (claude-sonnet-4-6), `anthropic_haiku_model` (claude-haiku-4-5), `anthropic_max_tokens` (4096), `anthropic_timeout` (600s) |
| **Replicate** | `replicate_api_token`, `replicate_model` (ideogram-ai/ideogram-v3-turbo) |
| **Resend** | `resend_api_key`, `resend_from_email` |
| **LemonSqueezy** | `lemonsqueezy_api_key`, `lemonsqueezy_store_id`, `lemonsqueezy_webhook_secret`, 6x variant IDs (starter/professional/enterprise x monthly/yearly) |
| **Google** | `google_client_id`, `google_client_secret`, `google_redirect_uri`, `google_auth_redirect_uri`, `google_pagespeed_api_key` |
| **Social OAuth** | `twitter_client_id/secret/redirect_uri`, `linkedin_*`, `facebook_*` |
| **ChromaDB** | `chroma_host`, `chroma_port`, `chroma_persist_directory`, `chroma_collection_prefix` |
| **Embeddings** | `embedding_model` (text-embedding-3-small), `openai_api_key`, `openai_outline_model` (gpt-4o-mini) |
| **Gemini** | `gemini_api_key`, `gemini_model` (gemini-2.5-flash) |
| **Pipeline flags** | `enable_serp_analysis`, `enable_research_step`, `ai_request_timeout` (60s), `bulk_item_sleep_seconds` (2s) |
| **Storage** | `storage_type` (local/s3), `storage_local_path`, `s3_bucket`, `s3_region`, `s3_access_key`, `s3_secret_key` |
| **URLs** | `frontend_url`, `api_base_url`, `cookie_domain` |
| **Sentry** | `sentry_dsn` (validates `sentry.io` domain) |

### Production Validation

`validate_production_secrets()` is called at startup and enforces:
- `SECRET_KEY` and `JWT_SECRET_KEY` must be >= 32 characters
- `ANTHROPIC_API_KEY`, `LEMONSQUEEZY_API_KEY`, `LEMONSQUEEZY_WEBHOOK_SECRET`, `RESEND_API_KEY` must be set
- All LemonSqueezy variant IDs are checked (warning, not fatal)
- OAuth redirect URIs are checked for `https://` and non-localhost (warning)
- `DATABASE_ECHO` must be false in production
- DB connection pool total is checked against 200 connections (warning)
- Railway environment auto-detected even if `ENVIRONMENT` is not explicitly set

---

## 9. Infrastructure

### Database Connection Pooling

**File:** `infrastructure/database/connection.py`

- **Engine:** `create_async_engine` with `asyncpg`
- **Pool size:** 20 connections (configurable via `db_pool_size`)
- **Max overflow:** 40 additional connections (configurable via `db_max_overflow`)
- **Pool timeout:** 10 seconds (raises `TimeoutError` if no connection available)
- **Pool recycle:** 3600 seconds (prevents stale connections)
- **Pool pre-ping:** Enabled (detects dead connections before use)
- **SSL:** Required in production (`connect_args={"ssl": "require"}`)
- **Session factory:** `async_sessionmaker` with `expire_on_commit=False`, `autocommit=False`, `autoflush=False`
- **Dependencies:** `get_db()` (FastAPI dependency), `get_db_context()` (async context manager)

### Redis Centralized Pool

**File:** `infrastructure/redis.py`

Two shared connection pools (lazy-initialized singletons):
- `get_redis()` -- Raw bytes (`decode_responses=False`) for token operations, webhooks
- `get_redis_text()` -- Decoded strings (`decode_responses=True`) for caching, pub/sub, keyword research

Both pools: `socket_timeout=5`, `socket_connect_timeout=5`, `max_connections=20`.

**Key namespacing:** All keys use `redis_key(key)` which prepends `{redis_key_prefix}:` to prevent collisions when multiple environments share the same Redis instance.

**Used for:** Rate limiting (slowapi storage), SERP/research cache (24h TTL), token blacklisting, distributed locks (content scheduler, social scheduler), post queue (sorted sets), keyword research cache.

### Logging

**File:** `infrastructure/logging_config.py`

- **Production:** JSON-formatted structured logging (single-line JSON objects) with `timestamp`, `level`, `logger`, `message`, optional `exception`, `request_id`, `method`, `path`, `status_code`, `duration_ms`
- **Development:** Human-readable format with timestamps
- **Sensitive data filter:** Regex-based redaction of Bearer tokens, API keys, passwords, and secrets (applied to all log records)
- **Quiet libraries:** `sqlalchemy.engine` -> WARNING, `httpx` -> WARNING, `uvicorn.access` -> INFO

### Alembic Migrations

**Directory:** `infrastructure/database/migrations/versions/`
**Total:** 61 migration files (001 through 060 with placeholders)

Key migration milestones:
- 001: Users table
- 002: Content tables (outlines, articles, images)
- 003-005: WordPress credentials, analytics tables, LemonSqueezy billing
- 006-007: Knowledge tables, social tables
- 008-011: Admin fields, team tables, team ownership
- 015: Rename teams to projects
- 016: Generation tracking
- 018-019: Article revisions, knowledge chunks
- 020-021: Password security, brand voice
- 038: Rename token columns to `*_encrypted` convention
- 050-052: Article templates, tags, SEO reports
- 056: Refund blocked emails, user refund_count
- 057: Composite indexes on high-traffic tables
- 058: Clean expired Replicate image URLs from blog posts
- 059: `image_prompt` (Text) -> `image_prompts` (JSON array) on articles
- 060: Email journey events table

**Migration conventions:**
- Must be idempotent (`DO $$ BEGIN IF NOT EXISTS ... END $$`)
- FK columns referencing `users.id` must use `UUID`, not `VARCHAR(36)` (Railway compatibility)
- Auto-applied on Railway deploy

### Startup Lifecycle

The `lifespan()` async context manager in `main.py` handles:

**Startup:**
1. Configure structured logging
2. Validate production secrets
3. Recover articles/outlines/images stuck in `generating` status (set to `failed`)
4. Initialize database tables (dev mode only)
5. Validate Redis connectivity (production warning if unreachable)
6. Validate CORS origins match `FRONTEND_URL`
7. Connect Redis post queue
8. Start background tasks:
   - Social media scheduler (every 60s)
   - Content calendar scheduler (every 120s)
   - Task queue cleanup (every 30 min, removes tasks > 1h old)
   - Content decay alert cleanup (daily, removes > 90 days)
   - Site audit cleanup (daily, removes > 90 days)
   - Email journey worker (email loop every 60s, inactivity check every 3600s)

**Shutdown:**
- Cancel all background tasks with graceful timeouts (30s for social scheduler)
- Disconnect Redis post queue
- Close shared Redis connection pools
- Dispose database engine

### Error Tracking

- **Sentry:** Initialized at module level with FastAPI, SQLAlchemy, Redis, and Logging integrations. Traces sample rate: 10% in production, 100% in dev. PII disabled.
- **System error logs:** All unhandled exceptions and connection errors are logged to `system_error_logs` table for admin dashboard visibility.
- **Global exception handlers:** Connection errors return 503, all other unhandled exceptions return 500. Production logs truncate exception messages to 200 chars to prevent secret leakage.

---

## 10. Dependencies & Middleware

### Rate Limiting (slowapi)

**File:** `api/middleware/rate_limit.py`

IP-based rate limiting using slowapi with Redis storage (falls back to in-memory if Redis unavailable).

| Endpoint | Limit |
|---|---|
| Login | 5/minute |
| Register | 3/minute |
| Password reset | 3/hour |
| Email verification | 5/hour |
| Resend verification | 5/hour |
| Delete account | 3/hour |
| Change email | 3/minute |
| Avatar upload | 10/minute |
| Default (all routes) | 100/minute |

**IP extraction:** Reads `X-Forwarded-For` header (first entry), validates it is a real public IP (rejects private/loopback IPs to prevent spoofed bypass), falls back to `X-Real-IP`, then connection address.

### Auth Dependencies

- `get_current_user` -- Extracts JWT from `access_token` cookie or `Authorization: Bearer` header. Validates token, checks user status (rejects PENDING/SUSPENDED/DELETED before `is_active`), checks `password_changed_at` for token invalidation.
- `get_current_admin_user` -- Chains on `get_current_user`, verifies `admin` or `super_admin` role.

### Project Scoping

- `verify_project_membership(db, user, project_id)` -- Checks `project_members` table for active membership
- `verify_content_access(db, content, user)` -- Personal content: `user_id` match. Project content: membership check. Returns 404 (not 403) to prevent info leakage.
- `verify_content_edit(db, content, user)` -- Same as access but excludes `viewer` role from editing
- `scoped_query(model, item_id, user)` -- Builds an ownership-filtered `SELECT` query: uses `project_id` scoping if the user has a `current_project_id`, otherwise falls back to `user_id` scoping

### Subscription Tier Checking

- `get_effective_tier(user)` -- Resolves effective tier (falls back to `free` if subscription is expired)
- `require_tier(minimum_tier)` -- Returns a callable that raises 403 if user's tier is below minimum
- **Tier hierarchy:** `free` < `starter` < `professional` < `enterprise`

### Subscription Plans

**File:** `core/plans.py`

| Feature | Free | Starter ($29/mo) | Professional ($79/mo) | Enterprise ($199/mo) |
|---|---|---|---|---|
| Articles/month | 3 (lifetime) | 30 | 100 | 300 |
| Outlines/month | 3 (lifetime) | 30 | 100 | 300 |
| Images/month | 3 (lifetime) | 60 | 200 | 600 |
| Social posts/month | 0 | 30 | 100 | 300 |
| Site audits/month | 0 | 5 (10 pages) | 15 (100 pages) | 50 (1000 pages) |
| AI improvements/article | 3 | 3 | 3 | 3 |

### HTTP Middleware Stack (order matters)

1. **Security headers** -- `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, HSTS (production), cache headers for `/uploads/`
2. **Request ID** -- UUID `X-Request-ID` (validates incoming, generates if absent)
3. **Request logging** -- Method, path, status code, duration (skips `/api/v1/health`)
4. **Request body size** -- 5MB limit for non-multipart POST/PUT/PATCH
5. **CORS** -- Configured origins, credentials enabled
6. **SlowAPI rate limiting** -- Global 100/minute default, per-endpoint overrides

### Sentry Integrations

FastAPI (URL-based transactions), SQLAlchemy, Redis, Logging (INFO level capture, ERROR level events). Traces: 10% in production. Profiles: 5% in production. PII sending disabled.
