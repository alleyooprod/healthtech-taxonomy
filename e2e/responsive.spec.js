/**
 * Responsive: tablet, mobile, desktop viewports don't overflow.
 */
import { test, expect } from './fixtures.js';

const viewports = [
  { name: 'mobile', width: 375, height: 812 },
  { name: 'tablet', width: 768, height: 1024 },
  { name: 'desktop', width: 1440, height: 900 },
  { name: 'large-desktop', width: 1920, height: 1080 },
];

test.describe('Responsive Design', () => {
  for (const vp of viewports) {
    test(`${vp.name} (${vp.width}x${vp.height}) — no horizontal overflow`, async ({ page }) => {
      await page.setViewportSize({ width: vp.width, height: vp.height });
      await page.goto('/');

      // Check for horizontal overflow
      const overflow = await page.evaluate(() => {
        return document.documentElement.scrollWidth > document.documentElement.clientWidth;
      });
      expect(overflow).toBe(false);
    });
  }

  for (const vp of viewports) {
    test(`${vp.name} — project selection renders without overflow`, async ({ page, seededProject }) => {
      await page.setViewportSize({ width: vp.width, height: vp.height });
      await page.goto('/');
      await expect(page.locator('#projectSelection')).toBeVisible();

      const overflow = await page.evaluate(() =>
        document.documentElement.scrollWidth > document.documentElement.clientWidth
      );
      expect(overflow).toBe(false);
    });
  }

  test('tablet viewport shows main app correctly', async ({ page, seededProject }) => {
    await page.setViewportSize({ width: 768, height: 1024 });
    await page.goto('/');
    await page.evaluate((id) => selectProject(id), seededProject.id);
    await expect(page.locator('#mainApp')).toBeVisible();

    // Tab bar should still be visible
    await expect(page.locator('nav.tabs')).toBeVisible();

    // All tabs should be accessible
    const tabs = page.locator('.tab');
    expect(await tabs.count()).toBeGreaterThanOrEqual(5);
  });

  test('mobile viewport shows main app', async ({ page, seededProject }) => {
    await page.setViewportSize({ width: 375, height: 812 });
    await page.goto('/');
    await page.evaluate((id) => selectProject(id), seededProject.id);
    await expect(page.locator('#mainApp')).toBeVisible();

    // On very narrow mobile, verify the app rendered and tabs are accessible
    await expect(page.locator('nav.tabs')).toBeVisible();
    const tabs = page.locator('.tab');
    expect(await tabs.count()).toBeGreaterThanOrEqual(5);
  });
});
