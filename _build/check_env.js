/* 验收：本机打开 vs 线上通道，环境提示与线上版入口 */
const { chromium } = require('playwright');
const fs = require('fs');
const P = '/Users/huizidemac/WorkBuddy/2026-09-19-21-23-47/全球选品平台.html';
const F = 'file://' + encodeURIComponent(P).replace(/%2F/g, '/');
const log = (...a) => console.log(...a);

const read = (page) => page.evaluate(() => {
  const t = document.querySelector('#syncText');
  const b = document.querySelector('#btnOnline');
  return {
    sync: t ? t.textContent.trim() : null,
    dot: document.querySelector('#syncDot') ? document.querySelector('#syncDot').className : null,
    btnShown: !!(b && b.offsetParent !== null),
    btnText: b ? b.textContent.trim() : null
  };
});

(async () => {
  const errs = [];
  const browser = await chromium.launch({ channel: 'chrome', args: ['--no-sandbox'] });

  /* A. 本机文件打开 */
  const c1 = await browser.newContext({ viewport: { width: 1440, height: 940 } });
  const p1 = await c1.newPage();
  p1.on('pageerror', e => errs.push('A PAGEERROR ' + e.message));
  p1.on('console', m => { if (m.type() === 'error') errs.push('A C:' + m.text()); });
  await p1.goto(F);
  await p1.evaluate(() => localStorage.clear());
  await p1.reload();
  await p1.waitForTimeout(1400);
  log('A_LOCAL ' + JSON.stringify(await read(p1)));
  await p1.screenshot({ path: '/Users/huizidemac/WorkBuddy/2026-09-19-21-23-47/_build/shot_env_local.png' });

  /* 更多面板措辞 */
  await p1.click('#btnMore');
  await p1.waitForTimeout(500);
  const hint = await p1.evaluate(() => (document.querySelector('#modal .hint') || {}).textContent || '');
  log('A_HINT ' + hint.trim().slice(0, 90));
  const a2 = await p1.evaluate(() => {
    const b = document.querySelector('#btnOnline2');
    return { exists: !!b, shown: !!(b && b.offsetParent !== null), text: b ? b.textContent.trim() : null };
  });
  log('A_MODAL_BTN ' + JSON.stringify(a2));
  await p1.screenshot({ path: '/Users/huizidemac/WorkBuddy/2026-09-19-21-23-47/_build/shot_env_more.png' });
  await p1.keyboard.press('Escape');
  await p1.waitForTimeout(400);

  /* A3. 手机窄屏（侧栏收起）也能从「更多操作」进线上版 */
  await p1.setViewportSize({ width: 430, height: 900 });
  await p1.waitForTimeout(400);
  await p1.click('#btnMore');
  await p1.waitForTimeout(500);
  const a3 = await p1.evaluate(() => {
    const b = document.querySelector('#btnOnline2');
    return { shown: !!(b && b.offsetParent !== null), text: b ? b.textContent.trim() : null };
  });
  log('A3_MOBILE_MODAL ' + JSON.stringify(a3));
  await p1.screenshot({ path: '/Users/huizidemac/WorkBuddy/2026-09-19-21-23-47/_build/shot_env_mobile.png' });

  /* B. 模拟线上通道（等同在线页面被注入 database） */
  const sch = JSON.parse(fs.readFileSync('/Users/huizidemac/WorkBuddy/2026-09-19-21-23-47/_build/schema_platform.json', 'utf8'));
  const c2 = await browser.newContext({ viewport: { width: 430, height: 900 } });
  await c2.addInitScript(({ sch }) => {
    const rows = [];
    for (let i = 0; i < 6; i++) rows.push({ _id: 'x' + i, '商品名称': '线上商品' + (i + 1), '市场': null, '价格': 100 + i });
    window.__SMART_PAGE__ = { database: {
      getSchema: () => Promise.resolve(sch),
      query: () => Promise.resolve({ results: rows, nextCursor: null, hasMore: false }),
      addRecord: () => Promise.resolve({ id: 'n1' }),
      updateRecord: () => Promise.resolve({}),
      deleteRecord: () => Promise.resolve({}),
      onUpdated: () => {}
    }};
  }, { sch });
  const p2 = await c2.newPage();
  p2.on('pageerror', e => errs.push('B PAGEERROR ' + e.message));
  p2.on('console', m => { if (m.type() === 'error') errs.push('B C:' + m.text()); });
  await p2.goto(F);
  await p2.waitForTimeout(1600);
  log('B_ONLINE ' + JSON.stringify(await read(p2)));
  await p2.screenshot({ path: '/Users/huizidemac/WorkBuddy/2026-09-19-21-23-47/_build/shot_env_online.png' });

  log('ERRORS ' + JSON.stringify(errs));
  await browser.close();
})();
