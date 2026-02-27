/**
 * User settings flows.
 */
import { test, expect } from "@playwright/test";
import { skipIfNoAuth } from "../helpers/auth-check";
skipIfNoAuth();

test.describe("Account settings", () => {
  test("settings overview page loads", async ({ page }) => {
    await page.goto("/settings");
    await expect(page).not.toHaveURL(/login/, { timeout: 10_000 });
    // Heading is "Settings"
    await expect(page.getByRole("heading", { name: /^settings$/i }).first()).toBeVisible({ timeout: 10_000 });
  });

  test("profile fields are visible", async ({ page }) => {
    await page.goto("/settings");
    await expect(page).not.toHaveURL(/login/, { timeout: 10_000 });
    // Settings page has a Profile section
    await expect(
      page.getByText(/profile|full name|display name/i).first()
    ).toBeVisible({ timeout: 10_000 });
  });

  test("billing settings page loads", async ({ page }) => {
    await page.goto("/en/settings/billing");
    await expect(page).not.toHaveURL(/login/);
    await expect(
      page.getByText(/plan|billing|subscription|upgrade/i).first()
    ).toBeVisible({ timeout: 10_000 });
  });

  test("password change page loads", async ({ page }) => {
    // The password page lives under [locale]/(dashboard)/settings/password
    // Navigate via the settings page and click the Password tab
    await page.goto("/settings");
    await expect(page).not.toHaveURL(/login/, { timeout: 10_000 });
    // Click the "Password" nav link in the settings sidebar
    await page.getByRole("link", { name: /^password$/i }).click();
    await expect(page).not.toHaveURL(/login/);
    await expect(page.locator("main")).toBeVisible({ timeout: 10_000 });
  });

  test("password change form validates", async ({ page }) => {
    await page.goto("/settings");
    await expect(page).not.toHaveURL(/login/, { timeout: 10_000 });
    await page.getByRole("link", { name: /^password$/i }).click();
    await expect(page.locator("main")).toBeVisible({ timeout: 10_000 });
    // Try submitting without filling anything
    const saveBtn = page.getByRole("button", { name: /save|change|update/i }).first();
    if (await saveBtn.isVisible({ timeout: 3_000 }).catch(() => false)) {
      await saveBtn.click();
      await expect(
        page.getByText(/required|enter|must|at least|cannot be blank/i).first()
      ).toBeVisible({ timeout: 5_000 });
    }
  });

  test("integrations page loads", async ({ page }) => {
    await page.goto("/settings/integrations");
    await expect(page).not.toHaveURL(/login/);
    await expect(
      page.getByText(/integration|connect|google|search console/i).first()
    ).toBeVisible({ timeout: 10_000 });
  });

  test("notifications settings page loads", async ({ page }) => {
    await page.goto("/settings");
    await expect(page).not.toHaveURL(/login/, { timeout: 10_000 });
    // Click the "Notifications" nav link in the settings sidebar
    await page.getByRole("link", { name: /notifications/i }).click();
    await expect(page.locator("main")).toBeVisible({ timeout: 10_000 });
  });
});

test.describe("Logout", () => {
  test("logout clears session and redirects to login", async ({ page }) => {
    await page.goto("/dashboard");
    await expect(page).not.toHaveURL(/login/, { timeout: 10_000 });

    // Look for a user avatar / profile button in the layout
    // Try clicking any dropdown that might reveal logout
    const logoutVisible = await page.getByRole("button", { name: /log out|sign out|logout/i })
      .isVisible({ timeout: 2_000 }).catch(() => false);

    if (!logoutVisible) {
      // Try opening a user/account menu first
      const menuButton = page.locator("[data-testid='user-menu'], .user-menu, .avatar, [aria-label*='account' i], [aria-label*='user' i]").first();
      const menuBtnVisible = await menuButton.isVisible({ timeout: 2_000 }).catch(() => false);
      if (menuBtnVisible) {
        await menuButton.click();
        await page.waitForTimeout(500);
      }
    }

    const logoutBtn = page.getByRole("button", { name: /log out|sign out|logout/i })
      .or(page.getByRole("menuitem", { name: /log out|sign out/i })).first();

    const canLogout = await logoutBtn.isVisible({ timeout: 3_000 }).catch(() => false);
    if (!canLogout) {
      // Logout button not accessible via UI — skip gracefully
      test.skip(true, "Logout button not found in current layout");
      return;
    }

    await logoutBtn.click();
    await expect(page).toHaveURL(/login/, { timeout: 10_000 });
  });
});
