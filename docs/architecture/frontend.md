# Frontend Architecture

## 1. Overview

- **Framework**: Next.js 14.2.35, App Router, React 18.2, TypeScript 5.3
- **Styling**: Tailwind CSS 3.4 + `@tailwindcss/typography`, class-variance-authority, tailwind-merge
- **State**: Zustand 4.5 (client), TanStack React Query 5.17 (server)
- **HTTP**: Axios 1.6 with interceptors (cookie-based auth, silent token refresh)
- **Forms**: react-hook-form 7.49 + zod 3.22
- **Charts**: Recharts 2.15
- **i18n**: next-intl 3.4 (5 locales: en, ro, es, de, fr)
- **Monitoring**: Sentry (client/server/edge configs), PostHog analytics
- **Payments**: LemonSqueezy (lemon.js overlay checkout)
- **E2E Testing**: Playwright 1.58
- **Deployment**: Vercel

Package name: `astats-frontend`, version `2.0.0`.

---

## 2. Directory Structure

```
frontend/
  app/                        # Next.js App Router pages and layouts
    (admin)/                  # Admin route group (role-gated)
      layout.tsx              # Admin sidebar layout with role verification
      loading.tsx             # Admin loading spinner
      error.tsx               # Admin error boundary
      admin/                  # 17 admin pages (see Section 3)
    (dashboard)/              # Dashboard route group (auth-gated)
      layout.tsx              # Dashboard sidebar, notifications, project switcher
      loading.tsx             # Dashboard loading spinner
      error.tsx               # Dashboard error boundary
      agency/                 # Agency management pages
      analytics/              # Analytics & GSC pages
      articles/               # Article management pages
      billing/                # Billing success page
      bulk/                   # Bulk content pages
      competitor-analysis/    # Competitor analysis page
      content-calendar/       # Content calendar page
      dashboard/              # Main dashboard overview
      help/                   # Help & documentation pages
      images/                 # Image management pages
      keyword-research/       # Keyword research page
      knowledge/              # Knowledge vault pages
      outlines/               # Outline management pages
      projects/               # Project management pages
      reports/                # SEO reports page
      settings/               # Settings pages (profile, billing, integrations, notifications)
      site-audit/             # Site audit page
      social/                 # Social media pages
      tags/                   # Tags management page
      templates/              # Article templates page
    [locale]/                 # Locale-prefixed public routes
      (auth)/                 # Auth pages (login, register, etc.)
      blog/                   # Public blog
      docs/                   # Public documentation
      legal/                  # Legal pages (terms, privacy, cookies, data-deletion)
      pricing/                # Pricing page
      page.tsx                # Landing page
      layout.tsx              # Public locale layout
    api/                      # API routes
      docs-content/[...path]/ # Docs content API route
    portal/                   # Client portal (token-based access)
    invite/[token]/           # Project invitation acceptance
    layout.tsx                # Root layout (Providers, LemonSqueezy, Toaster, CookieBanner)
    globals.css               # Global styles, CSS custom properties, component classes
    page.tsx                  # Root page (redirects to locale landing)
    sitemap.ts                # Dynamic sitemap generation
    opengraph-image.tsx       # Dynamic OG image generation
    global-error.tsx          # Global error page
    not-found.tsx             # 404 page
  components/                 # 75 reusable components (see Section 4)
    admin/                    # Admin-specific components (13)
    analytics/                # Analytics components (5)
    article/                  # Article components (2)
    auth/                     # Auth components (1)
    blog/                     # Blog components (3)
    docs/                     # Documentation components (4)
    knowledge/                # Knowledge vault components (4)
    landing/                  # Landing page components (3)
    project/                  # Project management components (10)
    settings/                 # Settings components (1)
    social/                   # Social media components (8)
    ui/                       # Shared UI primitives (14)
    providers.tsx             # QueryClient + PostHog provider wrapper
    GenerationTrackerProvider.tsx  # Background generation polling
    LemonSqueezyInit.tsx      # LemonSqueezy JS initialization
    PostHogProvider.tsx       # PostHog analytics provider + pageview tracker
    publish-to-wordpress-modal.tsx # WordPress publish dialog
    social-posts-modal.tsx    # Social posts generation dialog
  contexts/
    ProjectContext.tsx        # Project/workspace switching context
  hooks/
    useKeyboardShortcuts.ts   # Global keyboard event handler
  i18n/
    config.ts                 # Locale definitions (en, ro, es, de, fr)
  lib/
    api.ts                    # Centralized API client with 20 namespaces
    utils.ts                  # Utility functions (cn, etc.)
    posthog.ts                # PostHog trackEvent utility
    lemonsqueezy.ts           # LemonSqueezy overlay checkout helper
  stores/
    auth.ts                   # Zustand auth store (user, isAuthenticated)
    generation-tracker.ts     # Zustand generation tracking store
  styles/                     # (empty, styles in globals.css)
  types/                      # TypeScript type definitions
  e2e/                        # Playwright E2E tests (12 spec files)
    global-setup.ts           # Pre-test auth login
    global-teardown.ts        # Post-test cleanup
    tests/                    # Test spec files
    .auth/                    # Persisted auth state
  content/                    # Static content files
  docs/                       # Documentation source files
  public/                     # Static assets (favicons, icons, manifest)
  scripts/
    copy-docs.js              # Pre-build docs copy script
  middleware.ts               # next-intl locale routing middleware
  next.config.js              # Next.js configuration
  tailwind.config.ts          # Tailwind CSS configuration
  tsconfig.json               # TypeScript configuration
  playwright.config.ts        # Playwright test configuration
  sentry.client.config.ts     # Sentry client-side config
  sentry.server.config.ts     # Sentry server-side config
  sentry.edge.config.ts       # Sentry edge runtime config
  instrumentation.ts          # Next.js instrumentation
  vercel.json                 # Vercel deployment config
```

---

## 3. All Pages (97 pages)

### (dashboard) -- Authenticated User Pages

#### Core

| Route | File | Description |
|-------|------|-------------|
| `/dashboard` | `dashboard/page.tsx` | Main dashboard overview with stats, recent content, quick actions |

#### Content Management

| Route | File | Description |
|-------|------|-------------|
| `/outlines` | `outlines/page.tsx` | List all outlines with filtering, bulk actions, export |
| `/outlines/[id]` | `outlines/[id]/page.tsx` | Outline detail view, section editor, regeneration |
| `/articles` | `articles/page.tsx` | List all articles with filtering, bulk actions, export |
| `/articles/new` | `articles/new/page.tsx` | Create new article from outline or scratch |
| `/articles/[id]` | `articles/[id]/page.tsx` | Article detail view, editor, SEO analysis, social posts, revisions |
| `/images` | `images/page.tsx` | Image gallery with filtering, bulk delete |
| `/images/generate` | `images/generate/page.tsx` | AI image generation interface |
| `/content-calendar` | `content-calendar/page.tsx` | Calendar view for scheduled content |
| `/templates` | `templates/page.tsx` | Article templates management (CRUD) |
| `/tags` | `tags/page.tsx` | Tags management for organizing articles and outlines |
| `/keyword-research` | `keyword-research/page.tsx` | AI-powered keyword suggestion tool |

