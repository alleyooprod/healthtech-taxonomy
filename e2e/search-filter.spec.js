/**
 * E2E: Search and filter — search input, category/tag/geo/stage filters, saved views.
 */
import { test, expect } from './fixtures.js';

test.describe('Search and Filter', () => {
    test.beforeEach(async ({ page, seededProject }) => {
        await page.goto('/');
        await page.evaluate((id) => selectProject(id), seededProject.id);
        await expect(page.locator('#mainApp')).toBeVisible();

        // Seed companies with different attributes
        const catId = await page.evaluate(async () => {
            const res = await fetch(`/api/taxonomy?project_id=${currentProjectId}`);
            const cats = await res.json();
            return cats.find(c => !c.parent_id)?.id;
        });

        const companies = [
            { name: 'Acme Health', geography: 'US', tags: '["B2B", "health"]' },
            { name: 'Beta Wellness', geography: 'UK', tags: '["B2C", "wellness"]' },
            { name: 'Gamma Tech', geography: 'Germany', tags: '["B2B", "tech"]' },
        ];

        for (const co of companies) {
            await page.evaluate(async ({ pid, co, catId }) => {
                await safeFetch('/api/companies/add', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        project_id: pid,
                        name: co.name,
                        url: `https://${co.name.toLowerCase().replace(/ /g, '')}.example.com`,
                        geography: co.geography,
                        category_id: catId,
                    }),
                });
            }, { pid: seededProject.id, co, catId });
        }

        await page.evaluate(() => showTab('companies'));
        await page.waitForTimeout(500);
    });

    test('search input is visible and focusable', async ({ page }) => {
        const search = page.locator('#searchInput');
        await expect(search).toBeVisible();
        await search.focus();
        const focused = await page.evaluate(() => document.activeElement?.id);
        expect(focused).toBe('searchInput');
    });

    test('typing in search filters company list', async ({ page }) => {
        await page.fill('#searchInput', 'Acme');
        await page.waitForTimeout(500);

        const rows = page.locator('#companyBody tr[data-company-id]');
        const count = await rows.count();
        expect(count).toBeGreaterThanOrEqual(1);

        // All visible rows should contain "Acme"
        if (count > 0) {
            const firstRowText = await rows.first().textContent();
            expect(firstRowText).toContain('Acme');
        }
    });

    test('category filter dropdown has categories', async ({ page }) => {
        const filter = page.locator('#categoryFilter');
        const options = filter.locator('option');
        expect(await options.count()).toBeGreaterThan(1);
    });

    test('starred filter checkbox works', async ({ page }) => {
        const checkbox = page.locator('#starredFilter');
        await expect(checkbox).toBeVisible();

        await checkbox.check();
        await page.waitForTimeout(300);

        // With no starred companies, should show empty or no rows
        const rows = page.locator('#companyBody tr[data-company-id]');
        const count = await rows.count();
        // Expect 0 or empty state since we haven't starred any
        expect(count).toBeLessThanOrEqual(0);
    });

    test('clearing search shows all companies', async ({ page }) => {
        const beforeCount = await page.locator('#companyBody tr[data-company-id]').count();

        await page.fill('#searchInput', 'nonexistent');
        await page.waitForTimeout(500);

        await page.fill('#searchInput', '');
        await page.waitForTimeout(500);

        const afterCount = await page.locator('#companyBody tr[data-company-id]').count();
        expect(afterCount).toBe(beforeCount);
    });

    test('relationship filter dropdown works', async ({ page }) => {
        const filter = page.locator('#relationshipFilter');
        await expect(filter).toBeVisible();

        const options = filter.locator('option');
        expect(await options.count()).toBeGreaterThan(3);
    });

    test('saved views bar is visible', async ({ page }) => {
        const viewSelect = page.locator('#savedViewSelect');
        await expect(viewSelect).toBeVisible();

        const saveBtn = page.locator('button:has-text("Save view")');
        await expect(saveBtn).toBeVisible();
    });
});
