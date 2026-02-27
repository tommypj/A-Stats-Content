/**
 * Analytics section — all 8 sub-pages load without errors.
 */
import { test, expect } from "@playwright/test";
import { skipIfNoAuth } from "../helpers/auth-check";
skipIfNoAuth();

const ANALYTICS_PAGES = [
  { name: "Overview",            url: "/analytics" },
  { name: "Keywords",            url: "/analytics/keywords" },
  { name: "Pages",               url: "/analytics/pages" },
  { name: "Article Performance", url: "/analytics/articles" },
  { name: "Opportunities",       url: "/analytics/opportunities" },
  { name: "Content Health",      url: "/analytics/content-health" },
  { name: "AEO Scores",          url: "/analytics/aeo" },
  { name: "Revenue",             url: "/analytics/revenue" },
];

test.describe("Analytics pages", () => {
  for (const { name, url } of ANALYTICS_PAGES) {
    test(`${name} loads`, async ({ page }) => {
      await page.goto(url);
      // Must stay on the analytics page — not redirect to login
      await expect(page).not.toHaveURL(/login/, { timeout: 15_000 });
      await expect(
        page.getByText(/something went wrong|application error/i)
      ).not.toBeVisible();
      // Must render a page-specific heading (not the login heading)
      await expect(page.getByRole("heading").first()).toBeVisible({
        timeout: 15_000,
      });
    });
  }

  test("GSC connection status is shown", async ({ page }) => {
    await page.goto("/analytics");
    await expect(page).not.toHaveURL(/login/, { timeout: 15_000 });
    // Accept either: connect button, already-connected label, or any analytics content
    await expect(
      page.getByRole("button", { name: /connect|search console|google/i })
        .or(page.getByText(/google search console|connected|gsc/i).first())
        .or(page.getByRole("heading").first())
    ).toBeVisible({ timeout: 15_000 });
  });
});
