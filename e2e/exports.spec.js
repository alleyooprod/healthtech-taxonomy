/**
 * Export tab: links have correct hrefs, share section exists.
 */
import { test, expect } from './fixtures.js';

test.describe('Export Tab', () => {
  test.beforeEach(async ({ page, seededProject }) => {
    await page.goto('/');
    await page.evaluate((id) => selectProject(id), seededProject.id);
    await expect(page.locator('#mainApp')).toBeVisible();
    await page.evaluate(() => showTab('export'));
  });

  test('export tab renders with export cards', async ({ page }) => {
    await expect(page.locator('#tab-export')).toHaveClass(/active/);
    const cards = page.locator('.export-card');
    expect(await cards.count()).toBeGreaterThanOrEqual(4);
  });

  test('JSON export link has correct href', async ({ page }) => {
    const link = page.locator('#exportJson');
    await expect(link).toBeVisible();
    const href = await link.getAttribute('href');
    expect(href).toContain('/api/export/json');
  });

  test('Markdown export link has correct href', async ({ page }) => {
    const link = page.locator('#exportMd');
    await expect(link).toBeVisible();
    const href = await link.getAttribute('href');
    expect(href).toContain('/api/export/md');
  });

  test('CSV export link has correct href', async ({ page }) => {
    const link = page.locator('#exportCsv');
    await expect(link).toBeVisible();
    const href = await link.getAttribute('href');
    expect(href).toContain('/api/export/csv');
  });

  test('share section exists with generate button', async ({ page }) => {
    await expect(page.locator('#shareLinkLabel')).toBeVisible();
    const shareBtn = page.locator('button:has-text("Generate Link")');
    await expect(shareBtn).toBeVisible();
  });

  test('notification settings section exists', async ({ page }) => {
    await expect(page.locator('#slackWebhook')).toBeVisible();
    await expect(page.locator('#notifBatchComplete')).toBeVisible();
  });

  test('CSV import form exists', async ({ page }) => {
    await expect(page.locator('#csvFile')).toBeVisible();
  });
});
