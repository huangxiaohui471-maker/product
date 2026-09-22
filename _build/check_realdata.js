/* 用真实云表数据（119 条真实 + 40 条示例）驱动页面，验证在线模式下的渲染与计算 */
const { chromium } = require('playwright');
const fs = require('fs');
const DIR = '/Users/huizidemac/WorkBuddy/2026-09-19-21-23-47';
const P = DIR + '/全球选品平台.html';
const F = 'file://' + encodeURIComponent(P).replace(/%2F/g, '/');

const schema = JSON.parse(fs.readFileSync(DIR + '/_build/schema_platform.json', 'utf8'));
const cloud = JSON.parse(fs.readFileSync(DIR + '/_build/data/cloud_after.json', 'utf8'));
const rows = cloud.results || [];
console.log('注入云数据 ' + rows.length + ' 条');

(async () => {
  const errs = [];
  const browser = await chromium.launch({ channel: 'chrome', args: ['--no-sandbox'] });
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 980 } });
  await ctx.addInitScript(({ schema, rows }) => {
    window.__SMART_PAGE__ = {
      database: {
        getSchema: () => Promise.resolve(schema),
        query: () => Promise.resolve({ results: rows, nextCursor: null, hasMore: false }),
        addRecord: () => Promise.resolve({ id: 'n1' }),
        updateRecord: () => Promise.resolve({}),
        deleteRecord: () => Promise.resolve({}),
        onUpdated: () => { }
      }
    };
  }, { schema, rows });

  const page = await ctx.newPage();
  page.on('pageerror', e => errs.push('PAGEERROR ' + e.message));
  page.on('console', m => { if (m.type() === 'error') errs.push('C:' + m.text()); });
  await page.goto(F);
  await page.waitForTimeout(2500);

  const board = await page.evaluate(() => {
    const txt = (document.body.innerText || '');
    const grab = (sel) => [...document.querySelectorAll(sel)].map(e => (e.innerText || '').trim());
    return {
      sync: (document.querySelector('#syncText') || {}).textContent,
      onlineBtnShown: !!((document.querySelector('#btnOnline') || {}).offsetParent),
      kpi: grab('#view .kpi-v, #view [class*=kpi-v]').slice(0, 8),
      chips: grab('#chips *').filter(t => t && t.length < 24).slice(0, 14),
      flow: grab('#view .mk-r .badge').slice(0, 6),
      covCells: document.querySelectorAll('#view .cov .cell').length,
      covZero: document.querySelectorAll('#view .cov .cell.z').length
    };
  });
  console.log('BOARD ' + JSON.stringify(board, null, 1));
  await page.screenshot({ path: DIR + '/_build/shot_real_board.png', fullPage: false });

  const nav = await page.evaluate(() => [...document.querySelectorAll('#nav *')].map(e => (e.innerText || '').trim()).filter(t => t && t.length < 12).slice(0, 10));
  console.log('NAV ' + JSON.stringify(nav));

  const c = await page.evaluate(() => {
    const t = (document.body.innerText || '');
    return { text: t.replace(/\s+/g, ' ').slice(0, 400) };
  });
  console.log('TEXT ' + c.text);

  console.log('ERRORS ' + JSON.stringify(errs.slice(0, 6)));
  await browser.close();
})();
