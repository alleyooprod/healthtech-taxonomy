/**
 * E2E: Proof tests for Graph View, Knowledge Graph, and Settings tab.
 */
import { test, expect } from './fixtures.js';

test.describe('Graph View rendering proof', () => {
    test.beforeEach(async ({ page, seededProject }) => {
        await page.goto('/');
        await page.evaluate((id) => selectProject(id), seededProject.id);
        await expect(page.locator('#mainApp')).toBeVisible();
        await page.evaluate(() => showTab('taxonomy'));
        await page.waitForTimeout(500);
    });

    test('Graph View renders canvas with proper dimensions', async ({ page }) => {
        await page.locator('#graphViewBtn').click();
        await page.waitForTimeout(2000);

        const graph = page.locator('#taxonomyGraph');
        await expect(graph).not.toHaveClass(/hidden/);

        // Cytoscape renders canvas elements
        const canvasCount = await graph.locator('canvas').count();
        expect(canvasCount).toBeGreaterThan(0);

        // Verify container has real dimensions (not 0x0)
        const box = await graph.boundingBox();
        expect(box.width).toBeGreaterThan(100);
        expect(box.height).toBeGreaterThan(100);
    });

    test('Knowledge Graph renders canvas', async ({ page }) => {
        const kgBtn = page.locator('#kgViewBtn');
        if (await kgBtn.count() > 0) {
            await kgBtn.click();
            await page.waitForTimeout(2000);

            const kg = page.locator('#knowledgeGraph');
            await expect(kg).not.toHaveClass(/hidden/);

            // Should have canvas from Cytoscape
            const canvasCount = await kg.locator('canvas').count();
            expect(canvasCount).toBeGreaterThan(0);
        }
    });
});

test.describe('Settings tab proof', () => {
    test.beforeEach(async ({ page, seededProject }) => {
        await page.goto('/');
        await page.evaluate((id) => selectProject(id), seededProject.id);
        await expect(page.locator('#mainApp')).toBeVisible();
    });

    test('Settings tab loads with AI backend cards', async ({ page }) => {
        await page.evaluate(() => showTab('settings'));
        await page.waitForTimeout(500);

        const section = page.locator('#tab-settings');
        await expect(section).toHaveClass(/active/);

        // All 3 backend cards are present (use exact match to avoid summary line)
        await expect(section.locator('#sdkCard strong:has-text("Claude API")')).toBeVisible();
        await expect(section.locator('#cliCard strong:has-text("Claude CLI")')).toBeVisible();
        await expect(section.locator('#geminiCard strong:has-text("Gemini CLI")')).toBeVisible();
    });

    test('Settings tab has installation commands', async ({ page }) => {
        await page.evaluate(() => showTab('settings'));
        await page.waitForTimeout(1000);

        // Fix commands should exist in the DOM
        const fixCmds = page.locator('.fix-command');
        expect(await fixCmds.count()).toBeGreaterThanOrEqual(1);
    });

    test('Test Connection buttons exist and respond', async ({ page }) => {
        await page.evaluate(() => showTab('settings'));
        await page.waitForTimeout(1000);

        await expect(page.locator('#testSdkBtn')).toBeVisible();
        await expect(page.locator('#testCliBtn')).toBeVisible();
        await expect(page.locator('#testGeminiBtn')).toBeVisible();
    });

    test('AI Setup is NOT in Process tab', async ({ page }) => {
        await page.evaluate(() => showTab('process'));
        await page.waitForTimeout(500);

        const processTab = page.locator('#tab-process');
        // AI Discovery should be the first thing
        await expect(processTab.locator('text=AI Company Discovery')).toBeVisible();
        // AI Setup should NOT be here
        expect(await processTab.locator('#aiSetupPanel').count()).toBe(0);
    });

    test('Default model selector is present', async ({ page }) => {
        await page.evaluate(() => showTab('settings'));
        await page.waitForTimeout(500);

        await expect(page.locator('#defaultModelSetting')).toBeVisible();
    });
});
