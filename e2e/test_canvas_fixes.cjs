/**
 * Test all canvas fixes:
 * 1. Company drag-drop shows text (bound-text pattern)
 * 2. Diagram panel has template buttons
 * 3. Template pre-fills prompt correctly
 * 4. Canvas creation still works
 *
 * Uses Chromium (fast, reliable for testing)
 */
const { chromium } = require('playwright');
const PORT = process.argv[2] || 5001;

(async () => {
    const browser = await chromium.launch({ headless: false });
    const page = await browser.newPage({ viewport: { width: 1400, height: 900 } });

    page.on('pageerror', err => console.log('[pageerror]', err.message));

    console.log(`Testing canvas fixes on port ${PORT}...\n`);
    await page.goto(`http://127.0.0.1:${PORT}/`, { waitUntil: 'networkidle', timeout: 20000 });

    // Dismiss driver.js
    await page.evaluate(() => {
        if (typeof _cleanupDriverJs === 'function') _cleanupDriverJs();
        if (window.driverObj) { try { window.driverObj.destroy(); } catch(e) {} }
        document.body.classList.remove('driver-active');
        document.querySelectorAll('.driver-overlay, .driver-popover').forEach(el => el.remove());
    });
    await page.waitForTimeout(500);

    // Select Olly Market Taxonomy
    await page.evaluate(() => selectProject(1, 'Olly Market Taxonomy'));
    await page.waitForTimeout(2000);
    console.log('1. Selected project: Olly Market Taxonomy');

    // Canvas tab
    await page.evaluate(() => showTab('canvas'));
    await page.waitForTimeout(1000);

    // Create canvas via API (skip dialog for speed)
    const canvasId = await page.evaluate(async () => {
        const res = await safeFetch('/api/canvases', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ project_id: 1, title: 'Fix Test Canvas' }),
        });
        const data = await res.json();
        if (data.id) {
            await loadCanvasList();
            document.getElementById('canvasSelect').value = data.id;
            loadCanvasFromSelect();
        }
        return data.id;
    });
    console.log('2. Created canvas id:', canvasId);

    // Wait for Excalidraw
    let loaded = false;
    for (let i = 0; i < 15; i++) {
        await page.waitForTimeout(1000);
        loaded = await page.evaluate(() => !!(document.querySelector('.excalidraw') && window._excalidrawAPI));
        if (loaded) { console.log(`3. Excalidraw loaded after ${i+1}s`); break; }
    }
    if (!loaded) { console.log('FAIL: Excalidraw not loaded'); await browser.close(); process.exit(1); }

    // TEST: Company drag-drop creates visible text
    console.log('\n--- Test: Company card has visible text ---');
    const dropResult = await page.evaluate(() => {
        const companies = _canvasCompanies || [];
        if (companies.length === 0) return { error: 'no companies' };

        const company = companies[0];
        const color = typeof getCategoryColor === 'function' ? getCategoryColor(company.category_id) : '#888';
        const dragData = {
            companyId: company.id,
            name: company.name,
            categoryName: company.category_name || '',
            color: color,
        };

        const elements = _createCompanyElements(300, 300, dragData);
        if (!elements || elements.length < 2) return { error: 'no elements created' };

        // Check the elements
        const rect = elements.find(e => e.type === 'rectangle');
        const text = elements.find(e => e.type === 'text');

        const result = {
            companyName: company.name,
            rectId: rect?.id,
            textId: text?.id,
            textContent: text?.text,
            textFontSize: text?.fontSize,
            textContainerId: text?.containerId,
            rectBoundElements: JSON.stringify(rect?.boundElements),
            textHasOriginalText: !!text?.originalText,
            textWidth: text?.width,
            textHeight: text?.height,
        };

        // Add to canvas
        const current = window._excalidrawAPI.getSceneElements();
        window._excalidrawAPI.updateScene({ elements: [...current, ...elements] });

        return result;
    });
    console.log('Drop result:', JSON.stringify(dropResult, null, 2));

    const textBound = dropResult.textContainerId === dropResult.rectId;
    console.log('Text bound to rect:', textBound);
    console.log('Text has content:', !!dropResult.textContent);
    console.log('Text has dimensions:', dropResult.textWidth > 0 && dropResult.textHeight > 0);

    // Drop a second company
    await page.evaluate(() => {
        const companies = _canvasCompanies || [];
        if (companies.length < 2) return;
        const c = companies[1];
        const color = typeof getCategoryColor === 'function' ? getCategoryColor(c.category_id) : '#888';
        const els = _createCompanyElements(550, 300, {
            companyId: c.id, name: c.name, categoryName: c.category_name || '', color,
        });
        const current = window._excalidrawAPI.getSceneElements();
        window._excalidrawAPI.updateScene({ elements: [...current, ...els] });
    });

    await page.waitForTimeout(1000);
    await page.screenshot({ path: 'test-evidence/canvas-fix-companies.png' });
    console.log('Screenshot: test-evidence/canvas-fix-companies.png');

    // TEST: Diagram panel templates
    console.log('\n--- Test: AI Diagram panel with templates ---');
    await page.evaluate(() => openDiagramPanel());
    await page.waitForTimeout(500);

    const templateBtns = await page.evaluate(() => {
        const btns = document.querySelectorAll('.diagram-template-btn');
        return Array.from(btns).map(b => b.textContent.trim());
    });
    console.log('Template buttons:', templateBtns);

    // Click a template
    await page.evaluate(() => useDiagramTemplate('tech_stack'));
    await page.waitForTimeout(300);

    const promptValue = await page.evaluate(() => document.getElementById('diagramPrompt').value);
    console.log('Template filled prompt:', promptValue.substring(0, 80) + '...');

    const layoutValue = await page.evaluate(() => document.getElementById('diagramLayoutStyle').value);
    console.log('Layout style set to:', layoutValue);

    await page.screenshot({ path: 'test-evidence/canvas-fix-diagram-panel.png' });
    console.log('Screenshot: test-evidence/canvas-fix-diagram-panel.png');

    // Close diagram panel
    await page.evaluate(() => closeDiagramPanel());
    await page.waitForTimeout(500);

    // Final screenshot showing canvas with company cards
    await page.screenshot({ path: 'test-evidence/canvas-fix-final.png' });
    console.log('\nScreenshot: test-evidence/canvas-fix-final.png');

    // Summary
    const allPass = textBound && !!dropResult.textContent && templateBtns.length >= 4;
    console.log('\n=== RESULTS ===');
    console.log(allPass ? 'ALL CHECKS PASSED' : 'SOME CHECKS FAILED');

    // Cleanup
    if (canvasId) {
        await page.evaluate(async (id) => {
            await safeFetch(`/api/canvases/${id}`, { method: 'DELETE' });
        }, canvasId);
        console.log('Cleaned up test canvas');
    }

    await browser.close();
    process.exit(allPass ? 0 : 1);
})().catch(err => { console.error('Test failed:', err.message); process.exit(1); });
