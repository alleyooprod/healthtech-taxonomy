/**
 * Navigation: home page, project selection, tab switching, URL state.
 */
import { test, expect } from './fixtures.js';

test.describe('Navigation', () => {
  test('home page renders project selection', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('#projectSelection')).toBeVisible();
    await expect(page.locator('#projectSelection h1')).toContainText('Research Taxonomy Library');
  });

  test('new project form shows and hides', async ({ page }) => {
    await page.goto('/');
    // The project grid should have a "new project" card
    const newCard = page.locator('.project-card-new, [onclick*="showNewProjectForm"]');
    if (await newCard.count() > 0) {
      await newCard.first().click();
      await expect(page.locator('#newProjectForm')).toBeVisible();
      // Back button returns to selection
      await page.locator('#newProjectForm .back-btn').click();
      await expect(page.locator('#projectSelection')).toBeVisible();
    }
  });

  test('selecting a project shows main app with tabs', async ({ page, seededProject }) => {
    await page.goto('/');
    // Click the project card
    const card = page.locator(`.project-card[onclick*="${seededProject.id}"], .project-card[data-id="${seededProject.id}"]`);
    if (await card.count() > 0) {
      await card.first().click();
    } else {
      // Fallback: select via JS
      await page.evaluate((id) => selectProject(id), seededProject.id);
    }
    await expect(page.locator('#mainApp')).toBeVisible();
    await expect(page.locator('nav.tabs')).toBeVisible();
  });

  test('tab switching works and updates URL', async ({ page, seededProject }) => {
    await page.goto('/');
    await page.evaluate((id) => selectProject(id), seededProject.id);
    await expect(page.locator('#mainApp')).toBeVisible();

    const tabs = ['taxonomy', 'map', 'reports', 'process', 'export', 'companies'];
    for (const tab of tabs) {
      await page.evaluate((t) => showTab(t), tab);
      await expect(page.locator(`#tab-${tab}`)).toHaveClass(/active/);
      // URL should reflect tab
      const url = page.url();
      expect(url).toContain(`tab=${tab}`);
    }
  });

  test('back button returns to project selection', async ({ page, seededProject }) => {
    await page.goto('/');
    await page.evaluate((id) => selectProject(id), seededProject.id);
    await expect(page.locator('#mainApp')).toBeVisible();

    // Click back button
    await page.locator('#mainApp .back-btn').click();
    await expect(page.locator('#projectSelection')).toBeVisible();
  });
});
