/**
 * Global setup — runs once before the entire test suite.
 *
 * 1. Registers a fresh test user via the backend API
 * 2. Logs in to obtain the session cookie
 * 3. Saves browser storage state to e2e/.auth/user.json
 *    (reused by all authenticated tests)
 */
import { chromium, expect } from "@playwright/test";
import * as fs from "fs";
import * as path from "path";

const BASE_URL = process.env.BASE_URL ?? "https://a-stats-content.vercel.app";
const API_URL =
  process.env.API_URL ??
  "https://a-stats-content-production.up.railway.app";

// Stable test credentials (deterministic so teardown can delete the same user)
export const TEST_EMAIL = `e2e-test-${Date.now()}@playwright.test`;
export const TEST_PASSWORD = "TestPw!23456";
export const TEST_NAME = "Playwright Tester";

// Shared state written to disk so teardown can read the email
const STATE_FILE = path.join(__dirname, ".auth", "test-meta.json");

async function globalSetup() {
  const authDir = path.join(__dirname, ".auth");
  if (!fs.existsSync(authDir)) fs.mkdirSync(authDir, { recursive: true });

  const browser = await chromium.launch();
  const context = await browser.newContext({
    baseURL: BASE_URL,
    extraHTTPHeaders: { Accept: "application/json" },
  });
  const page = await context.newPage();

  // ── 1. Register ──────────────────────────────────────────────────────────
  console.log(`[setup] Registering test user: ${TEST_EMAIL}`);
  const regRes = await page.request.post(`${API_URL}/api/v1/auth/register`, {
    data: { name: TEST_NAME, email: TEST_EMAIL, password: TEST_PASSWORD },
  });

  if (!regRes.ok()) {
    const body = await regRes.text();
    // 400 "Email already exists" is fine — user from a previous run
    if (!body.includes("already")) {
      throw new Error(
        `Registration failed (${regRes.status()}): ${body}`
      );
    }
    console.log("[setup] User already exists — proceeding to login");
  }

  // ── 2. Login ─────────────────────────────────────────────────────────────
  console.log("[setup] Logging in…");
  const loginRes = await page.request.post(`${API_URL}/api/v1/auth/login`, {
    data: { email: TEST_EMAIL, password: TEST_PASSWORD },
  });

  if (!loginRes.ok()) {
    const body = await loginRes.text();
    // If email verification is required, print a clear message
    if (body.includes("verify") || body.includes("verified")) {
      console.warn(
        "\n⚠️  Email verification is required on this environment.\n" +
          "   Authenticated tests will be skipped.\n" +
          "   To fix: disable email verification for test accounts, or\n" +
          "   pre-create a verified user and set TEST_EMAIL / TEST_PASSWORD env vars.\n"
      );
      // Write empty storage state so authenticated tests are skipped gracefully
      fs.writeFileSync(
        path.join(authDir, "user.json"),
        JSON.stringify({ cookies: [], origins: [] })
      );
    } else {
      throw new Error(`Login failed (${loginRes.status()}): ${body}`);
    }
  } else {
    // ── 3. Save storage state (cookies set by backend) ───────────────────
    await context.storageState({ path: path.join(authDir, "user.json") });
    console.log("[setup] Auth state saved.");
  }

  // ── 4. Persist test meta for teardown ────────────────────────────────────
  fs.writeFileSync(
    STATE_FILE,
    JSON.stringify({ email: TEST_EMAIL, password: TEST_PASSWORD })
  );

  await browser.close();
}

export default globalSetup;
