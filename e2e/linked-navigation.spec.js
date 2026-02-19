/**
 * E2E: Linked record navigation — breadcrumbs, category detail, entity links.
 */
import { test, expect } from './fixtures.js';

test.describe('Linked Navigation', () => {
    test.beforeEach(async ({ page, seededProject }) => {
        await page.goto('/');
        await page.evaluate((id) => selectProject(id), seededProject.id);
        await expect(page.locator('#mainApp')).toBeVisible();
    });

    test('breadcrumb bar is hidden by default', async ({ page }) => {
        const bar = page.locator('#breadcrumbBar');
        await expect(bar).toHaveClass(/hidden/);
    });

    test('navigating to a category shows breadcrumbs', async ({ page }) => {
        // Get a category ID
        const catId = await page.evaluate(async () => {
            const res = await fetch(`/api/taxonomy?project_id=${currentProjectId}`);
            const cats = await res.json();
            return cats.find(c => !c.parent_id)?.id;
        });
        expect(catId).toBeTruthy();

        // Navigate to category
        await page.evaluate((id) => {
            navigateTo('category', id, 'Test Category');
        }, catId);
        await page.waitForTimeout(300);

        const bar = page.locator('#breadcrumbBar');
        await expect(bar).not.toHaveClass(/hidden/);
        await expect(bar).toContainText('Test Category');
    });

    test('category detail view shows category info', async ({ page }) => {
        await page.evaluate(() => showTab('taxonomy'));
        await page.waitForTimeout(500);

        // Get a category and navigate to its detail
        const catId = await page.evaluate(async () => {
            const res = await fetch(`/api/taxonomy?project_id=${currentProjectId}`);
            const cats = await res.json();
            return cats.find(c => !c.parent_id)?.id;
        });

        await page.evaluate((id) => {
            if (typeof showCategoryDetail === 'function') showCategoryDetail(id);
        }, catId);
        await page.waitForTimeout(300);

        const detailPanel = page.locator('#detailPanel');
        await expect(detailPanel).not.toHaveClass(/hidden/);
    });

    test('clickable category links in company table', async ({ page, seededProject }) => {
        // Add a company with a category
        const catId = await page.evaluate(async () => {
            const res = await fetch(`/api/taxonomy?project_id=${currentProjectId}`);
            const cats = await res.json();
            return cats.find(c => !c.parent_id)?.id;
        });

        await page.evaluate(async ({ pid, catId }) => {
            await safeFetch('/api/companies/add', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    project_id: pid,
                    name: 'Nav Test Co',
                    url: 'https://navtest.example.com',
                    category_id: catId,
                }),
            });
        }, { pid: seededProject.id, catId });

        await page.evaluate(() => showTab('companies'));
        await page.waitForTimeout(500);

        // Check for clickable category links
        const catLinks = page.locator('.cat-link');
        expect(await catLinks.count()).toBeGreaterThanOrEqual(1);
    });
});
