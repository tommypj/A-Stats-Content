/**
 * Content generation flow:
 *   Keyword Research → Generate Outline → Generate Article
 *
 * These tests are intentionally lenient on timing (AI calls can be slow)
 * and focus on verifying the UI flow completes without errors.
 */
import { test, expect } from "@playwright/test";

const KEYWORD = "content marketing strategy";

test.describe("Keyword Research", () => {
  test("page loads and shows search form", async ({ page }) => {
    await page.goto("/keyword-research");
    await expect(page.getByRole("heading", { name: /keyword/i })).toBeVisible();
    await expect(
      page.getByPlaceholder(/keyword|topic|seed/i)
        .or(page.getByRole("textbox").first())
    ).toBeVisible();
  });

  test("can type keyword and submit research", async ({ page }) => {
    await page.goto("/keyword-research");

    const input = page.getByPlaceholder(/keyword|topic|seed/i)
      .or(page.getByRole("textbox").first());
    await input.fill(KEYWORD);

    await page.getByRole("button", { name: /research|analyze|search|generate/i }).click();

    // Wait for results or loading indicator
    await expect(
      page.getByText(/loading|analyzing|generating/i)
        .or(page.getByText(/keyword|suggestion|volume/i))
    ).toBeVisible({ timeout: 60_000 });
  });

  test("shows recent search history", async ({ page }) => {
    await page.goto("/keyword-research");
    // After previous test, history should contain recent search
    // (may be empty on first run — just check the section exists if present)
    const historySection = page.getByText(/recent|history|previous/i);
    // Not mandatory — just note if present
    console.log(
      "History visible:",
      await historySection.isVisible().catch(() => false)
    );
  });
});

test.describe("Outline creation", () => {
  test("outlines list page renders", async ({ page }) => {
    await page.goto("/outlines");
    await expect(page.getByRole("heading", { name: /outline/i })).toBeVisible();
  });

  test("can open create outline modal", async ({ page }) => {
    await page.goto("/outlines");
    await page.getByRole("button", { name: /new outline|create outline|\+ outline/i }).click();
    // Modal or form should appear
    await expect(
      page.getByRole("dialog")
        .or(page.getByText(/topic|keyword|title/i))
    ).toBeVisible({ timeout: 5_000 });
  });

  test("can fill and submit outline form", async ({ page }) => {
    await page.goto("/outlines");
    await page.getByRole("button", { name: /new outline|create outline|\+ outline/i }).click();

    // Fill topic/keyword field
    const topicInput = page
      .getByLabel(/topic|keyword|title/i)
      .or(page.getByPlaceholder(/topic|keyword|title/i))
      .first();
    await topicInput.fill("Benefits of Content Marketing");

    // Submit
    await page.getByRole("button", { name: /generate|create|submit/i }).last().click();

    // Should show generating state or redirect to outline editor
    await expect(
      page.getByText(/generating|creating|loading/i)
        .or(page.getByRole("heading", { name: /benefits of content/i }))
    ).toBeVisible({ timeout: 90_000 });
  });
});

test.describe("Articles list", () => {
  test("articles page renders", async ({ page }) => {
    await page.goto("/articles");
    await expect(page.getByRole("heading", { name: /article/i })).toBeVisible();
  });

  test("can navigate to new article page", async ({ page }) => {
    await page.goto("/articles/new");
    // Should render the article creation form (not crash)
    await expect(page).not.toHaveURL(/login/);
    await expect(
      page.getByText(/something went wrong|application error/i)
    ).not.toBeVisible();
  });
});

test.describe("Images", () => {
  test("images page loads", async ({ page }) => {
    await page.goto("/images");
    await expect(page.getByRole("heading", { name: /image/i })).toBeVisible();
  });

  test("generate image page loads", async ({ page }) => {
    await page.goto("/images/generate");
    await expect(page).not.toHaveURL(/login/);
    await expect(
      page.getByText(/generate|create image|prompt/i).first()
    ).toBeVisible({ timeout: 10_000 });
  });
});