#### Analytics

| Route | File | Description |
|-------|------|-------------|
| `/analytics` | `analytics/page.tsx` | Analytics overview with GSC data, charts |
| `/analytics/keywords` | `analytics/keywords/page.tsx` | Keyword ranking tracking |
| `/analytics/pages` | `analytics/pages/page.tsx` | Page-level performance metrics |
| `/analytics/articles` | `analytics/articles/page.tsx` | Article performance list |
| `/analytics/articles/[id]` | `analytics/articles/[id]/page.tsx` | Individual article performance detail |
| `/analytics/opportunities` | `analytics/opportunities/page.tsx` | Content gap opportunities |
| `/analytics/content-health` | `analytics/content-health/page.tsx` | Content decay detection and alerts |
| `/analytics/aeo` | `analytics/aeo/page.tsx` | Answer Engine Optimization scores overview |
| `/analytics/revenue` | `analytics/revenue/page.tsx` | Content-to-revenue attribution dashboard |
| `/analytics/revenue/goals` | `analytics/revenue/goals/page.tsx` | Conversion goal management |
| `/analytics/callback` | `analytics/callback/page.tsx` | Google OAuth callback handler |

#### Social Media

| Route | File | Description |
|-------|------|-------------|
| `/social` | `social/page.tsx` | Social media dashboard overview |
| `/social/compose` | `social/compose/page.tsx` | Compose and schedule social posts |
| `/social/calendar` | `social/calendar/page.tsx` | Social media content calendar |
| `/social/history` | `social/history/page.tsx` | Published post history |
| `/social/accounts` | `social/accounts/page.tsx` | Connected social account management |
| `/social/callback` | `social/callback/page.tsx` | Social OAuth callback handler |
| `/social/posts/[id]` | `social/posts/[id]/page.tsx` | Individual social post detail |

#### Bulk Content

| Route | File | Description |
|-------|------|-------------|
| `/bulk` | `bulk/page.tsx` | Bulk content job management |
| `/bulk/templates` | `bulk/templates/page.tsx` | Bulk content templates |
| `/bulk/jobs/[id]` | `bulk/jobs/[id]/page.tsx` | Individual bulk job detail and progress |

#### Knowledge Vault

| Route | File | Description |
|-------|------|-------------|
| `/knowledge` | `knowledge/page.tsx` | Knowledge vault overview |
| `/knowledge/sources` | `knowledge/sources/page.tsx` | Knowledge source list |
| `/knowledge/sources/[id]` | `knowledge/sources/[id]/page.tsx` | Individual source detail with snippets |
| `/knowledge/query` | `knowledge/query/page.tsx` | Semantic search across knowledge base |

#### Projects

| Route | File | Description |
|-------|------|-------------|
| `/projects` | `projects/page.tsx` | Project list (personal + team workspaces) |
| `/projects/new` | `projects/new/page.tsx` | Create new project |
| `/projects/brand-voice` | `projects/brand-voice/page.tsx` | Brand voice settings for current project |
| `/projects/[projectId]/settings` | `projects/[projectId]/settings/page.tsx` | Project settings (GSC, WordPress, members) |

#### Settings

| Route | File | Description |
|-------|------|-------------|
| `/settings` | `settings/page.tsx` | Profile settings (name, email, avatar, password, delete account) |
| `/settings/billing` | `settings/billing/page.tsx` | Subscription tier, checkout, cancel, refund |
| `/settings/integrations` | `settings/integrations/page.tsx` | WordPress and GSC integration management |
| `/settings/notifications` | `settings/notifications/page.tsx` | Email notification and journey preferences |

#### Agency

| Route | File | Description |
|-------|------|-------------|
| `/agency` | `agency/page.tsx` | Agency dashboard overview |
| `/agency/clients` | `agency/clients/page.tsx` | Client workspace list |
| `/agency/clients/[id]` | `agency/clients/[id]/page.tsx` | Client detail with portal management |
| `/agency/reports` | `agency/reports/page.tsx` | Agency report list |
| `/agency/reports/[id]` | `agency/reports/[id]/page.tsx` | Generated report detail view |
| `/agency/branding` | `agency/branding/page.tsx` | White-label branding settings |

#### Other Dashboard Pages

| Route | File | Description |
|-------|------|-------------|
| `/competitor-analysis` | `competitor-analysis/page.tsx` | Competitor domain analysis with keyword gaps |
| `/site-audit` | `site-audit/page.tsx` | Site audit (crawl, issues, PageSpeed) |
| `/reports` | `reports/page.tsx` | SEO reports list and generation |
| `/billing/success` | `billing/success/page.tsx` | Post-checkout success page |
| `/help` | `help/page.tsx` | Help center index |
| `/help/[category]` | `help/[category]/page.tsx` | Help category listing |
| `/help/[category]/[slug]` | `help/[category]/[slug]/page.tsx` | Individual help article |

### (admin) -- Admin Pages (17 pages)

| Route | File | Description |
|-------|------|-------------|
| `/admin` | `admin/page.tsx` | Admin dashboard with stats cards, charts |
| `/admin/users` | `admin/users/page.tsx` | User management list (search, filter, suspend, delete) |
| `/admin/users/[id]` | `admin/users/[id]/page.tsx` | User detail view with edit, suspend, reset password |
| `/admin/content/articles` | `admin/content/articles/page.tsx` | All articles across all users |
| `/admin/content/outlines` | `admin/content/outlines/page.tsx` | All outlines across all users |
| `/admin/content/images` | `admin/content/images/page.tsx` | All images across all users |
| `/admin/analytics` | `admin/analytics/page.tsx` | Platform-wide analytics (users, content, revenue) |
| `/admin/audit-logs` | `admin/audit-logs/page.tsx` | System audit log viewer |
| `/admin/generations` | `admin/generations/page.tsx` | AI generation history and stats |
| `/admin/error-logs` | `admin/error-logs/page.tsx` | Application error log viewer |
| `/admin/alerts` | `admin/alerts/page.tsx` | System alerts (content decay, errors) |
| `/admin/settings` | `admin/settings/page.tsx` | Admin-level settings |
| `/admin/blog` | `admin/blog/page.tsx` | Blog post management |
| `/admin/blog/new` | `admin/blog/new/page.tsx` | Create new blog post (with AI generation) |
| `/admin/blog/[id]/edit` | `admin/blog/[id]/edit/page.tsx` | Edit existing blog post |
| `/admin/blog/categories` | `admin/blog/categories/page.tsx` | Blog category management |
| `/admin/emails` | `admin/emails/page.tsx` | Email template preview and test send |

### [locale]/(auth) -- Authentication Pages (8 pages)

