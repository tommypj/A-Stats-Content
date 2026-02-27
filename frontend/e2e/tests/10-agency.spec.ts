/**
 * Agency / white-label flows.
 */
import { test, expect } from "@playwright/test";

test.describe("Agency section", () => {
  test("agency dashboard loads", async ({ page }) => {
    await page.goto("/agency");
    await expect(page).not.toHaveURL(/login/);
    await expect(
      page.getByRole("heading", { name: /agency/i })
    ).toBeVisible({ timeout: 10_000 });
  });

  test("clients page loads", async ({ page }) => {
    await page.goto("/agency/clients");
    await expect(page).not.toHaveURL(/login/);
    await expect(
      page.getByText(/client|workspace|portal/i).first()
    ).toBeVisible({ timeout: 10_000 });
  });

  test("reports page loads", async ({ page }) => {
    await page.goto("/agency/reports");
    await expect(page).not.toHaveURL(/login/);
    await expect(
      page.getByText(/report|analytics|export/i).first()
    ).toBeVisible({ timeout: 10_000 });
  });

  test("branding page loads", async ({ page }) => {
    await page.goto("/agency/branding");
    await expect(page).not.toHaveURL(/login/);
    await expect(
      page.getByText(/brand|logo|color|white.label/i).first()
    ).toBeVisible({ timeout: 10_000 });
  });
});
