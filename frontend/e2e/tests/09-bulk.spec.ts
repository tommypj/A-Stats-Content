/**
 * Bulk content generation flows.
 */
import { test, expect } from "@playwright/test";
import { skipIfNoAuth } from "../helpers/auth-check";
skipIfNoAuth();

test.describe("Bulk content", () => {
  test("bulk dashboard loads", async ({ page }) => {
    await page.goto("/bulk");
    await expect(page).not.toHaveURL(/login/);
    await expect(
      page.getByRole("heading", { name: /bulk/i })
    ).toBeVisible({ timeout: 10_000 });
  });

  test("bulk templates page loads", async ({ page }) => {
    await page.goto("/bulk/templates");
    await expect(page).not.toHaveURL(/login/);
    await expect(
      page.getByText(/template|create|upload/i).first()
    ).toBeVisible({ timeout: 10_000 });
  });

  test("bulk job creation form is accessible", async ({ page }) => {
    await page.goto("/bulk");
    // Either shows existing jobs or an option to create
    await expect(
      page.getByRole("button", { name: /new job|create|import|upload csv/i })
        .or(page.getByText(/no jobs|get started|create your first/i))
    ).toBeVisible({ timeout: 10_000 });
  });
});
