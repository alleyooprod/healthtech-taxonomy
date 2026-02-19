/**
 * E2E: Market map — tile view, auto-layout view, geographic map, export.
 */
import { test, expect } from './fixtures.js';

test.describe('Market Map', () => {
    test.beforeEach(async ({ page, seededProject }) => {
        await page.goto('/');
        await page.evaluate((id) => selectProject(id), seededProject.id);
        await expect(page.locator('#mainApp')).toBeVisible();
        await page.evaluate(() => showTab('map'));
        await page.waitForTimeout(500);
    });

    test('market map view shows category columns', async ({ page }) => {
        const columns = page.locator('.map-column');
        expect(await columns.count()).toBeGreaterThanOrEqual(3);
    });

    test('three view toggle buttons exist', async ({ page }) => {
        await expect(page.locator('#marketMapBtn')).toBeVisible();
        await expect(page.locator('#autoMapBtn')).toBeVisible();
        await expect(page.locator('#geoMapBtn')).toBeVisible();
    });

    test('auto-layout view renders Cytoscape graph', async ({ page }) => {
        await page.locator('#autoMapBtn').click();
        await page.waitForTimeout(1000);

        const container = page.locator('#autoLayoutMap');
        await expect(container).toBeVisible();

        // Check that Cytoscape has initialized (canvas element inside container)
        const hasCanvas = await container.locator('canvas').count();
        expect(hasCanvas).toBeGreaterThan(0);
    });

    test('switching between views hides/shows correct containers', async ({ page }) => {
        // Start on market map
        await expect(page.locator('#marketMap')).toBeVisible();
        await expect(page.locator('#autoLayoutMap')).toHaveClass(/hidden/);
        await expect(page.locator('#geoMap')).toHaveClass(/hidden/);

        // Switch to auto-layout
        await page.locator('#autoMapBtn').click();
        await page.waitForTimeout(500);
        await expect(page.locator('#marketMap')).toHaveClass(/hidden/);
        await expect(page.locator('#autoLayoutMap')).toBeVisible();

        // Switch to geo
        await page.locator('#geoMapBtn').click();
        await page.waitForTimeout(500);
        await expect(page.locator('#autoLayoutMap')).toHaveClass(/hidden/);
        await expect(page.locator('#geoMap')).toBeVisible();

        // Back to market
        await page.locator('#marketMapBtn').click();
        await page.waitForTimeout(300);
        await expect(page.locator('#marketMap')).toBeVisible();
        await expect(page.locator('#geoMap')).toHaveClass(/hidden/);
    });

    test('export PNG button is visible', async ({ page }) => {
        await expect(page.locator('button:has-text("Export as PNG")')).toBeVisible();
    });

    test('compare bar appears when companies are on the map', async ({ page, seededProject }) => {
        // Add companies with categories
        const catId = await page.evaluate(async () => {
            const res = await fetch(`/api/taxonomy?project_id=${currentProjectId}`);
            const cats = await res.json();
            return cats.find(c => !c.parent_id)?.id;
        });

        for (const name of ['Map Co A', 'Map Co B']) {
            await page.evaluate(async ({ pid, name, catId }) => {
                await safeFetch('/api/companies/add', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        project_id: pid, name, category_id: catId,
                        url: `https://${name.toLowerCase().replace(/ /g, '')}.example.com`,
                    }),
                });
            }, { pid: seededProject.id, name, catId });
        }

        await page.evaluate(() => loadMarketMap());
        await page.waitForTimeout(500);

        // Click a tile to select for compare
        const tile = page.locator('.map-tile').first();
        if (await tile.count() > 0) {
            await tile.click();
            const bar = page.locator('#compareBar');
            await expect(bar).not.toHaveClass(/hidden/);
        }
    });
});
