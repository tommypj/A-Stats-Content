/**
 * User settings flows.
 */
import { test, expect } from "@playwright/test";
import { skipIfNoAuth } from "../helpers/auth-check";
skipIfNoAuth();

test.describe("Account settings", () => {
  test("settings overview page loads", async ({ page }) => {
    await page.goto("/settings");
    await expect(page.getByRole("heading", { name: /setting|account|profile/i })).toBeVisible();
  });

  test("profile fields are visible", async ({ page }) => {
    await page.goto("/settings");
    // Should show name + email fields
    await expect(
      page.getByLabel(/name/i).or(page.getByText(/full name|display name/i)).first()
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
    await page.goto("/en/settings/password");
    await expect(page).not.toHaveURL(/login/);
    await expect(page.getByLabel(/current password/i)).toBeVisible({ timeout: 10_000 });
    await expect(page.getByLabel(/new password/i)).toBeVisible();
  });

  test("password change form validates", async ({ page }) => {
    await page.goto("/en/settings/password");
    // Try submitting without filling anything
    await page.getByRole("button", { name: /save|change|update/i }).click();
    // Should show validation errors
    await expect(
      page.getByText(/required|enter|must|at least/i).first()
    ).toBeVisible({ timeout: 5_000 });
  });

  test("integrations page loads", async ({ page }) => {
    await page.goto("/en/settings/integrations");
    await expect(page).not.toHaveURL(/login/);
    await expect(
      page.getByText(/integration|connect|google|search console/i).first()
    ).toBeVisible({ timeout: 10_000 });
  });

  test("notifications settings page loads", async ({ page }) => {
    await page.goto("/en/settings/notifications");
    await expect(page).not.toHaveURL(/login/);
    await expect(
      page.getByText(/notification|email alert/i).first()
    ).toBeVisible({ timeout: 10_000 });
  });
});

test.describe("Logout", () => {
  test("logout clears session and redirects to login", async ({ page }) => {
    await page.goto("/dashboard");

    // Find and click logout (usually in user menu / avatar dropdown)
    const userMenu = page.getByRole("button", { name: /account|user|profile|menu/i })
      .or(page.locator("[data-testid='user-menu'], .user-menu, .avatar").first());

    if (await userMenu.isVisible({ timeout: 3_000 }).catch(() => false)) {
      await userMenu.click();
    }

    const logoutBtn = page.getByRole("button", { name: /log out|sign out|logout/i })
      .or(page.getByRole("menuitem", { name: /log out|sign out/i }));

    await logoutBtn.click();

    // Should redirect to login
    await expect(page).toHaveURL(/login/, { timeout: 10_000 });
  });
});
