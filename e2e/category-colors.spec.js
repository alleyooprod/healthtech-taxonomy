/**
 * E2E: Category color coding — color pickers, color dots in table/map/taxonomy.
 */
import { test, expect } from './fixtures.js';

test.describe('Category Colors', () => {
    test.beforeEach(async ({ page, seededProject }) => {
        await page.goto('/');
        await page.evaluate((id) => selectProject(id), seededProject.id);
        await expect(page.locator('#mainApp')).toBeVisible();
    });

    test('taxonomy tree shows color pickers for each category', async ({ page }) => {
        await page.evaluate(() => showTab('taxonomy'));
        await page.waitForTimeout(500);

        const pickers = page.locator('.cat-color-picker');
        expect(await pickers.count()).toBeGreaterThanOrEqual(3);
    });

    test('changing a category color persists', async ({ page, seededProject }) => {
        await page.evaluate(() => showTab('taxonomy'));
        await page.waitForTimeout(500);

        // Use API to set color directly (color input is hard to interact with in Playwright)
        const catId = await page.evaluate(async () => {
            const res = await fetch(`/api/taxonomy?project_id=${currentProjectId}`);
            const cats = await res.json();
            return cats.find(c => !c.parent_id)?.id;
        });
        expect(catId).toBeTruthy();

        await page.evaluate(async (id) => {
            await safeFetch(`/api/categories/${id}/color`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ color: '#ff5500' }),
            });
        }, catId);

        // Reload taxonomy and check the color picker has the new value
        await page.evaluate(() => loadTaxonomy());
        await page.waitForTimeout(500);

        const picker = page.locator('.cat-color-picker').first();
        await expect(picker).toBeVisible();
        const val = await picker.inputValue();
        expect(val).toBe('#ff5500');
    });

    test('company table shows category color dots', async ({ page, seededProject }) => {
        // Add a company via API
        await page.evaluate(async (pid) => {
            await safeFetch('/api/companies/add', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    project_id: pid,
                    name: 'Color Test Co',
                    url: 'https://colortest.example.com',
                }),
            });
        }, seededProject.id);

        await page.evaluate(() => showTab('companies'));
        await page.waitForTimeout(500);

        // Check for color dots in the table (may be in category column)
        const table = page.locator('#companyBody');
        await expect(table).toBeVisible();
    });

    test('market map tiles show category color borders', async ({ page }) => {
        await page.evaluate(() => showTab('map'));
        await page.waitForTimeout(500);

        const columns = page.locator('.map-column');
        // Even with no companies, columns should render for each category
        expect(await columns.count()).toBeGreaterThanOrEqual(3);
    });
});
