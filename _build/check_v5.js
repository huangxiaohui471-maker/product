const { chromium } = require('playwright');
const fs = require('fs');
const DIR = '/Users/huizidemac/WorkBuddy/2026-09-19-21-23-47';
const schema = JSON.parse(fs.readFileSync(DIR + '/_build/schema_platform.json', 'utf8'));
const cloud = JSON.parse(fs.readFileSync(DIR + '/_build/data/cloud_after_v3.json', 'utf8'));
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
  await p.goto('file:///tmp/v5.html');
  await p.waitForTimeout(2500);
  const r = await p.evaluate(() => {
    const t = (document.body.innerText || '').replace(/\s+/g, ' ');
    return { sync: (document.querySelector('#syncText') || {}).textContent,
             onlineBtnShown: !!((document.querySelector('#btnOnline') || {}).offsetParent),
             n: (t.match(/(\d+) 个商品/) || [])[1],
             scrProbe: t.indexOf('环比增速（商品榜单不提供）') >= 0 || document.documentElement.innerHTML.indexOf('环比增速（商品榜单不提供）') >= 0,
             fmProbe: document.documentElement.innerHTML.indexOf('游客态前 2 页免费') >= 0 };
  });
  console.log('V5 ' + JSON.stringify(r));
  console.log('ERRORS ' + JSON.stringify(errs.slice(0, 6)));
  await b.close();
})();
