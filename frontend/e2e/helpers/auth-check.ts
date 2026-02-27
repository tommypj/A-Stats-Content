/**
 * Helper: skip a test if auth state is empty (no verified account provided).
 *
 * Usage at the top of an authenticated test file:
 *   test.beforeEach(async ({ page }) => {
 *     await skipIfNoAuth(page);
 *   });
 */
import { Page, test } from "@playwright/test";
import * as fs from "fs";
import * as path from "path";

const AUTH_STATE = path.join(__dirname, "../.auth/user.json");

export function skipIfNoAuth() {
  test.beforeEach(async ({}) => {
    if (!fs.existsSync(AUTH_STATE)) {
      test.skip(true, "No auth state — run with TEST_EMAIL + TEST_PASSWORD to enable");
      return;
    }
    const state = JSON.parse(fs.readFileSync(AUTH_STATE, "utf8"));
    if (!state.cookies || state.cookies.length === 0) {
      test.skip(true, "No auth cookies — run with TEST_EMAIL + TEST_PASSWORD to enable authenticated tests");
    }
  });
}
