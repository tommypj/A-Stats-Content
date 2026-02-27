/**
 * Auth helper — shared login fixture for tests that need a fresh page
 * already authenticated, without depending on saved storage state.
 */
import { Page } from "@playwright/test";

const BASE_URL = process.env.BASE_URL ?? "https://a-stats-content.vercel.app";
const API_URL =
  process.env.API_URL ??
  "https://a-stats-content-production.up.railway.app";

export async function loginViaUI(
  page: Page,
  email: string,
  password: string
): Promise<void> {
  await page.goto("/en/login");
  await page.getByLabel(/email/i).fill(email);
  await page.getByLabel(/password/i).fill(password);
  await page.getByRole("button", { name: /sign in|log in/i }).click();
  // Wait for redirect to dashboard
  await page.waitForURL(/\/dashboard/, { timeout: 20_000 });
}

export async function loginViaAPI(page: Page, email: string, password: string) {
  const res = await page.request.post(`${API_URL}/api/v1/auth/login`, {
    data: { email, password },
  });
  return res;
}
