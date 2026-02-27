/**
 * Role-based access control tests.
 * Verifies that regular users cannot access admin routes.
 */
import { test, expect } from "@playwright/test";

test.describe("RBAC — regular user", () => {
  test("cannot access /admin (redirects away)", async ({ page }) => {
    await page.goto("/admin");
    // Should redirect to /dashboard or /login — never stay on /admin
    await expect(page).not.toHaveURL(/^https?:\/\/[^/]+\/admin\/?$/, {
      timeout: 10_000,
    });
  });

  test("cannot access /admin/users (redirects away)", async ({ page }) => {
    await page.goto("/admin/users");
    await expect(page).not.toHaveURL(/\/admin\/users/, { timeout: 10_000 });
  });

  test("cannot access /admin/analytics (redirects away)", async ({ page }) => {
    await page.goto("/admin/analytics");
    await expect(page).not.toHaveURL(/\/admin\/analytics/, { timeout: 10_000 });
  });
});
