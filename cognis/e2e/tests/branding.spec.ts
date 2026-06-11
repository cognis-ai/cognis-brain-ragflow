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

  // G5 — closes the innerText blind spot: hrefs never surface in innerText,
  // so the B2 boot-time URL rewrite (header GitHub/Docs links + ragflow.io
  // tooltip URLs in the compiled locales) could rot silently on a rebase
  // without this. Gate 2 made this test a binding condition of B2.
  test('no upstream hrefs anywhere in the authenticated chrome', async ({ page }) => {
    await page.goto('/knowledge');
    await expect(
      page.getByRole('button', { name: /create knowledge base/i }),
    ).toBeVisible({ timeout: 15_000 });

    const upstreamLinks = page.locator(
      'a[href*="ragflow.io"], a[href*="github.com/infiniflow"]',
    );
    await expect(upstreamLinks, 'every upstream link must be re-pointed at Cognis surfaces (B2)').toHaveCount(0);
  });
});

// G7 — invite-mail subject. Binding Gate-2 condition of B3.2: the boot-time
// sed of "RAGFlow Invitation" in /ragflow/api/utils/web_utils.py fails OPEN
// (silent no-op when a rebase moves the literal), so this MailHog assertion
// is the only de-branding tripwire for email.
//
// Environment contract (all three are required, suite skips otherwise):
//   KNOWLEDGE_SMTP_E2E=on        — the instance has SMTP wired (SMTP_SERVER
//                                  etc. point at MailHog; the smtp block in
//                                  service_conf.cognis.yaml.template is
//                                  env-inert by default, so plain dev
//                                  deploys cannot run this test)
//   KNOWLEDGE_MAILHOG_URL        — MailHog HTTP API (platform compose ships
//                                  MailHog; default http://localhost:8025)
//   KNOWLEDGE_INVITEE_EMAIL      — a SECOND pre-seeded account to invite
//                                  (REGISTER_ENABLED=0 / SEC-5 means the
//                                  suite cannot create it on the fly)
const SMTP_E2E = (process.env.KNOWLEDGE_SMTP_E2E ?? 'off') === 'on';
const MAILHOG_URL = process.env.KNOWLEDGE_MAILHOG_URL ?? 'http://localhost:8025';
const INVITEE = process.env.KNOWLEDGE_INVITEE_EMAIL ?? '';

test.describe('Cognis Knowledge — email branding (G7)', () => {
  test('invite email subject is "<product> Invitation"', async ({ page, request }) => {
    test.skip(!SMTP_E2E, 'SMTP not wired (set KNOWLEDGE_SMTP_E2E=on against a MailHog-backed instance)');
    test.skip(!INVITEE, 'KNOWLEDGE_INVITEE_EMAIL not set (needs a pre-seeded second account, SEC-5)');

    // The web app keeps its bearer token + user info in localStorage
    // (web/src/utils/authorization-util.ts); the storageState fixture has
    // already populated both for this origin.
    await page.goto('/knowledge');
    await expect(
      page.getByRole('button', { name: /create knowledge base/i }),
    ).toBeVisible({ timeout: 15_000 });
    const auth = await page.evaluate(() => localStorage.getItem('Authorization'));
    const userInfo = await page.evaluate(() =>
      JSON.parse(localStorage.getItem('userInfo') ?? '{}'),
    );
    expect(auth, 'Authorization token in localStorage').toBeTruthy();
    const tenantId: string = userInfo?.id;
    expect(tenantId, 'own user id (== own tenant id) from localStorage userInfo').toBeTruthy();

    // Trigger the invite (api/apps/restful_apis/tenant_api.py — the only
    // caller of send_invite_email). Logical errors come back HTTP 200 with
    // code != 0, so assert the body, not just the status.
    const res = await request.post(`/api/v1/tenants/${tenantId}/users`, {
      headers: { Authorization: auth! },
      data: { email: INVITEE },
    });
    expect(res.status()).toBe(200);
    const body = await res.json();
    expect(body.code, `invite accepted: ${JSON.stringify(body)}`).toBe(0);

    try {
      // The mail is sent fire-and-forget (asyncio.create_task) — poll MailHog.
      await expect
        .poll(
          async () => {
            const mh = await request.get(
              `${MAILHOG_URL}/api/v2/search?kind=to&query=${encodeURIComponent(INVITEE)}`,
            );
            if (!mh.ok()) return null;
            const json = await mh.json();
            return json?.items?.[0]?.Content?.Headers?.Subject?.[0] ?? null;
          },
          { timeout: 20_000 },
        )
        .toBe(`${BRAND} Invitation`);
    } finally {
      // Keep the test idempotent: drop the pending invite again so a re-run
      // does not fail with "already in the team".
      const invitedId = body?.data?.id;
      if (invitedId) {
        await request
          .delete(`/api/v1/tenants/${tenantId}/users`, {
            headers: { Authorization: auth! },
            data: { user_id: invitedId },
          })
          .catch(() => {});
      }
    }
  });
});
