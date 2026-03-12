# Frontend Audit — 2026-03-11

Auditor: Claude Opus 4.6 (automated)
Scope: `frontend/app/`, `frontend/components/`, `frontend/lib/`

---

## 1. Broken Links and Missing Pages

### Critical

- **`frontend/app/(dashboard)/content-calendar/page.tsx:254`** — `href="/outlines/new"` points to a page that does not exist. There is no `frontend/app/(dashboard)/outlines/new/page.tsx`. Only `/outlines` and `/outlines/[id]` exist. The "new outline" flow is handled via the articles/new page or inline on the outlines page.

- **`frontend/app/(admin)/admin/content/outlines/page.tsx:133`** — `href="/admin/content"` points to a non-existent page. There is no `frontend/app/(admin)/admin/content/page.tsx`. The admin content section has only `/admin/content/articles`, `/admin/content/images`, and `/admin/content/outlines`.

- **`frontend/app/(admin)/admin/content/images/page.tsx:126`** — Same broken link: `href="/admin/content"`.

- **`frontend/app/(admin)/admin/content/articles/page.tsx:177`** — Same broken link: `href="/admin/content"`.

### Warning

- **`frontend/app/(dashboard)/help/page.tsx:169`** — `href="/en/docs"` hardcodes the `en` locale prefix. This will break for non-English locales. Should use a locale-aware path or `/docs`.

- **`frontend/components/landing/PublicFooter.tsx:50-52`** — Three resources links all point to `/en/docs` with hardcoded locale:
  - Line 50: `href: "/en/docs"` (Documentation)
  - Line 51: `href: "/en/docs/getting-started/quick-start"` (Help Center)
  - Line 52: `href: "/en/docs"` (API Reference)

- **`frontend/components/landing/PublicFooter.tsx:53`** — Uses `key={i}` (index-based key) for the Resources list. Since two items share the same `href` (`/en/docs`), using `href` as key would also collide — but index-based keys prevent React from reordering correctly if the list ever changes.

---

## 2. Component Issues

### Warning

- **`frontend/app/(dashboard)/images/page.tsx:85-89`** — `useEffect` cleanup references `unsuppress` from `useGenerationTracker()` hook but the dependency array is empty `[]`. The `unsuppress` function comes from a Zustand store and is stable, so this is safe in practice, but technically violates exhaustive-deps.

- **`frontend/app/(dashboard)/images/page.tsx:880-886`** — Close button for the regenerate image modal has no `aria-label` or accessible name — it only contains an `<X>` icon with no text.

- **`frontend/app/(dashboard)/content-calendar/page.tsx:170-175`** — Close button for the SchedulePanel modal has no `aria-label` — only an `<X>` icon.

- **`frontend/app/(dashboard)/content-calendar/page.tsx:343-348`** — Close button for the DayDetailPanel modal has no `aria-label` — only an `<X>` icon.

- **`frontend/app/(dashboard)/layout.tsx:500-505`** — Mobile sidebar close button has no `aria-label` — only an `<X>` icon.

- **`frontend/app/(dashboard)/settings/page.tsx:742`** — `profile` is cast `as UserProfile | null` to pass to `ProfileSection`. The query returns `UserProfile` directly, so this is unnecessary and could mask type errors if the API response shape changes.

- **`frontend/components/ui/tier-gate.tsx:126`** — `(user?.subscription_tier || "free") as Tier` uses a type assertion. If the backend returns an unexpected tier string, this would silently pass an invalid value.

### Info

- **`frontend/app/(dashboard)/articles/page.tsx:121`** — `// eslint-disable-next-line react-hooks/exhaustive-deps` on mount-only useEffect. This is intentional (read URL params once) and documented, so it is acceptable.

- **`frontend/components/blog/BlogPostClient.tsx:243`** — `.catch(() => {})` on the related posts fetch silently swallows errors. This is intentional (non-critical fetch) but could hide debugging issues in development.

---

## 3. Type Safety

### Warning