| Route | File | Description |
|-------|------|-------------|
| `/login` | `[locale]/(auth)/login/page.tsx` | Email/password login with OAuth buttons |
| `/register` | `[locale]/(auth)/register/page.tsx` | Account registration form |
| `/forgot-password` | `[locale]/(auth)/forgot-password/page.tsx` | Password reset request |
| `/reset-password` | `[locale]/(auth)/reset-password/page.tsx` | Password reset with token |
| `/verify-email` | `[locale]/(auth)/verify-email/page.tsx` | Email verification handler |
| `/verify-email-change` | `[locale]/(auth)/verify-email-change/page.tsx` | Email change verification handler |
| `/auth/callback` | `[locale]/(auth)/auth/callback/page.tsx` | OAuth callback handler (Google) |

*Note: Auth pages use the `(auth)` route group nested under `[locale]`, inheriting locale layout.*

### [locale] -- Public Marketing Pages (15 pages)

| Route | File | Description |
|-------|------|-------------|
| `/` or `/en` | `[locale]/page.tsx` | Landing page (AEO differentiator hero) |
| `/pricing` | `[locale]/pricing/page.tsx` | Pricing plans with feature comparison |
| `/blog` | `[locale]/blog/page.tsx` | Public blog listing |
| `/blog/[slug]` | `[locale]/blog/[slug]/page.tsx` | Individual blog post |
| `/blog/category/[slug]` | `[locale]/blog/category/[slug]/page.tsx` | Blog posts filtered by category |
| `/docs` | `[locale]/docs/page.tsx` | Documentation index |
| `/docs/[category]` | `[locale]/docs/[category]/page.tsx` | Documentation category listing |
| `/docs/[category]/[slug]` | `[locale]/docs/[category]/[slug]/page.tsx` | Individual documentation article |
| `/legal/terms` | `[locale]/legal/terms/page.tsx` | Terms of service |
| `/legal/privacy` | `[locale]/legal/privacy/page.tsx` | Privacy policy |
| `/legal/cookies` | `[locale]/legal/cookies/page.tsx` | Cookie policy |
| `/legal/data-deletion` | `[locale]/legal/data-deletion/page.tsx` | Data deletion instructions (GDPR) |

*Layouts: `[locale]/layout.tsx`, `[locale]/blog/layout.tsx`, `[locale]/docs/layout.tsx`, `[locale]/legal/layout.tsx`, `[locale]/pricing/layout.tsx`*

### Special Pages

| Route | File | Description |
|-------|------|-------------|
| `/portal/[token]` | `portal/[token]/page.tsx` | Agency client portal (public, token-gated) |
| `/invite/[token]` | `invite/[token]/page.tsx` | Project invitation acceptance page |

---

## 4. Components (75 components)

### UI Primitives (14 components)

| Component | File | Description | Key Props |
|-----------|------|-------------|-----------|
| `Button` | `ui/button.tsx` | CVA-based button with 6 variants (primary/secondary/ghost/outline/destructive/link), 4 sizes (sm/md/lg/icon) | `variant`, `size`, `isLoading`, `leftIcon`, `rightIcon` |
| `Input` | `ui/input.tsx` | Styled text input | Standard `<input>` props |
| `Textarea` | `ui/textarea.tsx` | Styled multiline input | Standard `<textarea>` props |
| `Card` | `ui/card.tsx` | Container with `Card`, `CardHeader`, `CardFooter`, `CardTitle`, `CardDescription`, `CardContent` subcomponents | `className` |
| `Dialog` | `ui/dialog.tsx` | Modal dialog with escape key handling, focus trap, ARIA attributes | `isOpen`, `onClose`, `title`, `children` |
| `ConfirmDialog` | `ui/confirm-dialog.tsx` | Confirmation modal with cancel/confirm actions | `isOpen`, `onClose`, `onConfirm`, `title`, `message` |
| `Badge` | `ui/badge.tsx` | Inline status label | `variant`, `children` |
| `Progress` | `ui/progress.tsx` | Progress bar | `value`, `max` |
| `Skeleton` | `ui/skeleton.tsx` | Loading placeholder | `className` |
| `Breadcrumb` | `ui/breadcrumb.tsx` | Auto-generated breadcrumb from pathname using `PATH_LABELS` map | None (reads `usePathname()`) |
| `ErrorBoundary` | `ui/error-boundary.tsx` | React error boundary with fallback UI | `children` |
| `CookieBanner` | `ui/cookie-banner.tsx` | GDPR cookie consent banner (gates GA loading) | None |
| `AIGenerationProgress` | `ui/ai-generation-progress.tsx` | Animated progress indicator for AI generation | `status`, `type` |
| `KeyboardShortcutsDialog` | `ui/keyboard-shortcuts-dialog.tsx` | Modal showing available keyboard shortcuts | `isOpen`, `onClose` |
| `TierGate` | `ui/tier-gate.tsx` | Upgrade card shown when user lacks required tier | `requiredTier`, `featureName` |

*Barrel export: `ui/index.ts` exports Button, Input, Textarea, Card (+ subs), Dialog, Badge, Progress, Skeleton.*

### Admin Components (13 components)

| Component | File | Description |
|-----------|------|-------------|
| `ContentChart` | `admin/charts/content-chart.tsx` | Recharts line chart for content creation trends |
| `RevenueChart` | `admin/charts/revenue-chart.tsx` | Recharts bar chart for revenue metrics |
| `SubscriptionChart` | `admin/charts/subscription-chart.tsx` | Recharts pie chart for subscription distribution |
| `UserGrowthChart` | `admin/charts/user-growth-chart.tsx` | Recharts area chart for user growth |
| `DeleteUserModal` | `admin/delete-user-modal.tsx` | Confirmation dialog for user deletion (soft/hard delete) |
| `QuickActions` | `admin/quick-actions.tsx` | Admin dashboard quick-action buttons |
| `RoleBadge` | `admin/role-badge.tsx` | Color-coded badge for user roles (admin/super_admin/user) |
| `StatsCard` | `admin/stats-card.tsx` | Metric card for admin dashboard |
| `SubscriptionBadge` | `admin/subscription-badge.tsx` | Color-coded badge for subscription tiers |
| `SuspendUserModal` | `admin/suspend-user-modal.tsx` | Dialog for suspending a user with reason |
| `UserEditModal` | `admin/user-edit-modal.tsx` | Dialog for editing user details (name, role, tier) |
| `UserRow` | `admin/user-row.tsx` | Table row component for user list |
| `UserTable` | `admin/user-table.tsx` | Sortable, filterable user table |

### Analytics Components (5 components)

