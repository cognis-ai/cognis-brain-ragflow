import { test, expect } from '@playwright/test';
import { BRAND, emailInput } from './helpers';

// Brand-integrity checks: the product must present as "Cognis Knowledge",
// not the upstream name. Upstream is Apache-2.0: its attribution lives in
// LICENSE/NOTICE (which the fork retains, untouched) — Apache-2.0 does NOT
// require in-UI attribution, so the rendered chrome must be 100% Cognis.

test.describe('Cognis Knowledge — brand integrity', () => {
  test('login page is branded Cognis Knowledge with no upstream name', async ({ browser }) => {
    const ctx = await browser.newContext({ storageState: { cookies: [], origins: [] } });
    const page = await ctx.newPage();
    await page.goto('/login');

    await expect(page).toHaveTitle(new RegExp(BRAND));
    await expect(emailInput(page)).toBeVisible();

    const body = await page.locator('body').innerText();
    expect(body, 'no "RAGFlow" anywhere on the login page').not.toMatch(/ragflow/i);
    await ctx.close();
  });

  test('authenticated chrome (title + page text) reads Cognis Knowledge', async ({ page }) => {
    await page.goto('/knowledge');
    // Wait for the authenticated page to actually render (catches a delayed
    // 401 → /login bounce; networkidle never settles on this SPA).
    await expect(
      page.getByRole('button', { name: /create knowledge base/i }),
    ).toBeVisible({ timeout: 15_000 });
    await expect(page).not.toHaveURL(/\/login/);
    await expect(page).toHaveTitle(new RegExp(BRAND));

    // Navbar wordmark (fed by conf.json appName) must carry the Cognis name.
    await expect(page.locator('span[class*="appName"]').first()).toHaveText(BRAND);

    const body = await page.locator('body').innerText();
    expect(body, 'no "RAGFlow" in the authenticated chrome').not.toMatch(/ragflow/i);
  });

  test('served HTML title and bundles carry the Cognis name', async ({ request }) => {
    const res = await request.get('/');
    expect(res.status()).toBe(200);
    const html = await res.text();
    expect(html).toContain(`<title>${BRAND}</title>`);
    expect(html, 'no upstream name in the served shell').not.toMatch(/RAGFlow/);
  });
});