- **`frontend/e2e/tests/11-rbac.spec.ts:20,24`** — Uses `any` type for localStorage parsing. Only instance of `any` in the codebase (E2E test file, not production code).

- **`frontend/app/(dashboard)/agency/reports/[id]/page.tsx:141`** — `report?.report_data as Record<string, unknown>` assertion on data that could be any shape from the API. The subsequent field access (lines 142-147) does guard with `typeof` checks, which is good practice.

- **`frontend/app/portal/[token]/page.tsx:159`** — `summary.recent_articles as Array<{ title: string; published_at?: string }>` type assertion on data from API without runtime validation.

- **`frontend/app/(dashboard)/agency/branding/page.tsx:186`** — `payload as Parameters<typeof api.agency.createProfile>[0]` assertion bypasses type checking on the payload construction.

- **`frontend/app/(dashboard)/images/generate/page.tsx:277`** — `as GeneratedImage` cast that could fail if the spread shape does not match.

### Info

- Type safety is generally excellent across the codebase. No `any` types in production code. Type assertions are used sparingly and most have appropriate runtime guards.

---

## 4. Accessibility

### Warning — Missing `aria-label` on Icon-Only Buttons

The following icon-only buttons lack `aria-label`, `title`, or `sr-only` text:

- **`frontend/app/(dashboard)/images/page.tsx:880`** — Regenerate modal close button (X icon only)
- **`frontend/app/(dashboard)/content-calendar/page.tsx:170`** — SchedulePanel close button (X icon only)
- **`frontend/app/(dashboard)/content-calendar/page.tsx:343`** — DayDetailPanel close button (X icon only)
- **`frontend/app/(dashboard)/layout.tsx:500`** — Mobile sidebar close button (X icon only)

Note: Many other icon-only buttons DO have proper `aria-label` or `title` attributes (e.g., competitor analysis back buttons, calendar navigation, dashboard dismiss button).

### Warning — Clickable Divs Without Keyboard Support

The following `<div>` elements have `onClick` handlers but no `role="button"`, `tabIndex`, or `onKeyDown`:

- **`frontend/components/project/project-switcher.tsx:70`** — Overlay dismiss div
- **`frontend/app/(dashboard)/content-calendar/page.tsx:157`** — Modal backdrop
- **`frontend/app/(dashboard)/content-calendar/page.tsx:331`** — Modal backdrop
- **`frontend/app/(dashboard)/images/page.tsx:633`** — Menu dismiss overlay
- **`frontend/app/(dashboard)/images/page.tsx:769`** — Lightbox backdrop
- **`frontend/app/(dashboard)/images/page.tsx:873`** — Regen modal backdrop
- **`frontend/app/(dashboard)/outlines/page.tsx:444`** — Menu dismiss overlay
- **`frontend/app/(dashboard)/articles/page.tsx:686`** — Menu dismiss overlay
- **`frontend/app/(dashboard)/articles/[id]/page.tsx:1393`** — Export menu dismiss overlay

These are all overlay/backdrop dismiss elements. They are not blocking since they supplement existing close buttons, but screen readers cannot interact with them.

### Info — Missing `htmlFor` on Labels

- **194 total `<label>` elements** across 45 files
- **118 have `htmlFor`** attributes (61%)
- **~76 labels missing `htmlFor`** across 42 files (known issue — M-01 in deferred items)
- This is an incremental improvement item as noted in the project memory.

### Info — Skip Link

- **`frontend/app/(dashboard)/layout.tsx:461-466`** — Has a proper "Skip to main content" skip link. Good accessibility practice.

### Info — Breadcrumb

- **`frontend/components/ui/breadcrumb.tsx:92`** — Has proper `aria-label="Breadcrumb"` on the nav element.

---

## 5. Design System Violations

### Warning — Portal Page Uses Raw Tailwind Colors

