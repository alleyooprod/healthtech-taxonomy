/**
 * Processing tab: renders correctly, URL textarea visible, batch list.
 */
import { test, expect } from './fixtures.js';

test.describe('Processing Tab', () => {
  test.beforeEach(async ({ page, seededProject }) => {
    await page.goto('/');
    await page.evaluate((id) => selectProject(id), seededProject.id);
    await expect(page.locator('#mainApp')).toBeVisible();
    await page.evaluate(() => showTab('process'));
  });

  test('process tab renders with URL input', async ({ page }) => {
    await expect(page.locator('#tab-process')).toHaveClass(/active/);
    await expect(page.locator('#urlInput')).toBeVisible();
  });

  test('URL textarea accepts input', async ({ page }) => {
    const textarea = page.locator('#urlInput');
    await textarea.fill('https://example.com\nhttps://test.com');
    await expect(textarea).toHaveValue('https://example.com\nhttps://test.com');
  });

  test('model select and worker count are present', async ({ page }) => {
    await expect(page.locator('#modelSelect')).toBeVisible();
    await expect(page.locator('#workerCount')).toBeVisible();
  });

  test('batch list shows empty state', async ({ page }) => {
    const batchList = page.locator('#batchList');
    await expect(batchList).toBeVisible();
    // Should show the styled empty state
    await expect(batchList.locator('.empty-state, p')).toBeVisible();
  });

  test('AI discovery section is present', async ({ page }) => {
    await expect(page.locator('#discoveryQuery')).toBeVisible();
    await expect(page.locator('#discoveryBtn')).toBeVisible();
  });

  test('triage section is initially hidden', async ({ page }) => {
    await expect(page.locator('#triageSection')).toHaveClass(/hidden/);
  });
});
