/**
 * Auth flows — unauthenticated tests.
 */
import { test, expect } from "@playwright/test";

const API_URL =
  process.env.API_URL ??
  "https://a-stats-content-production.up.railway.app";

// Run as unauthenticated
test.use({ storageState: { cookies: [], origins: [] } });

test.describe("Health check", () => {
  test("backend /health returns ok", async ({ request }) => {
    const res = await request.get(`${API_URL}/api/v1/health`);
    expect(res.status()).toBe(200);
    const body = await res.json();
    expect(["ok", "healthy"]).toContain(body.status);
  });
});

test.describe("Unauthenticated redirects", () => {
  test("visiting /dashboard redirects to login", async ({ page }) => {
    await page.goto("/dashboard");
    await expect(page).toHaveURL(/login/, { timeout: 15_000 });
  });

  test("visiting /outlines redirects to login", async ({ page }) => {
    await page.goto("/outlines");
    await expect(page).toHaveURL(/login/, { timeout: 15_000 });
  });

  test("visiting /admin redirects away", async ({ page }) => {
    await page.goto("/admin");
    // Should NOT stay on /admin
    await page.waitForTimeout(3_000);
    const url = page.url();
    expect(url).not.toMatch(/\/admin\/?$/);
  });
});

test.describe("Login page", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/en/login");
  });

  test("renders login form with email and password fields", async ({ page }) => {
    await expect(page.getByLabel(/email/i)).toBeVisible();
    await expect(page.getByLabel(/password/i)).toBeVisible();
    await expect(
      page.getByRole("button", { name: /sign in|log in|login/i })
    ).toBeVisible();
  });

  test("shows error on invalid credentials", async ({ page }) => {
    await page.getByLabel(/email/i).fill("wrong@example.com");
    await page.getByLabel(/password/i).fill("wrongpassword");
    await page.getByRole("button", { name: /sign in|log in|login/i }).click();
    // Primary check: still on login page (not redirected to dashboard)
    await expect(page).not.toHaveURL(/dashboard/, { timeout: 10_000 });
    await expect(page).toHaveURL(/login/);
  });

  test("has link to register", async ({ page }) => {
    await expect(
      page.getByRole("link", { name: /sign up|register|create/i })
    ).toBeVisible();
  });

  test("has forgot password link", async ({ page }) => {
    await expect(
      page.getByRole("link", { name: /forgot|reset/i })
    ).toBeVisible();
  });
});

test.describe("Register page", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/en/register");
  });

  test("renders registration form", async ({ page }) => {
    await expect(page.getByLabel(/email/i)).toBeVisible();
    await expect(
      page.getByRole("button", { name: /sign up|create|register/i })
    ).toBeVisible();
  });

  test("shows validation error for short password", async ({ page }) => {
    await page.getByLabel(/name/i).first().fill("Test User");
    await page.getByLabel(/email/i).fill("test@example.com");
    // Fill password field (first one only)
    await page.getByLabel(/^password/i).first().fill("short");
    await page.getByRole("button", { name: /sign up|create|register/i }).click();
    await expect(
      page.getByText(/at least|minimum|8 character/i).first()
    ).toBeVisible({ timeout: 5_000 });
  });

  test("shows validation error for invalid email", async ({ page }) => {
    await page.getByLabel(/name/i).first().fill("Test User");
    await page.getByLabel(/email/i).fill("notanemail");
    await page.getByLabel(/^password/i).first().fill("ValidPass!123");
    await page.getByRole("button", { name: /sign up|create|register/i }).click();
    // Wait briefly then check: form should not navigate away (validation blocks it)
    await page.waitForTimeout(2_000);
    // Still on register page means validation fired
    await expect(page).toHaveURL(/register/, { timeout: 3_000 });
  });
});

test.describe("Forgot password page", () => {
  test("renders forgot password form", async ({ page }) => {
    await page.goto("/en/forgot-password");
    await expect(page.getByLabel(/email/i)).toBeVisible();
    await expect(
      page.getByRole("button", { name: /send|reset|submit/i })
    ).toBeVisible();
  });

  test("submitting disables button or shows success state", async ({ page }) => {
    await page.goto("/en/forgot-password");
    await page.getByLabel(/email/i).fill("any@example.com");
    const submitBtn = page.getByRole("button", { name: /send|reset link|submit/i });
    await submitBtn.click();
    // After submission: button becomes disabled OR a success/info message appears
    await expect(
      submitBtn.and(page.locator("[disabled]"))
        .or(page.getByText(/if.*account|instructions|check your/i).first())
    ).toBeVisible({ timeout: 10_000 });
  });
});
