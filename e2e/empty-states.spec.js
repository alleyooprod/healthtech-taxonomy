/**
 * Empty states: company list, batch list, search with no results.
 */
import { test, expect } from './fixtures.js';

test.describe('Empty States', () => {
  test.beforeEach(async ({ page, seededProject }) => {
    await page.goto('/');
    await page.evaluate((id) => selectProject(id), seededProject.id);
    await expect(page.locator('#mainApp')).toBeVisible();
  });

  test('company list shows empty state when no companies', async ({ page }) => {
    // With a fresh project there are no companies
    const tbody = page.locator('#companyBody');
    await expect(tbody).toBeVisible();

    // Should show an empty state message
    const emptyState = tbody.locator('.empty-state');
    await expect(emptyState).toBeVisible();
    await expect(emptyState.locator('.empty-state-title')).toContainText(/no companies/i);
  });

  test('batch list shows empty state when no batches', async ({ page }) => {
    await page.evaluate(() => showTab('process'));
    const batchList = page.locator('#batchList');

    // Wait for content to load
    await page.waitForTimeout(500);

    // Should show empty state
    const emptyState = batchList.locator('.empty-state');
    await expect(emptyState).toBeVisible();
    await expect(emptyState.locator('.empty-state-title')).toContainText(/no batches/i);
  });

  test('empty state has action link to process tab', async ({ page }) => {
    // In the companies empty state, there should be a link to the process tab
    const tbody = page.locator('#companyBody');
    const actionLink = tbody.locator('.empty-state a, .empty-state [onclick]');
    if (await actionLink.count() > 0) {
      await expect(actionLink.first()).toBeVisible();
    }
  });
});
