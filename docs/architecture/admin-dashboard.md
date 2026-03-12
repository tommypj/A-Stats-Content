# Admin Dashboard Architecture

Complete reference for the A-Stats-Online admin dashboard — pages, components, backend API endpoints, and access control.

---

## Table of Contents

1. [Access Control](#access-control)
2. [Admin Pages](#admin-pages)
3. [Admin Components](#admin-components)
4. [Backend API Endpoints](#backend-api-endpoints)

---

## Access Control

### Roles

| Role | Value | Access Level |
|------|-------|-------------|
| User | `user` | No admin access |
| Admin | `admin` | Full admin dashboard access |
| Super Admin | `super_admin` | Admin access + hard delete users |

### Backend Dependencies

All admin routes use FastAPI dependency injection for authorization:

- **`get_current_admin_user`** — Requires `role` of `admin` or `super_admin`. Used on all admin endpoints.
- **`get_current_super_admin_user`** — Requires `role` of `super_admin`. Used on destructive operations (hard user delete).

Both dependencies are defined in `backend/api/deps_admin.py`.

### Audit Logging

All mutating admin actions are recorded to the `AdminAuditLog` table with:
- `admin_user_id` — Who performed the action
- `action` — Enum value from `AuditAction` (e.g., `USER_UPDATED`, `ALERTS_MARK_ALL_READ`)
- `target_type` — Enum from `AuditTargetType` (e.g., `USER`, `ARTICLE`, `SYSTEM`)
- `target_id` — ID of affected resource
- `details` — JSON metadata about the change

### Rate Limiting

Mutating endpoints use `@limiter.limit()` (slowapi) to prevent abuse. Typical limits:
- `20/minute` on write operations (update user, resolve error, send test email)
- `10/minute` on heavy analytics queries

### Frontend Guard

The admin layout at `frontend/app/(admin)/` checks the user's role client-side and redirects non-admin users. The `(admin)` route group uses Next.js App Router grouping.

---

## Admin Pages

### Dashboard (`/admin`)

**File:** `frontend/app/(admin)/admin/page.tsx`

Main overview page with platform health metrics.

**Features:**
- 4 primary StatsCards: Total Users, Total Articles, Monthly Revenue, Active Subscriptions
- Secondary stats grid: Active Users (7d), New Users (7d), Total Outlines, Total Images
- LineChart (Recharts): 7-day active user trend
- PieChart (Recharts): Subscription tier distribution (Free/Starter/Professional/Enterprise)
- QuickActions panel: 5 link cards to common admin destinations

**API calls:** `GET /admin/analytics/dashboard`

---

### Users List (`/admin/users`)

**File:** `frontend/app/(admin)/admin/users/page.tsx`

Paginated user management table.

**Features:**
- Search by name/email
- Filter by role (`user`, `admin`, `super_admin`), subscription tier, status (`active`, `suspended`)
- UserTable with select-all (indeterminate checkbox state)
- Bulk suspend with reason
- Per-row actions: View, Edit (UserEditModal), Suspend (SuspendUserModal)
- Pagination: 20 users per page

**API calls:** `GET /admin/users`

---

### User Detail (`/admin/users/[id]`)

**File:** `frontend/app/(admin)/admin/users/[id]/page.tsx`

Single user profile with full management controls.

**Features:**
- 3-column grid layout:
  - User info (name, email, role, status, dates)
  - Subscription details (tier, status, LemonSqueezy ID)
  - Usage stats (articles, outlines, images counts)
- Recent activity feed from audit logs
- Actions: Edit, Suspend/Unsuspend, Reset Password, Delete (with ConfirmDialog)
- Hard delete option (super_admin only, requires email confirmation)

**API calls:** `GET /admin/users/{id}`, `PUT /admin/users/{id}`, `POST /admin/users/{id}/suspend`, `POST /admin/users/{id}/unsuspend`, `POST /admin/users/{id}/reset-password`, `DELETE /admin/users/{id}`

---

### Articles (`/admin/content/articles`)

**File:** `frontend/app/(admin)/admin/content/articles/page.tsx`

Platform-wide article management.

**Features:**
- Search by title/keyword
- Filter by status (draft, generating, completed, failed)
- Table with checkbox selection for bulk operations
- Bulk delete selected articles
- Push-to-blog modal: Select category + tags, creates blog post from article
- Per-row: View, Delete

**API calls:** `GET /admin/content/articles`, `DELETE /admin/content/articles/{id}`, `POST /admin/content/bulk-delete`

---

### Outlines (`/admin/content/outlines`)

**File:** `frontend/app/(admin)/admin/content/outlines/page.tsx`

Platform-wide outline management.

**Features:**
- Search by title
- Filter by status
- Table with section count column
- Bulk delete
- Per-row: View, Delete

**API calls:** `GET /admin/content/outlines`, `DELETE /admin/content/outlines/{id}`, `POST /admin/content/bulk-delete`

---

### Images (`/admin/content/images`)

**File:** `frontend/app/(admin)/admin/content/images/page.tsx`

Generated image gallery management.

**Features:**
- Search by prompt text
- Filter by status
- Responsive grid layout (2-5 columns depending on viewport)
- Hover overlay showing prompt, status, and delete button
- Date range filter

**API calls:** `GET /admin/content/images`, `DELETE /admin/content/images/{id}`

---

### Blog Posts (`/admin/blog`)

**File:** `frontend/app/(admin)/admin/blog/page.tsx`

Blog CMS with full CRUD.

**Features:**
- Search by title
- Filter by status (draft/published) and category
- Table with edit, preview (external link), and delete actions
- Bulk delete
- "New Post" button links to `/admin/blog/new`

**API calls:** `GET /admin/blog/posts`, `DELETE /admin/blog/posts/{id}`

---

### New Blog Post (`/admin/blog/new`)

**File:** `frontend/app/(admin)/admin/blog/new/page.tsx`

Full blog post editor with AI generation.

**Features:**
- 3-column layout: editor, AI panel, sidebar
- Rich text editor for content
- AI content generation panel with parameters:
  - Primary keyword, tone, word count
  - Writing style, voice, list usage, language
  - Custom instructions, secondary keywords, entities
- Image generation with polling for completion
- FAQ schema builder (structured data for SEO)
- Category and tag selection sidebar
- Save as Draft / Publish actions

**API calls:** `POST /admin/blog/posts`, `POST /admin/blog/generate-content`, `POST /admin/blog/posts/persist-images`

---

### Edit Blog Post (`/admin/blog/[id]/edit`)

**File:** `frontend/app/(admin)/admin/blog/[id]/edit/page.tsx`

Same editor as New Post with existing data loaded.

**Features:**
- Same AI generation and image generation as New Post
- Publish / Unpublish toggle
- Delete with confirmation dialog

**API calls:** `GET /admin/blog/posts/{id}`, `PATCH /admin/blog/posts/{id}`, `POST /admin/blog/posts/{id}/publish`, `POST /admin/blog/posts/{id}/unpublish`, `DELETE /admin/blog/posts/{id}`

---

### Blog Categories (`/admin/blog/categories`)

**File:** `frontend/app/(admin)/admin/blog/categories/page.tsx`

Category management for blog posts.

**Features:**
- Inline create (name + slug input)
- Inline edit (click to modify)
- Delete (blocked if category has posts attached)
- Post count per category

**API calls:** `GET /admin/blog/categories`, `POST /admin/blog/categories`, `PATCH /admin/blog/categories/{id}`, `DELETE /admin/blog/categories/{id}`

---

### Alerts (`/admin/alerts`)

**File:** `frontend/app/(admin)/admin/alerts/page.tsx`

System alert management and triage.

**Features:**
- Filter by severity (info, warning, critical) and read status
- "Mark All Read" bulk action
- Per-alert: Toggle read/unread, resolve
- Severity-colored left border (green=info, yellow=warning, red=critical)
- Alert count badge in sidebar (from `/admin/alerts/count`)

**API calls:** `GET /admin/alerts`, `GET /admin/alerts/count`, `PUT /admin/alerts/{id}`, `POST /admin/alerts/mark-all-read`

---

### Generations (`/admin/generations`)

**File:** `frontend/app/(admin)/admin/generations/page.tsx`

AI generation monitoring and analytics.

**Features:**
- 5 stat cards: Total Generations, Success Rate, Failed, Avg Duration, Total Credits
- Filter by resource type (article/outline/image), status (started/success/failed), user
- Table columns: Type, Resource, User, Status, Duration, Credits, Date

**API calls:** `GET /admin/generations`, `GET /admin/generations/stats`

---

### Error Logs (`/admin/error-logs`)

**File:** `frontend/app/(admin)/admin/error-logs/page.tsx`

System error tracking and resolution.

**Features:**
- 6 stat cards: Total, Unresolved, Critical, Today, This Week, This Month
- 30-day trend bar chart (stacked: critical/error/warning)
- By-service breakdown horizontal bars
- Top recurring unresolved errors list
- Expandable error details:
  - Full message and stack trace
  - Context JSON (collapsible)
  - Metadata grid (service, endpoint, HTTP method/status, request ID, user agent, IP)
  - Resolution info (resolver, date, notes)
- Copy error to clipboard button
- Resolve / Reopen toggle

**API calls:** `GET /admin/error-logs`, `GET /admin/error-logs/stats`, `GET /admin/error-logs/filters/options`, `PUT /admin/error-logs/{id}`

---

### Audit Logs (`/admin/audit-logs`)

**File:** `frontend/app/(admin)/admin/audit-logs/page.tsx`

Admin action audit trail.

**Features:**
- Search by admin email or target
- Filter by action type and resource type
- Expandable rows showing user agent and full metadata JSON
- 50 entries per page

**API calls:** `GET /admin/audit-logs`

---

### Analytics (`/admin/analytics`)

**File:** `frontend/app/(admin)/admin/analytics/page.tsx`

Deep platform analytics with charts.

**Features:**
- Date range picker (default: 90 days)
- 4 summary cards: Total Users, Total Articles, MRR, 30-Day Retention
- 4 chart panels (dynamically imported via `next/dynamic`):
  - UserGrowthChart (signup trends over time)
  - ContentChart (articles/outlines/images created per day)
  - RevenueChart (monthly revenue, MRR, subscription distribution)
  - SubscriptionChart (tier distribution pie chart)
- Top creators table (top 10 users by content volume)

**API calls:** `GET /admin/analytics/dashboard`, `GET /admin/analytics/users`, `GET /admin/analytics/content`, `GET /admin/analytics/revenue`

---

### Settings (`/admin/settings`)

**File:** `frontend/app/(admin)/admin/settings/page.tsx`

Platform configuration overview (read-only).

**Features:**
- System status panel: 6 services with green/red indicators
- Service configuration: 6 API integrations with configured/not-configured status
- Platform info: Version, environment, tech stack details

---

### Email Templates (`/admin/emails`)

**File:** `frontend/app/(admin)/admin/emails/page.tsx`

Email journey template preview and testing.

**Features:**
- Template selector dropdown grouped by phase:
  - Onboarding (welcome, first_outline_nudge, outline_to_article, outline_reminder, connect_tools, week_one_recap)
  - Conversion (usage_80, usage_100, power_user, audit_upsell)
  - Retention (inactive_7d, inactive_21d, inactive_45d)
  - Ongoing (weekly_digest, content_decay)
  - System (unsubscribe_confirmation, resubscribe_confirmation)
- User name personalization input
- Full HTML preview in iframe with auto-resize
- Send test email to any address

**API calls:** `GET /admin/emails/templates`, `POST /admin/emails/preview`, `POST /admin/emails/send-test`

---

## Admin Components

All located in `frontend/components/admin/`.

### StatsCard

**File:** `stats-card.tsx`

Reusable metric display card.

**Props:**
- `icon` — Lucide icon component
- `value` — Display value (string or number)
- `title` — Label text
- `trend` (optional) — `{ direction: "up" | "down" | "stable", value: number }` with percentage and colored arrow
- `loading` — Shows skeleton placeholder

---

### QuickActions

**File:** `quick-actions.tsx`

Dashboard navigation shortcuts. 5 cards linking to:
- Manage Users (`/admin/users`)
- View Content (`/admin/content/articles`)
- View Analytics (`/admin/analytics`)
- Audit Logs (`/admin/audit-logs`)
- Settings (`/admin/settings`)

---

### UserTable

**File:** `user-table.tsx`

Sortable, selectable user data table.

**Features:**
- Select-all checkbox with indeterminate state (when some but not all selected)
- Columns: Checkbox, User, Role, Subscription, Created, Status, Actions
- Delegates row rendering to UserRow component

---

### UserRow

**File:** `user-row.tsx`

Individual user table row.

**Features:**
- Avatar circle with first-letter initial
- Name + email display
- RoleBadge, SubscriptionBadge components
- Relative date formatting
- Active/Suspended status badge
- Action buttons: View, Edit, Suspend (minimum 44px touch targets for accessibility)

---

### RoleBadge

**File:** `role-badge.tsx`

Colored role indicator.

| Role | Color |
|------|-------|
| `super_admin` | Red (danger) |
| `admin` | Yellow (warning) |
| `user` | Gray (secondary) |

---

### SubscriptionBadge

**File:** `subscription-badge.tsx`

Two-part subscription display.

- **Tier badge**: Shows tier name (Free, Starter, Professional, Enterprise)
- **Status badge** (optional): active=green, cancelled/expired=red, paused=yellow

---

### UserEditModal

**File:** `user-edit-modal.tsx`

Dialog for editing user properties.

**Fields:**
- Role select dropdown
- Subscription tier select dropdown
- Suspend checkbox with conditional reason textarea

---

### SuspendUserModal

**File:** `suspend-user-modal.tsx`

Confirmation dialog for suspending users.

**Features:**
- Supports single user or bulk (accepts `userIds[]`)
- Required reason textarea
- Warning banner explaining consequences

---

### DeleteUserModal

**File:** `delete-user-modal.tsx`

High-friction deletion dialog.

**Features:**
- Hard delete checkbox (super_admin only) — permanently removes all data
- Email confirmation input (must type user's email to confirm)
- Lists what gets deleted: articles, outlines, images, subscription data

---

### Chart Components

**Directory:** `frontend/components/admin/charts/`

All loaded via `next/dynamic` with `ssr: false` (Recharts requires browser APIs).

| Component | File | Chart Type | Data |
|-----------|------|-----------|------|
| UserGrowthChart | `user-growth-chart.tsx` | LineChart | Daily signups (total + verified) |
| ContentChart | `content-chart.tsx` | LineChart | Daily articles, outlines, images |
| RevenueChart | `revenue-chart.tsx` | BarChart + Line | Monthly revenue, new/churned subs |
| SubscriptionChart | `subscription-chart.tsx` | PieChart | Tier distribution with percentages |

---

## Backend API Endpoints

### Users (`/admin/users`)

**File:** `backend/api/routes/admin_users.py`

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| GET | `/admin/users` | List users with search, filter (role, tier, status), sort, pagination | admin |
| GET | `/admin/users/{id}` | User detail with subscription and usage stats | admin |
| PUT | `/admin/users/{id}` | Update role, tier, suspension (uses `FOR UPDATE` row lock) | admin |
| POST | `/admin/users/{id}/suspend` | Suspend user with required reason | admin |
| POST | `/admin/users/{id}/unsuspend` | Reactivate suspended user | admin |
| DELETE | `/admin/users/{id}` | Delete user (soft by default, hard with `?hard=true`) | super_admin |
| POST | `/admin/users/{id}/reset-password` | Generate reset token, optionally send email | admin |
| POST | `/admin/users/{id}/reset-usage` | Reset monthly usage counters | admin |

**Notable:** PUT uses `SELECT ... FOR UPDATE` to prevent race conditions on concurrent user updates.

---

### Content (`/admin/content`)

**File:** `backend/api/routes/admin_content.py`

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| GET | `/admin/content/articles` | List all articles platform-wide | admin |
| GET | `/admin/content/articles/{id}` | Article detail with associated images | admin |
| DELETE | `/admin/content/articles/{id}` | Delete article | admin |
| GET | `/admin/content/outlines` | List all outlines | admin |
| DELETE | `/admin/content/outlines/{id}` | Delete outline | admin |
| GET | `/admin/content/images` | List images with optional date range filter | admin |
| DELETE | `/admin/content/images/{id}` | Delete image (removes from storage too) | admin |
| GET | `/admin/content/social-posts` | List all scheduled social posts | admin |
| DELETE | `/admin/content/social-posts/{id}` | Delete social post | admin |
| POST | `/admin/content/bulk-delete` | Bulk delete articles or outlines by ID list | admin |

---

### Analytics (`/admin/analytics`)

**File:** `backend/api/routes/admin_analytics.py`

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| GET | `/admin/analytics/dashboard` | Main dashboard stats: users, content, subscriptions, revenue, usage trends (7d/30d) | admin |
| GET | `/admin/analytics/users` | Signup trends (30d), retention metrics (1d/7d/30d), conversion rates, geographic distribution | admin |
| GET | `/admin/analytics/content` | Content creation trends (30d), top 10 creators, article/outline status breakdown | admin |
| GET | `/admin/analytics/revenue` | Monthly revenue (12mo), subscription distribution, churn indicators (6mo), MRR/ARR, growth rate | admin |
| GET | `/admin/analytics/system` | Table record counts, storage estimates, background job status (social posts, knowledge processing) | admin |

**Tier pricing used for revenue estimates:**
- Free: $0
- Starter: $29/mo
- Professional: $79/mo
- Enterprise: $199/mo

**Retention calculation:** Percentage of users who logged in N days after signup (excludes deleted and suspended users).

---

### Blog (`/admin/blog`)

**File:** `backend/api/routes/admin_blog.py`

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| GET | `/admin/blog/posts` | List blog posts with search, status/category filters | admin |
| POST | `/admin/blog/posts` | Create new blog post | admin |
| GET | `/admin/blog/posts/{id}` | Get single blog post | admin |
| PATCH | `/admin/blog/posts/{id}` | Update blog post fields | admin |
| DELETE | `/admin/blog/posts/{id}` | Delete blog post | admin |
| POST | `/admin/blog/posts/{id}/publish` | Set post status to published, set published_at | admin |
| POST | `/admin/blog/posts/{id}/unpublish` | Revert post to draft status | admin |
| GET | `/admin/blog/categories` | List categories with post counts | admin |
| POST | `/admin/blog/categories` | Create category | admin |
| PATCH | `/admin/blog/categories/{id}` | Update category | admin |
| DELETE | `/admin/blog/categories/{id}` | Delete category (blocked if posts exist) | admin |
| GET | `/admin/blog/tags` | List tags | admin |
| POST | `/admin/blog/tags` | Create tag | admin |
| DELETE | `/admin/blog/tags/{id}` | Delete tag | admin |
| POST | `/admin/blog/generate-content` | AI content generation via content_pipeline | admin |
| POST | `/admin/blog/posts/from-article` | Convert user article to blog post | admin |
| POST | `/admin/blog/posts/persist-images` | Download and persist generated images | admin |

---

### Alerts (`/admin/alerts`)

**File:** `backend/api/routes/admin_alerts.py`

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| GET | `/admin/alerts/count` | Unread + critical alert counts (for badge) | admin |
| GET | `/admin/alerts` | List alerts with pagination, filter by read/severity/type | admin |
| PUT | `/admin/alerts/{id}` | Update alert (mark read/resolved) | admin |
| POST | `/admin/alerts/mark-all-read` | Mark all unread alerts as read (with audit log) | admin |

---

### Error Logs (`/admin/error-logs`)

**File:** `backend/api/routes/admin_error_logs.py`

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| GET | `/admin/error-logs` | List errors with filter by severity, type, service, resolution status, search | admin |
| GET | `/admin/error-logs/stats` | Aggregated stats: totals, by type (top 10), by service (top 10), 30-day trend, top recurring | admin |
| GET | `/admin/error-logs/filters/options` | Distinct values for filter dropdowns (types, services, severities) | admin |
| PUT | `/admin/error-logs/{id}` | Resolve or reopen an error log with optional resolution notes | admin |

---

### Generations (`/admin/generations`)

**File:** `backend/api/routes/admin_generations.py`

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| GET | `/admin/generations` | List generation logs with filter by resource_type, status, user_id | admin |
| GET | `/admin/generations/stats` | Aggregated stats: totals by type/status, success rate, avg duration, total credits | admin |

---

### Emails (`/admin/emails`)

**File:** `backend/api/routes/admin_emails.py`

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| GET | `/admin/emails/templates` | List all email journey templates with phase and priority | admin |
| POST | `/admin/emails/preview` | Render template with sample data, returns HTML + subject | admin |
| POST | `/admin/emails/send-test` | Send test email via Resend API (prefixes subject with `[TEST]`) | admin |

**Template keys:** 17 templates across 5 phases (onboarding, conversion, retention, ongoing, system). Rendering uses `JourneyTemplates` class with sample data for each template.

---

### Audit Logs (`/admin/audit-logs`)

Served from `backend/api/routes/admin_users.py` (same router).

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| GET | `/admin/audit-logs` | List audit logs with filter by admin user, target, action type, date range | admin |
