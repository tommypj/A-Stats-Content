#!/bin/bash
# Overnight Full Code Review — run before bed, read results in the morning
# Usage: bash scripts/overnight-review.sh
# Results: review-results/ directory with markdown reports

set -e

RESULTS_DIR="review-results"
mkdir -p "$RESULTS_DIR"
TIMESTAMP=$(date +%Y-%m-%d)

echo "=== A-Stats Overnight Review — $TIMESTAMP ==="
echo "Starting at $(date)"
echo ""

# ─── Pass 1: Backend Security & API ──────────────────────────────────────────
echo "[1/6] Backend Security & API Review..."
claude -p "$(cat <<'PROMPT'
You are reviewing the A-Stats-Online codebase (FastAPI + SQLAlchemy async + PostgreSQL).

Do a THOROUGH security and API review of the entire backend. Check every file in backend/api/routes/, backend/services/, backend/adapters/, and backend/infrastructure/.

Review for:
- **Auth bypass**: endpoints missing get_current_user, broken ownership checks, privilege escalation
- **Injection**: SQL injection via raw queries, command injection, path traversal
- **Rate limiting**: write endpoints missing @limiter.limit, missing request: Request param
- **Data leaks**: responses exposing passwords, tokens, internal IDs, or other users' data
- **Error handling**: unhandled exceptions, 500s leaking stack traces
- **Input validation**: missing/weak Pydantic constraints, unbounded queries (no LIMIT)
- **Race conditions**: non-atomic read-modify-write, missing row locks on billing/credits
- **CORS/CSRF**: misconfigured origins, missing CSRF on state-changing ops
- **Dependency issues**: outdated packages with known CVEs

For each finding, report:
- Severity (CRITICAL/HIGH/MEDIUM/LOW)
- File and line number
- What's wrong
- How to fix it

Write the full report to review-results/01-backend-security.md
PROMPT
)" --allowedTools Read,Grep,Glob,Write,Bash 2>&1 | tail -5

# ─── Pass 2: Frontend Security & Code Quality ────────────────────────────────
echo "[2/6] Frontend Security & Code Quality..."
claude -p "$(cat <<'PROMPT'
You are reviewing the A-Stats-Online frontend (Next.js 14, TypeScript, Tailwind).

Do a THOROUGH review of ALL files in frontend/app/, frontend/components/, frontend/lib/, frontend/stores/, frontend/contexts/, frontend/hooks/.

Review for:
- **XSS**: dangerouslySetInnerHTML without DOMPurify, unsanitized user content in JSX
- **Auth**: pages missing useRequireAuth(), unprotected routes, token handling issues
- **State bugs**: stale closures, missing useCallback/useMemo deps, race conditions in fetches
- **Error handling**: missing try/catch on API calls, missing parseApiError, silent failures
- **TypeScript**: any types, missing null checks, type assertions hiding bugs
- **API client**: mismatched types between api.ts interfaces and actual backend responses
- **Memory leaks**: missing cleanup in useEffect, uncleared intervals/timeouts
- **Accessibility**: missing aria-labels on icon buttons, missing form labels, keyboard nav

For each finding, report severity, file, line, what's wrong, and how to fix.

Write the full report to review-results/02-frontend-code-quality.md
PROMPT
)" --allowedTools Read,Grep,Glob,Write,Bash 2>&1 | tail -5

# ─── Pass 3: UI/UX Review ────────────────────────────────────────────────────
echo "[3/6] UI/UX Review..."
claude -p "$(cat <<'PROMPT'
You are reviewing the A-Stats-Online frontend UI/UX (Next.js 14, Tailwind CSS).

Read EVERY page component in frontend/app/(dashboard)/ and frontend/app/(auth)/ and all shared components in frontend/components/.

Review for:
- **Consistency**: inconsistent spacing, font sizes, border radii, color usage across pages
- **Loading states**: pages that show nothing while fetching (no skeleton/spinner)
- **Empty states**: pages with no content that show a blank white page instead of a helpful message
- **Error states**: what happens when API calls fail — is it just a console.log or a visible toast?
- **Responsive design**: components that break on mobile (fixed widths, overflow issues, hidden content)
- **Navigation**: dead links, missing breadcrumbs, pages not in sidebar nav
- **Forms**: missing validation messages, no disabled state on submit buttons during loading
- **Modals/Dialogs**: can they be closed with Escape? Do they trap focus? Backdrop click to close?
- **Dark mode**: if using CSS variables, check for hardcoded colors that won't adapt
- **Pagination**: pages with lists that have no pagination or load everything at once
- **Design system drift**: components not using the shared Button/Card/Input components, one-off styling

For each finding, report the page/component, what's wrong, and a specific fix.

