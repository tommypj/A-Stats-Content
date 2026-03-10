---
name: review-codebase
description: Comprehensive codebase review — bugs, security, code quality, conventions, performance. Dispatches parallel agents across 6 review passes. Use when user says "review codebase", "full review", "code review", "audit code", "review everything", or "check my code".
disable-model-invocation: true
---

# Full Codebase Review

Systematic 6-pass review of the codebase dispatching parallel agents. Each pass focuses on a different category with specific checklists.

## Scope Selection

Ask the user:
> **What scope should I review?**
> 1. **Changed files only** — files modified since last commit (fastest)
> 2. **Branch diff** — all changes on current branch vs `master` (recommended after feature work)
> 3. **Full codebase** — every file, line by line (thorough, takes longest)
> 4. **Specific directory** — e.g., just `backend/api/` or `frontend/app/`

### Get the file list based on scope

```bash
# Option 1: Changed files (uncommitted)
git diff --name-only HEAD && git ls-files --others --exclude-standard

# Option 2: Branch diff
git diff --name-only master...HEAD

# Option 3: Full codebase
find backend/api backend/services backend/adapters backend/schemas backend/infrastructure/database/models frontend/app frontend/components frontend/lib -type f \( -name "*.py" -o -name "*.ts" -o -name "*.tsx" \) | sort

# Option 4: Specific directory
find <dir> -type f \( -name "*.py" -o -name "*.ts" -o -name "*.tsx" \) | sort
```

## Dispatch 6 Parallel Review Agents

Launch ALL 6 agents in parallel using the Agent tool. Each agent gets the file list and its specific checklist. Use `subagent_type: "feature-dev:code-reviewer"` for all agents.

**IMPORTANT:** Send all 6 Agent tool calls in a SINGLE message to maximize parallelism.

---

### Agent 1: Bug Hunter

**Prompt template:**
```
Review these files for bugs, logic errors, and edge cases. For each file, check line by line:

FILES: <file_list>

CHECKLIST:
- [ ] Null/undefined access without guards
- [ ] Off-by-one errors in loops, pagination, slicing
- [ ] Async/await: missing await, unhandled promise rejections, race conditions
- [ ] Type mismatches: string vs number, UUID vs string comparisons
- [ ] Error handling: caught exceptions that swallow errors silently
- [ ] State mutations: React state updated without spreading, SQLAlchemy detached instances
- [ ] Boundary conditions: empty arrays, zero values, negative numbers, MAX_INT
- [ ] Dead code paths: unreachable branches, impossible conditions
- [ ] Resource leaks: unclosed DB sessions, file handles, HTTP connections
- [ ] Date/time: timezone-naive comparisons, UTC vs local assumptions

REPORT FORMAT:
For each finding:
- File path and line number
- Category (logic-error / edge-case / race-condition / resource-leak / dead-code)
- Severity (critical / high / medium / low)
- Description of the bug
- Suggested fix (code snippet)

Only report issues with HIGH confidence (>80%). Do not report style issues or hypothetical problems.
```

---

### Agent 2: Security Reviewer

**Prompt template:**
```
Review these files for security vulnerabilities. For each file, check line by line:

FILES: <file_list>

CHECKLIST:
- [ ] SQL injection: raw SQL with string interpolation or f-strings
- [ ] Command injection: subprocess/os.system with user input
- [ ] XSS: user content rendered as raw HTML without sanitization
- [ ] Auth bypass: endpoints missing get_current_user / get_current_admin_user dependency
- [ ] Broken access control: missing user_id ownership checks after fetching resources
- [ ] IDOR: sequential/guessable IDs without ownership validation
- [ ] Sensitive data exposure: passwords, tokens, API keys in responses or logs
- [ ] SSRF: user-controlled URLs passed to httpx/aiohttp/requests without validation
- [ ] Mass assignment: accepting arbitrary fields in Pydantic schemas that map to sensitive model fields
- [ ] Rate limiting: sensitive endpoints (login, register, password reset, webhooks) without slowapi
- [ ] Webhook security: missing signature verification, processing before validation
- [ ] JWT issues: weak algorithms, missing expiry, token reuse after logout
- [ ] CORS: overly permissive origins
- [ ] File upload: path traversal, unrestricted file types, no size limits
- [ ] Cryptography: weak hashing, hardcoded secrets, insufficient randomness

PROJECT-SPECIFIC:
- LemonSqueezy webhook must verify X-Signature via HMAC-SHA256 BEFORE parsing body
- Refund guard: webhook handler must check subscription_status == "refunded" before any updates
- Admin endpoints must use get_current_admin_user, not get_current_user
- slowapi: first param must be named "request: Request" (not http_request)

REPORT FORMAT:
For each finding:
- File path and line number
- OWASP category (A01-A10)
- Severity (critical / high / medium / low)
- Description with attack scenario
- Suggested fix (code snippet)

Only report confirmed vulnerabilities, not theoretical risks.
```

