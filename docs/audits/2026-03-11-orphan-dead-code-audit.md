# Orphan Files & Dead Code Audit

**Date:** 2026-03-11
**Scope:** Full codebase (backend + frontend)
**Auditor:** Claude Opus 4.6 (comprehensive re-audit)

---

## Summary

| Category | Findings |
|----------|----------|
| Backend orphan files | 2 |
| Backend dead functions/classes | 5 |
| Backend unused interfaces | 6 |
| Frontend orphan components | 1 |
| Frontend unused hooks | 1 |
| Frontend unused lib exports | 8 |
| Frontend unused API methods | 7 |
| Frontend unused TypeScript types | 18 |
| Frontend unused UI barrel exports | 8 |

---

## Backend Findings

### 1. Orphan Files

#### B-01: `backend/services/background_tasks.py` (entire file)
- **Confidence:** HIGH
- **Details:** This file defines `process_document_task()` but is never imported by any other file in the codebase. The knowledge processing flow uses `knowledge_processor.py` directly via the routes.
- **Recommendation:** DELETE. The document processing is handled inline in the knowledge route. This was likely a planned abstraction that was never wired up.

#### B-02: `backend/core/interfaces/repositories.py` (entire file)
- **Confidence:** HIGH
- **Details:** Defines `UserRepository`, `OutlineRepository`, `ArticleRepository` abstract classes. These are re-exported from `core/interfaces/__init__.py` but never imported or inherited anywhere else in the codebase. The project uses SQLAlchemy models directly instead of the repository pattern.
- **Recommendation:** DELETE both `repositories.py` and remove the import from `core/interfaces/__init__.py`.

---

### 2. Dead Functions and Classes

#### B-03: `backend/core/interfaces/services.py` — unused interface classes
- **Line:** 9-139
- **Confidence:** HIGH
- **Details:** Defines 6 classes (`GenerationResult`, `ImageResult`, `AIService`, `ImageService`, `EmailService`, `PaymentService`) as abstract interfaces. None are inherited by the actual adapter implementations (e.g., `ReplicateImageService` does not extend `ImageService`; `ResendEmailService` does not extend `EmailService`). These are dead architectural stubs.
- **Recommendation:** DELETE. The adapters define their own concrete classes without these interfaces.

#### B-04: `backend/api/deps_project.py` — `get_content_filter()`
- **Line:** 34
- **Confidence:** HIGH
- **Details:** Function defined but never called from any file. It was likely superseded by `apply_content_filters()` or `verify_content_access()`.
- **Recommendation:** DELETE.

#### B-05: `backend/api/deps_project.py` — `apply_content_filters()`
- **Line:** 250
- **Confidence:** HIGH
- **Details:** Function defined but never called from any route or service. Likely superseded by `scoped_query()` from `api/utils.py`.
- **Recommendation:** DELETE.

#### B-06: `backend/api/deps_project.py` — `require_project_membership()`
- **Line:** 361
- **Confidence:** HIGH
- **Details:** Function defined but never used as a dependency or called directly. Other functions like `verify_project_membership()` are used instead.
- **Recommendation:** DELETE.

#### B-07: `backend/api/deps_project.py` — `require_project_role()`
- **Line:** 391
- **Confidence:** HIGH
- **Details:** Function defined but never used. `require_project_admin()` and `require_project_owner()` are used directly instead.
- **Recommendation:** DELETE.

---

### 3. Backend Observations (Not Actionable)

- All route files in `api/routes/` are properly registered in `api/routes/__init__.py`. No orphan routes.
- All SQLAlchemy model files in `infrastructure/database/models/` are imported in the models `__init__.py` and used.
- All schema files in `api/schemas/` are imported and used by routes.
- `_check_tier()` in `dependencies.py` is called internally by `require_tier()` — not dead.
- `ArticleRevisionResponse` in `content.py` schemas is a base class for `ArticleRevisionDetailResponse` — not dead.

---

## Frontend Findings

### 4. Orphan Components

#### F-01: `frontend/components/analytics/site-selector.tsx`
- **Confidence:** HIGH
- **Details:** This component (`SiteSelector`) is never imported by any page or other component. It was likely replaced by inline site selection in the analytics pages.
- **Recommendation:** DELETE.

---

### 5. Unused Hooks

#### F-02: `frontend/hooks/useProjectPermissions.ts`
- **Confidence:** HIGH
- **Details:** This hook is defined but never imported or used anywhere in the codebase. Project permission checks are done differently (via the `ProjectContext` or backend-side validation).
- **Recommendation:** DELETE.

---

### 6. Unused Library Exports

#### F-03: `frontend/lib/utils.ts` — `generateId()`
- **Line:** 64
- **Confidence:** HIGH
- **Details:** Exported but never imported anywhere. Code uses `crypto.randomUUID()` directly or server-generated IDs.
- **Recommendation:** DELETE.

#### F-04: `frontend/lib/utils.ts` — `sleep()`
- **Line:** 78
- **Confidence:** HIGH
- **Details:** Exported but never imported anywhere.
- **Recommendation:** DELETE.

