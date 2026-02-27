/**
 * Auth flows — unauthenticated tests (no storageState needed).
 * Tests: login, logout, register form, forgot password, RBAC redirects.
 */
import { test, expect } from "@playwright/test";

const API_URL =
  process.env.API_URL ??
  "https://a-stats-content-production.up.railway.app";

// Override storageState — these tests run as unauthenticated
test.use({ storageState: { cookies: [], origins: [] } });

test.describe("Health check", () => {
  test("backend /health returns ok", async ({ request }) => {
    const res = await request.get(`${API_URL}/health`);
    expect(res.status()).toBe(200);
    const body = await res.json();
    expect(body).toMatchObject({ status: "ok" });
  });
});

test.describe("Unauthenticated redirects", () => {
  test("visiting /dashboard redirects to login", async ({ page }) => {
    await page.goto("/dashboard");
    await expect(page).toHaveURL(/login/);
  });

  test("visiting /outlines redirects to login", async ({ page }) => {
    await page.goto("/outlines");
    await expect(page).toHaveURL(/login/);
  });

  test("visiting /admin redirects away", async ({ page }) => {
    await page.goto("/admin");
    // Should redirect to login or dashboard (not stay on /admin)
    await expect(page).not.toHaveURL(/^.*\/admin$/);
  });
});

test.describe("Login page", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/en/login");
  });

  test("renders login form", async ({ page }) => {
    await expect(page.getByRole("heading", { name: /sign in|log in|welcome/i })).toBeVisible();
    await expect(page.getByLabel(/email/i)).toBeVisible();
    await expect(page.getByLabel(/password/i)).toBeVisible();
    await expect(page.getByRole("button", { name: /sign in|log in/i })).toBeVisible();
  });

  test("shows error on invalid credentials", async ({ page }) => {
    await page.getByLabel(/email/i).fill("wrong@example.com");
    await page.getByLabel(/password/i).fill("wrongpassword");
    await page.getByRole("button", { name: /sign in|log in/i }).click();
    // Expect some error message
    await expect(
      page.getByText(/invalid|incorrect|not found|credentials/i)
    ).toBeVisible({ timeout: 10_000 });
  });

  test("has link to register", async ({ page }) => {
    await expect(page.getByRole("link", { name: /sign up|register|create/i })).toBeVisible();
  });

  test("has forgot password link", async ({ page }) => {
    await expect(page.getByRole("link", { name: /forgot|reset password/i })).toBeVisible();
  });
});

test.describe("Register page", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/en/register");
  });

  test("renders registration form", async ({ page }) => {
    await expect(page.getByLabel(/name/i).first()).toBeVisible();
    await expect(page.getByLabel(/email/i)).toBeVisible();
    await expect(page.getByLabel(/^password/i).first()).toBeVisible();
    await expect(page.getByRole("button", { name: /sign up|create|register/i })).toBeVisible();
  });

  test("shows validation error for short password", async ({ page }) => {
    await page.getByLabel(/name/i).first().fill("Test User");
    await page.getByLabel(/email/i).fill("test@example.com");
    await page.getByLabel(/^password/i).first().fill("short");
    await page.getByRole("button", { name: /sign up|create|register/i }).click();
    await expect(
      page.getByText(/at least|minimum|8 characters/i)
    ).toBeVisible({ timeout: 5_000 });
  });

  test("shows validation error for invalid email", async ({ page }) => {
    await page.getByLabel(/name/i).first().fill("Test User");
    await page.getByLabel(/email/i).fill("notanemail");
    await page.getByLabel(/^password/i).first().fill("ValidPass!123");
    await page.getByRole("button", { name: /sign up|create|register/i }).click();
    await expect(
      page.getByText(/invalid|valid email/i)
    ).toBeVisible({ timeout: 5_000 });
  });
});

test.describe("Forgot password page", () => {
  test("renders forgot password form", async ({ page }) => {
    await page.goto("/en/forgot-password");
    await expect(page.getByLabel(/email/i)).toBeVisible();
    await expect(page.getByRole("button", { name: /send|reset|submit/i })).toBeVisible();
  });

  test("submitting shows confirmation message", async ({ page }) => {
    await page.goto("/en/forgot-password");
    await page.getByLabel(/email/i).fill("any@example.com");
    await page.getByRole("button", { name: /send|reset|submit/i }).click();
    // Should show a generic success message (no email enumeration)
    await expect(
      page.getByText(/check|sent|email|instructions/i)
    ).toBeVisible({ timeout: 10_000 });
  });
});