| Component | File | Description |
|-----------|------|-------------|
| `DateRangePicker` | `analytics/date-range-picker.tsx` | Start/end date selector for analytics queries |
| `GoogleAnalytics` | `analytics/GoogleAnalytics.tsx` | GA4 script loader (respects cookie consent) |
| `GSCConnectBanner` | `analytics/gsc-connect-banner.tsx` | Banner prompting GSC connection |
| `PerformanceChart` | `analytics/performance-chart.tsx` | Recharts line chart for clicks/impressions/CTR |
| `StatCard` | `analytics/stat-card.tsx` | Metric card for analytics dashboards |

### Article Components (2 components)

| Component | File | Description |
|-----------|------|-------------|
| `QualityTierBadge` | `article/quality-tier-badge.tsx` | Badge showing article quality tier |
| `StructuredDataPreview` | `article/structured-data-preview.tsx` | JSON-LD structured data preview |

### Blog Components (3 components)

| Component | File | Description |
|-----------|------|-------------|
| `BlogListClient` | `blog/BlogListClient.tsx` | Client-side blog listing with pagination and search |
| `BlogPostClient` | `blog/BlogPostClient.tsx` | Client-side blog post renderer |
| `PostCard` | `blog/PostCard.tsx` | Blog post card for listing pages |

### Documentation Components (4 components)

| Component | File | Description |
|-----------|------|-------------|
| `DocsArticle` | `docs/DocsArticle.tsx` | Documentation article renderer |
| `DocsSearch` | `docs/DocsSearch.tsx` | Fuzzy search across docs (Fuse.js) |
| `DocsSidebar` | `docs/DocsSidebar.tsx` | Documentation sidebar navigation |
| `DocsSidebarLink` | `docs/DocsSidebarLink.tsx` | Individual sidebar navigation link |

### Project Components (10 components)

| Component | File | Description |
|-----------|------|-------------|
| `ContentOwnershipBadge` | `project/content-ownership-badge.tsx` | Badge showing which project owns content |
| `DeleteProjectModal` | `project/delete-project-modal.tsx` | Project deletion confirmation dialog |
| `InviteMemberForm` | `project/invite-member-form.tsx` | Form for inviting members by email |
| `ProjectInvitationsList` | `project/project-invitations-list.tsx` | Pending invitations list with revoke/resend |
| `ProjectMembersList` | `project/project-members-list.tsx` | Current members list with role management |
| `ProjectSettingsGeneral` | `project/project-settings-general.tsx` | Project name, description, logo settings |
| `ProjectSwitcher` | `project/project-switcher.tsx` | Dropdown to switch between projects/personal workspace |
| `RoleBadge` | `project/role-badge.tsx` | Badge for project roles (owner/admin/editor/viewer) |
| `TransferOwnershipModal` | `project/transfer-ownership-modal.tsx` | Dialog for transferring project ownership |
| `UsageLimitWarning` | `project/usage-limit-warning.tsx` | Warning shown when approaching generation limits |

### Knowledge Components (4 components)

| Component | File | Description |
|-----------|------|-------------|
| `QueryInput` | `knowledge/query-input.tsx` | Search input for knowledge base queries |
| `SourceCard` | `knowledge/source-card.tsx` | Knowledge source card with status |
| `SourceSnippet` | `knowledge/source-snippet.tsx` | Snippet preview from knowledge source |
| `UploadModal` | `knowledge/upload-modal.tsx` | File upload dialog for knowledge sources |

### Social Media Components (8 components)

| Component | File | Description |
|-----------|------|-------------|
| `CalendarView` | `social/calendar-view.tsx` | Monthly calendar grid for scheduled posts |
| `DateNavigation` | `social/date-navigation.tsx` | Date navigation for social calendar |
| `PlatformSelector` | `social/platform-selector.tsx` | Multi-select for social platforms (Twitter, LinkedIn, Facebook, Instagram) |
| `PostAnalyticsCard` | `social/post-analytics-card.tsx` | Analytics metrics for individual social post |
| `PostListItem` | `social/post-list-item.tsx` | Social post row in list view |
| `PostPreview` | `social/post-preview.tsx` | Platform-specific post preview |
| `PostStatusBadge` | `social/post-status-badge.tsx` | Badge for social post status (draft/scheduled/published/failed) |
| `SchedulePicker` | `social/schedule-picker.tsx` | Date/time picker for scheduling posts |

### Settings Components (1 component)

| Component | File | Description |
|-----------|------|-------------|
| `SettingsTabs` | `settings/settings-tabs.tsx` | Shared tab navigation for settings pages (Profile/Password/Billing/Integrations/Notifications) |

### Auth Components (1 component)

| Component | File | Description |
|-----------|------|-------------|
| `OAuthButtons` | `auth/oauth-buttons.tsx` | Google OAuth login/register buttons |

### Landing Page Components (3 components)

| Component | File | Description |
|-----------|------|-------------|
| `LandingPageClient` | `landing/LandingPageClient.tsx` | Client-side landing page with hero, features, CTA sections |
| `PublicFooter` | `landing/PublicFooter.tsx` | Footer for public pages (links, legal) |
| `PublicNav` | `landing/PublicNav.tsx` | Navigation bar for public pages (logo, links, login/register) |

### Top-Level Components (6 components)

| Component | File | Description |
|-----------|------|-------------|
| `Providers` | `providers.tsx` | Root provider: QueryClientProvider + PostHogProvider + ReactQueryDevtools |
| `GenerationTrackerProvider` | `GenerationTrackerProvider.tsx` | Polls backend for generation status, shows toast on completion |
| `LemonSqueezyInit` | `LemonSqueezyInit.tsx` | Calls `createLemonSqueezy()` on mount to enable overlay checkout |
| `PostHogProvider` | `PostHogProvider.tsx` | PostHog analytics initialization and pageview capture |
| `PublishToWordPressModal` | `publish-to-wordpress-modal.tsx` | Dialog for publishing articles to WordPress with category/tag selection |
| `SocialPostsModal` | `social-posts-modal.tsx` | Dialog for generating and editing social posts from an article |

---

## 5. API Client (`lib/api.ts`)

The API client is built on Axios with:
- **Base URL**: `NEXT_PUBLIC_API_URL/api/v1` (default `http://localhost:8000`)
- **Auth**: HttpOnly cookie-based (no localStorage tokens)
- **CSRF**: `X-Requested-With: XMLHttpRequest` header forces CORS preflight
- **Token refresh**: Automatic silent refresh on 401 via response interceptor with request queuing
- **Error handling**: `parseApiError()` extracts message from Axios/Pydantic errors; network/5xx errors show retry toast
- **Caching**: In-memory SWR-like cache (`apiCache` Map, max 100 entries) with TTL-based `cachedGet()`
- **Timeouts**: 30s default, 180s for AI generation (`AI_TIMEOUT`)

### Namespaces and Methods

#### `api.health`
- `check()` -- GET `/health`

