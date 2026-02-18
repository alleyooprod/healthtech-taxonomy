/**
 * Filters: search input, starred filter, category filter, active filter chips.
 */
import { test, expect } from './fixtures.js';

test.describe('Filters', () => {
  test.beforeEach(async ({ page, seededProject }) => {
    await page.goto('/');
    await page.evaluate((id) => selectProject(id), seededProject.id);
    await expect(page.locator('#mainApp')).toBeVisible();
  });

  test('search input accepts text', async ({ page }) => {
    const input = page.locator('#searchInput');
    await expect(input).toBeVisible();
    await input.fill('test search');
    await expect(input).toHaveValue('test search');
  });

  test('starred filter checkbox is present', async ({ page }) => {
    const checkbox = page.locator('#starredFilter');
    await expect(checkbox).toBeVisible();
    await expect(checkbox).not.toBeChecked();

    // Toggle it
    await checkbox.check();
    await expect(checkbox).toBeChecked();
  });

  test('category filter dropdown is present', async ({ page }) => {
    const select = page.locator('#categoryFilter');
    await expect(select).toBeVisible();
    // Should have at least the default option
    const options = select.locator('option');
    expect(await options.count()).toBeGreaterThanOrEqual(1);
  });

  test('enrichment filter checkbox works', async ({ page }) => {
    const checkbox = page.locator('#enrichmentFilter');
    await expect(checkbox).toBeVisible();
    await checkbox.check();
    await expect(checkbox).toBeChecked();
  });

  test('relationship filter dropdown has options', async ({ page }) => {
    const select = page.locator('#relationshipFilter');
    await expect(select).toBeVisible();
    const options = select.locator('option');
    // Should have default + at least a few relationship types
    expect(await options.count()).toBeGreaterThan(2);
  });
});
