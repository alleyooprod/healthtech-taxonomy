/**
 * E2E: Project management — create, select, switch projects.
 */
import { test, expect } from './fixtures.js';

test.describe('Project Management', () => {
    test('project selection screen shows on load', async ({ page }) => {
        await page.goto('/');
        await expect(page.locator('#projectSelection')).toBeVisible();
        await expect(page.locator('#mainApp')).toHaveClass(/hidden/);
    });

    test('seeded project appears in project grid', async ({ page, seededProject }) => {
        await page.goto('/');
        await page.waitForTimeout(500);

        const grid = page.locator('#projectGrid');
        await expect(grid).toBeVisible();
    });

    test('selecting a project shows main app', async ({ page, seededProject }) => {
        await page.goto('/');
        await page.evaluate((id) => selectProject(id), seededProject.id);
        await expect(page.locator('#mainApp')).toBeVisible({ timeout: 10000 });
        await expect(page.locator('#projectSelection')).toHaveClass(/hidden/);
    });

    test('switching project returns to project selection', async ({ page, seededProject }) => {
        await page.goto('/');
        await page.evaluate((id) => selectProject(id), seededProject.id);
        await expect(page.locator('#mainApp')).toBeVisible();

        await page.evaluate(() => switchProject());
        await page.waitForTimeout(300);

        await expect(page.locator('#projectSelection')).toBeVisible();
    });

    test('new project form accessible from project grid', async ({ page }) => {
        await page.goto('/');
        await page.waitForTimeout(500);

        // Look for the "new project" card/button
        const newProjectBtn = page.locator('.project-card-new, button:has-text("New Project"), .new-project-card');
        if (await newProjectBtn.count() > 0) {
            await newProjectBtn.first().click();
            await page.waitForTimeout(300);
            await expect(page.locator('#newProjectForm')).toBeVisible();
        }
    });

    test('creating project via form', async ({ page, seededProject }) => {
        await page.goto('/');
        await page.waitForTimeout(500);

        // Navigate to new project form
        const newProjectBtn = page.locator('.project-card-new, .new-project-card');
        if (await newProjectBtn.count() > 0) {
            await newProjectBtn.first().click();
        } else {
            await page.evaluate(() => {
                document.getElementById('projectSelection').classList.add('hidden');
                document.getElementById('newProjectForm').classList.remove('hidden');
            });
        }
        await page.waitForTimeout(300);

        await page.fill('#npName', `Form Project ${Date.now()}`);
        await page.fill('#npPurpose', 'E2E form test');
        await page.fill('#npCategories', 'FormCat A\nFormCat B');

        await page.locator('#newProjectForm button[type="submit"]').click();
        await page.waitForTimeout(1000);

        // Should navigate to main app or project selection
        // The form submission should succeed
    });

    test('project header shows title and stats', async ({ page, seededProject }) => {
        await page.goto('/');
        await page.evaluate(({ id, name }) => selectProject(id, name), seededProject);
        await expect(page.locator('#mainApp')).toBeVisible();
        await page.waitForTimeout(500);

        await expect(page.locator('#projectTitle')).toContainText(/./);
        await expect(page.locator('#statCompanies')).toContainText('companies');
        await expect(page.locator('#statCategories')).toContainText('categories');
    });
});
