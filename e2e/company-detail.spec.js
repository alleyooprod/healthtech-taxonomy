/**
 * E2E: Company detail panel — edit, star, notes, relationships, deep dive button.
 */
import { test, expect } from './fixtures.js';

test.describe('Company Detail', () => {
    let companyId;

    test.beforeEach(async ({ page, seededProject }) => {
        await page.goto('/');
        await page.evaluate((id) => selectProject(id), seededProject.id);
        await expect(page.locator('#mainApp')).toBeVisible();

        // Get a category
        const catId = await page.evaluate(async () => {
            const res = await fetch(`/api/taxonomy?project_id=${currentProjectId}`);
            const cats = await res.json();
            return cats.find(c => !c.parent_id)?.id;
        });

        // Create a test company
        companyId = await page.evaluate(async ({ pid, catId }) => {
            const res = await safeFetch('/api/companies/add', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    project_id: pid,
                    name: 'Detail Test Co',
                    url: 'https://detailtest.example.com',
                    what: 'A company for testing detail panel',
                    category_id: catId,
                }),
            });
            const data = await res.json();
            return data.id;
        }, { pid: seededProject.id, catId });

        await page.evaluate(() => showTab('companies'));
        await page.waitForTimeout(500);
    });

    test('clicking company row opens detail panel', async ({ page }) => {
        const row = page.locator(`#companyBody tr`).first();
        await row.click();
        await page.waitForTimeout(300);

        const panel = page.locator('#detailPanel');
        await expect(panel).not.toHaveClass(/hidden/);
    });

    test('detail panel shows company info', async ({ page }) => {
        await page.evaluate((id) => showDetail(id), companyId);
        await page.waitForTimeout(500);

        await expect(page.locator('#detailName')).toContainText('Detail Test Co');
        await expect(page.locator('#detailContent')).toContainText('A company for testing');
    });

    test('detail panel has Deep Dive button', async ({ page }) => {
        await page.evaluate((id) => showDetail(id), companyId);
        await page.waitForTimeout(500);

        const deepDiveBtn = page.locator('.detail-actions button:has-text("Deep Dive")');
        await expect(deepDiveBtn).toBeVisible();
    });

    test('detail panel has action buttons', async ({ page }) => {
        await page.evaluate((id) => showDetail(id), companyId);
        await page.waitForTimeout(500);

        const actions = page.locator('.detail-actions');
        await expect(actions.locator('button:has-text("Edit")')).toBeVisible();
        await expect(actions.locator('button:has-text("Re-research")')).toBeVisible();
        await expect(actions.locator('button:has-text("Find Similar")')).toBeVisible();
        await expect(actions.locator('button:has-text("History")')).toBeVisible();
        await expect(actions.locator('button:has-text("Delete")')).toBeVisible();
    });

    test('close button hides detail panel', async ({ page }) => {
        await page.evaluate((id) => showDetail(id), companyId);
        await page.waitForTimeout(300);

        await page.locator('#detailPanel .close-btn').click();
        await page.waitForTimeout(300);

        await expect(page.locator('#detailPanel')).toHaveClass(/hidden/);
    });

    test('Deep Dive button navigates to research tab', async ({ page }) => {
        await page.evaluate((id) => showDetail(id), companyId);
        await page.waitForTimeout(500);

        await page.locator('.detail-actions button:has-text("Deep Dive")').click();
        await page.waitForTimeout(500);

        // Should be on research tab in deep dive mode
        await expect(page.locator('#tab-reports')).toHaveClass(/active/);
        await expect(page.locator('#researchModeDeepDive')).toBeVisible();
        await expect(page.locator('#researchCompanySearch')).toHaveValue('Detail Test Co');
    });
});
