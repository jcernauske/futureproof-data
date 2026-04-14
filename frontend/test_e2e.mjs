import { chromium } from 'playwright';

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });

const consoleErrors = [];
page.on('console', msg => {
  if (msg.type() === 'error') consoleErrors.push(msg.text());
});
page.on('pageerror', err => consoleErrors.push('PAGE ERROR: ' + err.message));

console.log('=== FULL FLOW: Landing → Career Pick ===\n');

// 1-4: Quick path to career-pick
await page.goto('http://localhost:5173');
await page.waitForLoadState('networkidle');
await page.locator('button:has-text("See where your path leads")').first().click();
await page.waitForTimeout(3000);
await page.locator('button:has-text("Let")').first().click();
await page.waitForTimeout(1500);
await page.locator('input').first().fill('University of Illinois');
await page.waitForTimeout(2000);
await page.locator('[role="option"]').first().click();
await page.waitForTimeout(2000);
await page.locator('input[placeholder*="anything"]').first().fill('Computer Science');
await page.waitForTimeout(500);
await page.locator('button:has-text("→")').first().click();
await page.locator('button:has-text("That\'s right")').waitFor({ timeout: 30000 });
await page.locator('button:has-text("That\'s right")').first().click();
await page.waitForTimeout(2000);
await page.locator('button:has-text("Spec my build")').first().click();
console.log('Clicked "Spec my build", now on:', page.url());

// 5. Wait for career paths to load (outcomes + tier = two API calls + Gemma)
console.log('Waiting for career cards to load (up to 60s)...');
try {
  await page.waitForFunction(() => {
    const body = document.body.innerText;
    return body.includes('Common') || body.includes('error') || body.includes('Error') || body.includes('Try Again');
  }, { timeout: 60000 });
  console.log('Career data loaded!');
} catch {
  console.log('TIMEOUT: career data never loaded');
}

await page.screenshot({ path: '/private/tmp/ss_career_pick_loaded.png', fullPage: true });
console.log('URL:', page.url());
const body = await page.locator('body').innerText();
console.log('Body (first 1200):', body.slice(0, 1200));

if (consoleErrors.length > 0) {
  console.log('\n--- Console Errors ---');
  for (const e of consoleErrors) console.log('  ERROR:', e);
}

await browser.close();
