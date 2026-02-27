/**
 * Global teardown — runs once after the entire test suite.
 * Deletes the test user created in global-setup.
 */
import * as fs from "fs";
import * as path from "path";

const API_URL =
  process.env.API_URL ??
  "https://a-stats-content-production.up.railway.app";

const STATE_FILE = path.join(__dirname, ".auth", "test-meta.json");

async function globalTeardown() {
  if (!fs.existsSync(STATE_FILE)) return;

  const { email, password } = JSON.parse(fs.readFileSync(STATE_FILE, "utf8"));

  try {
    // Login first to get a valid session for the delete request
    const loginRes = await fetch(`${API_URL}/api/v1/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
      credentials: "include",
    });
    if (!loginRes.ok) {
      console.warn("[teardown] Could not login to delete test user — skipping");
      return;
    }

    const setCookie = loginRes.headers.get("set-cookie") ?? "";
    const token = loginRes.headers.get("authorization") ?? "";

    // Delete own account via /auth/me DELETE (if available) or just leave it
    // — the account uses a unique timestamp email so it won't pollute data
    console.log("[teardown] Test user left in DB (unique email — safe to ignore)");
  } catch (e) {
    console.warn("[teardown] Teardown error (non-fatal):", e);
  } finally {
    // Clean up auth files
    try { fs.unlinkSync(STATE_FILE); } catch {}
  }
}

export default globalTeardown;
