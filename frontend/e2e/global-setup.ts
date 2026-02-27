/**
 * Global setup — runs once before the entire test suite.
 *
 * Logs in through the VERCEL FRONTEND (not the API directly) so that:
 *   - HttpOnly cookies are set for the Railway domain
 *   - Zustand auth-storage is populated in localStorage for the Vercel domain
 *   - Both are saved in storageState and reused across all tests
 *
 * Usage:
 *   TEST_EMAIL=you@example.com TEST_PASSWORD=pass npx playwright test
 */
import { chromium } from "@playwright/test";
import * as fs from "fs";
import * as path from "path";

const BASE_URL = process.env.BASE_URL ?? "https://a-stats-content.vercel.app";
const API_URL =
  process.env.API_URL ??
  "https://a-stats-content-production.up.railway.app";

const AUTH_DIR = path.join(__dirname, ".auth");
const AUTH_STATE = path.join(AUTH_DIR, "user.json");
const META_FILE = path.join(AUTH_DIR, "test-meta.json");

const EMPTY_STATE = JSON.stringify({ cookies: [], origins: [] });

export const TEST_NAME = "Playwright Tester";
export const TEST_EMAIL = process.env.TEST_EMAIL ?? `e2e-${Date.now()}@e2etests.io`;
export const TEST_PASSWORD = process.env.TEST_PASSWORD ?? "E2eTest!Password9";

async function globalSetup() {
  if (!fs.existsSync(AUTH_DIR)) fs.mkdirSync(AUTH_DIR, { recursive: true });

  const browser = await chromium.launch();
  const context = await browser.newContext({ baseURL: BASE_URL });
  const page = await context.newPage();

  // ── Register if no credentials provided ──────────────────────────────────
  if (!process.env.TEST_EMAIL) {
    console.log(`[setup] Registering test user: ${TEST_EMAIL}`);
    const regRes = await page.request.post(`${API_URL}/api/v1/auth/register`, {
      data: { name: TEST_NAME, email: TEST_EMAIL, password: TEST_PASSWORD },
    });
    if (!regRes.ok()) {
      const body = await regRes.text();
      if (!body.toLowerCase().includes("already")) {
        console.warn(`[setup] Registration failed — writing empty auth state`);
        fs.writeFileSync(AUTH_STATE, EMPTY_STATE);
        await browser.close();
        return;
      }
    }
  } else {
    console.log(`[setup] Using provided credentials for: ${TEST_EMAIL}`);
  }

  // ── Log in through the Vercel UI ─────────────────────────────────────────
  // This populates BOTH the Railway HttpOnly cookies AND Zustand localStorage
  console.log("[setup] Navigating to login page…");
  await page.goto(`${BASE_URL}/en/login`);

  await page.getByLabel(/email/i).fill(TEST_EMAIL);
  await page.getByLabel(/password/i).fill(TEST_PASSWORD);
  await page.getByRole("button", { name: /sign in|log in|login/i }).click();

  // Wait for redirect to dashboard (proves auth succeeded)
  try {
    await page.waitForURL(/\/dashboard/, { timeout: 20_000 });
    console.log(`[setup] ✓ Logged in — on dashboard`);
  } catch {
    // Check if we got an error message
    const errorText = await page.getByText(/invalid|inactive|verify|error/i).first().textContent().catch(() => "");
    if (errorText) {
      console.warn(`[setup] Login failed: ${errorText}`);
    } else {
      console.warn(`[setup] Login did not reach /dashboard (current: ${page.url()})`);
    }
    console.warn("[setup] Writing empty auth state — authenticated tests will be SKIPPED");
    fs.writeFileSync(AUTH_STATE, EMPTY_STATE);
    await browser.close();
    return;
  }

  // Wait for the page to fully hydrate (Zustand store written to localStorage)
  await page.waitForTimeout(2_000);

  // ── Save storageState (cookies + localStorage) ────────────────────────────
  await context.storageState({ path: AUTH_STATE });
  console.log(`[setup] ✓ Auth state saved (cookies + localStorage)`);

  // Persist meta for teardown
  fs.writeFileSync(META_FILE, JSON.stringify({ email: TEST_EMAIL, password: TEST_PASSWORD }));

  await browser.close();
}

export default globalSetup;
