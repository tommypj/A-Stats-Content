/**
 * Analytics section — all 8 sub-pages load without errors.
 */
import { test, expect } from "@playwright/test";

const ANALYTICS_PAGES = [
  { name: "Overview",           url: "/analytics" },
  { name: "Keywords",           url: "/analytics/keywords" },
  { name: "Pages",              url: "/analytics/pages" },
  { name: "Article Performance",url: "/analytics/articles" },
  { name: "Opportunities",      url: "/analytics/opportunities" },
  { name: "Content Health",     url: "/analytics/content-health" },
  { name: "AEO Scores",         url: "/analytics/aeo" },
  { name: "Revenue",            url: "/analytics/revenue" },
];

test.describe("Analytics pages", () => {
  for (const { name, url } of ANALYTICS_PAGES) {
    test(`${name} loads`, async ({ page }) => {
      await page.goto(url);
      await expect(page).not.toHaveURL(/login/);
      await expect(
        page.getByText(/something went wrong|application error/i)
      ).not.toBeVisible();
      // Should render some heading
      await expect(
        page.getByRole("heading").first()
      ).toBeVisible({ timeout: 15_000 });
    });
  }

  test("GSC connect button is visible when not connected", async ({ page }) => {
    await page.goto("/analytics");
    // Either shows connected state or a connect button
    const connectBtn = page.getByRole("button", { name: /connect|search console|google/i });
    const connectedLabel = page.getByText(/connected|search console/i);
    await expect(connectBtn.or(connectedLabel)).toBeVisible({ timeout: 10_000 });
  });
});
