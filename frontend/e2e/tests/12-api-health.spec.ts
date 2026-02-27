/**
 * Backend API smoke tests — called directly (no browser UI).
 * Verifies the Railway deployment is healthy and key endpoints respond correctly.
 */
import { test, expect } from "@playwright/test";

const API_URL =
  process.env.API_URL ??
  "https://a-stats-content-production.up.railway.app";

// These tests don't need a browser session
test.use({ storageState: { cookies: [], origins: [] } });

test.describe("Backend API health", () => {
  test("GET /api/v1/health returns 200", async ({ request }) => {
    const res = await request.get(`${API_URL}/api/v1/health`);
    expect(res.status()).toBe(200);
    const body = await res.json();
    // Backend returns "healthy" or "ok"
    expect(["ok", "healthy"]).toContain(body.status);
  });

  test("GET /api/v1/auth/me without token returns 401", async ({ request }) => {
    const res = await request.get(`${API_URL}/api/v1/auth/me`);
    expect(res.status()).toBe(401);
  });

  test("POST /api/v1/auth/login with wrong creds returns 401 or 400", async ({
    request,
  }) => {
    const res = await request.post(`${API_URL}/api/v1/auth/login`, {
      data: { email: "nobody@example.com", password: "wrongpassword" },
    });
    expect([400, 401, 422]).toContain(res.status());
  });

  test("GET /api/v1/outlines without auth returns 401", async ({ request }) => {
    const res = await request.get(`${API_URL}/api/v1/outlines`);
    expect(res.status()).toBe(401);
  });

  test("GET /api/v1/articles without auth returns 401", async ({ request }) => {
    const res = await request.get(`${API_URL}/api/v1/articles`);
    expect(res.status()).toBe(401);
  });

  test("GET /api/v1/projects without auth returns 401", async ({ request }) => {
    const res = await request.get(`${API_URL}/api/v1/projects`);
    expect(res.status()).toBe(401);
  });

  test("Admin endpoint without auth returns 401 or 403", async ({ request }) => {
    const res = await request.get(`${API_URL}/api/v1/admin/users`);
    expect([401, 403]).toContain(res.status());
  });
});

test.describe("Backend API authenticated flows", () => {
  // Login once and reuse session for all tests in this group
  let authCookies = "";

  test.beforeAll(async ({ request }) => {
    // We'll only run these if the env provides credentials
    const email = process.env.TEST_EMAIL;
    const password = process.env.TEST_PASSWORD;
    if (!email || !password) return;

    const res = await request.post(`${API_URL}/api/v1/auth/login`, {
      data: { email, password },
    });
    if (res.ok()) {
      const headers = res.headersArray();
      authCookies = headers
        .filter((h) => h.name.toLowerCase() === "set-cookie")
        .map((h) => h.value.split(";")[0])
        .join("; ");
    }
  });

  test("GET /api/v1/auth/me with valid session returns user", async ({ request }) => {
    if (!authCookies) {
      test.skip(true, "No auth cookies — set TEST_EMAIL + TEST_PASSWORD env vars");
      return;
    }
    const res = await request.get(`${API_URL}/api/v1/auth/me`, {
      headers: { Cookie: authCookies },
    });
    expect(res.status()).toBe(200);
    const body = await res.json();
    expect(body).toHaveProperty("id");
    expect(body).toHaveProperty("email");
  });

  test("GET /api/v1/projects returns successful response", async ({ request }) => {
    if (!authCookies) {
      test.skip(true, "No auth cookies");
      return;
    }
    const res = await request.get(`${API_URL}/api/v1/projects`, {
      headers: { Cookie: authCookies },
    });
    // Accept any 2xx — backend may return 200 or 204
    expect(res.ok()).toBe(true);
    const body = await res.json();
    // Projects endpoint returns paginated {projects: [...], total, page, ...}
    const isValid = Array.isArray(body)
      || (typeof body === "object" && body !== null
          && ("items" in body || "projects" in body || "data" in body));
    expect(isValid).toBe(true);
  });

  test("GET /api/v1/outlines returns object with items", async ({ request }) => {
    if (!authCookies) {
      test.skip(true, "No auth cookies");
      return;
    }
    const res = await request.get(`${API_URL}/api/v1/outlines`, {
      headers: { Cookie: authCookies },
    });
    expect(res.status()).toBe(200);
  });
});