---

### Agent 3: Code Quality & Dead Code

**Prompt template:**
```
Review these files for code quality issues, duplication, and dead code. For each file, check line by line:

FILES: <file_list>

CHECKLIST:
- [ ] Dead code: unused imports, unreachable branches, commented-out code blocks
- [ ] Unused variables/functions: defined but never referenced
- [ ] Code duplication: identical or near-identical logic in multiple places (>5 lines)
- [ ] Function complexity: functions >50 lines or >4 levels of nesting
- [ ] Magic numbers/strings: hardcoded values that should be constants
- [ ] Inconsistent error handling: some paths use try/catch, others don't
- [ ] God objects: classes with >10 methods or >300 lines
- [ ] Overly broad try/catch: catching Exception/BaseException without specificity
- [ ] Mutable default arguments in Python functions
- [ ] Console.log / print statements left in production code
- [ ] TODO/FIXME/HACK comments that indicate incomplete work
- [ ] Unused API response fields: types defined but never accessed in frontend

REPORT FORMAT:
For each finding:
- File path and line number
- Category (dead-code / duplication / complexity / inconsistency)
- Severity (high / medium / low)
- Description
- Suggested fix or refactoring

Skip trivial findings (single unused import, one-off console.log). Focus on patterns that indicate real maintenance burden.
```

---

### Agent 4: Convention Enforcement

**Prompt template:**
```
Review these files against A-Stats-Online project conventions. For each file, check line by line:

FILES: <file_list>

FRONTEND CONVENTIONS:
- [ ] Design tokens: NEVER use bg-white, bg-gray-*, text-gray-* in dashboard pages
  - Must use: bg-surface, bg-surface-secondary, bg-surface-tertiary
  - Must use: text-text-primary, text-text-secondary, text-text-muted
  - Must use: border-surface-tertiary for borders
  - Must use: rounded-2xl + shadow-soft for cards
- [ ] Error handling: toast.error(parseApiError(err).message) — not toast.error("string literal")
- [ ] API calls: use apiRequest from lib/api.ts — not raw axios/fetch
- [ ] Button variants: primary/secondary/ghost/outline/destructive/link — no custom styles
- [ ] New dashboard routes: must be in middleware.ts exclusion regex, PATH_LABELS, and sidebar nav
- [ ] Loading states: use proper loading skeletons, not just "Loading..."
- [ ] React Query: use useQuery/useMutation, not useEffect+useState for API calls

BACKEND CONVENTIONS:
- [ ] Alembic migrations: ALL DDL wrapped in DO $$ BEGIN IF NOT EXISTS ... END $$;
- [ ] FK columns: must use UUID(as_uuid=True), never VARCHAR/String
- [ ] Pydantic v2: unannotated class variables need ClassVar[Set[str]]
- [ ] Auth: all user-facing endpoints use Depends(get_current_user)
- [ ] Admin: all admin endpoints use Depends(get_current_admin_user)
- [ ] Logging: use logger.info/error/warning, not print()
- [ ] Settings: use get_settings() dependency, not direct env var access
- [ ] Project roles: valid values are owner/admin/editor/viewer (not "member")

REPORT FORMAT:
For each finding:
- File path and line number
- Convention violated (with the specific rule)
- Severity (high / medium / low)
- Current code snippet
- Fixed code snippet

Only report actual convention violations, not style preferences.
```

---

### Agent 5: Performance Reviewer