#### `api.auth`
- `login(email, password, rememberMe?)` -- POST `/auth/login`
- `register(data)` -- POST `/auth/register`
- `me()` -- GET `/auth/me` (cached 60s)
- `logout()` -- POST `/auth/logout`
- `forgotPassword(email)` -- POST `/auth/password/reset-request`
- `resetPassword(token, password)` -- POST `/auth/password/reset`
- `verifyEmail(token)` -- POST `/auth/verify-email`
- `updateProfile(data)` -- PUT `/auth/me`
- `changePassword(currentPassword, newPassword)` -- POST `/auth/password/change`
- `deleteAccount()` -- DELETE `/auth/account`
- `changeEmail(newEmail, currentPassword)` -- POST `/auth/change-email`
- `verifyEmailChange(token)` -- POST `/auth/verify-email-change`
- `uploadAvatar(file)` -- POST `/auth/me/avatar` (multipart)
- `exportData()` -- GET `/auth/me/export` (blob download)

#### `api.outlines`
- `list(params?)` -- GET `/outlines`
- `get(id)` -- GET `/outlines/:id`
- `create(data)` -- POST `/outlines` (AI timeout)
- `update(id, data)` -- PUT `/outlines/:id`
- `delete(id)` -- DELETE `/outlines/:id`
- `bulkDelete(ids)` -- POST `/outlines/bulk-delete`
- `regenerate(id)` -- POST `/outlines/:id/regenerate` (AI timeout)
- `exportAll(format?)` -- GET `/outlines/export` (blob)
- `exportOne(id, format)` -- GET `/outlines/:id/export` (blob)

#### `api.articles`
- `list(params?)` -- GET `/articles`
- `get(id)` -- GET `/articles/:id`
- `create(data)` -- POST `/articles`
- `generate(data)` -- POST `/articles/generate` (AI timeout)
- `update(id, data)` -- PUT `/articles/:id`
- `delete(id)` -- DELETE `/articles/:id`
- `bulkDelete(ids)` -- POST `/articles/bulk-delete`
- `improve(id, improvementType)` -- POST `/articles/:id/improve` (AI timeout)
- `analyzeSeo(id)` -- POST `/articles/:id/analyze-seo`
- `generateImagePrompts(id)` -- POST `/articles/:id/generate-image-prompts` (AI timeout)
- `getSocialPosts(id)` -- GET `/articles/:id/social-posts`
- `generateSocialPosts(id)` -- POST `/articles/:id/generate-social-posts` (AI timeout)
- `updateSocialPost(id, platform, text)` -- PUT `/articles/:id/social-posts`
- `listRevisions(articleId, params?)` -- GET `/articles/:id/revisions`
- `getRevision(articleId, revisionId)` -- GET `/articles/:id/revisions/:revisionId`
- `restoreRevision(articleId, revisionId)` -- POST `/articles/:id/revisions/:revisionId/restore`
- `linkSuggestions(articleId)` -- GET `/articles/:id/link-suggestions`
- `healthSummary()` -- GET `/articles/health-summary`
- `keywordSuggestions(seedKeyword, count?)` -- POST `/articles/keyword-suggestions` (AI timeout)
- `keywordHistory()` -- GET `/articles/keyword-history`
- `exportAll(format?)` -- GET `/articles/export` (blob)
- `exportOne(id, format)` -- GET `/articles/:id/export` (blob)
- `getAeoScore(articleId)` -- GET `/articles/:id/aeo-score`
- `refreshAeoScore(articleId)` -- POST `/articles/:id/aeo-score`

#### `api.images`
- `list(params?)` -- GET `/images`
- `get(id)` -- GET `/images/:id`
- `generate(data)` -- POST `/images/generate` (returns 202 immediately)
- `delete(id)` -- DELETE `/images/:id`
- `bulkDelete(ids)` -- POST `/images/bulk-delete`
- `setFeatured(imageId, data)` -- POST `/images/:id/set-featured`

#### `api.wordpress`
- `connect(data)` -- POST `/wordpress/connect`
- `disconnect()` -- POST `/wordpress/disconnect`
- `status()` -- GET `/wordpress/status`
- `categories()` -- GET `/wordpress/categories`
- `tags()` -- GET `/wordpress/tags`
- `publish(data)` -- POST `/wordpress/publish`
- `uploadMedia(data)` -- POST `/wordpress/upload-media`

#### `api.analytics`
- `getAuthUrl()` -- GET `/analytics/gsc/auth-url`
- `handleCallback(code, state)` -- GET `/analytics/gsc/callback`
- `status()` -- GET `/analytics/gsc/status`
- `sites()` -- GET `/analytics/gsc/sites`
- `selectSite(siteUrl)` -- POST `/analytics/gsc/select-site`
- `disconnect()` -- POST `/analytics/gsc/disconnect`
- `sync()` -- POST `/analytics/gsc/sync`
- `keywords(params?)` -- GET `/analytics/keywords`
- `pages(params?)` -- GET `/analytics/pages`
- `daily(params?)` -- GET `/analytics/daily`
- `summary(params?)` -- GET `/analytics/summary`
- `articlePerformance(params?)` -- GET `/analytics/article-performance`
- `articlePerformanceDetail(articleId, params?)` -- GET `/analytics/article-performance/:id`
- `articleIndexStatus(articleId)` -- GET `/analytics/article-performance/:id/index-status`
- `opportunities(params?)` -- GET `/analytics/opportunities`
- `suggestContent(keywords, maxSuggestions?)` -- POST `/analytics/opportunities/suggest`
- `contentHealth()` -- GET `/analytics/decay/health`
- `decayAlerts(params?)` -- GET `/analytics/decay/alerts`
- `detectDecay()` -- POST `/analytics/decay/detect`
- `resolveAlert(alertId)` -- POST `/analytics/decay/alerts/:id/resolve`
- `suggestRecovery(alertId)` -- POST `/analytics/decay/alerts/:id/suggest`
- `markAllAlertsRead()` -- POST `/analytics/decay/alerts/mark-all-read`
- `aeoOverview()` -- GET `/analytics/aeo/overview`
- `revenueOverview(params?)` -- GET `/analytics/revenue/overview`
- `revenueByArticle(params?)` -- GET `/analytics/revenue/by-article`
- `revenueByKeyword(params?)` -- GET `/analytics/revenue/by-keyword`
- `revenueGoals()` -- GET `/analytics/revenue/goals`
- `createRevenueGoal(data)` -- POST `/analytics/revenue/goals`
- `updateRevenueGoal(goalId, data)` -- PUT `/analytics/revenue/goals/:id`
- `deleteRevenueGoal(goalId)` -- DELETE `/analytics/revenue/goals/:id`
- `importConversions(data)` -- POST `/analytics/revenue/import`
- `generateRevenueReport(reportType?)` -- POST `/analytics/revenue/report`
- `deviceBreakdown(days?)` -- GET `/analytics/device-breakdown`
- `countryBreakdown(days?, topN?)` -- GET `/analytics/country-breakdown`