**`frontend/app/portal/[token]/page.tsx`** — The entire portal page (white-label client-facing report) uses raw Tailwind color classes instead of design tokens. This is across ~40 lines:
- `bg-white` (lines 52, 75, 209, 373, 386)
- `bg-gray-50` (lines 167, 186, 205)
- `text-gray-900` (lines 61, 80, 189, 231, 326)
- `text-gray-500` (lines 60, 175, 192, 325, 375, 388)
- `text-gray-400` (lines 228, 238, 277, 348, 363, 394)
- `text-gray-800` (lines 239, 344)
- `text-gray-300` (line 374)
- `border-gray-200` (lines 52, 75, 209, 373, 386)
- `border-gray-100` (lines 77, 338)
- `divide-gray-100` (line 338)

**Severity note:** This page is intentionally standalone (white-label portal for agency clients), so it may deliberately use neutral grays instead of the warm cream/sage dashboard palette. However, it should be documented as a design decision.

### Warning — Portal Layout

**`frontend/app/portal/layout.tsx:3`** — `bg-gray-50` instead of `bg-surface-secondary`.

### Warning — Invite Page

**`frontend/app/invite/[token]/page.tsx:29`** — Uses `bg-gray-100 text-gray-800` for the viewer role badge instead of design tokens.

### Info — Landing Page and Auth

The landing page (`LandingPageClient.tsx`), public nav, auth pages, and legal layout use `bg-white` extensively. This is appropriate for public-facing pages that are outside the dashboard design system.

### Info — Admin Emails Page

**`frontend/app/(admin)/admin/emails/page.tsx`** — Uses `bg-white` for email template builder cards (lines 155, 166, 196, 209, 226, 242, 263, 276, 292). Admin pages are separate from the dashboard design system, so this is acceptable.

---

## 6. Error Handling

### Info — Consistent Error Pattern

Error handling is consistently implemented using `toast.error(parseApiError(err).message)` across all dashboard pages. No empty catch blocks were found. The codebase follows a disciplined pattern.

### Info — Loading States

All major pages use either:
- React Query's `isLoading` for data-driven skeleton states
- Dedicated `loading.tsx` files for route-level loading (articles, outlines, images, dashboard)
- Inline skeleton placeholders for sub-components

### Info — Empty States

Pages consistently handle empty data:
- Articles page shows "No articles yet" with CTA links
- Images page shows empty state with "Generate Images" CTA
- Knowledge page shows overview cards linking to sources
- Calendar shows "No completed articles available to schedule"

### Warning — Silent Catch in Layout Auth

**`frontend/app/(dashboard)/layout.tsx:433-434`** — `api.auth.me()` catch silently redirects to login without logging the error. While this is appropriate for expired sessions, a network error would also trigger a login redirect, which could confuse users with temporary connectivity issues.

---

## 7. Security

### Info — XSS Protection

- **`frontend/app/(dashboard)/articles/[id]/page.tsx:1655`** — `dangerouslySetInnerHTML` is properly sanitized via `DOMPurify.sanitize()` with explicit allowlists for tags and attributes, and explicit forbid lists for `script`, `iframe`, `object`, `embed`, `form`, `input`, and event handlers.

- **`frontend/components/blog/BlogPostClient.tsx:255`** — Blog content is sanitized via `DOMPurify.sanitize()`.

- JSON-LD scripts use `JSON.stringify()` which inherently escapes HTML.

---

## Summary

| Severity | Count |
|----------|-------|
| Critical | 4 |
| Warning | 18 |
| Info | 12 |

### Critical findings (4):
1. Broken link: `/outlines/new` does not exist (content-calendar)
2. Broken link: `/admin/content` does not exist (3 admin content sub-pages)

### Top recommendations:
1. **Fix broken links**: Create the missing pages or update the links to valid routes
2. **Add `aria-label` to icon-only buttons**: 4 close/dismiss buttons need accessible names
3. **Standardize portal page**: Document the design system exemption for the white-label portal, or migrate to design tokens
4. **Fix hardcoded locale in `/en/docs` links**: Use locale-aware routing (3 occurrences)