**Prompt template:**
```
Review these files for performance issues. For each file, check line by line:

FILES: <file_list>

BACKEND CHECKLIST:
- [ ] N+1 queries: loading related objects in a loop instead of eager loading / joinedload
- [ ] Missing database indexes: columns used in WHERE/ORDER BY/JOIN without index
- [ ] Unbounded queries: SELECT without LIMIT on potentially large tables
- [ ] Synchronous I/O in async context: blocking calls without run_in_executor
- [ ] Missing pagination: list endpoints that return all results
- [ ] Redundant queries: same data fetched multiple times in one request
- [ ] Large response payloads: returning full objects when only IDs/summaries needed
- [ ] Missing caching: expensive computations repeated on every request
- [ ] Connection pool exhaustion: long-running transactions holding connections

FRONTEND CHECKLIST:
- [ ] Unnecessary re-renders: missing React.memo, useMemo, useCallback where needed
- [ ] Bundle size: large imports that could be dynamic (e.g., import entire library for one function)
- [ ] Missing React Query staleTime/cacheTime: refetching on every mount
- [ ] Image optimization: unoptimized images, missing next/image usage
- [ ] Layout shifts: content loading without proper dimensions/skeletons
- [ ] Excessive API calls: fetching data that's already in cache or parent component
- [ ] Missing pagination in UI: rendering 100+ items without virtualization
- [ ] Heavy computations in render: filtering/sorting in JSX instead of useMemo

REPORT FORMAT:
For each finding:
- File path and line number
- Category (n-plus-1 / missing-index / re-render / bundle-size / unbounded-query)
- Impact estimate (high / medium / low)
- Description with expected performance impact
- Suggested fix (code snippet)

Only report issues with measurable performance impact. Skip micro-optimizations.
```

---

### Agent 6: Completeness & Integration

**Prompt template:**
```
Review these files for completeness and integration issues — things that are partially implemented, disconnected, or inconsistent across the stack.

FILES: <file_list>

CHECKLIST:
- [ ] Frontend types vs backend schemas: mismatched field names, missing fields, wrong types
- [ ] API client methods vs backend routes: endpoints that exist in backend but not in frontend api.ts (or vice versa)
- [ ] Missing error handling: API calls without .catch or try/catch
- [ ] Incomplete CRUD: create exists but no update/delete (or vice versa)
- [ ] Orphaned components: React components defined but never imported/used
- [ ] Missing loading/error states: pages that fetch data but don't handle loading or error
- [ ] Inconsistent response shapes: some endpoints return {items, total, page} others return bare arrays
- [ ] Missing form validation: forms that submit without client-side validation (zod/react-hook-form)
- [ ] Broken navigation: links/hrefs pointing to routes that don't exist
- [ ] Missing breadcrumb entries: dashboard routes not in PATH_LABELS
- [ ] Missing middleware entries: dashboard routes not in middleware.ts exclusion
- [ ] Stale feature flags / env vars: referenced in code but never set
- [ ] Test coverage gaps: features with no corresponding E2E tests

REPORT FORMAT:
For each finding:
- File path and line number (both frontend and backend if cross-stack)
- Category (type-mismatch / missing-endpoint / incomplete-crud / orphaned / integration-gap)
- Severity (high / medium / low)
- Description
- Files that need to be updated together to fix

Focus on cross-stack inconsistencies and incomplete features. Skip single-file issues covered by other reviewers.
```

---

## Collecting Results

After all 6 agents complete, compile a unified report:

### Unified Report Format

```markdown
# Codebase Review Report — <date>

## Summary
- **Scope:** <what was reviewed>
- **Files reviewed:** <count>
- **Total findings:** <count>
  - Critical: <N>
  - High: <N>
  - Medium: <N>
  - Low: <N>

## Critical & High Findings (fix before shipping)

### 1. [CRITICAL] <title> — <file>:<line>
**Category:** <bug/security/performance/convention/integration>
**Description:** ...
**Fix:** ...

### 2. [HIGH] <title> — <file>:<line>
...

## Medium Findings (fix soon)
...

## Low Findings (tech debt)
...

## Duplicate/Overlap Removal
<note any findings that appeared in multiple passes — deduplicate>

## Recommendations
<top 3-5 actionable recommendations based on patterns in findings>
```

### Deduplication Rules

Findings from multiple agents that point to the same file+line should be merged:
- Keep the highest severity
- Combine descriptions from each perspective
- List all relevant categories

### Present to User

After compiling the report:
1. Show the summary counts first
2. Ask if they want the full report or just critical+high
3. Offer to fix issues — start with critical, then high
4. Save report to `docs/reviews/YYYY-MM-DD-review.md` if user wants

## Tips for Large Codebases

If the file list is very large (>100 files), split the work differently:
- Agent 1-3: Review backend files only
- Agent 4-6: Review frontend files only
- Then swap: agents review the other half

This prevents context window overflow while maintaining thoroughness.
