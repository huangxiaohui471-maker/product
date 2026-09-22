/* 诊断：本地打开 vs 在线页面，资料库通道是否激活 */
const { chromium } = require('playwright');
const LOCAL = 'file://' + encodeURIComponent('/Users/huizidemac/WorkBuddy/2026-09-19-21-23-47/全球选品平台.html').replace(/%2F/g, '/');
const ONLINE = 'https://www.workbuddy.cn/space/d/lMO9EIAM8o5cIwqudwUDr1';
const log = (...a) => console.log(...a);

async function probe(page, label) {
  const r = await page.evaluate(() => {
    const t = document.querySelector('#syncText');
    return {
      sync: t ? t.textContent.trim() : '(无)',
      hasSmartPage: typeof window.__SMART_PAGE__ !== 'undefined',
      hasDb: !!(window.__SMART_PAGE__ && window.__SMART_PAGE__.database),
      proto: location.protocol,
      host: location.host,
      title: document.title,
      cards: document.querySelectorAll('.pcard, .card-p, [data-rid]').length,
      listTxt: (document.body.innerText.match(/共\s*\d+\s*条|已收录[^。\n]*/g) || []).slice(0, 3)
    };
  });
  log('=== ' + label + ' ===');
  log(JSON.stringify(r, null, 1));
}

(async () => {
  const browser = await chromium.launch({ channel: 'chrome', args: ['--no-sandbox'] });
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 960 } });

  const p1 = await ctx.newPage();
  await p1.goto(LOCAL);
  await p1.waitForTimeout(1500);
  await probe(p1, '本地文件 file://');

  const p2 = await ctx.newPage();
  try {
    await p2.goto(ONLINE, { waitUntil: 'domcontentloaded', timeout: 45000 });
    await p2.waitForTimeout(6000);
    await probe(p2, '在线链接');
    log('URL_NOW ' + p2.url());
  } catch (e) {
    log('ONLINE_FAIL ' + e.message);
  }

  await browser.close();
})();
