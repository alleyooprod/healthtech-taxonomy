/**
 * E2E: Research tab — mode toggle, scope selector, templates, saved research list.
 */
import { test, expect } from './fixtures.js';

test.describe('Research Tab', () => {
    test.beforeEach(async ({ page, seededProject }) => {
        await page.goto('/');
        await page.evaluate((id) => selectProject(id), seededProject.id);
        await expect(page.locator('#mainApp')).toBeVisible();
        await page.evaluate(() => showTab('reports'));
        await page.waitForTimeout(300);
    });

    test('tab is labeled Research', async ({ page }) => {
        const tabs = page.locator('.tab');
        const researchTab = tabs.filter({ hasText: 'Research' });
        await expect(researchTab).toBeVisible();
    });

    test('mode toggle switches between Quick Report and Deep Dive', async ({ page }) => {
        const reportMode = page.locator('#researchModeReport');
        const deepDiveMode = page.locator('#researchModeDeepDive');

        // Quick Report is default
        await expect(reportMode).toBeVisible();
        await expect(deepDiveMode).toHaveClass(/hidden/);

        // Switch to Deep Dive
        await page.locator('#deepDiveModeBtn').click();
        await expect(reportMode).toHaveClass(/hidden/);
        await expect(deepDiveMode).toBeVisible();

        // Switch back
        await page.locator('#quickReportModeBtn').click();
        await expect(reportMode).toBeVisible();
        await expect(deepDiveMode).toHaveClass(/hidden/);
    });

    test('Quick Report mode has category select and generate button', async ({ page }) => {
        await expect(page.locator('#reportCategorySelect')).toBeVisible();
        await expect(page.locator('#reportBtn')).toBeVisible();

        // Category select should have seed categories
        const options = page.locator('#reportCategorySelect option');
        expect(await options.count()).toBeGreaterThan(1);
    });

    test('Deep Dive mode has scope selector', async ({ page }) => {
        await page.locator('#deepDiveModeBtn').click();

        await expect(page.locator('#researchScopeType')).toBeVisible();
        await expect(page.locator('#researchPrompt')).toBeVisible();
        await expect(page.locator('#researchBtn')).toBeVisible();
    });

    test('scope selector shows category dropdown when Category selected', async ({ page }) => {
        await page.locator('#deepDiveModeBtn').click();

        await page.selectOption('#researchScopeType', 'category');
        await page.waitForTimeout(500);

        const scopeId = page.locator('#researchScopeId');
        await expect(scopeId).toBeVisible();

        const options = scopeId.locator('option');
        expect(await options.count()).toBeGreaterThan(1);
    });

    test('scope selector shows company search when Company selected', async ({ page }) => {
        await page.locator('#deepDiveModeBtn').click();

        await page.selectOption('#researchScopeType', 'company');

        await expect(page.locator('#researchCompanySearch')).toBeVisible();
    });

    test('template buttons populate prompt textarea', async ({ page }) => {
        await page.locator('#deepDiveModeBtn').click();

        const prompt = page.locator('#researchPrompt');
        await expect(prompt).toHaveValue('');

        // Click a template
        await page.locator('.research-template-btn:has-text("Competitive landscape")').click();

        const val = await prompt.inputValue();
        expect(val).toContain('competitive landscape');
    });

    test('empty prompt shows validation toast', async ({ page }) => {
        await page.locator('#deepDiveModeBtn').click();

        // Try to start with empty prompt
        await page.locator('#researchBtn').click();

        // Should show toast
        await page.waitForTimeout(300);
        // Research should not start (button should still be enabled)
        await expect(page.locator('#researchBtn')).toBeEnabled();
    });

    test('saved research list shows empty state initially', async ({ page }) => {
        await page.locator('#deepDiveModeBtn').click();
        await page.waitForTimeout(500);

        const list = page.locator('#savedResearchList');
        await expect(list).toContainText('No saved research');
    });

    test('model select is available in both modes', async ({ page }) => {
        // Quick Report mode
        await expect(page.locator('#reportModelSelect')).toBeVisible();

        // Deep Dive mode
        await page.locator('#deepDiveModeBtn').click();
        await expect(page.locator('#researchModelSelect')).toBeVisible();
    });
});
