/* 用真实云表数据（186 条真实 + 40 条示例）驱动页面，验证渲染 / 计算 / 洞察 */
const { chromium } = require('playwright');
const fs = require('fs');
const DIR = '/Users/huizidemac/WorkBuddy/2026-09-19-21-23-47';
const P = DIR + '/全球选品平台.html';
const F = 'file://' + encodeURIComponent(P).replace(/%2F/g, '/');

const schema = JSON.parse(fs.readFileSync(DIR + '/_build/schema_platform.json', 'utf8'));
const cloud = JSON.parse(fs.readFileSync(DIR + '/_build/data/cloud_after_v3.json', 'utf8'));
const rows = Array.isArray(cloud) ? cloud : (cloud.results || []);
console.log('注入云数据 ' + rows.length + ' 条（真实 ' + rows.filter(r => r['数据标记'] === '真实').length + '）');

(async () => {
  const errs = [];
  const browser = await chromium.launch({ channel: 'chrome', args: ['--no-sandbox'] });
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
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
  await page.waitForTimeout(2600);

  const out = await page.evaluate(() => {
    const txt = (document.body.innerText || '').replace(/\s+/g, ' ');
    const grab = s => [...document.querySelectorAll(s)].map(e => (e.innerText || '').trim());
    return {
      sync: (document.querySelector('#syncText') || {}).textContent,
      onlineBtnShown: !!((document.querySelector('#btnOnline') || {}).offsetParent),
      kpi: grab('#view [class*=kpi]').slice(0, 10),
      covZero: document.querySelectorAll('#view .cov .cell.z').length,
      covAll: document.querySelectorAll('#view .cov .cell').length,
      text400: txt.slice(0, 360)
    };
  });
  console.log('BOARD ' + JSON.stringify(out, null, 1));

  // 切到「机会洞察」
  const nav = await page.evaluate(() => [...document.querySelectorAll('#nav *')].map(e => (e.innerText || '').trim()).filter(t => t && t.length < 14));
  console.log('NAV ' + JSON.stringify(nav.slice(0, 12)));

  const clicked = await page.evaluate(() => {
    const b = [...document.querySelectorAll('button,a,div,span')].find(e => (e.innerText || '').trim() === '机会洞察');
    if (b) { b.click(); return true; }
    return false;
  });
  await page.waitForTimeout(1600);
  const ins = await page.evaluate(() => {
    const t = (document.body.innerText || '').replace(/\s+/g, ' ');
    const grab = s => [...document.querySelectorAll(s)].map(e => (e.innerText || '').trim());
    return { clicked: true, cards: grab('#view [class*=ins]').slice(0, 16), text: t.slice(0, 900) };
  });
  console.log('INSIGHT clicked=' + clicked + ' ' + JSON.stringify(ins, null, 1).slice(0, 2200));

  await page.screenshot({ path: DIR + '/_build/shot_v3_insight.png', fullPage: false });
  console.log('ERRORS ' + JSON.stringify(errs.slice(0, 6)));
  await browser.close();
})();
