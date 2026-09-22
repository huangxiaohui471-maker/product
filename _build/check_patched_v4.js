const { chromium } = require('playwright');
const fs = require('fs');
const DIR = '/Users/huizidemac/WorkBuddy/2026-09-19-21-23-47';
const schema = JSON.parse(fs.readFileSync(DIR + '/_build/schema_platform.json', 'utf8'));
const cloud = JSON.parse(fs.readFileSync(DIR + '/_build/data/cloud_after_v4.json', 'utf8'));
const rows = Array.isArray(cloud) ? cloud : (cloud.results || []);
(async () => {
  const errs = [];
  const b = await chromium.launch({ channel: 'chrome', args: ['--no-sandbox'] });
  const ctx = await b.newContext({ viewport: { width: 1440, height: 1000 } });
  await ctx.addInitScript(({ schema, rows }) => {
    window.__SMART_PAGE__ = { database: {
      getSchema: () => Promise.resolve(schema),
      query: () => Promise.resolve({ results: rows, nextCursor: null, hasMore: false }),
      addRecord: () => Promise.resolve({ id: 'n1' }), updateRecord: () => Promise.resolve({}),
      deleteRecord: () => Promise.resolve({}), onUpdated: () => {} } };
  }, { schema, rows });
  const p = await ctx.newPage();
  p.on('pageerror', e => errs.push('PAGEERROR ' + e.message));
  p.on('console', m => { if (m.type() === 'error' && !/inject\.js|Failed to load|net::/.test(m.text())) errs.push('C:' + m.text()); });
  await p.goto('file:///Users/huizidemac/WorkBuddy/2026-09-19-21-23-47/_build/.page_tmp/index.html');
  await p.waitForTimeout(2500);
  // 切到「机会洞察」视图
  await p.evaluate(() => {
    const items = [...document.querySelectorAll('*')].filter(e => (e.innerText || '').trim() === '机会洞察' && e.children.length === 0);
    if (items.length) { (items[items.length - 1]).click(); return true; }
    const alt = [...document.querySelectorAll('[data-v],button,a,li')].find(e => /机会洞察/.test(e.innerText || ''));
    if (alt) alt.click();
    return false;
  });
  await p.waitForTimeout(1200);
  const r = await p.evaluate(() => {
    const t = (document.body.innerText || '').replace(/\s+/g, ' ');
    const cards = [...document.querySelectorAll('.card')].map(e => (e.innerText || '').replace(/\s+/g, ' '));
    const pick = (kw) => { const c = cards.find(x => x.includes(kw)); return c ? c.slice(0, 150) : null; };
    const chips = [...document.querySelectorAll('#chips button')].map(e => (e.innerText || '').trim());
    return { sync: (document.querySelector('#syncText') || {}).textContent,
             onlineBtnShown: !!((document.querySelector('#btnOnline') || {}).offsetParent),
             chips: chips,
             win: pick('窗口期商品'), fix: pick('改良机会'), risk: pick('风险提醒'),
             health: pick('引擎体检') };
  });
  console.log('V5 ' + JSON.stringify(r));
  console.log('ERRORS ' + JSON.stringify(errs.slice(0, 6)));
  await b.close();
})();
