/**
 * Dark mode: toggle changes data-theme, persists via localStorage, correct CSS vars.
 */
import { test, expect } from './fixtures.js';

test.describe('Dark Mode', () => {
  test('toggle sets data-theme attribute', async ({ page }) => {
    await page.goto('/');

    // Default state — should be light (empty or "light")
    const initial = await page.locator('html').getAttribute('data-theme');
    expect(initial === '' || initial === 'light' || initial === null).toBeTruthy();

    // Click theme toggle
    await page.locator('.theme-toggle').first().click();
    await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark');

    // Toggle back
    await page.locator('.theme-toggle').first().click();
    const after = await page.locator('html').getAttribute('data-theme');
    expect(after === 'light').toBeTruthy();
  });

  test('theme persists in localStorage', async ({ page }) => {
    await page.goto('/');

    await page.locator('.theme-toggle').first().click();
    const stored = await page.evaluate(() => localStorage.getItem('theme'));
    expect(stored).toBe('dark');

    // Reload page — theme should persist
    await page.reload();
    await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark');
  });

  test('dark mode has different background color', async ({ page }) => {
    await page.goto('/');

    const lightBg = await page.evaluate(() =>
      getComputedStyle(document.documentElement).getPropertyValue('--bg-page').trim()
    );

    await page.locator('.theme-toggle').first().click();
    await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark');

    const darkBg = await page.evaluate(() =>
      getComputedStyle(document.documentElement).getPropertyValue('--bg-page').trim()
    );

    expect(lightBg).not.toBe(darkBg);
  });

  test('dark mode borders are visible (not same as background)', async ({ page }) => {
    await page.goto('/');
    await page.locator('.theme-toggle').first().click();
    await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark');

    const [bg, border] = await page.evaluate(() => {
      const style = getComputedStyle(document.documentElement);
      return [
        style.getPropertyValue('--bg-container').trim(),
        style.getPropertyValue('--border-default').trim(),
      ];
    });

    expect(bg).not.toBe(border);
  });
});
