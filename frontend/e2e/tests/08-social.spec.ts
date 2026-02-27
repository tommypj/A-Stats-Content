/**
 * Social media section flows.
 */
import { test, expect } from "@playwright/test";
import { skipIfNoAuth } from "../helpers/auth-check";
skipIfNoAuth();

test.describe("Social media", () => {
  test("social dashboard loads", async ({ page }) => {
    await page.goto("/social");
    await expect(page).not.toHaveURL(/login/);
    await expect(
      page.getByRole("heading", { name: /social/i })
    ).toBeVisible({ timeout: 10_000 });
  });

  test("compose page loads", async ({ page }) => {
    await page.goto("/social/compose");
    await expect(page).not.toHaveURL(/login/);
    await expect(
      page.getByText(/compose|create post|write/i).first()
    ).toBeVisible({ timeout: 10_000 });
  });

  test("accounts page loads and shows connect options", async ({ page }) => {
    await page.goto("/social/accounts");
    await expect(page).not.toHaveURL(/login/);
    // Should show social platform options
    await expect(
      page.getByText(/twitter|linkedin|facebook|instagram|connect/i).first()
    ).toBeVisible({ timeout: 10_000 });
  });

  test("calendar page loads", async ({ page }) => {
    await page.goto("/social/calendar");
    await expect(page).not.toHaveURL(/login/);
    await expect(
      page.getByText(/calendar|schedule|upcoming/i).first()
    ).toBeVisible({ timeout: 10_000 });
  });

  test("history page loads", async ({ page }) => {
    await page.goto("/social/history");
    await expect(page).not.toHaveURL(/login/);
    await expect(
      page.getByText(/history|published|sent/i).first()
    ).toBeVisible({ timeout: 10_000 });
  });
});
