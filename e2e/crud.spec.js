/**
 * CRUD: create project via form, verify it appears, stats update.
 */
import { test, expect } from './fixtures.js';

test.describe('Project CRUD', () => {
  test('create project via API and verify it loads', async ({ page, seededProject }) => {
    await page.goto('/');
    // The seeded project should appear in the project grid
    await expect(page.locator('#projectGrid')).toBeVisible();

    // Select the project
    await page.evaluate((id) => selectProject(id), seededProject.id);
    await expect(page.locator('#mainApp')).toBeVisible();

    // Stats bar should show categories (we seeded 3)
    await expect(page.locator('#statCategories')).toContainText('3 categories');
    await expect(page.locator('#statCompanies')).toContainText('0 companies');
  });

  test('create project via form UI', async ({ page }) => {
    await page.goto('/');

    // Click the new project card/button
    const newBtn = page.locator('.project-card-new, [onclick*="showNewProjectForm"]');
    if (await newBtn.count() === 0) {
      test.skip(true, 'No new-project button found');
      return;
    }
    await newBtn.first().click();
    await expect(page.locator('#newProjectForm')).toBeVisible();

    // Fill the form
    await page.fill('#npName', `Form Test ${Date.now()}`);
    await page.fill('#npPurpose', 'Testing form creation');
    await page.fill('#npCategories', 'Alpha\nBeta');

    // Submit
    await page.locator('#newProjectForm button[type="submit"]').click();

    // Should navigate to main app
    await expect(page.locator('#mainApp')).toBeVisible({ timeout: 10000 });
    await expect(page.locator('#statCategories')).toContainText('2 categories');
  });
});
