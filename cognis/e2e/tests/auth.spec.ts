import { test, expect } from '@playwright/test';
import {
  E2E_EMAIL,
  SIGNUP_ENABLED,
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
    // Register path needs signup; under the SEC-5 posture the dedicated
    // user is only usable if pre-seeded, so gate the test on the flag.
    test.skip(!SIGNUP_ENABLED, 'self-signup disabled (REGISTER_ENABLED=0, SEC-5)');
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

  test('native self-signup is rejected (SEC-5)', async ({ request }) => {
    test.skip(SIGNUP_ENABLED, 'instance intentionally runs with signup on');
    // POST /api/v1/users is the register endpoint; with REGISTER_ENABLED=0
    // it must refuse before even parsing the body (api/apps/restful_apis/
    // user_api.py gates on settings.REGISTER_ENABLED first).
    const res = await request.post('/api/v1/users', {
      data: {
        email: E2E_EMAIL.replace('@', '-sec5@'),
        nickname: 'Cognis E2E SEC5',
        password: 'irrelevant',
      },
    });
    const body = await res.json();
    expect(body.message, 'registration must be disabled').toMatch(/registration is disabled/i);
    expect(body.data).toBeFalsy();
  });
});
