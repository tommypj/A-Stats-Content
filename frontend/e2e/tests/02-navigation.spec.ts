/**
 * Navigation — authenticated tests.
 * Verifies every sidebar link loads without a 500/crash.
 */
import { test, expect } from "@playwright/test";

// storageState is inherited from playwright.config.ts (e2e/.auth/user.json)

const PAGES = [
  { name: "Dashboard",         url: "/dashboard" },
  { name: "Outlines",          url: "/outlines" },
  { name: "Articles",          url: "/articles" },
  { name: "Keyword Research",  url: "/keyword-research" },
  { name: "Images",            url: "/images" },
  { name: "Bulk Content",      url: "/bulk" },
  { name: "Analytics",         url: "/analytics" },
  { name: "Analytics Keywords",url: "/analytics/keywords" },
  { name: "Analytics Pages",   url: "/analytics/pages" },
  { name: "Analytics AEO",     url: "/analytics/aeo" },
  { name: "Analytics Revenue", url: "/analytics/revenue" },
  { name: "Analytics Health",  url: "/analytics/content-health" },
  { name: "Knowledge",         url: "/knowledge" },
  { name: "Knowledge Sources", url: "/knowledge/sources" },
  { name: "Knowledge Query",   url: "/knowledge/query" },
  { name: "Social",            url: "/social" },
  { name: "Social Compose",    url: "/social/compose" },
  { name: "Social Calendar",   url: "/social/calendar" },
  { name: "Social Accounts",   url: "/social/accounts" },
  { name: "Projects",          url: "/projects" },
  { name: "Agency",            url: "/agency" },
  { name: "Settings",          url: "/settings" },
];

test.describe("Sidebar navigation", () => {
  for (const { name, url } of PAGES) {
    test(`${name} page loads without error`, async ({ page }) => {
      await page.goto(url);

      // Should NOT redirect to login
      await expect(page).not.toHaveURL(/login/, { timeout: 15_000 });

      // Should NOT show a crash/error boundary
      await expect(
        page.getByText(/something went wrong|application error|unexpected error/i)
      ).not.toBeVisible();

      // Should render the main layout (sidebar)
      await expect(
        page.locator("nav, aside, [data-testid='sidebar']").first()
      ).toBeVisible({ timeout: 10_000 });
    });
  }
});

test.describe("Dashboard landing", () => {
  test("shows welcome/stats cards", async ({ page }) => {
    await page.goto("/dashboard");
    // At minimum the page should have some visible content
    await expect(page.locator("main, [role='main'], .dashboard").first()).toBeVisible({
      timeout: 15_000,
    });
  });

  test("project switcher is visible", async ({ page }) => {
    await page.goto("/dashboard");
    // Project selector / switcher should appear somewhere in the header or sidebar
    await expect(
      page.getByRole("button", { name: /project|workspace/i })
        .or(page.getByText(/project/i).first())
    ).toBeVisible({ timeout: 10_000 });
  });
});
