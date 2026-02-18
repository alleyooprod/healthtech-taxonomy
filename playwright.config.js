import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  timeout: 60_000,
  retries: 1,
  workers: 1, // serial — single Flask server
  use: {
    baseURL: 'http://127.0.0.1:5099',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },
  webServer: {
    command: 'python e2e/server.py',
    port: 5099,
    timeout: 15_000,
    reuseExistingServer: !process.env.CI,
    env: {
      E2E_PORT: '5099',
    },
  },
  projects: [
    { name: 'chromium', use: { browserName: 'chromium' } },
  ],
});
