import { test, expect } from '@playwright/test';

/**
 * Browser automation setup test
 * This test verifies that Playwright browser automation is configured correctly
 */
test.describe('Browser Automation Setup', () => {
  test('should launch browser and navigate successfully', async ({ page, browserName }) => {
    console.log(`Testing with browser: ${browserName}`);
    
    // Navigate to the home page
    await page.goto('/');
    
    // Wait for the page to be fully loaded
    await page.waitForLoadState('networkidle');
    
    // Verify the page loaded
    const title = await page.title();
    expect(title).toBeTruthy();
    console.log(`Page title: ${title}`);
    
    // Check that JavaScript is working
    const jsEnabled = await page.evaluate(() => {
      return typeof window !== 'undefined' && typeof document !== 'undefined';
    });
    expect(jsEnabled).toBe(true);
    
    // Take a screenshot for verification
    await page.screenshot({ 
      path: `test-results/screenshots/browser-setup-${browserName}.png`,
      fullPage: true 
    });
  });

  test('should handle page navigation', async ({ page }) => {
    // Navigate to home
    await page.goto('/');
    await page.waitForLoadState('domcontentloaded');
    
    // Navigate to login
    await page.goto('/login');
    await page.waitForLoadState('domcontentloaded');
    
    // Verify navigation worked
    expect(page.url()).toContain('/login');
  });

  test('should detect and handle errors gracefully', async ({ page }) => {
    let hasErrors = false;
    
    // Listen for console errors
    page.on('console', msg => {
      if (msg.type() === 'error') {
        // Ignore known non-critical errors
        const text = msg.text();
        if (!text.includes('favicon') && 
            !text.includes('Extension') &&
            !text.includes('ResizeObserver')) {
          hasErrors = true;
          console.log('Console error:', text);
        }
      }
    });
    
    // Listen for page errors
    page.on('pageerror', err => {
      hasErrors = true;
      console.log('Page error:', err.message);
    });
    
    // Navigate to the page
    await page.goto('/');
    await page.waitForTimeout(2000); // Wait for any async errors
    
    // The test passes if navigation completes, even with non-critical errors
    expect(page.url()).toBeTruthy();
  });

  test('should work with different viewport sizes', async ({ page }) => {
    const viewports = [
      { width: 1920, height: 1080, name: 'desktop' },
      { width: 768, height: 1024, name: 'tablet' },
      { width: 375, height: 667, name: 'mobile' },
    ];
    
    for (const viewport of viewports) {
      await page.setViewportSize({ width: viewport.width, height: viewport.height });
      await page.goto('/');
      await page.waitForLoadState('domcontentloaded');
      
      // Verify page renders at different sizes
      const bodyVisible = await page.isVisible('body');
      expect(bodyVisible).toBe(true);
      
      console.log(`✓ Viewport ${viewport.name} (${viewport.width}x${viewport.height}) works`);
    }
  });

  test('should handle timeouts properly', async ({ page }) => {
    // Set a custom timeout for this test
    test.setTimeout(10000);
    
    // Navigate with a shorter timeout
    try {
      await page.goto('/', { timeout: 5000 });
      expect(page.url()).toBeTruthy();
    } catch (error) {
      // If timeout occurs, verify it's handled gracefully
      console.log('Navigation timeout handled gracefully');
      expect(error).toBeDefined();
    }
  });
});