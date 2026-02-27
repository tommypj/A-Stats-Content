import { defineConfig, devices } from "@playwright/test";
import * as path from "path";

/**
 * E2E test configuration.
 *
 * Targets the live Vercel frontend + Railway backend.
 * Override via env vars when running locally:
 *   BASE_URL=http://localhost:3000 npx playwright test
 */

const BASE_URL = process.env.BASE_URL ?? "https://a-stats-content.vercel.app";
const API_URL =
  process.env.API_URL ??
  "https://a-stats-content-production.up.railway.app";

export { BASE_URL, API_URL };

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false, // run serially against live app to avoid rate-limit conflicts
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: [["html", { open: "on-failure" }], ["list"]],

  // Shared settings for all tests
  use: {
    baseURL: BASE_URL,
    // Persist cookies across requests (needed for HttpOnly session cookies)
    extraHTTPHeaders: { Accept: "application/json" },
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
    actionTimeout: 15_000,
    navigationTimeout: 30_000,
  },

  // Saved auth state path (set by global-setup, reused in tests)
  // Each test file requiring auth imports the storageState fixture
  projects: [
    // ── Global setup (runs once before all tests) ──────────────────────────
    {
      name: "setup",
      testMatch: "**/global-setup.ts",
    },

    // ── Main test suite (requires setup) ──────────────────────────────────
    {
      name: "chromium",
      use: {
        ...devices["Desktop Chrome"],
        storageState: path.join(__dirname, "e2e/.auth/user.json"),
      },
      dependencies: ["setup"],
      testIgnore: "**/global-setup.ts",
    },
  ],

  // Env vars exposed to tests
  globalSetup: undefined, // handled via project dependency above
  globalTeardown: "./e2e/global-teardown.ts",
});