#### F-05: `frontend/lib/auth.ts` — `useRedirectIfAuthenticated()`
- **Line:** 65
- **Confidence:** HIGH
- **Details:** Exported but never imported. Auth pages handle redirect logic inline.
- **Recommendation:** DELETE.

#### F-06: `frontend/lib/auth.ts` — `useRequireRole()`
- **Line:** 81
- **Confidence:** HIGH
- **Details:** Exported but never imported. Admin role checks are done in the admin layout directly.
- **Recommendation:** DELETE.

#### F-07: `frontend/lib/auth.ts` — `getAuthHeaders()`
- **Line:** 101
- **Confidence:** HIGH
- **Details:** Returns an empty object (comment says "cookies sent automatically"). Exported but never imported.
- **Recommendation:** DELETE.

#### F-08: `frontend/lib/chart-colors.ts` — `CHART_COLORS` (entire file)
- **Line:** 1-15
- **Confidence:** HIGH
- **Details:** The `CHART_COLORS` constant is never imported by any file. Chart components use hardcoded color values instead.
- **Recommendation:** DELETE the file, or migrate chart components to use it (preferred for consistency).

#### F-09: `frontend/lib/posthog.ts` — `trackEvent()` (entire file)
- **Line:** 1-14
- **Confidence:** HIGH
- **Details:** The `trackEvent()` function is exported but never called anywhere. PostHog pageviews work via the providers, but custom event tracking was never wired up.
- **Recommendation:** KEEP if custom events are planned. DELETE if not.

#### F-10: `frontend/lib/utils.ts` — `debounce()`
- **Line:** 85
- **Confidence:** MEDIUM
- **Details:** Only used in 1 file. Not truly dead but borderline.
- **Recommendation:** KEEP.

---

### 7. Unused API Methods in `frontend/lib/api.ts`

#### F-11: `api.articles.aeoOptimize()`
- **Line:** 594
- **Confidence:** HIGH
- **Details:** Never called from any page or component.
- **Recommendation:** DELETE.

#### F-12: `api.analytics.markAlertRead()`
- **Line:** 773
- **Confidence:** HIGH
- **Details:** Never called. `markAllAlertsRead()` and `resolveAlert()` are used instead.
- **Recommendation:** DELETE.

#### F-13: `api.tasks.getStatus()` (entire `tasks` namespace)
- **Line:** 1512-1517
- **Confidence:** HIGH
- **Details:** Never called. Task status polling was replaced by generation notification polling.
- **Recommendation:** DELETE.

#### F-14: `api.agency.deleteProfile()`
- **Line:** 1538
- **Confidence:** MEDIUM
- **Details:** Never called from any page. Could be intentionally withheld from UI.
- **Recommendation:** INVESTIGATE — if deleting agency profile is not a user action, DELETE.

#### F-15: `api.agency.createReportTemplate()`
- **Line:** 1584
- **Confidence:** MEDIUM
- **Details:** Never called from any page.
- **Recommendation:** INVESTIGATE — the report template CRUD may be planned for a future UI.

#### F-16: `api.agency.updateReportTemplate()`
- **Line:** 1590
- **Confidence:** MEDIUM
- **Details:** Never called from any page.
- **Recommendation:** Same as F-15.

#### F-17: `api.agency.deleteReportTemplate()`
- **Line:** 1596
- **Confidence:** MEDIUM
- **Details:** Never called from any page.
- **Recommendation:** Same as F-15.

---

### 8. Unused TypeScript Types/Interfaces in `frontend/lib/api.ts`

All of the following are exported but never imported by any page, component, or other file:

| # | Type Name | Confidence | Recommendation |
|---|-----------|------------|----------------|
| F-18 | `LinkSuggestionsResponse` | HIGH | DELETE |
| F-19 | `ContentHealthArticle` | HIGH | DELETE (separate `ContentHealthSummary` is used) |
| F-20 | `KeywordHistoryEntry` | HIGH | DELETE (only used inside `KeywordHistoryResponse`) |
| F-21 | `KeywordHistoryResponse` | MEDIUM | INVESTIGATE — check if `keywordHistory()` is used |
| F-22 | `WordPressMediaUploadInput` | HIGH | DELETE |
| F-23 | `WordPressMediaUploadResponse` | HIGH | DELETE |
| F-24 | `URLInspectionResponse` | HIGH | DELETE |
| F-25 | `ContentSuggestionsResponse` | MEDIUM | Used by `suggestContent()` which is called |
| F-26 | `DecayRecoverySuggestions` | MEDIUM | Used by `suggestRecovery()` which is called |
| F-27 | `DecayDetectionResponse` | MEDIUM | Used by `detectDecay()` which is called |
| F-28 | `AEOSuggestionsResponse` | HIGH | DELETE (used only by unused `aeoOptimize()`) |
| F-29 | `DeviceBreakdownItem` | MEDIUM | Used by `deviceBreakdown()` which is called |
| F-30 | `CountryBreakdownItem` | MEDIUM | Used by `countryBreakdown()` which is called |
| F-31 | `RevenueReport` | MEDIUM | Used by `generateRevenueReport()` which is called |
| F-32 | `TaskStatus` | HIGH | DELETE (used only by unused `tasks.getStatus()`) |
| F-33 | `AnalyticsQueryParams` | HIGH | DELETE (used inline instead) |
| F-34 | `ConnectSocialAccountInput` | HIGH | DELETE |
| F-35 | `SocialPostQueryParams` | MEDIUM | Used as param type in `social.posts()` but never imported standalone |
| F-36 | `AdminSystemAnalytics` | HIGH | DELETE |
| F-37 | `AdminGenerationQueryParams` | HIGH | DELETE (query params built inline) |
| F-38 | `AdminAlertQueryParams` | HIGH | DELETE (query params built inline) |
| F-39 | `AdminErrorTypeStat` | HIGH | DELETE |
| F-40 | `AdminErrorServiceStat` | HIGH | DELETE |
| F-41 | `AdminErrorTrend` | HIGH | DELETE |
| F-42 | `AdminAlertCount` | HIGH | DELETE |