#### `api.bulk`
- `templates()` -- GET `/bulk/templates`
- `createTemplate(data)` -- POST `/bulk/templates`
- `updateTemplate(id, data)` -- PUT `/bulk/templates/:id`
- `deleteTemplate(id)` -- DELETE `/bulk/templates/:id`
- `jobs(params?)` -- GET `/bulk/jobs`
- `getJob(jobId)` -- GET `/bulk/jobs/:id`
- `createOutlineJob(data)` -- POST `/bulk/jobs/outlines`
- `cancelJob(jobId)` -- POST `/bulk/jobs/:id/cancel`
- `retryFailed(jobId)` -- POST `/bulk/jobs/:id/retry-failed`

#### `api.billing`
- `pricing()` -- GET `/billing/pricing` (cached 5 min)
- `subscription()` -- GET `/billing/subscription`
- `checkout(plan, billingCycle)` -- POST `/billing/checkout`
- `portal()` -- GET `/billing/portal`
- `cancel()` -- POST `/billing/cancel`
- `refund()` -- POST `/billing/refund`

#### `api.knowledge`
- `upload(file, title?, description?, tags?, projectId?)` -- POST `/knowledge/upload` (multipart)
- `sources(params?)` -- GET `/knowledge/sources`
- `getSource(id)` -- GET `/knowledge/sources/:id`
- `deleteSource(id)` -- DELETE `/knowledge/sources/:id`
- `query(query, sourceIds?, maxResults?)` -- POST `/knowledge/query`
- `stats()` -- GET `/knowledge/stats`
- `reprocess(id)` -- POST `/knowledge/sources/:id/reprocess`

#### `api.social`
- `posts(params?)` -- GET `/social/posts`
- `getPost(id)` -- GET `/social/posts/:id`
- `createPost(data)` -- POST `/social/posts`
- `updatePost(id, data)` -- PUT `/social/posts/:id`
- `deletePost(id)` -- DELETE `/social/posts/:id`
- `publishNow(id)` -- POST `/social/posts/:id/publish-now`
- `reschedule(id, newDate)` -- PUT `/social/posts/:id`
- `retryFailed(id, targetIds?)` -- PUT `/social/posts/:id`
- `accounts()` -- GET `/social/accounts`
- `getConnectUrl(platform)` -- GET `/social/:platform/connect`
- `disconnectAccount(id)` -- DELETE `/social/accounts/:id`
- `verify(accountId)` -- POST `/social/accounts/:id/verify`
- `analytics(postId)` -- GET `/social/posts/:id/analytics`

#### `api.admin`
- `dashboard()` -- GET `/admin/analytics/dashboard`
- **`admin.users`**: `list`, `get`, `update`, `suspend`, `unsuspend`, `delete`, `resetPassword`, `bulkSuspend`
- **`admin.analytics`**: `users`, `content`, `revenue`, `system`
- **`admin.content`**: `articles`, `deleteArticle`, `outlines`, `deleteOutline`, `images`, `deleteImage`
- `auditLogs(params?)` -- GET `/admin/audit-logs`
- **`admin.generations`**: `list`, `stats`
- **`admin.errorLogs`**: `list`, `get`, `stats`, `update`, `filterOptions`
- **`admin.alerts`**: `list`, `count`, `update`, `markAllRead`
- **`admin.blog.posts`**: `list`, `get`, `create`, `update`, `delete`, `publish`, `unpublish`
- **`admin.blog.categories`**: `list`, `create`, `update`, `delete`
- **`admin.blog.tags`**: `list`, `create`, `delete`
- `admin.blog.generateContent(data)` -- POST `/admin/blog/generate-content` (AI timeout)
- `admin.blog.fromArticle(data)` -- POST `/admin/blog/posts/from-article`
- **`admin.emails`**: `templates`, `preview`, `sendTest`

#### `api.projects`
- `list()` -- GET `/projects` (cached 30s)
- `get(id)` -- GET `/projects/:id`
- `create(data)` -- POST `/projects`
- `update(id, data)` -- PUT `/projects/:id`
- `delete(id)` -- DELETE `/projects/:id`
- `switch(id)` -- POST `/projects/switch`
- `getCurrent()` -- GET `/projects/current` (cached 30s)
- `uploadLogo(projectId, file)` -- POST `/projects/:id/logo` (multipart)
- `transferOwnership(projectId, newOwnerId)` -- POST `/projects/:id/transfer-ownership`
- `leave(projectId)` -- POST `/projects/:id/leave`
- `getBrandVoice()` -- GET `/projects/current/brand-voice`
- `updateBrandVoice(data)` -- PUT `/projects/current/brand-voice`
- **`projects.members`**: `list`, `update`, `remove`
- **`projects.invitations`**: `list`, `create`, `revoke`, `resend`, `getByToken`, `accept`

#### `api.notifications`
- `generationStatus(params?)` -- GET `/notifications/generation-status`
- `getPreferences()` -- GET `/notifications/preferences`
- `updatePreferences(data)` -- PUT `/notifications/preferences`

#### `api.agency`
- `getProfile()` -- GET `/agency/profile`
- `createProfile(data)` -- POST `/agency/profile`
- `updateProfile(data)` -- PUT `/agency/profile`
- `deleteProfile()` -- DELETE `/agency/profile`
- `clients()` -- GET `/agency/clients`
- `createClient(data)` -- POST `/agency/clients`
- `getClient(id)` -- GET `/agency/clients/:id`
- `updateClient(id, data)` -- PUT `/agency/clients/:id`
- `deleteClient(id)` -- DELETE `/agency/clients/:id`
- `enablePortal(id)` -- POST `/agency/clients/:id/enable-portal`
- `disablePortal(id)` -- POST `/agency/clients/:id/disable-portal`
- `reportTemplates()` -- GET `/agency/templates`
- `createReportTemplate(data)` -- POST `/agency/templates`
- `updateReportTemplate(id, data)` -- PUT `/agency/templates/:id`
- `deleteReportTemplate(id)` -- DELETE `/agency/templates/:id`
- `generateReport(data)` -- POST `/agency/reports/generate`
- `reports(params?)` -- GET `/agency/reports`
- `getReport(id)` -- GET `/agency/reports/:id`
- `portal(token)` -- GET `/agency/portal/:token` (public)

#### `api.competitors`
- `analyze(domain, projectId?)` -- POST `/competitors/analyze`
- `list(page?, pageSize?)` -- GET `/competitors/analyses`
- `get(id)` -- GET `/competitors/analyses/:id`
- `delete(id)` -- DELETE `/competitors/analyses/:id`
- `keywords(id)` -- GET `/competitors/analyses/:id/keywords`
- `gaps(id)` -- GET `/competitors/analyses/:id/gaps`

#### `api.siteAudit`
- `start(domain)` -- POST `/site-audit/start`
- `list(params)` -- GET `/site-audit/audits`
- `get(id)` -- GET `/site-audit/audits/:id`
- `pages(id, params)` -- GET `/site-audit/audits/:id/pages`
- `issues(id, params)` -- GET `/site-audit/audits/:id/issues`
- `delete(id)` -- DELETE `/site-audit/audits/:id`
- `exportCsv(id)` -- GET `/site-audit/audits/:id/export`

