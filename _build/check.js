const { chromium } = require('playwright-core');
(async () => {
  const errs = [];
  let browser;
  try {
    browser = await chromium.launch({ args: ['--no-sandbox','--disable-dev-shm-usage'] });
  } catch (e) { console.log('LAUNCH_FAIL ' + e.message); process.exit(2); }
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  page.on('console', m => { if (m.type() === 'error') errs.push(m.text()); });
  page.on('pageerror', e => errs.push('PAGEERROR ' + e.message));
  await page.goto('file:///Users/huizidemac/WorkBuddy/2026-09-19-21-23-47/美妆情报台.html');
  await page.waitForTimeout(900);
  await page.screenshot({ path: '_build/shot_pc.png', fullPage: true });
  const info = await page.evaluate(() => ({
    nav: document.querySelectorAll('#nav .nav-item').length,
    tabs: document.querySelectorAll('#tabbar .tab').length,
    today: document.querySelectorAll('#todayList .today-row').length,
    cards: document.querySelectorAll('#intelBody .card').length,
    bannerShown: !document.querySelector('#offBanner').classList.contains('hide'),
    sync: document.querySelector('#syncText').textContent
  }));
  console.log('INFO ' + JSON.stringify(info));
  console.log('ERRORS ' + JSON.stringify(errs));
  await browser.close();
})();
