import { test as setup } from '@playwright/test';
import fs from 'node:fs';
import { registerOrLogin } from './helpers';

// Produces an authenticated storageState reused by the flow/branding specs.
// RAGFlow keeps its bearer token + user info in localStorage, which
// storageState captures per-origin. Login is ALSO asserted independently
// (positive + negative) in auth.spec.ts, so this isn't the only coverage.
const AUTH_FILE = '.auth/user.json';

setup('register-or-login the e2e user', async ({ page }) => {
  await registerOrLogin(page);
  fs.mkdirSync('.auth', { recursive: true });
  await page.context().storageState({ path: AUTH_FILE });
});
