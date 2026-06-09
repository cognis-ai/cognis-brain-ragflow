import { test, expect } from '@playwright/test';
import {
  E2E_EMAIL,
  emailInput,
  fillLogin,
  passwordInput,
  registerOrLogin,
} from './helpers';

// Exercises the raw native (email/password) auth surface, so every test
// starts from a clean, unauthenticated context.
test.use({ storageState: { cookies: [], origins: [] } });

test.describe('Cognis Knowledge — authentication', () => {
  test('anonymous visit to the app redirects to /login', async ({ page }) => {
    await page.goto('/knowledge');
    await expect(page).toHaveURL(/\/login/);
    await expect(emailInput(page)).toBeVisible();
  });

  test('login page renders the email/password form', async ({ page }) => {
    const res = await page.goto('/login');
    expect(res?.status()).toBe(200);
    await expect(emailInput(page)).toBeVisible();
    await expect(passwordInput(page)).toBeVisible();
    await expect(page.getByRole('button', { name: /sign in/i })).toBeVisible();
  });

  test('rejects bad credentials and stays unauthenticated', async ({ page }) => {
    await page.goto('/login');
    await fillLogin(page, E2E_EMAIL, 'definitely-the-wrong-password');
    await page.getByRole('button', { name: /sign in/i }).click();

    // Stays on /login; no token is persisted for the SPA to use.
    await page.waitForTimeout(3_000);
    await expect(page).toHaveURL(/\/login/);
    const token = await page.evaluate(() => window.localStorage.getItem('Authorization'));
    expect(token, 'no Authorization token on failed login').toBeFalsy();
  });

  test('register-or-login establishes a session (dedicated user)', async ({ page }) => {
    // RAGFlow rotates access_token per login — use a user OTHER than the
    // shared storageState user so this login doesn't invalidate the session
    // the flow/branding specs run with.
    // NB: hyphen, not plus-addressing — RAGFlow's register email regex
    // (\w/._- only) rejects '+'.
    await registerOrLogin(page, {
      email: E2E_EMAIL.replace('@', '-authspec@'),
      nickname: 'Cognis E2E AuthSpec',
    });
    await expect(page).not.toHaveURL(/\/login/);
    const token = await page.evaluate(() => window.localStorage.getItem('Authorization'));
    expect(token, 'Authorization token issued on success').toBeTruthy();
  });
});