**Note:** Types marked MEDIUM with "used by method X which is called" are not truly orphaned -- they're used as return types for API methods that are called. They just aren't imported standalone by consumer code (which is normal for return types that are inferred). These should be KEPT.

The HIGH-confidence items (F-18, F-19, F-22, F-23, F-24, F-28, F-32, F-33, F-34, F-36, F-37, F-38, F-39, F-40, F-41, F-42) are truly unused and can be deleted.

---

### 9. Unused UI Barrel Exports (`frontend/components/ui/index.ts`)

The following are re-exported from `index.ts` but never imported by any consumer:

| Export | Confidence | Recommendation |
|--------|------------|----------------|
| `buttonVariants` | MEDIUM | KEEP — useful for extending Button styles |
| `ButtonProps` | MEDIUM | KEEP — useful for typing custom components |
| `InputProps` | MEDIUM | KEEP — same |
| `TextareaProps` | MEDIUM | KEEP — same |
| `CardFooter` | HIGH | DELETE from barrel (or use in a component) |
| `CardDescription` | HIGH | DELETE from barrel (or use in a component) |
| `BadgeProps` | MEDIUM | KEEP — useful for typing |
| `ProgressProps` | MEDIUM | KEEP — useful for typing |

**Note:** These are type/variant re-exports. While not currently imported, they're standard library-style exports that are useful for consumers. Recommend keeping variant/type exports but reviewing `CardFooter` and `CardDescription`.

---

### 10. Duplicate PostHog Providers (Observation)

Two separate PostHog provider implementations exist:
1. `frontend/components/PostHogProvider.tsx` — used in `(dashboard)/layout.tsx`
2. `frontend/components/providers/posthog-provider.tsx` — used in root `providers.tsx`

Both are in active use but create redundant PostHog initialization. The root provider wraps ALL pages (including public ones), while the dashboard provider wraps only authenticated pages.

- **Confidence:** MEDIUM
- **Recommendation:** INVESTIGATE — consolidate into one provider if the root-level one is sufficient. If dashboard needs special PostHog config, document why both exist.

---

## High-Priority Deletions (Safe to Remove)

| # | File/Item | Type |
|---|-----------|------|
| B-01 | `backend/services/background_tasks.py` | Orphan file |
| B-02 | `backend/core/interfaces/repositories.py` | Orphan file |
| B-03 | `backend/core/interfaces/services.py` (all 6 classes) | Dead interfaces |
| B-04 | `backend/api/deps_project.py` — `get_content_filter()` | Dead function |
| B-05 | `backend/api/deps_project.py` — `apply_content_filters()` | Dead function |
| B-06 | `backend/api/deps_project.py` — `require_project_membership()` | Dead function |
| B-07 | `backend/api/deps_project.py` — `require_project_role()` | Dead function |
| F-01 | `frontend/components/analytics/site-selector.tsx` | Orphan component |
| F-02 | `frontend/hooks/useProjectPermissions.ts` | Unused hook |
| F-03 | `frontend/lib/utils.ts` — `generateId()` | Unused export |
| F-04 | `frontend/lib/utils.ts` — `sleep()` | Unused export |
| F-05 | `frontend/lib/auth.ts` — `useRedirectIfAuthenticated()` | Unused export |
| F-06 | `frontend/lib/auth.ts` — `useRequireRole()` | Unused export |
| F-07 | `frontend/lib/auth.ts` — `getAuthHeaders()` | Unused export |
| F-08 | `frontend/lib/chart-colors.ts` | Unused file |
| F-11 | `frontend/lib/api.ts` — `api.articles.aeoOptimize()` | Unused API method |
| F-12 | `frontend/lib/api.ts` — `api.analytics.markAlertRead()` | Unused API method |
| F-13 | `frontend/lib/api.ts` — `api.tasks` namespace | Unused API namespace |

**Estimated dead code:** ~500 lines across backend, ~200 lines across frontend.
