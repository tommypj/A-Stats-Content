/**
 * Knowledge vault flows.
 */
import { test, expect } from "@playwright/test";

test.describe("Knowledge vault", () => {
  test("knowledge overview loads", async ({ page }) => {
    await page.goto("/knowledge");
    await expect(page).not.toHaveURL(/login/);
    await expect(
      page.getByRole("heading", { name: /knowledge/i })
    ).toBeVisible({ timeout: 10_000 });
  });

  test("knowledge sources list loads", async ({ page }) => {
    await page.goto("/knowledge/sources");
    await expect(page).not.toHaveURL(/login/);
    await expect(
      page.getByText(/source|document|upload/i).first()
    ).toBeVisible({ timeout: 10_000 });
  });

  test("can see add source option", async ({ page }) => {
    await page.goto("/knowledge/sources");
    await expect(
      page.getByRole("button", { name: /add|upload|new source/i })
        .or(page.getByText(/add source|upload/i))
    ).toBeVisible({ timeout: 10_000 });
  });

  test("knowledge query page loads", async ({ page }) => {
    await page.goto("/knowledge/query");
    await expect(page).not.toHaveURL(/login/);
    await expect(
      page.getByPlaceholder(/ask|query|question/i)
        .or(page.getByRole("textbox").first())
    ).toBeVisible({ timeout: 10_000 });
  });
});
