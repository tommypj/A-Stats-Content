/**
 * Navigation — authenticated tests.
 * Verifies every sidebar link loads without a crash.
 */
import { test, expect } from "@playwright/test";
import { skipIfNoAuth } from "../helpers/auth-check";
skipIfNoAuth();

const PAGES = [
  { name: "Dashboard",          url: "/dashboard" },
  { name: "Outlines",           url: "/outlines" },
  { name: "Articles",           url: "/articles" },
  { name: "Keyword Research",   url: "/keyword-research" },
  { name: "Images",             url: "/images" },
  { name: "Bulk Content",       url: "/bulk" },
  { name: "Analytics",          url: "/analytics" },
  { name: "Analytics Keywords", url: "/analytics/keywords" },
  { name: "Analytics Pages",    url: "/analytics/pages" },
  { name: "Analytics AEO",      url: "/analytics/aeo" },
  { name: "Analytics Revenue",  url: "/analytics/revenue" },
  { name: "Analytics Health",   url: "/analytics/content-health" },
  { name: "Knowledge",          url: "/knowledge" },
  { name: "Knowledge Sources",  url: "/knowledge/sources" },
  { name: "Knowledge Query",    url: "/knowledge/query" },
  { name: "Social",             url: "/social" },
  { name: "Social Compose",     url: "/social/compose" },
  { name: "Social Calendar",    url: "/social/calendar" },
  { name: "Social Accounts",    url: "/social/accounts" },
  { name: "Projects",           url: "/projects" },
  { name: "Agency",             url: "/agency" },
  { name: "Settings",           url: "/settings" },
];

test.describe("Sidebar navigation", () => {
  for (const { name, url } of PAGES) {
    test(`${name} page loads without error`, async ({ page }) => {
      await page.goto(url);

      // Must NOT redirect to login
      await expect(page).not.toHaveURL(/login/, { timeout: 15_000 });

      // Must NOT show app crash
      await expect(
        page.getByText(/something went wrong|application error|unexpected error/i)
      ).not.toBeVisible();

      // Must have visible content (at minimum a heading or nav)
      await expect(
        page.getByRole("heading").first()
          .or(page.locator("nav, aside").first())
          .or(page.locator("main").first())
      ).toBeVisible({ timeout: 15_000 });
    });
  }
});

test.describe("Dashboard landing", () => {
  test("renders main content area", async ({ page }) => {
    await page.goto("/dashboard");
    await expect(page.locator("main, [role='main']").first()).toBeVisible({
      timeout: 15_000,
    });
  });

  test("shows project context somewhere on page", async ({ page }) => {
    await page.goto("/dashboard");
    // Project name or switcher should appear
    await expect(
      page.getByText(/project/i).first()
    ).toBeVisible({ timeout: 10_000 });
  });
});