#### `api.templates`
- `list(params?)` -- GET `/templates`
- `get(id)` -- GET `/templates/:id`
- `create(data)` -- POST `/templates`
- `update(id, data)` -- PUT `/templates/:id`
- `delete(id)` -- DELETE `/templates/:id`

#### `api.tags`
- `list(params?)` -- GET `/tags`
- `create(data)` -- POST `/tags`
- `update(id, data)` -- PUT `/tags/:id`
- `delete(id)` -- DELETE `/tags/:id`
- `getArticleTags(articleId)` -- GET `/tags/articles/:id`
- `setArticleTags(articleId, tagIds)` -- PUT `/tags/articles/:id`
- `getOutlineTags(outlineId)` -- GET `/tags/outlines/:id`
- `setOutlineTags(outlineId, tagIds)` -- PUT `/tags/outlines/:id`

#### `api.reports`
- `list(params?)` -- GET `/reports`
- `get(id)` -- GET `/reports/:id`
- `create(data)` -- POST `/reports`
- `delete(id)` -- DELETE `/reports/:id`

#### `api.blog` (public)
- `list(params?)` -- GET `/blog/posts`
- `getBySlug(slug)` -- GET `/blog/posts/:slug`
- `categories()` -- GET `/blog/categories`
- `tags()` -- GET `/blog/tags`

---

## 6. State Management

### Zustand Stores

#### Auth Store (`stores/auth.ts`)

Persisted to `localStorage` under key `auth-storage`.

```
State:
  user: User | null          # { id, email, name, role, subscription_tier }
  isAuthenticated: boolean
  isLoading: boolean         # true until Zustand hydration completes

Actions:
  setUser(user)              # Update user, derive isAuthenticated
  login(user)                # Set user + isAuthenticated + isLoading=false
  logout()                   # Clear user state (cookies cleared by backend)
  setLoading(loading)        # Manual loading control

Persistence:
  Partializes: user, isAuthenticated (not isLoading)
  onRehydrateStorage: sets isLoading=false after hydration
```

#### Generation Tracker Store (`stores/generation-tracker.ts`)

Persisted to `localStorage` under key `generation-tracker`.

```
Types:
  GenerationType: "article" | "image" | "outline" | "bulk"
  GenerationStatus: "generating" | "completed" | "failed"
  TrackedGeneration: { id, type, status, title, startedAt, articleId?, imageId? }

Timeouts:
  article: 12 min, image: 3 min, outline: 3 min, bulk: 30 min

State:
  generations: TrackedGeneration[]
  suppressedIds: string[]      # IDs user has dismissed

Actions:
  track(gen)       # Add new generation (deduplicates by id)
  update(id, data) # Partial update
  remove(id)       # Remove generation and its suppression
  clear()          # Remove all
  suppress(id)     # Hide notification
  unsuppress(id)   # Show notification again

Persistence:
  Partializes: generations only (not suppressedIds)
  onRehydrateStorage: prunes expired generations based on timeouts
```

### React Query

All dashboard pages use `useQuery` for data fetching and `useMutation` for write operations.

**Configuration** (in `providers.tsx`):
- `staleTime`: 60 seconds
- `gcTime`: 5 minutes
- `retry`: 1 for queries, 0 for mutations
- `refetchOnWindowFocus`: disabled

**Patterns**:
- Never use global `onSuccess`/`onError` on `useMutation` when the mutation is called from multiple handlers -- React Query fires both callbacks. Use per-call callbacks only.
- Derived arrays (`.filter()`, `.map()`) that create new references every render must be wrapped in `useMemo` if used as `useEffect` dependencies.
- `ReactQueryDevtools` rendered in development only.

### Context

#### ProjectContext (`contexts/ProjectContext.tsx`)

Provides workspace/project switching for multi-tenancy.

```
State:
  currentProject: Project | null
  projects: Project[]
  isLoading: boolean
  isPersonalWorkspace: boolean  # true when no project or personal project

Permission helpers (derived from my_role):
  canCreate: boolean     # owner/admin/member or personal workspace
  canEdit: boolean       # owner/admin/member or personal workspace
  canManage: boolean     # owner/admin in project
  canBilling: boolean    # owner in project
  isViewer: boolean      # viewer role

Usage tracking:
  usage: { articles_used, outlines_used, images_used } | null
  limits: { articles_per_month, outlines_per_month, images_per_month } | null
  isAtLimit(resource)    # Returns true when usage >= limit

Actions:
  switchProject(projectId | null)  # Calls API + updates local state
  refreshProjects()                # Re-fetch from API
  createProject(data)              # Create + auto-switch
```

Persists current project ID in `localStorage` under `current_project_id`.

---

## 7. Hooks

### `useKeyboardShortcuts(shortcuts: KeyboardShortcut[])`

**File**: `hooks/useKeyboardShortcuts.ts`

Registers global `keydown` event listeners for keyboard shortcuts.

**Interface**:
```typescript
interface KeyboardShortcut {
  key: string;           // Key to match (case-insensitive)
  ctrl?: boolean;        // Require Ctrl (Win/Linux) or Cmd (Mac)
  shift?: boolean;       // Require Shift
  handler: () => void;   // Callback
}
```

**Behavior**:
- Bare-key shortcuts (no ctrl) are suppressed when user is typing in an input, textarea, or contenteditable element
- Modifier shortcuts (ctrl/cmd) fire regardless of focus context (e.g., Ctrl+S works inside the article editor)
- Inherently shifted characters (`?`, `!`, `@`, etc.) skip the shift modifier check since `event.key` already encodes the shift state
- Uses a ref to avoid re-registering event listeners when shortcuts change

**Dashboard usage**: `?` or `Ctrl+/` opens the keyboard shortcuts dialog.

### Auth Guard (Dashboard Layout)

Authentication is handled directly in the `(dashboard)/layout.tsx` rather than a separate hook:

1. Wait for Zustand hydration to complete
2. If `isAuthenticated` is false in Zustand, redirect to `/login`
3. Verify session against backend via `api.auth.me()`
4. On failure: call `logout()` and redirect to `/login`
5. Safety timeout: if Zustand hydration never completes, redirect after 10 seconds

The admin layout uses the same pattern, additionally checking that `user.role` is `admin` or `super_admin`.

---

## 8. Design System & Styles

### Tailwind Configuration

**File**: `tailwind.config.ts`

#### Fonts

| Token | Font Stack | Usage |
|-------|-----------|-------|
| `font-sans` | Source Sans 3, Inter, system-ui, sans-serif | Body text, UI elements |
| `font-display` | Playfair Display, Cal Sans, Georgia, serif | Headings (h1-h6 via globals.css) |

#### Color Palette

**Sage Green Primary** (brand color `#627862`):
- `primary-50` through `primary-950` -- 11 shades from `#f6f7f6` to `#171c17`
- Main brand: `primary-500` (`#627862`)

