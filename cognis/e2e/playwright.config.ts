import { defineConfig, devices } from '@playwright/test';

// Cognis Knowledge e2e — drives the LIVE RAGFlow fork (cognis-knowledge-1).
// The web UI is the in-container nginx published on :9382 by
// cognis-platform/docker-compose.dev.yml. Target is configurable so the same
// suite runs against dev or a staging URL in CI.
const BASE_URL = process.env.KNOWLEDGE_BASE_URL ?? 'http://localhost:9382';

export default defineConfig({
  testDir: './tests',
  // Auth state is shared via storageState produced by the auth setup project
  // (RAGFlow keeps its session token in localStorage, which storageState
  // captures per-origin). Login itself is tested explicitly in auth.spec.ts.
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: [['list'], ['html', { open: 'never', outputFolder: 'playwright-report' }]],
  timeout: 45_000,
  expect: { timeout: 10_000 },
  use: {
    baseURL: BASE_URL,
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
  projects: [
    { name: 'setup', testMatch: /auth\.setup\.ts/ },
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'], storageState: '.auth/user.json' },
      dependencies: ['setup'],
    },
  ],
});
