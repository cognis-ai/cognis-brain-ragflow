import { expect, type Page } from '@playwright/test';

// Fixture credentials for the LOCAL dev RAGFlow instance only — the user is
// created by the suite itself (register-or-login), so these are not secrets.
// Override via env to point the suite at another environment.
export const E2E_EMAIL = process.env.KNOWLEDGE_E2E_EMAIL ?? 'e2e-knowledge@cognis.io';
export const E2E_PASSWORD = process.env.KNOWLEDGE_E2E_PASSWORD ?? 'Cognis-e2e-9382!';
export const E2E_NICKNAME = process.env.KNOWLEDGE_E2E_NICKNAME ?? 'Cognis E2E';

export const BRAND = 'Cognis Knowledge';

// The served UI renders ONE AntD form at a time (login OR register) and its
// inputs carry no ids — locate them by placeholder.
export const emailInput = (page: Page) => page.getByPlaceholder(/email/i).first();
export const passwordInput = (page: Page) => page.getByPlaceholder(/password/i).first();
export const nicknameInput = (page: Page) => page.getByPlaceholder(/name|nickname/i).first();

export async function fillLogin(page: Page, email: string, password: string) {
  await emailInput(page).fill(email);
  await passwordInput(page).fill(password);
}

/**
 * Log in via the UI; if the account does not exist yet, flip to the sign-up
 * form, register it (RAGFlow native email/password — registration is enabled
 * by default via REGISTER_ENABLED=1), then ensure we end up authenticated.
 *
 * NOTE: RAGFlow rotates the user's access_token on EVERY login, so logging
 * in invalidates any previously captured storageState for that user. Tests
 * that exercise login directly must therefore use their own dedicated user
 * (pass custom creds) instead of the shared storageState user.
 */
export async function registerOrLogin(
  page: Page,
  creds: { email?: string; password?: string; nickname?: string } = {},
) {
  const email = creds.email ?? E2E_EMAIL;
  const password = creds.password ?? E2E_PASSWORD;
  const nickname = creds.nickname ?? E2E_NICKNAME;
  await page.goto('/login');
  await expect(emailInput(page)).toBeVisible();
  await fillLogin(page, email, password);
  await page.getByRole('button', { name: /sign in/i }).click();

  // Either we leave /login (success) or an error toast appears (no account).
  const left = await page
    .waitForURL((url) => !url.pathname.includes('/login'), { timeout: 8_000 })
    .then(() => true)
    .catch(() => false);
  if (left) return;

  // Register path: switch to the sign-up form and submit it.
  await page.getByRole('button', { name: /sign up/i }).click();
  await expect(nicknameInput(page)).toBeVisible();
  await nicknameInput(page).fill(nickname);
  await fillLogin(page, email, password);
  await page.getByRole('button', { name: /continue|sign up/i }).last().click();

  // RAGFlow either auto-logs-in after register or flips back to login.
  const authed = await page
    .waitForURL((url) => !url.pathname.includes('/login'), { timeout: 10_000 })
    .then(() => true)
    .catch(() => false);
  if (!authed) {
    await fillLogin(page, email, password);
    await page.getByRole('button', { name: /sign in/i }).click();
    await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 10_000 });
  }
}