**Warm Cream Surfaces**:
- `surface` / `surface-DEFAULT`: `#fdfcfa` (main background)
- `surface-secondary`: `#f9f6f0` (sidebar backgrounds, hover states)
- `surface-tertiary`: `#f3ece0` (borders, dividers)

**Text Colors**:
- `text-primary`: `#2e352e` (headings, body)
- `text-secondary`: `#533f38` (subtext)
- `text-muted`: `#6c5b45` (captions, hints)
- `text-tertiary`: `#9b8e7b` (timestamps, placeholders)

**Extended Palettes**:
- `cream-50` to `cream-500` -- warm tones for cards and accents
- `earth-400` to `earth-800` -- earthy browns for accents
- `terra-400` to `terra-800` -- terracotta tones

**Social Platform Colors**:
- `social-twitter`: `#1DA1F2`
- `social-linkedin`: `#0A66C2`
- `social-facebook`: `#1877F2`
- `social-instagram`: `#E4405F`
- `social-wordpress`: `#21759B`

**Healing Palette** (legacy/branding):
- `healing-sage`: `#627862`
- `healing-lavender`: `#a17d66`
- `healing-sky`: `#bc7a5c`
- `healing-sand`: `#e9dcc8`
- `healing-cream`: `#fdfcfa`

#### Border Radius

- `rounded-soft`: `0.625rem` (10px)
- `rounded-softer`: `1rem` (16px)
- `rounded-4xl`: `2rem` (32px)

#### Shadows

- `shadow-soft`: Subtle dual-layer shadow for cards
- `shadow-soft-lg`: Larger shadow for dropdowns
- `shadow-inner-soft`: Inset shadow for pressed states

#### Animations

| Name | Duration | Description |
|------|----------|-------------|
| `animate-fade-in` | 0.3s | Opacity 0 to 1 |
| `animate-slide-up` | 0.4s | 10px translateY with fade |
| `animate-pulse-soft` | 2s infinite | Gentle opacity pulse |
| `animate-writing` | 1.5s infinite | Pen-writing motion (rotate + translate) |

### CSS Custom Properties (`globals.css`)

HSL-based properties for shadcn/ui compatibility:

```css
:root {
  --background: 40 40% 98%;
  --foreground: 138 10% 19%;
  --primary: 138 20% 42%;
  --secondary: 38 30% 88%;
  --muted: 38 30% 88%;
  --accent: 14 40% 55%;
  --destructive: 0 65% 50%;
  --border: 36 15% 86%;
  --ring: 138 20% 42%;
  --radius: 0.75rem;
}
```

### Component Classes

Defined in `@layer components` within `globals.css`:

- `.btn` -- Base button styles (rounded-xl, transition, focus ring)
- `.btn-primary` -- Primary button (sage green bg, white text)
- `.btn-secondary` -- Secondary button (cream bg, dark text)
- `.btn-ghost` -- Transparent button (hover reveals bg)
- `.card` -- Card container (cream bg, tertiary border, soft shadow)

### Global Base Styles

- Body: `bg-surface text-text-primary antialiased` with OpenType features
- Headings (h1-h6): `font-display tracking-tight`
- Responsive typography: h1 scales `text-2xl sm:text-3xl`, h2 scales `text-xl sm:text-2xl`
- LemonSqueezy overlay: `.lemonsqueezy-loader` with 40% opacity backdrop + blur

### Design Rules

- **No `bg-white` or `gray-*` in dashboard** -- use design tokens (`bg-surface`, `bg-surface-secondary`, etc.)
- Button component uses `class-variance-authority` (CVA) for variant management
- All utility merging done via `tailwind-merge` (`cn()` helper)
- Icons from `lucide-react`

---

## 9. Middleware

**File**: `middleware.ts`

Uses `next-intl/middleware` for locale-aware routing on public pages.

### Configuration

- **Locales**: `en`, `ro`, `es`, `de`, `fr` (defined in `i18n/config.ts`)
- **Default locale**: `en`
- **Locale prefix**: `as-needed` (no prefix for default locale)

### Route Matching

The middleware only applies to public/marketing routes. Dashboard and admin routes are excluded via a negative lookahead regex:

```
/((?!api|_next|_vercel|.*\\..*|dashboard|outlines|articles|images|social|analytics|
  knowledge|projects|settings|help|admin|content-calendar|keyword-research|billing|
  invite|bulk|agency|portal|competitor-analysis|site-audit|templates|reports|tags).*)
```

Any new dashboard route must be added to this exclusion list in `middleware.ts` to prevent next-intl from intercepting it.

---

## 10. E2E Tests

**Framework**: Playwright 1.58
**Config**: `playwright.config.ts`
**Test directory**: `e2e/tests/`
**Default target**: `https://a-stats-content.vercel.app` (production)

### Configuration

- Sequential execution (`fullyParallel: false`, `workers: 1`) -- tests share state
- Browser: Chromium (Desktop Chrome device)
- Auth: `global-setup.ts` logs in via the Vercel-hosted UI, saves session to `e2e/.auth/user.json`
- Retries: 1 in CI, 0 locally
- Artifacts: trace/screenshot/video retained on failure
- Timeouts: 15s action, 30s navigation

### Test Files (12 specs, 96 tests)

| File | Focus | Description |
|------|-------|-------------|
| `01-auth.spec.ts` | Authentication | Login, register, password flows, OAuth |
| `02-navigation.spec.ts` | Navigation | Sidebar links, breadcrumbs, mobile menu |
| `03-content-generation.spec.ts` | Content | Outline creation, article generation, image generation |
| `04-projects.spec.ts` | Projects | Project CRUD, switching, members, invitations |
| `05-settings.spec.ts` | Settings | Profile update, password change, billing, integrations |
| `06-analytics.spec.ts` | Analytics | GSC connection, keyword/page data, charts |
| `07-knowledge.spec.ts` | Knowledge | Upload, query, source management |
| `08-social.spec.ts` | Social | Account connection, post compose, scheduling |
| `09-bulk.spec.ts` | Bulk Content | Template management, job creation, progress |
| `10-agency.spec.ts` | Agency | Profile setup, client management, reports |
| `11-rbac.spec.ts` | RBAC | Role-based access control, tier gating |
| `12-api-health.spec.ts` | API Health | Backend endpoint availability checks |

### Running Tests

```bash
# Full suite
cd frontend && TEST_EMAIL=x TEST_PASSWORD=y npx playwright test

# Single file
TEST_EMAIL=x TEST_PASSWORD=y npx playwright test e2e/tests/12-api-health.spec.ts

# With UI
TEST_EMAIL=x TEST_PASSWORD=y npx playwright test --ui

# Headed mode
TEST_EMAIL=x TEST_PASSWORD=y npx playwright test --headed
```

**Status**: 95 pass, 1 skipped (logout test).
