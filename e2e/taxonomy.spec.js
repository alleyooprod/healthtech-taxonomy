/**
 * E2E: Taxonomy tab — tree view, graph view, analytics, quality, history.
 */
import { test, expect } from './fixtures.js';

test.describe('Taxonomy Tab', () => {
    test.beforeEach(async ({ page, seededProject }) => {
        await page.goto('/');
        await page.evaluate((id) => selectProject(id), seededProject.id);
        await expect(page.locator('#mainApp')).toBeVisible();
        await page.evaluate(() => showTab('taxonomy'));
        await page.waitForTimeout(500);
    });

    test('taxonomy tab loads with tree view active', async ({ page }) => {
        await expect(page.locator('#tab-taxonomy')).toHaveClass(/active/);
        await expect(page.locator('#treeViewBtn')).toHaveClass(/active/);
    });

    test('taxonomy tree shows seed categories', async ({ page }) => {
        const tree = page.locator('#taxonomyTree');
        await expect(tree).toBeVisible();

        // Should have the 3 seed categories (Alpha, Beta, Gamma)
        const catHeaders = page.locator('.cat-header');
        expect(await catHeaders.count()).toBeGreaterThanOrEqual(3);
    });

    test('switching to graph view shows Cytoscape', async ({ page }) => {
        await page.locator('#graphViewBtn').click();
        await page.waitForTimeout(1000);

        const graph = page.locator('#taxonomyGraph');
        await expect(graph).not.toHaveClass(/hidden/);

        // Should have a canvas (Cytoscape renders to canvas)
        const canvasCount = await graph.locator('canvas').count();
        expect(canvasCount).toBeGreaterThan(0);
    });

    test('analytics dashboard section exists', async ({ page }) => {
        const dashboard = page.locator('.analytics-dashboard');
        await expect(dashboard).toBeVisible();
    });

    test('collapsible sections toggle', async ({ page }) => {
        const analyticsBody = page.locator('#analyticsSection');
        await expect(analyticsBody).toBeVisible();

        // Click to collapse
        await page.locator('.collapsible-header').first().click();
        await page.waitForTimeout(400);

        // Should have collapsed class
        await expect(analyticsBody).toHaveClass(/collapsed/);

        // Click to expand
        await page.locator('.collapsible-header').first().click();
        await page.waitForTimeout(400);

        await expect(analyticsBody).not.toHaveClass(/collapsed/);
    });

    test('taxonomy review section has textarea and button', async ({ page }) => {
        await expect(page.locator('#reviewObservations')).toBeVisible();
        await expect(page.locator('#reviewBtn')).toBeVisible();
    });

    test('quality dashboard has refresh button', async ({ page }) => {
        const qualityBtn = page.locator('button:has-text("Refresh Quality Metrics")');
        await expect(qualityBtn).toBeVisible();
    });
});
