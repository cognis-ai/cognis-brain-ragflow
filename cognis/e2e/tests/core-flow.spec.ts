import { test, expect } from '@playwright/test';

// Core product flow: create a knowledge base (dataset) and see it listed.
// Runs with the authenticated storageState from auth.setup.ts.

test.describe('Cognis Knowledge — knowledge-base flow', () => {
  test('create a knowledge base and see it in the list', async ({ page }) => {
    const kbName = `cognis-e2e-${Date.now()}`;

    await page.goto('/knowledge');
    await expect(page).not.toHaveURL(/\/login/);

    // Open the creation dialog and name the knowledge base.
    await page.getByRole('button', { name: /create knowledge base/i }).click();
    const dialog = page.getByRole('dialog');
    await expect(dialog).toBeVisible();
    await dialog.locator('input').first().fill(kbName);
    await dialog.getByRole('button', { name: /^(ok|save|create)$/i }).click();

    // Creation either navigates into the new KB or closes the modal in place.
    await expect(dialog).toBeHidden({ timeout: 15_000 });

    // Back on the listing, the new knowledge base card is present.
    await page.goto('/knowledge');
    await expect(page.getByText(kbName, { exact: false }).first()).toBeVisible({
      timeout: 15_000,
    });
  });
});
