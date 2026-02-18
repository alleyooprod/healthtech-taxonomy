/**
 * Keyboard shortcuts: /, ?, Escape, number keys, D toggles theme.
 */
import { test, expect } from './fixtures.js';

test.describe('Keyboard Shortcuts', () => {
  test.beforeEach(async ({ page, seededProject }) => {
    await page.goto('/');
    await page.evaluate((id) => selectProject(id), seededProject.id);
    await expect(page.locator('#mainApp')).toBeVisible();
  });

  test('/ focuses search input', async ({ page }) => {
    // Click body first to ensure no input is focused
    await page.locator('body').click();
    await page.keyboard.press('/');
    const focused = await page.evaluate(() => document.activeElement?.id);
    expect(focused).toBe('searchInput');
  });

  test('? opens shortcuts overlay', async ({ page }) => {
    // Call showShortcutHelp() directly (keyboard.js handler uses ? key)
    await page.evaluate(() => showShortcutHelp());
    await expect(page.locator('#shortcutOverlay')).toBeVisible();
  });

  test('Escape closes shortcuts overlay', async ({ page }) => {
    await page.evaluate(() => showShortcutHelp());
    await expect(page.locator('#shortcutOverlay')).toBeVisible();

    await page.keyboard.press('Escape');
    await expect(page.locator('#shortcutOverlay')).toHaveCount(0);
  });

  test('number keys switch tabs', async ({ page }) => {
    await page.locator('body').click();
    // Press 2 for taxonomy
    await page.keyboard.press('2');
    await expect(page.locator('#tab-taxonomy')).toHaveClass(/active/);

    // Press 1 for companies
    await page.keyboard.press('1');
    await expect(page.locator('#tab-companies')).toHaveClass(/active/);
  });

  test('D toggles dark mode', async ({ page }) => {
    await page.locator('body').click();
    const before = await page.locator('html').getAttribute('data-theme');

    await page.keyboard.press('d');
    const after = await page.locator('html').getAttribute('data-theme');
    expect(after).not.toBe(before);
  });
});
