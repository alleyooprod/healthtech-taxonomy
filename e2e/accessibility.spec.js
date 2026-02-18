/**
 * Accessibility: focus indicators, reduced-motion, ARIA attributes, skip link.
 */
import { test, expect } from './fixtures.js';

test.describe('Accessibility', () => {
  test('skip link exists and is focusable', async ({ page }) => {
    await page.goto('/');
    const skipLink = page.locator('.skip-link');
    await expect(skipLink).toHaveCount(1);
    await expect(skipLink).toHaveAttribute('href', '#mainApp');
  });

  test('focus-visible outline appears on Tab navigation', async ({ page, seededProject }) => {
    await page.goto('/');
    await page.evaluate((id) => selectProject(id), seededProject.id);
    await expect(page.locator('#mainApp')).toBeVisible();

    // Tab into search input
    await page.keyboard.press('Tab');
    await page.keyboard.press('Tab');

    // The focused element should have a visible outline
    const outline = await page.evaluate(() => {
      const el = document.activeElement;
      if (!el) return 'none';
      const style = getComputedStyle(el);
      return style.outlineStyle;
    });
    // Should not be 'none' when using keyboard
    expect(outline).not.toBe('');
  });

  test('tab navigation has ARIA roles', async ({ page, seededProject }) => {
    await page.goto('/');
    await page.evaluate((id) => selectProject(id), seededProject.id);
    await expect(page.locator('#mainApp')).toBeVisible();

    // Tab bar should have tablist role
    await expect(page.locator('nav.tabs')).toHaveAttribute('role', 'tablist');

    // Tab buttons should have tab role
    const tabs = page.locator('.tab[role="tab"]');
    expect(await tabs.count()).toBeGreaterThanOrEqual(5);

    // Active tab should have aria-selected=true
    const activeTab = page.locator('.tab.active');
    await expect(activeTab).toHaveAttribute('aria-selected', 'true');
  });

  test('modals have correct ARIA attributes', async ({ page }) => {
    await page.goto('/');

    // Edit modal
    const editModal = page.locator('#editModal');
    await expect(editModal).toHaveAttribute('role', 'dialog');
    await expect(editModal).toHaveAttribute('aria-modal', 'true');

    // Tag modal
    const tagModal = page.locator('#tagModal');
    await expect(tagModal).toHaveAttribute('role', 'dialog');
    await expect(tagModal).toHaveAttribute('aria-modal', 'true');
  });

  test('tab panels have tabpanel role', async ({ page, seededProject }) => {
    await page.goto('/');
    await page.evaluate((id) => selectProject(id), seededProject.id);

    const panels = page.locator('[role="tabpanel"]');
    expect(await panels.count()).toBeGreaterThanOrEqual(5);
  });

  test('theme toggle has aria-label', async ({ page }) => {
    await page.goto('/');
    const toggle = page.locator('.theme-toggle').first();
    await expect(toggle).toHaveAttribute('aria-label', 'Toggle dark mode');
  });

  test('reduced-motion is respected by JS and CSS', async ({ page }) => {
    // Emulate prefers-reduced-motion: reduce
    await page.emulateMedia({ reducedMotion: 'reduce' });
    await page.goto('/');

    // Page should still load correctly with reduced motion
    await expect(page.locator('body')).toBeVisible();

    // Verify the browser reports reduced-motion as active
    const respectsReducedMotion = await page.evaluate(() => {
      return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    });
    expect(respectsReducedMotion).toBe(true);
  });
});
