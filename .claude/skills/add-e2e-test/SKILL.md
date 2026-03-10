---
name: add-e2e-test
description: Generate a Playwright E2E test following project conventions (global auth setup, API fixtures, selector patterns). Use when user says "add test", "write e2e", "test this feature", "add playwright test", or "e2e for".
disable-model-invocation: true
---

# Add Playwright E2E Test

Generate E2E tests that match the existing test suite conventions.

## Project Test Setup

- **Test dir:** `frontend/e2e/tests/`
- **Config:** `frontend/playwright.config.ts`
- **Auth:** `frontend/e2e/global-setup.ts` logs in via Vercel UI and stores auth state
- **Run:** `cd frontend && TEST_EMAIL=x TEST_PASSWORD=y npx playwright test`
- **Existing:** 12 spec files, 96 tests (numbered 01-12)

## Step 1: Determine Test File

Check existing test files to pick the next number:
```bash
ls frontend/e2e/tests/*.spec.ts | sort
```

Name: `<NN>-<feature-slug>.spec.ts` (e.g., `13-templates.spec.ts`)

## Step 2: Write Test File

### For UI Tests (authenticated)

```typescript
/**
 * <Feature> E2E tests — verifies <what it tests>.
 */
import { test, expect, type Page } from "@playwright/test";

const BASE_URL = process.env.BASE_URL ?? "https://a-stats-online.vercel.app";

test.describe("<Feature Name>", () => {
  test.beforeEach(async ({ page }) => {
    // Auth state is pre-loaded via global-setup.ts
    await page.goto(`${BASE_URL}/<route>`);
    // Wait for page to be ready
    await page.waitForLoadState("networkidle");
  });

  test("displays <feature> page", async ({ page }) => {
    await expect(page.getByRole("heading", { name: /<Feature>/i })).toBeVisible();
  });

  test("can create a new <item>", async ({ page }) => {
    await page.getByRole("button", { name: /new|create|add/i }).click();
    // ... fill form, submit, verify ...
    await expect(page.getByText(/created|success/i)).toBeVisible();
  });

  test("shows error on invalid input", async ({ page }) => {
    // Test error handling with toast
    // Toast errors use: toast.error(parseApiError(err).message)
    await expect(page.locator("[data-sonner-toast]")).toBeVisible();
  });
});
```

### For API-Only Tests (no browser session)

```typescript
/**
 * <Feature> API tests — verifies endpoints directly.
 */
import { test, expect } from "@playwright/test";

const API_URL =
  process.env.API_URL ??
  "https://a-stats-content-production.up.railway.app";

// No browser session needed
test.use({ storageState: { cookies: [], origins: [] } });

test.describe("<Feature> API", () => {
  test("GET /api/v1/<resource> returns expected shape", async ({ request }) => {
    const res = await request.get(`${API_URL}/api/v1/<resource>`);
    expect(res.status()).toBe(200);
    const body = await res.json();
    expect(body).toHaveProperty("items");
    expect(body).toHaveProperty("total");
  });

  test("POST /api/v1/<resource> without auth returns 401", async ({ request }) => {
    const res = await request.post(`${API_URL}/api/v1/<resource>`, {
      data: {},
    });
    expect(res.status()).toBe(401);
  });
});
```

## Conventions

### Selectors (in priority order)
1. `page.getByRole()` — preferred (accessible)
2. `page.getByText()` — for visible text
3. `page.getByTestId()` — if no semantic alternative
4. `page.locator("[data-*]")` — last resort

### Assertions
- Use `expect(locator).toBeVisible()` not `toBeInTheDocument()`
- Use `expect(response.status()).toBe(N)` for API tests
- Use regex for text matching: `{ name: /pattern/i }`

### Special Patterns
- **Settings page:** Tab-based SPA — navigate tabs with `page.getByRole("tab", { name: /billing/i }).click()`, NOT by URL
- **Toasts:** Sonner toasts use `[data-sonner-toast]` selector
- **Loading states:** Wait with `page.waitForLoadState("networkidle")` or `page.waitForSelector()`
- **Modals:** Dialog component uses `[role="dialog"]`

### What NOT to do
- Don't test logout (skipped — known flaky)
- Don't hardcode auth tokens — use the global setup storage state
- Don't use `page.waitForTimeout()` — use proper wait conditions
- Don't test external services (LemonSqueezy, Google OAuth) — mock or skip

## Step 3: Verify

```bash
cd frontend && npx playwright test e2e/tests/<NN>-<feature>.spec.ts --headed
```

If tests need a running backend, remind the user to set `API_URL` and `BASE_URL` env vars.
