/**
 * Loading states: tab switches don't error, page loads cleanly.
 */
import { test, expect } from './fixtures.js';

test.describe('Loading States', () => {
  test('all tabs load without JS errors', async ({ page, seededProject }) => {
    const errors = [];
    page.on('pageerror', (err) => errors.push(err.message));

    await page.goto('/');
    await page.evaluate((id) => selectProject(id), seededProject.id);
    await expect(page.locator('#mainApp')).toBeVisible();

    const tabs = ['companies', 'taxonomy', 'map', 'reports', 'process', 'export'];
    for (const tab of tabs) {
      await page.evaluate((t) => showTab(t), tab);
      await page.waitForTimeout(300); // Brief pause for async loads
      await expect(page.locator(`#tab-${tab}`)).toHaveClass(/active/);
    }

    // Filter out CDN errors (external resources may fail in test env)
    const appErrors = errors.filter(e => !e.includes('cdn.jsdelivr') && !e.includes('fonts.googleapis'));
    expect(appErrors).toHaveLength(0);
  });

  test('rapid tab switching does not break UI', async ({ page, seededProject }) => {
    await page.goto('/');
    await page.evaluate((id) => selectProject(id), seededProject.id);
    await expect(page.locator('#mainApp')).toBeVisible();

    // Rapidly switch tabs
    const tabs = ['taxonomy', 'map', 'companies', 'export', 'process', 'reports', 'companies'];
    for (const tab of tabs) {
      await page.evaluate((t) => showTab(t), tab);
    }

    // Final state should be companies
    await expect(page.locator('#tab-companies')).toHaveClass(/active/);
  });

  test('page loads without console errors', async ({ page }) => {
    const errors = [];
    page.on('pageerror', (err) => errors.push(err.message));

    await page.goto('/');
    await page.waitForTimeout(1000);

    const appErrors = errors.filter(e => !e.includes('cdn.jsdelivr') && !e.includes('fonts.googleapis'));
    expect(appErrors).toHaveLength(0);
  });
});