Write the full report to review-results/03-ui-ux-review.md
PROMPT
)" --allowedTools Read,Grep,Glob,Write,Bash 2>&1 | tail -5

# ─── Pass 4: CSS & Tailwind Review ───────────────────────────────────────────
echo "[4/6] CSS & Tailwind Review..."
claude -p "$(cat <<'PROMPT'
You are reviewing the A-Stats-Online CSS and Tailwind usage.

Check frontend/app/globals.css, tailwind.config.ts, and scan ALL .tsx files for Tailwind patterns.

Review for:
- **Unused CSS**: custom CSS classes in globals.css that are never referenced
- **Tailwind anti-patterns**: using @apply excessively, inline styles instead of Tailwind, !important usage
- **Custom theme**: are design tokens (colors, fonts, spacing) defined in tailwind.config.ts and used consistently, or are there hardcoded hex values scattered in components?
- **Responsive breakpoints**: classes missing sm:/md:/lg: variants where needed
- **Animation**: janky or missing transitions on interactive elements (hover, focus, open/close)
- **Typography**: inconsistent heading sizes, line heights, font weights across pages
- **Spacing system**: mixing px values with Tailwind spacing scale
- **Z-index chaos**: arbitrary z-index values that could conflict (modals, dropdowns, toasts)
- **Bundle size**: importing entire icon libraries instead of individual icons

Write the full report to review-results/04-css-tailwind.md
PROMPT
)" --allowedTools Read,Grep,Glob,Write,Bash 2>&1 | tail -5

# ─── Pass 5: Database & Migrations ───────────────────────────────────────────
echo "[5/6] Database & Migrations Review..."
claude -p "$(cat <<'PROMPT'
You are reviewing the A-Stats-Online database layer (SQLAlchemy async, Alembic, PostgreSQL).

Check ALL files in backend/infrastructure/database/models/ and backend/infrastructure/database/migrations/versions/.

Review for:
- **Migration chain**: verify down_revision chain is unbroken from 001 to 052 (009 is a placeholder, skip it)
- **Migration idempotency**: every migration MUST use DO $$ BEGIN IF NOT EXISTS ... END $$ pattern — flag any that don't
- **FK types**: any FK column referencing users.id that uses VARCHAR(36) instead of UUID — this breaks on Railway
- **Missing indexes**: columns used in WHERE clauses (user_id, project_id, status, deleted_at) without indexes
- **N+1 queries**: routes that load a list then query related data in a loop instead of joining/batching
- **Connection management**: missing async with for sessions, sessions not closed on error
- **Soft delete leaks**: queries that forget to filter by deleted_at IS NULL
- **Model/migration drift**: model defines a column that no migration creates, or vice versa
- **Transaction safety**: operations that should be atomic but aren't wrapped in a transaction

Write the full report to review-results/05-database-migrations.md
PROMPT
)" --allowedTools Read,Grep,Glob,Write,Bash 2>&1 | tail -5

# ─── Pass 6: Architecture & Integration ───────────────────────────────────────
echo "[6/6] Architecture & Integration Review..."
claude -p "$(cat <<'PROMPT'
You are reviewing the A-Stats-Online full-stack architecture.

Review the overall system integration between frontend (Next.js) and backend (FastAPI).

Check for:
- **Schema drift**: compare Pydantic response models in backend/api/schemas/ with TypeScript interfaces in frontend/lib/api.ts — find any field name mismatches, missing fields, or type mismatches
- **Route registration**: every router file in backend/api/routes/ must be imported and included in __init__.py — find any orphaned route files
- **Middleware gaps**: every dashboard route must be in the next-intl exclusion regex in frontend/middleware.ts — find any missing
- **Breadcrumb gaps**: every dashboard page slug should have an entry in breadcrumb.tsx PATH_LABELS — find any missing
- **Nav gaps**: dashboard pages that exist but aren't in the sidebar navigation in layout.tsx
- **Dead code**: exported functions/types in api.ts that are never imported anywhere, unused components
- **Environment variables**: env vars referenced in code but not in .env.example files
- **Import cycles**: circular imports in Python or TypeScript that could cause runtime issues
- **Deployment risks**: anything that would break on Railway/Vercel deploy (localhost URLs, hardcoded paths, missing build steps)

Write the full report to review-results/06-architecture-integration.md
PROMPT
)" --allowedTools Read,Grep,Glob,Write,Bash 2>&1 | tail -5

# ─── Generate Dashboard ──────────────────────────────────────────────────────
echo ""
echo "Generating dashboard..."
bash scripts/generate-review-dashboard.sh

echo ""
echo "=== All passes complete at $(date) ==="
echo ""
echo "Results in $RESULTS_DIR/:"
ls -la "$RESULTS_DIR/"
echo ""
echo "Open dashboard: start review-results/dashboard.html"
