/**
 * Shared Playwright fixtures: seeded project, CSRF handling.
 */
import { test as base, expect } from '@playwright/test';

export const test = base.extend({
  /** Create a fresh project for the test via API. */
  seededProject: async ({ page, request }, use) => {
    // Load page to get CSRF token
    await page.goto('/');
    const csrf = await page.locator('meta[name="csrf-token"]').getAttribute('content');

    // Create a test project
    const resp = await request.post('/api/projects', {
      headers: { 'X-CSRF-Token': csrf, 'Content-Type': 'application/json' },
      data: {
        name: `E2E Test ${Date.now()}`,
        purpose: 'Playwright E2E testing',
        seed_categories: 'Category Alpha\nCategory Beta\nCategory Gamma',
      },
    });
    const project = await resp.json();
    await use({ id: project.id, name: project.name, csrf });
  },
});

export { expect };
