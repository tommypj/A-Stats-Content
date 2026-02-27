/**
 * Global setup — runs once before the entire test suite.
 *
 * Priority:
 *   1. If TEST_EMAIL + TEST_PASSWORD env vars are set, log in directly.
 *   2. Otherwise, register a new account and try to log in.
 *      If the account is inactive (email verification required), write an
 *      EMPTY auth state so authenticated tests are skipped gracefully.
 *
 * To run the full suite including authenticated tests, create a verified
 * account and pass credentials:
 *   TEST_EMAIL=you@example.com TEST_PASSWORD=yourpass npx playwright test
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
export const TEST_PASSWORD = process.env.TEST_PASSWORD ?? "E2eTest!Password9";

// Use env var or generate a timestamped email
export const TEST_EMAIL =
  process.env.TEST_EMAIL ?? `e2e-${Date.now()}@e2etests.io`;

async function globalSetup() {
  if (!fs.existsSync(AUTH_DIR)) fs.mkdirSync(AUTH_DIR, { recursive: true });

  const browser = await chromium.launch();
  const context = await browser.newContext({ baseURL: BASE_URL });
  const page = await context.newPage();

  // ── 1. Register (skip if using pre-provided credentials) ─────────────────
  if (!process.env.TEST_EMAIL) {
    console.log(`[setup] Registering test user: ${TEST_EMAIL}`);
    const regRes = await page.request.post(`${API_URL}/api/v1/auth/register`, {
      data: { name: TEST_NAME, email: TEST_EMAIL, password: TEST_PASSWORD },
    });

    if (!regRes.ok()) {
      const body = await regRes.text();
      if (!body.toLowerCase().includes("already")) {
        console.warn(`[setup] Registration failed (${regRes.status()}): ${body}`);
        console.warn("[setup] Proceeding with empty auth state — authenticated tests will be skipped.");
        fs.writeFileSync(AUTH_STATE, EMPTY_STATE);
        await browser.close();
        return;
      }
      console.log("[setup] User already exists — proceeding to login");
    }
  } else {
    console.log(`[setup] Using provided credentials for: ${TEST_EMAIL}`);
  }

  // ── 2. Login ─────────────────────────────────────────────────────────────
  console.log("[setup] Logging in…");
  const loginRes = await page.request.post(`${API_URL}/api/v1/auth/login`, {
    data: { email: TEST_EMAIL, password: TEST_PASSWORD },
  });

  if (!loginRes.ok()) {
    const body = await loginRes.text();
    const isVerificationRequired =
      body.toLowerCase().includes("inactive") ||
      body.toLowerCase().includes("verify") ||
      body.toLowerCase().includes("not verified");

    if (isVerificationRequired) {
      console.warn(
        "\n⚠️  Email verification required.\n" +
          "   Authenticated tests will be SKIPPED.\n" +
          "   To run them, create a verified account and set:\n" +
          `     TEST_EMAIL=<email> TEST_PASSWORD=<pass> npx playwright test\n`
      );
    } else {
      console.warn(`[setup] Login failed (${loginRes.status()}): ${body}`);
    }

    fs.writeFileSync(AUTH_STATE, EMPTY_STATE);
    await browser.close();
    return;
  }

  // ── 3. Save storage state ────────────────────────────────────────────────
  await context.storageState({ path: AUTH_STATE });
  console.log(`[setup] ✓ Auth state saved for ${TEST_EMAIL}`);

  // ── 4. Persist meta for teardown ─────────────────────────────────────────
  fs.writeFileSync(
    META_FILE,
    JSON.stringify({ email: TEST_EMAIL, password: TEST_PASSWORD })
  );

  await browser.close();
}

export default globalSetup;
