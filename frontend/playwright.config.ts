import { defineConfig, devices } from "@playwright/test";
import * as path from "path";

const BASE_URL = process.env.BASE_URL ?? "https://a-stats-content.vercel.app";
export const API_URL =
  process.env.API_URL ??
  "https://a-stats-content-production.up.railway.app";

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: [["html", { open: "on-failure" }], ["list"]],

  use: {
    baseURL: BASE_URL,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
    actionTimeout: 15_000,
    navigationTimeout: 30_000,
  },

  // Runs once before all tests — creates auth state
  globalSetup: "./e2e/global-setup.ts",
  globalTeardown: "./e2e/global-teardown.ts",

  projects: [
    {
      name: "chromium",
      use: {
        ...devices["Desktop Chrome"],
        storageState: path.join(__dirname, "e2e/.auth/user.json"),
      },
      // Auth tests override storageState to {} themselves
    },
  ],
});
