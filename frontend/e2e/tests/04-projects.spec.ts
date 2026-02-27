/**
 * Project management flows.
 */
import { test, expect } from "@playwright/test";
import { skipIfNoAuth } from "../helpers/auth-check";
skipIfNoAuth();

test.describe("Projects list", () => {
  test("projects page renders", async ({ page }) => {
    await page.goto("/projects");
    await expect(page.getByRole("heading", { name: /project/i }).first()).toBeVisible({ timeout: 10_000 });
  });

  test("can navigate to new project form", async ({ page }) => {
    await page.goto("/projects/new");
    await expect(page).not.toHaveURL(/login/);
    await expect(
      page.getByLabel(/project name|name/i).first()
        .or(page.getByPlaceholder(/project name|name/i).first())
    ).toBeVisible({ timeout: 10_000 });
  });

  test("can create a new project", async ({ page }) => {
    await page.goto("/projects/new");

    // Fill name field — try label first, then placeholder
    const nameInput = page.getByLabel(/^name$/i).first()
      .or(page.getByLabel(/project name/i).first())
      .or(page.getByPlaceholder(/project name|name/i).first());

    await nameInput.first().fill("Playwright Test Project");

    // Fill domain if required
    const domainInput = page.getByLabel(/domain|website/i).first()
      .or(page.getByPlaceholder(/domain|website|url/i).first());
    if (await domainInput.isVisible({ timeout: 2_000 }).catch(() => false)) {
      await domainInput.fill("playwright-test.io");
    }

    await page.getByRole("button", { name: /create|save|submit/i }).click();

    // Should redirect to projects list or new project settings
    await expect(
      page.getByText(/playwright test project/i)
        .or(page.getByRole("heading", { name: /project/i }).first())
    ).toBeVisible({ timeout: 15_000 });
  });
});

test.describe("Brand voice", () => {
  test("brand voice page loads", async ({ page }) => {
    await page.goto("/projects/brand-voice");
    await expect(page).not.toHaveURL(/login/);
    await expect(
      page.getByText(/brand voice|writing style|tone/i).first()
    ).toBeVisible({ timeout: 10_000 });
  });
});
