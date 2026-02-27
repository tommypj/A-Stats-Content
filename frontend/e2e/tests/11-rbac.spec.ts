/**
 * Role-based access control tests.
 *
 * Note: if the test user is an admin/super_admin, admin pages will
 * be accessible — which is CORRECT behaviour. These tests verify
 * the pages respond appropriately for the test account's role.
 */
import { test, expect } from "@playwright/test";
import { skipIfNoAuth } from "../helpers/auth-check";
import * as fs from "fs";
import * as path from "path";
skipIfNoAuth();

const AUTH_STATE = path.join(__dirname, "../.auth/user.json");

function getTestUserRole(): string | null {
  try {
    const state = JSON.parse(fs.readFileSync(AUTH_STATE, "utf8"));
    // Zustand persists to auth-storage in localStorage
    const origin = state.origins?.find((o: any) =>
      o.origin?.includes("vercel.app") || o.origin?.includes("localhost")
    );
    if (!origin) return null;
    const authStorage = origin.localStorage?.find((e: any) => e.name === "auth-storage");
    if (!authStorage) return null;
    const parsed = JSON.parse(authStorage.value);
    return parsed?.state?.user?.role ?? null;
  } catch {
    return null;
  }
}

test.describe("Admin access control", () => {
  test("admin panel access matches user role", async ({ page }) => {
    const role = getTestUserRole();
    console.log(`[rbac] Test user role: ${role ?? "unknown"}`);

    await page.goto("/admin");
    await page.waitForTimeout(3_000); // let redirects settle

    const url = page.url();

    if (role === "admin" || role === "super_admin") {
      // Admin users SHOULD be on the admin page
      expect(url).toMatch(/\/admin/);
      console.log("[rbac] ✓ Admin user has admin access");
    } else {
      // Regular users SHOULD be redirected away
      expect(url).not.toMatch(/\/admin\/?$/);
      console.log("[rbac] ✓ Regular user redirected from admin");
    }
  });

  test("admin dashboard renders without errors when accessible", async ({ page }) => {
    const role = getTestUserRole();
    await page.goto("/admin");
    await page.waitForTimeout(2_000);

    if (role === "admin" || role === "super_admin") {
      await expect(
        page.getByText(/something went wrong|application error/i)
      ).not.toBeVisible();
      // Should show admin content
      await expect(page.getByRole("heading").first()).toBeVisible({ timeout: 10_000 });
    } else {
      // Regular user — expect redirect to dashboard or login
      await expect(page).toHaveURL(/dashboard|login/, { timeout: 5_000 });
    }
  });
});
